import type { TrainResult } from "@/types/chat";

interface TrainListCardProps {
  trains: TrainResult[];
}

export function TrainListCard({ trains }: TrainListCardProps) {
  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-rail-line bg-rail-bg/60">
      {trains.map((train, i) => (
        <div
          key={train.number}
          className={cn(
            "grid grid-cols-[auto_1fr_auto] items-center gap-3 px-3.5 py-2.5 text-[13px]",
            i !== trains.length - 1 && "border-b border-rail-line/60"
          )}
        >
          <div className="font-display text-rail-amber">{train.number}</div>
          <div className="min-w-0">
            <div className="truncate text-rail-text">{train.name}</div>
            <div className="text-[11px] text-rail-muted">
              {train.from} {train.departure} → {train.to} {train.arrival}
            </div>
          </div>
          <div className="text-right text-[11px] text-rail-muted">{train.duration}</div>
        </div>
      ))}
    </div>
  );
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
