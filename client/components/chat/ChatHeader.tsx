import { ConnectionStatus } from "./ConnectionStatus";
import type { ConnectionState } from "@/types/socket";

interface ChatHeaderProps {
  connectionState: ConnectionState;
}

export function ChatHeader({ connectionState }: ChatHeaderProps) {
  return (
    <header
      className="flex items-center justify-between px-6 py-4 border-b"
      style={{
        borderColor: "rgba(245,176,66,0.1)",
        background: "linear-gradient(90deg, rgba(245,176,66,0.04) 0%, transparent 60%)",
      }}
    >
      <div className="flex items-center gap-4">
        {/* Logo badge */}
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl font-display text-sm font-semibold"
          style={{
            background: "linear-gradient(135deg, rgba(245,176,66,0.2), rgba(245,176,66,0.05))",
            border: "1px solid rgba(245,176,66,0.3)",
            boxShadow: "0 0 16px rgba(245,176,66,0.15), inset 0 1px 0 rgba(255,255,255,0.06)",
            color: "#f5b042",
          }}
        >
          IR
        </div>

        <div>
          <h1 className="font-display text-[15px] tracking-wider text-rail-text font-semibold">
            IRCTC{" "}
            <span style={{ background: "linear-gradient(90deg,#f5b042,#fde68a)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Assist
            </span>
          </h1>
          <div className="flex items-center gap-2 mt-0.5 text-[11px] text-rail-muted font-display tracking-widest uppercase">
            <span>You</span>
            <span className="flex-1 h-px w-8" style={{ background: "linear-gradient(90deg, #2a3d5c, transparent)" }} />
            <span className="animate-pulse-soft" style={{ color: "#f5b042", textShadow: "0 0 8px rgba(245,176,66,0.8)" }}>●</span>
            <span className="flex-1 h-px w-8" style={{ background: "linear-gradient(90deg, transparent, #2a3d5c)" }} />
            <span>Agent</span>
          </div>
        </div>
      </div>

      <ConnectionStatus state={connectionState} />
    </header>
  );
}
