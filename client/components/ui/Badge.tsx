import { cn } from "@/lib/utils/cn";
import type { ReactNode } from "react";

type BadgeTone = "green" | "red" | "amber" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  green: "bg-rail-signal-green/10 text-rail-signal-green border-rail-signal-green/30",
  red: "bg-rail-signal-red/10 text-rail-signal-red border-rail-signal-red/30",
  amber: "bg-rail-amber/10 text-rail-amber border-rail-amber/30",
  neutral: "bg-rail-line/30 text-rail-muted border-rail-line",
};

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
}

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        TONE_CLASSES[tone]
      )}
    >
      {children}
    </span>
  );
}
