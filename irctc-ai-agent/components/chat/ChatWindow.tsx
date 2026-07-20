"use client";

import { useChat } from "@/hooks/useChat";
import { ChatHeader } from "./ChatHeader";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";

export function ChatWindow() {
  const { messages, isAgentTyping, connectionState, sendQuery } = useChat();
  const inputDisabled = connectionState !== "connected";

  return (
    <div className="flex h-[100dvh] w-full flex-col bg-rail-surface md:h-[85vh] md:max-w-2xl md:rounded-xl md:border md:border-rail-line md:shadow-2xl">
      <ChatHeader connectionState={connectionState} />
      <MessageList messages={messages} isAgentTyping={isAgentTyping} />
      <MessageInput onSend={sendQuery} disabled={inputDisabled} />
    </div>
  );
}
