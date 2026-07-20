"use client";

import { useState } from "react";
import type { PassengerCountWidget } from "@/types/chat";
import { WidgetShell, ConfirmButton } from "./WidgetShell";

interface Props {
  widget: PassengerCountWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function PassengerCountWidgetCard({ widget, onSubmit, submitted }: Props) {
  const [count, setCount] = useState(widget.min);

  const dec = () => setCount((c) => Math.max(widget.min, c - 1));
  const inc = () => setCount((c) => Math.min(widget.max, c + 1));

  const btnStyle = (active: boolean) => ({
    background: "rgba(22,32,53,0.8)",
    border: `1px solid ${active ? "rgba(245,176,66,0.4)" : "rgba(42,61,92,0.8)"}`,
    color: "#edf1fa",
  });

  return (
    <WidgetShell label={widget.label} submitted={submitted}>
      <div className="flex items-center justify-between px-6 py-5">
        <button
          onClick={dec}
          disabled={count <= widget.min}
          className="flex h-11 w-11 items-center justify-center rounded-xl text-xl font-bold transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-25"
          style={btnStyle(false)}
          onMouseEnter={(e) => { if (count > widget.min) (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(245,176,66,0.4)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(42,61,92,0.8)"; }}
        >
          −
        </button>

        <div className="flex flex-col items-center gap-1">
          <span
            className="font-display text-5xl font-semibold tabular-nums"
            style={{ color: "#f5b042", textShadow: "0 0 24px rgba(245,176,66,0.4)" }}
          >
            {count}
          </span>
          <span className="font-display text-[10px] uppercase tracking-wider text-rail-muted">
            {count === 1 ? "passenger" : "passengers"}
          </span>
        </div>

        <button
          onClick={inc}
          disabled={count >= widget.max}
          className="flex h-11 w-11 items-center justify-center rounded-xl text-xl font-bold transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-25"
          style={btnStyle(false)}
          onMouseEnter={(e) => { if (count < widget.max) (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(245,176,66,0.4)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(42,61,92,0.8)"; }}
        >
          +
        </button>
      </div>

      {/* Progress dots */}
      <div className="flex justify-center gap-1.5 pb-4">
        {Array.from({ length: widget.max }, (_, i) => (
          <span
            key={i}
            className="h-1.5 rounded-full transition-all duration-200"
            style={{
              width: i < count ? "20px" : "6px",
              background: i < count ? "#f5b042" : "rgba(42,61,92,0.8)",
              boxShadow: i < count ? "0 0 6px rgba(245,176,66,0.5)" : "none",
            }}
          />
        ))}
      </div>

      <ConfirmButton onClick={() => onSubmit(`${widget.label}: ${count}`)}>
        Confirm — {count} {count === 1 ? "Passenger" : "Passengers"}
      </ConfirmButton>
    </WidgetShell>
  );
}
