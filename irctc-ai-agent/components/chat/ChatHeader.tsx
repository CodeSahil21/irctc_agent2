import { ConnectionStatus } from "./ConnectionStatus";
import type { ConnectionState } from "@/types/socket";

export function ChatHeader({ connectionState }: { connectionState: ConnectionState }) {
  return (
    <header className="flex items-center justify-between border-b border-rail-line px-5 py-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md border border-rail-line bg-rail-panel">
          <span className="font-display text-sm text-rail-amber">IR</span>
        </div>
        <div>
          <h1 className="font-display text-[15px] tracking-wide text-rail-text">
            IRCTC Assist
          </h1>
          <div className="flex items-center gap-1.5 text-[11px] text-rail-muted">
            <span>YOU</span>
            <span className="inline-block h-px w-6 bg-rail-line" />
            <span className="text-rail-amber">●</span>
            <span className="inline-block h-px w-6 bg-rail-line" />
            <span>AGENT</span>
          </div>
        </div>
      </div>
      <ConnectionStatus state={connectionState} />
    </header>
  );
}
