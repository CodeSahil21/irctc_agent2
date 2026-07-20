"use client";

import { useState } from "react";
import type { DatePickerWidget } from "@/types/chat";
import { WidgetShell, ConfirmButton } from "./WidgetShell";

const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

interface Props {
  widget: DatePickerWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function DatePickerWidgetCard({ widget, onSubmit, submitted }: Props) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const min = widget.minDate ? new Date(widget.minDate) : today;

  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [selected, setSelected] = useState<Date | null>(null);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  function pick(day: number) {
    const d = new Date(year, month, day);
    if (d < min) return;
    setSelected(d);
  }

  function confirm() {
    if (!selected) return;
    onSubmit(`${widget.label}: ${selected.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}`);
  }

  return (
    <WidgetShell label={widget.label} submitted={submitted}>
      {/* Month nav */}
      <div className="flex items-center justify-between px-4 py-2">
        <button
          onClick={() => setCursor(new Date(year, month - 1, 1))}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-rail-muted transition-colors hover:bg-white/5 hover:text-rail-text"
        >
          ‹
        </button>
        <span className="font-display text-xs text-rail-text">{MONTHS[month]} {year}</span>
        <button
          onClick={() => setCursor(new Date(year, month + 1, 1))}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-rail-muted transition-colors hover:bg-white/5 hover:text-rail-text"
        >
          ›
        </button>
      </div>

      {/* Day labels */}
      <div className="grid grid-cols-7 px-3 pb-1">
        {DAYS.map((d) => (
          <div key={d} className="py-1 text-center font-display text-[10px] tracking-wider" style={{ color: "#3a4560" }}>
            {d}
          </div>
        ))}
      </div>

      {/* Date cells */}
      <div className="grid grid-cols-7 gap-y-1 px-3 pb-3">
        {cells.map((day, i) => {
          if (!day) return <div key={i} />;
          const date = new Date(year, month, day);
          const isPast = date < min;
          const isSelected = selected?.getDate() === day && selected?.getMonth() === month && selected?.getFullYear() === year;
          const isToday = date.getTime() === today.getTime();

          return (
            <button
              key={i}
              onClick={() => pick(day)}
              disabled={isPast}
              className="flex h-8 w-full items-center justify-center rounded-lg text-sm transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-25"
              style={
                isSelected
                  ? { background: "linear-gradient(135deg,#f5b042,#e8960a)", color: "#080c18", fontWeight: 600 }
                  : isToday
                  ? { background: "rgba(245,176,66,0.12)", color: "#f5b042", border: "1px solid rgba(245,176,66,0.3)" }
                  : { color: "#8992a9" }
              }
              onMouseEnter={(e) => {
                if (!isSelected && !isPast) {
                  (e.currentTarget as HTMLButtonElement).style.background = "rgba(245,176,66,0.1)";
                  (e.currentTarget as HTMLButtonElement).style.color = "#edf1fa";
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected && !isPast) {
                  (e.currentTarget as HTMLButtonElement).style.background = isToday ? "rgba(245,176,66,0.12)" : "";
                  (e.currentTarget as HTMLButtonElement).style.color = isToday ? "#f5b042" : "#8992a9";
                }
              }}
            >
              {day}
            </button>
          );
        })}
      </div>

      <ConfirmButton onClick={confirm} disabled={!selected}>
        {selected
          ? `Confirm — ${selected.toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}`
          : "Select a date"}
      </ConfirmButton>
    </WidgetShell>
  );
}
