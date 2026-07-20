import { Avatar } from "@/components/ui/Avatar";

export function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 animate-rise">
      <Avatar role="agent" />
      <div
        className="flex items-center gap-1.5 rounded-2xl px-4 py-3.5"
        style={{
          background: "linear-gradient(135deg, #162035, #111a2e)",
          border: "1px solid rgba(42,61,92,0.8)",
          borderBottomLeftRadius: "4px",
        }}
      >
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="h-2 w-2 rounded-full animate-blink"
            style={{
              background: "#f5b042",
              boxShadow: "0 0 6px rgba(245,176,66,0.7)",
              animationDelay: `${delay}ms`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
