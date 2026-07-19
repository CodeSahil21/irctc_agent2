import { Request, Response } from "express";
import { z } from "zod";
import * as authService from "../services/auth.service";
import { AppError } from "../utils/errors";
import { AuthRequest } from "../middleware/authenticate";
import { REFRESH_TOKEN_TTL_MS } from "../services/token.service";

// Cookie config
const COOKIE_BASE = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
};

function setTokenCookies(res: Response, accessToken: string, refreshToken: string) {
  res.cookie("access_token", accessToken, {
    ...COOKIE_BASE,
    maxAge: 15 * 60 * 1000, // 15 min
  });
  res.cookie("refresh_token", refreshToken, {
    ...COOKIE_BASE,
    maxAge: REFRESH_TOKEN_TTL_MS,
  });
}

function clearTokenCookies(res: Response) {
  res.clearCookie("access_token", COOKIE_BASE);
  res.clearCookie("refresh_token", COOKIE_BASE);
}

// ── Register ──────────────────────────────────────────────────────────────────

const RegisterSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "Password must be at least 8 characters"),
  name: z.string().optional(),
});

export async function register(req: Request, res: Response) {
  try {
    const { email, password, name } = RegisterSchema.parse(req.body);
    const result = await authService.register(email, password, name);
    setTokenCookies(res, result.accessToken, result.refreshToken);
    res.status(201).json({ user: result.user });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Login ─────────────────────────────────────────────────────────────────────

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export async function login(req: Request, res: Response) {
  try {
    const { email, password } = LoginSchema.parse(req.body);
    const result = await authService.login(email, password);
    setTokenCookies(res, result.accessToken, result.refreshToken);
    res.json({ user: result.user });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Refresh ───────────────────────────────────────────────────────────────────

export async function refresh(req: Request, res: Response) {
  try {
    const refreshToken = req.cookies?.refresh_token;
    if (!refreshToken) {
      res.status(401).json({ error: "Missing refresh token", code: "UNAUTHORIZED" });
      return;
    }
    const result = await authService.refresh(refreshToken);
    setTokenCookies(res, result.accessToken, result.refreshToken);
    res.json({ ok: true });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────

export async function logout(req: AuthRequest, res: Response) {
  try {
    const refreshToken = req.cookies?.refresh_token;
    await authService.logout(req.accessToken!, refreshToken);
    clearTokenCookies(res);
    res.json({ ok: true });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Logout all devices ────────────────────────────────────────────────────────

export async function logoutAll(req: AuthRequest, res: Response) {
  try {
    await authService.logoutAll(req.user!.userId, req.accessToken!);
    clearTokenCookies(res);
    res.json({ ok: true });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Me ────────────────────────────────────────────────────────────────────────

export async function me(req: AuthRequest, res: Response) {
  try {
    const user = await authService.getMe(req.user!.userId);
    res.json({ user });
  } catch (err: any) {
    handleError(err, res);
  }
}

// ── Error handler ─────────────────────────────────────────────────────────────

function handleError(err: any, res: Response) {
  if (err instanceof z.ZodError) {
    res.status(400).json({ error: err.issues[0].message, code: "VALIDATION_ERROR" });
    return;
  }
  if (err instanceof AppError) {
    res.status(err.statusCode).json({ error: err.message, code: err.code });
    return;
  }
  console.error(err instanceof Error ? err.message.replace(/[\r\n]/g, " ") : "Unknown error");
  res.status(500).json({ error: "Internal server error", code: "INTERNAL_ERROR" });
}
