"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
          {message.content && (
            isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 className="text-base font-bold mb-2 text-[#f5b042]">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-sm font-bold mb-1.5 text-[#f5b042]">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
                  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-[#f5b042]">{children}</strong>,
                  em: ({ children }) => <em className="italic opacity-90">{children}</em>,
                  code: ({ children }) => <code className="bg-[#0d1526] rounded px-1 py-0.5 text-[12px] font-mono text-[#f5b042]">{children}</code>,
                  pre: ({ children }) => <pre className="bg-[#0d1526] rounded-lg p-3 mb-2 overflow-x-auto text-[12px] font-mono">{children}</pre>,
                  hr: () => <hr className="border-[rgba(42,61,92,0.8)] my-2" />,
                  table: ({ children }) => (
                    <div className="overflow-x-auto mb-2">
                      <table className="w-full text-[13px] border-collapse">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="border-b border-[rgba(245,176,66,0.3)]">{children}</thead>,
                  th: ({ children }) => <th className="text-left py-1.5 px-2 font-semibold text-[#f5b042] whitespace-nowrap">{children}</th>,
                  td: ({ children }) => <td className="py-1.5 px-2 border-b border-[rgba(42,61,92,0.5)]">{children}</td>,
                  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#f5b042] underline underline-offset-2 hover:opacity-80">{children}</a>,
                  blockquote: ({ children }) => <blockquote className="border-l-2 border-[#f5b042] pl-3 opacity-80 mb-2">{children}</blockquote>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )
          )}

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
