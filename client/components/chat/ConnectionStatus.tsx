import { cn } from "@/lib/utils/cn";
import type { ConnectionState } from "@/types/socket";

const COPY: Record<ConnectionState, string> = {
  connected: "Live",
  connecting: "Connecting",
  reconnecting: "Reconnecting",
  disconnected: "Offline",
};

const STYLES: Record<ConnectionState, { dot: string; pill: React.CSSProperties }> = {
  connected: {
    dot: "bg-rail-signal-green",
    pill: {
      background: "rgba(52,211,153,0.08)",
      border: "1px solid rgba(52,211,153,0.25)",
      boxShadow: "0 0 12px rgba(52,211,153,0.1)",
    },
  },
  connecting: {
    dot: "bg-rail-signal-yellow animate-blink",
    pill: {
      background: "rgba(251,191,36,0.08)",
      border: "1px solid rgba(251,191,36,0.2)",
    },
  },
  reconnecting: {
    dot: "bg-rail-signal-yellow animate-blink",
    pill: {
      background: "rgba(251,191,36,0.08)",
      border: "1px solid rgba(251,191,36,0.2)",
    },
  },
  disconnected: {
    dot: "bg-rail-signal-red",
    pill: {
      background: "rgba(248,113,113,0.08)",
      border: "1px solid rgba(248,113,113,0.2)",
    },
  },
};

const DOT_GLOW: Record<ConnectionState, string> = {
  connected: "0 0 8px 2px rgba(52,211,153,0.6)",
  connecting: "",
  reconnecting: "",
  disconnected: "",
};

interface ConnectionStatusProps {
  state: ConnectionState;
}

export function ConnectionStatus({ state }: ConnectionStatusProps) {
  const { dot, pill } = STYLES[state];
  return (
    <div className="flex items-center gap-2 rounded-full px-3.5 py-1.5" style={pill}>
      <span
        className={cn("h-2 w-2 rounded-full shrink-0", dot)}
        style={{ boxShadow: DOT_GLOW[state] }}
      />
      <span className="font-display text-[11px] uppercase tracking-[0.12em] text-rail-muted">
        {COPY[state]}
      </span>
    </div>
  );
}
