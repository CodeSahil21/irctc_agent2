"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils/cn";

const QUICK_PROMPTS = [
  "Check PNR status for 4815162342",
  "Trains from Ahmedabad to Delhi tomorrow",
  "Seat availability in Rajdhani Express",
];

export function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (value: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!value.trim() || disabled) return;
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
    <div className="border-t border-rail-line px-5 py-4">
      <div className="mb-3 flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={disabled}
            onClick={() => onSend(prompt)}
            className="rounded-full border border-rail-line px-3 py-1 text-[11px] text-rail-muted transition-colors hover:border-rail-amber/50 hover:text-rail-amber disabled:opacity-40"
          >
            {prompt}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="flex items-end gap-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={
            disabled ? "Reconnecting to the platform…" : "Ask about PNR, trains, or seats…"
          }
          className="max-h-32 min-h-[44px] flex-1 resize-none rounded-lg border border-rail-line bg-rail-panel px-3.5 py-2.5 text-[13.5px] text-rail-text placeholder:text-rail-muted focus:border-rail-amber/60 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className={cn(
            "flex h-[44px] shrink-0 items-center justify-center rounded-lg border border-rail-amberDim bg-rail-amber/15 px-4 font-display text-[12px] uppercase tracking-wide text-rail-amber transition-colors",
            "hover:bg-rail-amber/25 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-rail-amber/15"
          )}
        >
          Send
        </button>
      </form>
    </div>
  );
}
