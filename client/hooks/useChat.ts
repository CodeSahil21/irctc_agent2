"use client";

import { nanoid } from "nanoid";
import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatMessage } from "@/types/chat";
import { useSocket } from "./useSocket";

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
        const onAck = ({ id }: { id: string }) => {
            setMessages((prev) =>
                prev.map((m) => (m.id === id ? { ...m, status: "sent" } : m)),
            );
        };

        const onChunk = ({ id, delta }: { id: string; delta: string }) => {
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
                    m.id === id
                        ? {
                              ...m,
                              content: m.content + delta,
                              status: "streaming",
                          }
                        : m,
                );
            });
        };

        const onComplete = ({ message }: { message: ChatMessage }) => {
            streamingIdRef.current = null;

            setMessages((prev) => {
                const exists = prev.some((m) => m.id === message.id);

                if (!exists) {
                    return [
                        ...prev,
                        {
                            ...message,
                            status: "sent",
                        },
                    ];
                }

                return prev.map((m) =>
                    m.id === message.id
                        ? {
                              ...message,
                              status: "sent",
                          }
                        : m,
                );
            });

            setIsAgentTyping(false);
        };

        const onError = ({ id, error }: { id: string; error: string }) => {
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === id
                        ? {
                              ...m,
                              status: "error",
                              content: error,
                          }
                        : m,
                ),
            );

            setIsAgentTyping(false);
        };

        const onTyping = ({ isTyping }: { isTyping: boolean }) => {
            setIsAgentTyping(isTyping);
        };

        socket.on("query:ack", onAck);
        socket.on("message:chunk", onChunk);
        socket.on("message:complete", onComplete);
        socket.on("message:error", onError);
        socket.on("agent:typing", onTyping);

        return () => {
            socket.off("query:ack", onAck);
            socket.off("message:chunk", onChunk);
            socket.off("message:complete", onComplete);
            socket.off("message:error", onError);
            socket.off("agent:typing", onTyping);
        };
    }, [socket]);

    const sendQuery = useCallback(
        (content: string) => {
            const trimmed = content.trim();

            if (!trimmed) return;

            const id = nanoid();

            setMessages((prev) => [
                ...prev,
                {
                    id,
                    role: "user",
                    status: "sending",
                    createdAt: Date.now(),
                    content: trimmed,
                },
            ]);

            setIsAgentTyping(true);

            socket.emit("query:send", {
                id,
                content: trimmed,
            });
        },
        [socket],
    );

    return {
        messages,
        isAgentTyping,
        connectionState,
        sendQuery,
    };
}
