"use client";

import { useState, useRef } from "react";
import type { StationPickerWidget } from "@/types/chat";
import { WidgetShell, ConfirmButton } from "./WidgetShell";

const STATIONS = [
  { code: "NDLS", name: "New Delhi" },
  { code: "BCT", name: "Mumbai Central" },
  { code: "CSTM", name: "Mumbai CST" },
  { code: "MAS", name: "Chennai Central" },
  { code: "HWH", name: "Howrah Junction" },
  { code: "SBC", name: "Bengaluru City" },
  { code: "ADI", name: "Ahmedabad Junction" },
  { code: "PUNE", name: "Pune Junction" },
  { code: "JP", name: "Jaipur Junction" },
  { code: "LKO", name: "Lucknow" },
  { code: "BPL", name: "Bhopal Junction" },
  { code: "HYB", name: "Hyderabad Deccan" },
  { code: "VSKP", name: "Visakhapatnam" },
  { code: "GHY", name: "Guwahati" },
  { code: "CDG", name: "Chandigarh" },
  { code: "AMD", name: "Amritsar Junction" },
  { code: "KOTA", name: "Kota Junction" },
  { code: "NZM", name: "Hazrat Nizamuddin" },
];

interface Props {
  widget: StationPickerWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function StationPickerWidgetCard({ widget, onSubmit, submitted }: Props) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [selected, setSelected] = useState<{ code: string; name: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = query.length > 0
    ? STATIONS.filter((s) =>
        s.name.toLowerCase().includes(query.toLowerCase()) ||
        s.code.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 6)
    : STATIONS.slice(0, 6);

  function pick(station: { code: string; name: string }) {
    setSelected(station);
    setQuery(station.name);
    setFocused(false);
  }

  return (
    <WidgetShell label={widget.label} submitted={submitted}>
      <div className="p-3">
        {/* Search input */}
        <div
          className="mb-2 flex items-center gap-2 rounded-xl px-3 py-2.5 transition-all duration-200"
          style={{
            background: "rgba(22,32,53,0.8)",
            border: `1px solid ${focused ? "rgba(245,176,66,0.5)" : "rgba(42,61,92,0.8)"}`,
            boxShadow: focused ? "0 0 0 3px rgba(245,176,66,0.06)" : "none",
          }}
        >
          <svg className="h-4 w-4 shrink-0" style={{ color: "#3a4560" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0Z" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(null); }}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            placeholder="Search station or code…"
            className="flex-1 bg-transparent text-sm text-rail-text placeholder:text-rail-muted focus:outline-none"
          />
          {query && (
            <button
              onClick={() => { setQuery(""); setSelected(null); inputRef.current?.focus(); }}
              className="text-rail-muted transition-colors hover:text-rail-text"
            >
              ✕
            </button>
          )}
        </div>

        {/* Suggestions */}
        {(focused || !selected) && (
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(42,61,92,0.5)" }}>
            {filtered.length === 0 ? (
              <div className="px-4 py-3 text-xs text-rail-muted text-center">No stations found</div>
            ) : (
              filtered.map((s, i) => (
                <button
                  key={s.code}
                  onMouseDown={() => pick(s)}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-white/5"
                  style={{ borderTop: i > 0 ? "1px solid rgba(42,61,92,0.4)" : "none" }}
                >
                  <span
                    className="font-display text-[10px] shrink-0 rounded-md px-1.5 py-0.5"
                    style={{ background: "rgba(245,176,66,0.1)", color: "#f5b042", border: "1px solid rgba(245,176,66,0.2)" }}
                  >
                    {s.code}
                  </span>
                  <span className="text-sm text-rail-text">{s.name}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <ConfirmButton onClick={() => selected && onSubmit(`${widget.label}: ${selected.name} (${selected.code})`)} disabled={!selected}>
        {selected ? `Confirm — ${selected.name}` : "Select a station"}
      </ConfirmButton>
    </WidgetShell>
  );
}
