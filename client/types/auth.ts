// Matches Prisma User model fields returned by auth service
export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  createdAt?: string; // only present in /auth/me response
}

export interface AuthErrorResponse {
  error: string;
  code:
    | "VALIDATION_ERROR"
    | "UNAUTHORIZED"
    | "FORBIDDEN"
    | "NOT_FOUND"
    | "CONFLICT"
    | "INTERNAL_ERROR";
}

// POST /auth/register body
export interface RegisterBody {
  email: string;
  password: string;
  name?: string;
}

// POST /auth/login body
export interface LoginBody {
  email: string;
  password: string;
}

// POST /auth/register → 201 { user }
// POST /auth/login    → 200 { user }
export interface AuthResponse {
  user: AuthUser;
}

// GET /auth/me → 200 { user }
export interface MeResponse {
  user: AuthUser;
}

// POST /auth/refresh | /auth/logout | /auth/logout-all → { ok: true }
export interface OkResponse {
  ok: true;
}
