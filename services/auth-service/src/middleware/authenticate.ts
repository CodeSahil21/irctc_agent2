import { Request, Response, NextFunction } from "express";
import { verifyAccessToken, isAccessTokenBlacklisted } from "../services/token.service";
import { UnauthorizedError } from "../utils/errors";

export interface AuthRequest extends Request {
  user?: { userId: string; email: string; name?: string };
  accessToken?: string;
}

export async function authenticate(req: AuthRequest, res: Response, next: NextFunction) {
  try {
    const token = req.cookies?.access_token;
    if (!token) throw new UnauthorizedError("Missing access token");

    // Check Redis blacklist first (logged out tokens)
    const blacklisted = await isAccessTokenBlacklisted(token);
    if (blacklisted) throw new UnauthorizedError("Token has been revoked");

    const payload = verifyAccessToken(token);
    req.user = { userId: payload.userId, email: payload.email, name: payload.name };
    req.accessToken = token;

    next();
  } catch (err: any) {
    if (err instanceof UnauthorizedError) {
      res.status(401).json({ error: err.message, code: err.code });
    } else {
      // jwt.verify throws JsonWebTokenError / TokenExpiredError
      res.status(401).json({ error: "Invalid or expired token", code: "UNAUTHORIZED" });
    }
  }
}
