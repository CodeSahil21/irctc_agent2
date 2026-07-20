"use client";

import type { QuickReplyWidget } from "@/types/chat";
import { WidgetShell } from "./WidgetShell";

interface Props {
  widget: QuickReplyWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function QuickReplyWidgetCard({ widget, onSubmit, submitted }: Props) {
  return (
    <WidgetShell label={widget.label} submitted={submitted}>
      <div className="flex flex-col gap-px p-2">
        {widget.options.map((opt, i) => (
          <button
            key={opt}
            onClick={() => onSubmit(opt)}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm transition-all duration-150"
            style={{
              background: "transparent",
              color: "#edf1fa",
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.background = "rgba(245,176,66,0.08)";
              el.style.color = "#f5b042";
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.background = "transparent";
              el.style.color = "#edf1fa";
            }}
          >
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ background: "#f5b042", boxShadow: "0 0 6px rgba(245,176,66,0.6)" }}
            />
            {opt}
          </button>
        ))}
      </div>
    </WidgetShell>
  );
}
