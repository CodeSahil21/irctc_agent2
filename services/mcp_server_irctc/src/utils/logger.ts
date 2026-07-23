import { Prisma } from "@prisma/client";
import { prisma } from "../prisma";
import { AppError, ValidationError, NotFoundError, ForbiddenError, IrctcError } from "./errors";

/**
 * Maps our typed AppError subclasses to distinct JSON-RPC error codes so MCP
 * clients can distinguish "bad input → retry with fixes" (-32602) from
 * "not found → don't retry" (-32001) from "upstream failure → maybe retry" (-32003).
 *
 * Standard JSON-RPC reserved range:
 *   -32700  Parse error
 *   -32600  Invalid Request
 *   -32601  Method not found
 *   -32602  Invalid params        ← ValidationError
 *   -32603  Internal error        ← unexpected/unhandled
 *
 * Custom range (server-defined, >= -32099):
 *   -32001  Not found             ← NotFoundError
 *   -32002  Forbidden             ← ForbiddenError
 *   -32003  Upstream error        ← IrctcError
 */
function toJsonRpcCode(err: unknown): number {
  if (err instanceof ValidationError)  return -32602; // Invalid params
  if (err instanceof NotFoundError)    return -32001; // Not found
  if (err instanceof ForbiddenError)   return -32002; // Forbidden
  if (err instanceof IrctcError)       return -32003; // Upstream IRCTC error
  return -32603; // Internal error (catch-all)
}

function sanitizeForLog(value: unknown): unknown {
    if (typeof value === "string")
        return value.replace(/[\r\n\t]/g, " ").slice(0, 500);
    if (Array.isArray(value)) return value.map(sanitizeForLog);
    if (typeof value === "object" && value !== null)
        return Object.fromEntries(
            Object.entries(value as Record<string, unknown>).map(([k, v]) => [k, sanitizeForLog(v)]),
        );
    return value;
}

type McpContent = { content: { type: "text"; text: string }[]; isError?: boolean };

export async function logToolExecution(
    toolName: string,
    input: object,
    fn: () => Promise<McpContent>,
    options?: { userId?: string; requestId?: string; sessionId?: string; statusCode?: number },
): Promise<McpContent> {
    const start = Date.now();
    let output: McpContent | undefined;
    let success = true;
    let error: string | undefined;
    let statusCode = options?.statusCode;
    const safeInput = sanitizeForLog(input) as object;

    try {
        output = await fn();
        return output;
    } catch (err: any) {
        success = false;
        error = (err?.message ?? String(err)).replace(/[\r\n]/g, " ").slice(0, 500);
        if (err instanceof AppError) statusCode = err.statusCode;
        const jsonRpcCode = toJsonRpcCode(err);
        output = {
            content: [{ type: "text", text: JSON.stringify({
                error: err?.message ?? String(err),
                code: err?.code ?? "INTERNAL_ERROR",
                jsonRpcCode,
            }) }],
            isError: true,
        };
        return output;
    } finally {
        // fire-and-forget — never let logging crash the tool response
        prisma.toolExecution.create({
            data: {
                toolName,
                userId: options?.userId,
                requestId: options?.requestId,
                sessionId: options?.sessionId,
                statusCode: statusCode ?? null,
                input: safeInput,
                output: output !== undefined ? (output as Prisma.InputJsonValue) : Prisma.JsonNull,
                success,
                error,
                durationMs: Date.now() - start,
            },
        }).catch(() => { /* swallow logging errors */ });
    }
}
