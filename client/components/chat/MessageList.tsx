"use client";

import { useAutoScroll } from "@/hooks/useAutoScroll";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { ChatMessage } from "@/types/chat";

interface MessageListProps {
  messages: ChatMessage[];
  isAgentTyping: boolean;
  onWidgetSubmit: (value: string) => void;
}

export function MessageList({ messages, isAgentTyping, onWidgetSubmit }: MessageListProps) {
  const containerRef = useAutoScroll(messages.length + (isAgentTyping ? 1 : 0));

  return (
    <div ref={containerRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onWidgetSubmit={onWidgetSubmit} />
      ))}
      {isAgentTyping && <TypingIndicator />}
    </div>
  );
}
