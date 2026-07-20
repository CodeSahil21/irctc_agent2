"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils/cn";

const QUICK_PROMPTS = [
  "Check PNR status for 4815162342",
  "Trains from Ahmedabad to Delhi tomorrow",
  "Seat availability in Rajdhani Express",
] as const;

interface MessageInputProps {
  onSend: (value: string) => void;
  disabled: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [value, setValue] = useState("");
  const canSend = !disabled && value.trim().length > 0;

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!canSend) return;
    onSend(value);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div
      className="px-5 py-4 border-t"
      style={{ borderColor: "rgba(245,176,66,0.08)", background: "rgba(8,12,24,0.4)" }}
    >
      {/* Quick prompts */}
      <div className="mb-3 flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={disabled}
            onClick={() => onSend(prompt)}
            className="rounded-full px-3 py-1 text-[11px] font-display tracking-wide transition-all duration-200 disabled:opacity-30"
            style={{
              background: "rgba(245,176,66,0.05)",
              border: "1px solid rgba(245,176,66,0.15)",
              color: "#7a85a0",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(245,176,66,0.12)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(245,176,66,0.4)";
              (e.currentTarget as HTMLButtonElement).style.color = "#f5b042";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(245,176,66,0.05)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(245,176,66,0.15)";
              (e.currentTarget as HTMLButtonElement).style.color = "#7a85a0";
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input row */}
      <form onSubmit={submit} className="flex items-end gap-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={disabled ? "Reconnecting to the platform…" : "Ask about PNR, trains, or seats…"}
          className="flex-1 resize-none rounded-xl px-4 py-3 text-[14px] text-rail-text placeholder:text-rail-muted focus:outline-none disabled:opacity-40 transition-all duration-200"
          style={{
            minHeight: "48px",
            maxHeight: "128px",
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

        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send message"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-30"
          style={{
            background: canSend
              ? "linear-gradient(135deg, #f5b042, #e8960a)"
              : "rgba(245,176,66,0.1)",
            border: canSend ? "1px solid rgba(245,176,66,0.5)" : "1px solid rgba(245,176,66,0.15)",
            boxShadow: canSend ? "0 0 20px rgba(245,176,66,0.35), 0 4px 12px rgba(0,0,0,0.3)" : "none",
            color: canSend ? "#080c18" : "#f5b042",
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-5 w-5"
            aria-hidden
          >
            <path d="M3.478 2.405a.75.75 0 0 0-.926.94l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.405Z" />
          </svg>
        </button>
      </form>
    </div>
  );
}
