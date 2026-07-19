import jwt from "jsonwebtoken";
import crypto from "crypto";
import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL ?? "redis://localhost:6380");
redis.on("error", (err) => console.error("Redis error:", err.message.replace(/[\r\n]/g, " ")));

const ACCESS_SECRET  = process.env.ACCESS_TOKEN_SECRET!;
const REFRESH_SECRET = process.env.REFRESH_TOKEN_SECRET!;
const ACCESS_EXPIRY  = process.env.ACCESS_TOKEN_EXPIRY  ?? "15m";
const REFRESH_TOKEN_TTL_MS = parseInt(process.env.REFRESH_TOKEN_TTL_MS ?? String(7 * 24 * 60 * 60 * 1000));

// Access token TTL in seconds for Redis blacklist — must match ACCESS_TOKEN_EXPIRY
const ACCESS_TOKEN_TTL_SECONDS = parseInt(process.env.ACCESS_TOKEN_TTL_SECONDS ?? "900");

export { REFRESH_TOKEN_TTL_MS };

export interface TokenPayload {
  userId: string;
  email: string;
  name?: string;
}

// ── Access token ──────────────────────────────────────────────────────────────

export function signAccessToken(payload: TokenPayload): string {
  return jwt.sign(payload, ACCESS_SECRET, { expiresIn: ACCESS_EXPIRY } as jwt.SignOptions);
}

export function verifyAccessToken(token: string): TokenPayload {
  return jwt.verify(token, ACCESS_SECRET) as TokenPayload;
}

// ── Refresh token ─────────────────────────────────────────────────────────────

export function signRefreshToken(payload: TokenPayload): string {
  return jwt.sign(payload, REFRESH_SECRET, { expiresIn: process.env.REFRESH_TOKEN_EXPIRY ?? "7d" } as jwt.SignOptions);
}

export function verifyRefreshToken(token: string): TokenPayload {
  return jwt.verify(token, REFRESH_SECRET) as TokenPayload;
}

export function refreshTokenExpiresAt(): Date {
  return new Date(Date.now() + REFRESH_TOKEN_TTL_MS);
}

// ── Token hash (for DB storage — never store raw refresh token) ───────────────

export function hashToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

// ── Redis blacklist (for logged-out access tokens) ────────────────────────────

export async function blacklistAccessToken(token: string): Promise<void> {
  const key = `blacklist:${hashToken(token)}`;
  await redis.set(key, "1", "EX", ACCESS_TOKEN_TTL_SECONDS);
}

export async function isAccessTokenBlacklisted(token: string): Promise<boolean> {
  const key = `blacklist:${hashToken(token)}`;
  const val = await redis.get(key);
  return val !== null;
}
