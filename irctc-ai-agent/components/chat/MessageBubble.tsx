import { Avatar } from "@/components/ui/Avatar";
import { formatTime } from "@/lib/utils/formatTime";
import { cn } from "@/lib/utils/cn";
import type { ChatMessage } from "@/types/chat";
import { PnrStatusCard } from "./attachments/PnrStatusCard";
import { TrainListCard } from "./attachments/TrainListCard";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex items-start gap-3 animate-rise",
        isUser && "flex-row-reverse"
      )}
    >
      <Avatar role={isUser ? "user" : "agent"} />

      <div className={cn("flex max-w-[78%] flex-col gap-1", isUser && "items-end")}>
        <div
          className={cn(
            "relative rounded-lg border px-3.5 py-2.5 text-[13.5px] leading-relaxed shadow-ticket",
            isUser
              ? "rounded-tr-sm border-rail-amberDim bg-rail-amber/10 text-rail-text"
              : "rounded-tl-sm border-rail-line bg-rail-panel text-rail-text",
            message.status === "error" && "border-rail-signal-red/50 bg-rail-signal-red/10"
          )}
        >
          {/* perforated ticket edge */}
          <span
            aria-hidden
            className={cn(
              "pointer-events-none absolute top-0 h-full w-px bg-[radial-gradient(circle,theme(colors.rail.bg)_1.5px,transparent_1.5px)] bg-[length:1px_8px]",
              isUser ? "right-full mr-[1px]" : "left-full ml-[1px]"
            )}
          />
          <p className="whitespace-pre-wrap">{message.content}</p>

          {message.attachment?.type === "pnr_status" && (
            <PnrStatusCard
              pnr={message.attachment.pnr}
              status={message.attachment.status}
              chart={message.attachment.chart}
            />
          )}
          {message.attachment?.type === "train_list" && (
            <TrainListCard trains={message.attachment.trains} />
          )}
        </div>

        <div className="flex items-center gap-1.5 px-1 text-[10px] text-rail-muted">
          <span>{formatTime(message.createdAt)}</span>
          {message.status === "sending" && <span>· sending</span>}
          {message.status === "error" && <span className="text-rail-signal-red">· failed</span>}
        </div>
      </div>
    </div>
  );
}
