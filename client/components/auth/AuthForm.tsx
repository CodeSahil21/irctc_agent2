"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { loginUser, registerUser, clearError } from "@/store/slices/authSlice";

type Mode = "signin" | "signup";

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { status, error } = useAppSelector((s) => s.auth);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const loading = status === "loading";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(clearError());
    const action =
      mode === "signup"
        ? registerUser({ email: form.email, password: form.password, name: form.name || undefined })
        : loginUser({ email: form.email, password: form.password });
    const result = await dispatch(action);
    if (result.meta.requestStatus === "fulfilled") router.push("/");
  };

  return (
    <div
      className="flex h-[100dvh] w-full flex-col md:h-auto md:max-w-md md:rounded-2xl overflow-hidden"
      style={{
        border: "1px solid rgba(245,176,66,0.12)",
        background: "linear-gradient(160deg, #0f1829 0%, #0d1424 60%, #0a1020 100%)",
        boxShadow: "0 32px 80px -16px rgba(0,0,0,0.8), 0 0 0 1px rgba(245,176,66,0.06)",
      }}
    >
      {/* Top accent line */}
      <div
        className="h-[2px] w-full shrink-0"
        style={{ background: "linear-gradient(90deg, transparent, #f5b042, #34d399, transparent)" }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-4 px-6 py-4 border-b"
        style={{
          borderColor: "rgba(245,176,66,0.1)",
          background: "linear-gradient(90deg, rgba(245,176,66,0.04) 0%, transparent 60%)",
        }}
      >
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl font-display text-sm font-semibold shrink-0"
          style={{
            background: "linear-gradient(135deg, rgba(245,176,66,0.2), rgba(245,176,66,0.05))",
            border: "1px solid rgba(245,176,66,0.3)",
            boxShadow: "0 0 16px rgba(245,176,66,0.15), inset 0 1px 0 rgba(255,255,255,0.06)",
            color: "#f5b042",
          }}
        >
          IR
        </div>
        <div>
          <h1 className="font-display text-[15px] tracking-wider text-rail-text font-semibold">
            IRCTC{" "}
            <span
              style={{
                background: "linear-gradient(90deg,#f5b042,#fde68a)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Assist
            </span>
          </h1>
          <p className="text-[11px] font-display tracking-widest uppercase text-rail-muted mt-0.5">
            {mode === "signup" ? "Create account" : "Welcome back"}
          </p>
        </div>
      </div>

      {/* Form body */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
        {mode === "signup" && (
          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-display tracking-widest uppercase text-rail-muted">
              Full name
            </label>
            <input
              type="text"
              placeholder="John Doe"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="rounded-xl px-4 py-3 text-[14px] text-rail-text placeholder:text-rail-muted focus:outline-none transition-all duration-200"
              style={{
                background: "rgba(22,32,53,0.8)",
                border: "1px solid rgba(42,61,92,0.8)",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "rgba(245,176,66,0.5)";
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(245,176,66,0.06)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "rgba(42,61,92,0.8)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] font-display tracking-widest uppercase text-rail-muted">
            Email
          </label>
          <input
            type="email"
            placeholder="you@example.com"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="rounded-xl px-4 py-3 text-[14px] text-rail-text placeholder:text-rail-muted focus:outline-none transition-all duration-200"
            style={{
              background: "rgba(22,32,53,0.8)",
              border: "1px solid rgba(42,61,92,0.8)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "rgba(245,176,66,0.5)";
              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(245,176,66,0.06)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "rgba(42,61,92,0.8)";
              e.currentTarget.style.boxShadow = "none";
            }}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] font-display tracking-widest uppercase text-rail-muted">
            Password
          </label>
          <input
            type="password"
            placeholder="Min. 8 characters"
            required
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="rounded-xl px-4 py-3 text-[14px] text-rail-text placeholder:text-rail-muted focus:outline-none transition-all duration-200"
            style={{
              background: "rgba(22,32,53,0.8)",
              border: "1px solid rgba(42,61,92,0.8)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "rgba(245,176,66,0.5)";
              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(245,176,66,0.06)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "rgba(42,61,92,0.8)";
              e.currentTarget.style.boxShadow = "none";
            }}
          />
        </div>

        {error && (
          <p
            className="rounded-xl px-4 py-2.5 text-[13px]"
            style={{
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.3)",
              color: "#fca5a5",
            }}
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-1 flex h-12 w-full items-center justify-center rounded-xl text-[14px] font-semibold font-display tracking-wide transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40"
          style={{
            background: "linear-gradient(135deg, #f5b042, #e8960a)",
            border: "1px solid rgba(245,176,66,0.5)",
            boxShadow: "0 0 20px rgba(245,176,66,0.35), 0 4px 12px rgba(0,0,0,0.3)",
            color: "#080c18",
          }}
        >
          {loading ? (
            <span className="animate-pulse-soft">Please wait…</span>
          ) : mode === "signup" ? (
            "Create account"
          ) : (
            "Sign in"
          )}
        </button>
      </form>

      {/* Footer */}
      <div
        className="px-6 py-4 border-t text-center"
        style={{ borderColor: "rgba(245,176,66,0.08)", background: "rgba(8,12,24,0.4)" }}
      >
        <p className="text-[12px] text-rail-muted font-display tracking-wide">
          {mode === "signup" ? (
            <>
              Already have an account?{" "}
              <a
                href="/auth/signin"
                className="transition-colors duration-200"
                style={{ color: "#f5b042" }}
                onMouseEnter={(e) => (e.currentTarget.style.textShadow = "0 0 8px rgba(245,176,66,0.8)")}
                onMouseLeave={(e) => (e.currentTarget.style.textShadow = "none")}
              >
                Sign in
              </a>
            </>
          ) : (
            <>
              No account?{" "}
              <a
                href="/auth/signup"
                className="transition-colors duration-200"
                style={{ color: "#f5b042" }}
                onMouseEnter={(e) => (e.currentTarget.style.textShadow = "0 0 8px rgba(245,176,66,0.8)")}
                onMouseLeave={(e) => (e.currentTarget.style.textShadow = "none")}
              >
                Sign up
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
