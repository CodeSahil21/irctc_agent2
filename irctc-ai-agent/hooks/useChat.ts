"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { nanoid } from "nanoid";
import { useSocket } from "./useSocket";
import type { ChatMessage } from "@/types/chat";

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "agent",
  status: "sent",
  createdAt: Date.now(),
  content:
    "Namaste! I'm your IRCTC assistant. Ask me to check PNR status, find trains between stations, or check seat availability.",
};

export function useChat() {
  const { socket, connectionState } = useSocket();
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const streamingIdRef = useRef<string | null>(null);

  useEffect(() => {
    function handleAck({ id }: { id: string }) {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: "sent" } : m))
      );
    }

    function handleChunk({ id, delta }: { id: string; delta: string }) {
      streamingIdRef.current = id;
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === id);
        if (!exists) {
          return [
            ...prev,
            {
              id,
              role: "agent",
              status: "streaming",
              createdAt: Date.now(),
              content: delta,
            },
          ];
        }
        return prev.map((m) =>
          m.id === id ? { ...m, content: m.content + delta, status: "streaming" } : m
        );
      });
    }

    function handleComplete({ message }: { message: ChatMessage }) {
      streamingIdRef.current = null;
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === message.id);
        if (!exists) return [...prev, { ...message, status: "sent" }];
        return prev.map((m) => (m.id === message.id ? { ...message, status: "sent" } : m));
      });
      setIsAgentTyping(false);
    }

    function handleError({ id, error }: { id: string; error: string }) {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: "error", content: error } : m))
      );
      setIsAgentTyping(false);
    }

    function handleTyping({ isTyping }: { isTyping: boolean }) {
      setIsAgentTyping(isTyping);
    }

    socket.on("query:ack", handleAck);
    socket.on("message:chunk", handleChunk);
    socket.on("message:complete", handleComplete);
    socket.on("message:error", handleError);
    socket.on("agent:typing", handleTyping);

    return () => {
      socket.off("query:ack", handleAck);
      socket.off("message:chunk", handleChunk);
      socket.off("message:complete", handleComplete);
      socket.off("message:error", handleError);
      socket.off("agent:typing", handleTyping);
    };
  }, [socket]);

  const sendQuery = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      const id = nanoid();
      const userMessage: ChatMessage = {
        id,
        role: "user",
        status: "sending",
        createdAt: Date.now(),
        content: trimmed,
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsAgentTyping(true);
      socket.emit("query:send", { id, content: trimmed });
    },
    [socket]
  );

  return { messages, isAgentTyping, connectionState, sendQuery };
}
