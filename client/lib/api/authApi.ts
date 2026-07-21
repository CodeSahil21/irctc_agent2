import type {
  AuthErrorResponse,
  AuthResponse,
  LoginBody,
  MeResponse,
  OkResponse,
  RegisterBody,
} from "@/types/auth";
import axios from "axios";

// Axios instance — all requests go to auth-service with httpOnly cookies
const authClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_AUTH_URL ?? "http://localhost:4000/auth",
    withCredentials: true, // send/receive httpOnly cookies (access_token, refresh_token)
    headers: { "Content-Type": "application/json" },
});

// Normalise error shape from auth-service { error, code } into a plain Error
authClient.interceptors.response.use(
    (res) => res,
    (err) => {
        const message: string =
            (err.response?.data as AuthErrorResponse)?.error ??
            err.message ??
            "Request failed";
        return Promise.reject(new Error(message));
    },
);

// POST /auth/register → 201 { user }
export const register = (body: RegisterBody) =>
    authClient.post<AuthResponse>("/register", body).then((r) => r.data);

// POST /auth/login → 200 { user }
export const login = (body: LoginBody) =>
    authClient.post<AuthResponse>("/login", body).then((r) => r.data);

// POST /auth/refresh → 200 { ok: true }  (uses refresh_token cookie)
export const refresh = () =>
    authClient.post<OkResponse>("/refresh").then((r) => r.data);

// POST /auth/logout → 200 { ok: true }
export const logout = () =>
    authClient.post<OkResponse>("/logout").then((r) => r.data);

// POST /auth/logout-all → 200 { ok: true }
export const logoutAll = () =>
    authClient.post<OkResponse>("/logout-all").then((r) => r.data);

// GET /auth/me → 200 { user }
export const getMe = () =>
    authClient.get<MeResponse>("/me").then((r) => r.data);
