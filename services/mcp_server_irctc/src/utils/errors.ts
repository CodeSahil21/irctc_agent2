export class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

// 404 — resource not found
export class NotFoundError extends AppError {
  constructor(resource: string, identifier?: string) {
    super(
      identifier ? `${resource} '${identifier}' not found` : `${resource} not found`,
      "NOT_FOUND",
      404
    );
  }
}

// 403 — resource exists but belongs to another user
export class ForbiddenError extends AppError {
  constructor(resource: string) {
    super(`${resource} does not belong to this user`, "FORBIDDEN", 403);
  }
}

// 409 — conflict, e.g. duplicate entry
export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, "CONFLICT", 409);
  }
}

// 400 — bad input
export class ValidationError extends AppError {
  constructor(message: string) {
    super(message, "VALIDATION_ERROR", 400);
  }
}

// 503 — upstream IRCTC call not yet implemented
export class NotImplementedError extends AppError {
  constructor(fnName: string) {
    super(`${fnName} is not yet implemented`, "NOT_IMPLEMENTED", 503);
  }
}

// 502 — upstream IRCTC call failed
export class IrctcError extends AppError {
  constructor(message: string) {
    super(message, "IRCTC_ERROR", 502);
  }
}
