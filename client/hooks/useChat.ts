"use client";

import { nanoid } from "nanoid";
import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatMessage } from "@/types/chat";
import type { InterruptPayload, ToolProgressPayload } from "@/types/socket";
import { useSocket } from "./useSocket";

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "agent",
  status: "sent",
  createdAt: Date.now(),
  content:
    "Namaste! I'm your IRCTC assistant. Ask me to check PNR status, find trains between stations, or check seat availability.",
};

export interface ToolProgress {
  tool: string;
  index: number;
  total: number;
  status: "running" | "done" | "failed";
}

export function useChat() {
  const { socket, connectionState } = useSocket();

  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const [toolProgress, setToolProgress] = useState<ToolProgress | null>(null);
  const [interrupt, setInterrupt] = useState<InterruptPayload | null>(null);

  const streamingIdRef = useRef<string | null>(null);

  useEffect(() => {
    const onAck = ({ id }: { id: string }) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: "sent" } : m))
      );
    };

    const onTyping = ({ isTyping }: { isTyping: boolean }) => {
      setIsAgentTyping(isTyping);
      if (!isTyping) setToolProgress(null);
    };

    const onToolStart = (payload: ToolProgressPayload) => {
      setToolProgress({ ...payload, status: "running" });
    };

    const onToolDone = ({ tool, index }: { tool: string; index: number }) => {
      setToolProgress((prev) =>
        prev ? { ...prev, tool, index, status: "done" } : null
      );
    };

    const onToolFailed = ({ tool, index }: { tool: string; index: number; error: string }) => {
      setToolProgress((prev) =>
        prev ? { ...prev, tool, index, status: "failed" } : null
      );
    };

    const onChunk = ({ id, delta }: { id: string; delta: string }) => {
      streamingIdRef.current = id;
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === id);
        if (!exists) {
          return [
            ...prev,
            { id, role: "agent", status: "streaming", createdAt: Date.now(), content: delta },
          ];
        }
        return prev.map((m) =>
          m.id === id ? { ...m, content: m.content + delta, status: "streaming" } : m
        );
      });
    };

    const onComplete = ({ message }: { message: ChatMessage }) => {
      streamingIdRef.current = null;
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === message.id);
        if (!exists) return [...prev, { ...message, status: "sent" }];
        return prev.map((m) =>
          m.id === message.id ? { ...message, status: "sent" } : m
        );
      });
      setIsAgentTyping(false);
      setToolProgress(null);
    };

    const onError = ({ id, error }: { id: string; error: string }) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id ? { ...m, status: "error", content: error } : m
        )
      );
      setIsAgentTyping(false);
      setToolProgress(null);
    };

    const onInterrupt = (payload: InterruptPayload) => {
      setIsAgentTyping(false);
      setToolProgress(null);
      setInterrupt(payload);
    };

    socket.on("query:ack", onAck);
    socket.on("agent:typing", onTyping);
    socket.on("tool:start", onToolStart);
    socket.on("tool:done", onToolDone);
    socket.on("tool:failed", onToolFailed);
    socket.on("message:chunk", onChunk);
    socket.on("message:complete", onComplete);
    socket.on("message:error", onError);
    socket.on("agent:interrupt", onInterrupt);

    return () => {
      socket.off("query:ack", onAck);
      socket.off("agent:typing", onTyping);
      socket.off("tool:start", onToolStart);
      socket.off("tool:done", onToolDone);
      socket.off("tool:failed", onToolFailed);
      socket.off("message:chunk", onChunk);
      socket.off("message:complete", onComplete);
      socket.off("message:error", onError);
      socket.off("agent:interrupt", onInterrupt);
    };
  }, [socket]);

  const sendQuery = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      const id = nanoid();
      setMessages((prev) => [
        ...prev,
        { id, role: "user", status: "sending", createdAt: Date.now(), content: trimmed },
      ]);
      setIsAgentTyping(true);
      socket.emit("query:send", { id, content: trimmed });
    },
    [socket]
  );

  const sendResume = useCallback(
    (approved: boolean) => {
      if (!interrupt) return;
      socket.emit("resume", { id: interrupt.id, approved });
      setInterrupt(null);
      setIsAgentTyping(true);
    },
    [socket, interrupt]
  );

  return {
    messages,
    isAgentTyping,
    toolProgress,
    interrupt,
    connectionState,
    sendQuery,
    sendResume,
  };
}
