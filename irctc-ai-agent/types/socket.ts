import type { ChatMessage } from "./chat";

/** Events the client emits to the server */
export interface ClientToServerEvents {
  "query:send": (payload: { id: string; content: string }) => void;
  "typing:start": () => void;
  "typing:stop": () => void;
}

/** Events the server emits to the client */
export interface ServerToClientEvents {
  "query:ack": (payload: { id: string }) => void;
  "message:chunk": (payload: { id: string; delta: string }) => void;
  "message:complete": (payload: { message: ChatMessage }) => void;
  "message:error": (payload: { id: string; error: string }) => void;
  "agent:typing": (payload: { isTyping: boolean }) => void;
}

export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";
