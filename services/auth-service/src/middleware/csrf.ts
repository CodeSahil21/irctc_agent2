import { doubleCsrf } from "csrf-csrf";
import type { Request } from "express";

const { doubleCsrfProtection, generateCsrfToken } = doubleCsrf({
  getSecret: () => process.env.CSRF_SECRET ?? process.env.ACCESS_TOKEN_SECRET!,
  getSessionIdentifier: (req: Request) => req.ip ?? "",
  cookieName: "csrf-token-cookie",
  cookieOptions: {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  },
  size: 64,
  getCsrfTokenFromRequest: (req: Request) =>
    (req.headers["x-csrf-token"] as string) ?? req.body?._csrf ?? "",
});

export { doubleCsrfProtection as csrfProtect, generateCsrfToken as generateToken };
