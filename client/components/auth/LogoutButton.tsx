"use client";

import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { logoutUser } from "@/store/slices/authSlice";

export default function LogoutButton() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);

  const handleLogout = async () => {
    await dispatch(logoutUser());
    router.push("/auth/signin");
  };

  if (!user) return null;

  return (
    <div className="flex items-center gap-3">
      {/* User badge — mirrors Avatar style */}
      <div
        className="flex items-center gap-2 rounded-xl px-3 py-1.5"
        style={{
          background: "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(99,102,241,0.05))",
          border: "1px solid rgba(99,102,241,0.25)",
        }}
      >
        <div
          className="flex h-5 w-5 items-center justify-center rounded-md font-display text-[9px] font-semibold tracking-wider shrink-0"
          style={{
            background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(99,102,241,0.1))",
            border: "1px solid rgba(99,102,241,0.3)",
            color: "#a5b4fc",
          }}
        >
          {(user.name ?? user.email).slice(0, 2).toUpperCase()}
        </div>
        <span className="text-[12px] font-display tracking-wide" style={{ color: "#a5b4fc" }}>
          {user.name ?? user.email}
        </span>
      </div>

      {/* Sign out button */}
      <button
        onClick={handleLogout}
        className="rounded-xl px-4 py-1.5 text-[12px] font-display tracking-widest uppercase transition-all duration-200"
        style={{
          background: "rgba(248,113,113,0.05)",
          border: "1px solid rgba(248,113,113,0.2)",
          color: "#7a85a0",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(248,113,113,0.1)";
          e.currentTarget.style.borderColor = "rgba(248,113,113,0.5)";
          e.currentTarget.style.color = "#fca5a5";
          e.currentTarget.style.boxShadow = "0 0 12px rgba(248,113,113,0.15)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "rgba(248,113,113,0.05)";
          e.currentTarget.style.borderColor = "rgba(248,113,113,0.2)";
          e.currentTarget.style.color = "#7a85a0";
          e.currentTarget.style.boxShadow = "none";
        }}
      >
        Sign out
      </button>
    </div>
  );
}
