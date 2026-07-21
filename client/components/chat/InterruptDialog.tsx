"use client";

import type { InterruptPayload } from "@/types/socket";

interface InterruptDialogProps {
  interrupt: InterruptPayload;
  onConfirm: (approved: boolean) => void;
}

export function InterruptDialog({ interrupt, onConfirm }: InterruptDialogProps) {
  return (
    <div className="mx-5 mb-3 animate-rise">
      <div
        className="rounded-2xl p-4"
        style={{
          background: "linear-gradient(135deg, #1a2540, #141e35)",
          border: "1px solid rgba(245,176,66,0.3)",
          boxShadow: "0 0 24px rgba(245,176,66,0.08)",
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <span
            className="flex h-6 w-6 items-center justify-center rounded-lg text-[11px]"
            style={{ background: "rgba(245,176,66,0.15)", color: "#f5b042" }}
          >
            ⚠
          </span>
          <span
            className="font-display text-[11px] uppercase tracking-widest"
            style={{ color: "#f5b042" }}
          >
            Confirmation Required
          </span>
        </div>

        {/* Prompt text — render markdown-like bold */}
        <p
          className="text-[13px] leading-relaxed mb-4 whitespace-pre-wrap"
          style={{ color: "#c8d0e0" }}
        >
          {interrupt.prompt}
        </p>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onConfirm(true)}
            className="flex-1 rounded-xl py-2 text-[13px] font-semibold transition-all duration-200"
            style={{
              background: "linear-gradient(135deg, #f5b042, #e8960a)",
              color: "#080c18",
              border: "1px solid rgba(245,176,66,0.5)",
              boxShadow: "0 0 16px rgba(245,176,66,0.25)",
            }}
          >
            Confirm
          </button>
          <button
            onClick={() => onConfirm(false)}
            className="flex-1 rounded-xl py-2 text-[13px] font-semibold transition-all duration-200"
            style={{
              background: "rgba(248,113,113,0.08)",
              color: "#f87171",
              border: "1px solid rgba(248,113,113,0.25)",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
