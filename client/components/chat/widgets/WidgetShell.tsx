"use client";

import type { ReactNode } from "react";

const SHELL_STYLE = {
  background: "rgba(11,17,32,0.95)",
  border: "1px solid rgba(42,61,92,0.8)",
} as const;

const SUBMITTED_STYLE = {
  background: "rgba(245,176,66,0.06)",
  border: "1px solid rgba(245,176,66,0.15)",
  color: "#f5b042",
} as const;

interface WidgetShellProps {
  label: string;
  submitted: boolean;
  children: ReactNode;
}

export function WidgetShell({ label, submitted, children }: WidgetShellProps) {
  if (submitted) {
    return (
      <div className="mt-3 rounded-xl px-4 py-2 text-xs font-display tracking-wide" style={SUBMITTED_STYLE}>
        ✓ {label} confirmed
      </div>
    );
  }

  return (
    <div className="mt-3 w-full max-w-sm rounded-2xl overflow-hidden" style={SHELL_STYLE}>
      <div
        className="px-4 py-2.5 border-b"
        style={{ borderColor: "rgba(42,61,92,0.6)", background: "rgba(245,176,66,0.03)" }}
      >
        <span className="text-[11px] font-display tracking-widest uppercase" style={{ color: "#f5b042" }}>
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

interface ConfirmButtonProps {
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}

export function ConfirmButton({ onClick, disabled, children }: ConfirmButtonProps) {
  return (
    <div className="px-3 pb-3">
      <button
        onClick={onClick}
        disabled={disabled}
        className="w-full rounded-xl py-2.5 text-xs font-display tracking-widest uppercase transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
        style={{
          background: disabled ? "rgba(245,176,66,0.08)" : "linear-gradient(135deg,#f5b042,#e8960a)",
          color: disabled ? "#f5b042" : "#080c18",
          boxShadow: disabled ? "none" : "0 0 16px rgba(245,176,66,0.3)",
        }}
      >
        {children}
      </button>
    </div>
  );
}
