"use client";

import { useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { formatTime } from "@/lib/utils/formatTime";
import { cn } from "@/lib/utils/cn";
import type { ChatMessage } from "@/types/chat";
import { PnrStatusCard } from "./attachments/PnrStatusCard";
import { TrainListCard } from "./attachments/TrainListCard";
import { WidgetRenderer } from "./widgets/WidgetRenderer";

interface MessageBubbleProps {
  message: ChatMessage;
  onWidgetSubmit?: (value: string) => void;
}

export function MessageBubble({ message, onWidgetSubmit }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.status === "error";
  const [widgetSubmitted, setWidgetSubmitted] = useState(false);

  function handleWidgetSubmit(value: string) {
    setWidgetSubmitted(true);
    onWidgetSubmit?.(value);
  }

  return (
    <div className={cn("flex items-end gap-3 animate-rise", isUser && "flex-row-reverse")}>
      <Avatar role={isUser ? "user" : "agent"} />

      <div className={cn("flex max-w-[75%] flex-col gap-1.5", isUser && "items-end")}>
        <div
          className="relative rounded-2xl px-4 py-3 text-[14px] leading-relaxed"
          style={
            isError
              ? { background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.3)", color: "#fca5a5" }
              : isUser
              ? {
                  background: "linear-gradient(135deg, rgba(245,176,66,0.18), rgba(245,176,66,0.08))",
                  border: "1px solid rgba(245,176,66,0.25)",
                  boxShadow: "0 4px 20px rgba(245,176,66,0.08)",
                  color: "#edf1fa",
                  borderBottomRightRadius: "4px",
                }
              : {
                  background: "linear-gradient(135deg, #162035, #111a2e)",
                  border: "1px solid rgba(42,61,92,0.8)",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
                  color: "#edf1fa",
                  borderBottomLeftRadius: "4px",
                }
          }
        >
          {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}

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
          {message.attachment?.type === "widget" && (
            <WidgetRenderer
              widget={message.attachment.widget}
              onSubmit={handleWidgetSubmit}
              submitted={widgetSubmitted}
            />
          )}
        </div>

        <div className="flex items-center gap-1.5 px-1 text-[10px] text-rail-muted">
          <span>{formatTime(message.createdAt)}</span>
          {message.status === "sending" && <span className="animate-pulse-soft">· sending</span>}
          {message.status === "streaming" && (
            <span className="animate-pulse-soft" style={{ color: "#f5b042" }}>· streaming</span>
          )}
          {isError && <span style={{ color: "#f87171" }}>· failed</span>}
        </div>
      </div>
    </div>
  );
}
