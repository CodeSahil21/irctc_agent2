import { cn } from "@/lib/utils/cn";
import type { ConnectionState } from "@/types/socket";

const COPY: Record<ConnectionState, string> = {
  connected: "On track",
  connecting: "Connecting",
  reconnecting: "Rejoining line",
  disconnected: "Off the grid",
};

const DOT_CLASSES: Record<ConnectionState, string> = {
  connected: "bg-rail-signal-green shadow-[0_0_8px_2px_rgba(62,207,142,0.55)]",
  connecting: "bg-rail-signal-yellow animate-blink",
  reconnecting: "bg-rail-signal-yellow animate-blink",
  disconnected: "bg-rail-signal-red",
};

export function ConnectionStatus({ state }: { state: ConnectionState }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-rail-line bg-rail-panel/60 px-3 py-1">
      <span className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASSES[state])} />
      <span className="font-display text-[11px] uppercase tracking-[0.14em] text-rail-muted">
        {COPY[state]}
      </span>
    </div>
  );
}
