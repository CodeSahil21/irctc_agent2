import { Badge } from "@/components/ui/Badge";

interface PnrStatusCardProps {
  pnr: string;
  status: string;
  chart: string;
}

export function PnrStatusCard({ pnr, status, chart }: PnrStatusCardProps) {
  const tone = /confirm/i.test(status) ? "green" : /wait|rac/i.test(status) ? "amber" : "red";

  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-rail-line bg-rail-bg/60">
      <div className="flex items-center justify-between border-b border-dashed border-rail-line px-3.5 py-2">
        <span className="font-display text-[11px] uppercase tracking-[0.14em] text-rail-muted">
          PNR {pnr}
        </span>
        <Badge tone={tone}>{status}</Badge>
      </div>
      <div className="px-3.5 py-2 text-[13px] text-rail-muted">Chart: {chart}</div>
    </div>
  );
}
