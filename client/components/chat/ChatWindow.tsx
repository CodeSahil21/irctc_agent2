"use client";

import { useChat } from "@/hooks/useChat";
import { ChatHeader } from "./ChatHeader";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";

export function ChatWindow() {
  const { messages, isAgentTyping, connectionState, sendQuery } = useChat();

  return (
    <div
      className="flex h-[100dvh] w-full flex-col md:h-[92vh] md:max-w-5xl md:rounded-2xl overflow-hidden"
      style={{
        border: "1px solid rgba(245,176,66,0.12)",
        background: "linear-gradient(160deg, #0f1829 0%, #0d1424 60%, #0a1020 100%)",
        boxShadow: "0 32px 80px -16px rgba(0,0,0,0.8), 0 0 0 1px rgba(245,176,66,0.06)",
      }}
    >
      <div className="h-[2px] w-full shrink-0" style={{ background: "linear-gradient(90deg, transparent, #f5b042, #34d399, transparent)" }} />
      <ChatHeader connectionState={connectionState} />
      <MessageList messages={messages} isAgentTyping={isAgentTyping} onWidgetSubmit={sendQuery} />
      <MessageInput onSend={sendQuery} disabled={connectionState !== "connected"} />
    </div>
  );
}
