interface AvatarProps {
  role: "user" | "agent";
}

export function Avatar({ role }: AvatarProps) {
  if (role === "agent") {
    return (
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-display text-[15px]"
        style={{
          background: "linear-gradient(135deg, rgba(245,176,66,0.25), rgba(245,176,66,0.06))",
          border: "1px solid rgba(245,176,66,0.35)",
          boxShadow: "0 0 12px rgba(245,176,66,0.2)",
          color: "#f5b042",
        }}
      >
        ◇
      </div>
    );
  }
  return (
    <div
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-display text-[11px] font-semibold tracking-wider"
      style={{
        background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(99,102,241,0.1))",
        border: "1px solid rgba(99,102,241,0.3)",
        color: "#a5b4fc",
      }}
    >
      YOU
    </div>
  );
}
