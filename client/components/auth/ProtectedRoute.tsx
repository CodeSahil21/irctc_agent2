"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/store/hooks";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, initialized } = useAppSelector((s) => s.auth);

  useEffect(() => {
    if (initialized && !user) {
      router.replace("/auth/signin");
    }
  }, [initialized, user, router]);

  if (!initialized) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          {/* Logo badge */}
          <div
            className="flex h-12 w-12 items-center justify-center rounded-xl font-display text-base font-semibold"
            style={{
              background: "linear-gradient(135deg, rgba(245,176,66,0.2), rgba(245,176,66,0.05))",
              border: "1px solid rgba(245,176,66,0.3)",
              boxShadow: "0 0 24px rgba(245,176,66,0.2), inset 0 1px 0 rgba(255,255,255,0.06)",
              color: "#f5b042",
            }}
          >
            IR
          </div>
          <div className="flex items-center gap-2">
            <span
              className="animate-pulse-soft text-[11px] font-display tracking-widest uppercase"
              style={{ color: "#f5b042", textShadow: "0 0 8px rgba(245,176,66,0.8)" }}
            >
              ●
            </span>
            <span className="text-[11px] font-display tracking-widest uppercase text-rail-muted">
              Checking session…
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
