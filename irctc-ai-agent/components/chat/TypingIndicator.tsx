import { Avatar } from "@/components/ui/Avatar";

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-rise">
      <Avatar role="agent" />
      <div className="flex items-center gap-1 rounded-lg border border-rail-line bg-rail-panel px-3.5 py-3">
        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-rail-amber [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-rail-amber [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-rail-amber [animation-delay:300ms]" />
      </div>
    </div>
  );
}
