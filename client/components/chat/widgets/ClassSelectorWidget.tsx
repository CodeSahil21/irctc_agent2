"use client";

import { useState } from "react";
import type { ClassSelectorWidget } from "@/types/chat";
import { WidgetShell, ConfirmButton } from "./WidgetShell";

const CLASS_META: Record<string, { label: string; desc: string }> = {
  "1A": { label: "First AC", desc: "4-berth, fully enclosed" },
  "2A": { label: "Second AC", desc: "6-berth, curtained" },
  "3A": { label: "Third AC", desc: "8-berth, open" },
  "SL": { label: "Sleeper", desc: "Non-AC, 8-berth" },
  "CC": { label: "Chair Car", desc: "AC seating" },
  "EC": { label: "Exec Chair", desc: "Premium AC seating" },
  "2S": { label: "Second Sitting", desc: "Non-AC seating" },
  "GN": { label: "General", desc: "Unreserved" },
};

interface Props {
  widget: ClassSelectorWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function ClassSelectorWidgetCard({ widget, onSubmit, submitted }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <WidgetShell label={widget.label} submitted={submitted}>
      <div className="grid grid-cols-2 gap-2 p-3">
        {widget.options.map((cls) => {
          const meta = CLASS_META[cls];
          const isSelected = selected === cls;
          return (
            <button
              key={cls}
              onClick={() => setSelected(cls)}
              className="flex flex-col items-start rounded-xl px-3 py-2.5 text-left transition-all duration-150"
              style={
                isSelected
                  ? {
                      background: "linear-gradient(135deg, rgba(245,176,66,0.2), rgba(245,176,66,0.08))",
                      border: "1px solid rgba(245,176,66,0.45)",
                      boxShadow: "0 0 12px rgba(245,176,66,0.12)",
                    }
                  : { background: "rgba(22,32,53,0.6)", border: "1px solid rgba(42,61,92,0.6)" }
              }
            >
              <span className="font-display text-sm font-semibold" style={{ color: isSelected ? "#f5b042" : "#edf1fa" }}>
                {cls}
              </span>
              {meta && (
                <>
                  <span className="text-xs mt-0.5" style={{ color: isSelected ? "#f5b042" : "#7a85a0" }}>
                    {meta.label}
                  </span>
                  <span className="text-[10px] mt-0.5" style={{ color: "#3a4560" }}>
                    {meta.desc}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>

      <ConfirmButton onClick={() => selected && onSubmit(`${widget.label}: ${selected}`)} disabled={!selected}>
        {selected ? `Confirm — ${selected} · ${CLASS_META[selected]?.label ?? ""}` : "Select a class"}
      </ConfirmButton>
    </WidgetShell>
  );
}
