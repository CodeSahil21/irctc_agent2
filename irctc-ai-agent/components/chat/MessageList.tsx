"use client";

import { useAutoScroll } from "@/hooks/useAutoScroll";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { ChatMessage } from "@/types/chat";

export function MessageList({
  messages,
  isAgentTyping,
}: {
  messages: ChatMessage[];
  isAgentTyping: boolean;
}) {
  const containerRef = useAutoScroll(messages.length + (isAgentTyping ? 1 : 0));

  return (
    <div ref={containerRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isAgentTyping && <TypingIndicator />}
    </div>
  );
}
