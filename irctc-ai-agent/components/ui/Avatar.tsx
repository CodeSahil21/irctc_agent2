import { cn } from "@/lib/utils/cn";

export function Avatar({ role }: { role: "user" | "agent" }) {
  if (role === "agent") {
    return (
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-rail-line bg-rail-panel font-display text-[13px] text-rail-amber">
        ◇
      </div>
    );
  }

  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-rail-line/40 font-display text-[13px] text-rail-text">
      you
    </div>
  );
}
