"use client";

import { useAutoScroll } from "@/hooks/useAutoScroll";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { ToolProgressBar } from "./ToolProgressBar";
import { InterruptDialog } from "./InterruptDialog";
import type { ChatMessage } from "@/types/chat";
import type { ToolProgress } from "@/hooks/useChat";
import type { InterruptPayload } from "@/types/socket";

interface MessageListProps {
  messages: ChatMessage[];
  isAgentTyping: boolean;
  toolProgress: ToolProgress | null;
  interrupt: InterruptPayload | null;
  onWidgetSubmit: (value: string) => void;
  onResume: (approved: boolean) => void;
}

export function MessageList({
  messages,
  isAgentTyping,
  toolProgress,
  interrupt,
  onWidgetSubmit,
  onResume,
}: MessageListProps) {
  const containerRef = useAutoScroll(
    messages.length + (isAgentTyping ? 1 : 0) + (interrupt ? 1 : 0)
  );

  return (
    <div ref={containerRef} className="min-h-0 flex-1 overflow-y-auto py-5 space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onWidgetSubmit={onWidgetSubmit} />
      ))}

      {/* Tool progress — shown above typing indicator */}
      {toolProgress && <ToolProgressBar progress={toolProgress} />}

      {/* Typing dots */}
      {isAgentTyping && !toolProgress && (
        <div className="px-5">
          <TypingIndicator />
        </div>
      )}

      {/* Human-approval interrupt */}
      {interrupt && <InterruptDialog interrupt={interrupt} onConfirm={onResume} />}
    </div>
  );
}
