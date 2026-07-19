import prisma, { Prisma } from "../prisma";
import { AppError } from "./errors";

// Sanitize input at the logger level — strips newlines from all string values (CWE-117)
function sanitizeForLog(value: unknown): unknown {
  if (typeof value === "string") return value.replace(/[\r\n\t]/g, " ").slice(0, 500);
  if (Array.isArray(value)) return value.map(sanitizeForLog);
  if (typeof value === "object" && value !== null)
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([k, v]) => [k, sanitizeForLog(v)]));
  return value;
}

export async function logToolExecution<T>(
  toolName: string,
  input: object,
  fn: () => Promise<T>,
  options?: { userId?: string; requestId?: string; sessionId?: string; statusCode?: number }
): Promise<T> {
  const start = Date.now();
  let output: T | undefined;
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
    throw err;
  } finally {
    await prisma.toolExecution.create({
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
    });
  }
}
