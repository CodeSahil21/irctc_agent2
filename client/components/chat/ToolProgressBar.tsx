"use client";

import type { ToolProgress } from "@/hooks/useChat";

interface ToolProgressBarProps {
  progress: ToolProgress;
}

const STATUS_COLOR: Record<ToolProgress["status"], string> = {
  running: "#f5b042",
  done: "#34d399",
  failed: "#f87171",
};

const STATUS_LABEL: Record<ToolProgress["status"], string> = {
  running: "Running",
  done: "Done",
  failed: "Failed",
};

export function ToolProgressBar({ progress }: ToolProgressBarProps) {
  const { tool, index, total, status } = progress;
  const pct = total > 0 ? Math.round(((index + (status === "running" ? 0.5 : 1)) / total) * 100) : 0;
  const color = STATUS_COLOR[status];

  return (
    <div
      className="mx-5 mb-2 rounded-xl px-4 py-2.5 text-[12px]"
      style={{
        background: "rgba(22,32,53,0.9)",
        border: `1px solid ${color}22`,
      }}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span style={{ color }} className="font-display tracking-wide uppercase text-[10px]">
          {STATUS_LABEL[status]}
        </span>
        <span className="text-rail-muted font-mono">
          {index + 1}/{total}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {status === "running" && (
          <span
            className="h-1.5 w-1.5 rounded-full animate-pulse"
            style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          />
        )}
        <span style={{ color: "#edf1fa" }} className="truncate">
          {tool.replace(/_/g, " ")}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className="mt-2 h-0.5 w-full rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.06)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color, boxShadow: `0 0 8px ${color}66` }}
        />
      </div>
    </div>
  );
}
