import { Prisma } from "@prisma/client";
import { prisma } from "../prisma";
import { AppError } from "./errors";

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
        output = {
            content: [{ type: "text", text: JSON.stringify({ error: err?.message ?? String(err), code: err?.code ?? "INTERNAL_ERROR" }) }],
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
