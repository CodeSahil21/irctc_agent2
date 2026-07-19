import bcrypt from "bcrypt";
import {
  findUserByEmail,
  findUserById,
  createUser,
  saveRefreshToken,
  findRefreshToken,
  deleteRefreshToken,
  deleteAllRefreshTokensForUser,
} from "../repositories/user.repository";
import {
  signAccessToken,
  signRefreshToken,
  verifyRefreshToken,
  hashToken,
  refreshTokenExpiresAt,
  blacklistAccessToken,
} from "./token.service";
import { ConflictError, UnauthorizedError, NotFoundError } from "../utils/errors";

const SALT_ROUNDS = 12;

export async function register(email: string, password: string, name?: string) {
  const existing = await findUserByEmail(email);
  if (existing) throw new ConflictError("Email already registered");

  const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);
  const user = await createUser(email, name, passwordHash);

  const payload = { userId: user.id, email: user.email, name: user.name ?? undefined };
  const accessToken  = signAccessToken(payload);
  const refreshToken = signRefreshToken(payload);

  await saveRefreshToken(user.id, hashToken(refreshToken), refreshTokenExpiresAt());

  return { accessToken, refreshToken, user: { id: user.id, email: user.email, name: user.name } };
}

export async function login(email: string, password: string) {
  const user = await findUserByEmail(email);
  if (!user) throw new UnauthorizedError("Invalid email or password");

  const valid = await bcrypt.compare(password, user.passwordHash);
  if (!valid) throw new UnauthorizedError("Invalid email or password");

  const payload = { userId: user.id, email: user.email, name: user.name ?? undefined };
  const accessToken  = signAccessToken(payload);
  const refreshToken = signRefreshToken(payload);

  await saveRefreshToken(user.id, hashToken(refreshToken), refreshTokenExpiresAt());

  return { accessToken, refreshToken, user: { id: user.id, email: user.email, name: user.name } };
}

export async function refresh(refreshToken: string) {
  // Verify JWT signature first
  let payload;
  try {
    payload = verifyRefreshToken(refreshToken);
  } catch {
    throw new UnauthorizedError("Invalid or expired refresh token");
  }

  // Check token exists in DB (not revoked)
  const stored = await findRefreshToken(hashToken(refreshToken));
  if (!stored || stored.expiresAt < new Date()) {
    throw new UnauthorizedError("Refresh token revoked or expired");
  }

  // Rotate — delete old, issue new
  await deleteRefreshToken(hashToken(refreshToken));

  const newPayload = { userId: payload.userId, email: payload.email, name: payload.name };
  const accessToken     = signAccessToken(newPayload);
  const newRefreshToken = signRefreshToken(newPayload);

  await saveRefreshToken(stored.userId, hashToken(newRefreshToken), refreshTokenExpiresAt());

  return { accessToken, refreshToken: newRefreshToken };
}

export async function logout(accessToken: string, refreshToken?: string) {
  // Blacklist access token in Redis so it can't be reused until expiry
  await blacklistAccessToken(accessToken);

  // Revoke refresh token from DB if provided
  if (refreshToken) {
    await deleteRefreshToken(hashToken(refreshToken));
  }
}

export async function logoutAll(userId: string, accessToken: string) {
  await blacklistAccessToken(accessToken);
  await deleteAllRefreshTokensForUser(userId);
}

export async function getMe(userId: string) {
  const user = await findUserById(userId);
  if (!user) throw new NotFoundError("User");
  return { id: user.id, email: user.email, name: user.name, createdAt: user.createdAt };
}
