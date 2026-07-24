import type { ChatMessage } from "./chat";

export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";

export interface ToolProgressPayload {
  tool: string;
  index: number;
  total: number;
}

export interface InterruptPayload {
  id: string;
  prompt: string;
}

export interface ClientToServerEvents {
  "query:send": (payload: { id: string; content: string; conversationId?: string }) => void;
  "resume": (payload: { id: string; approved: boolean }) => void;
  "typing:start": () => void;
  "typing:stop": () => void;
}

export interface ServerToClientEvents {
  "query:ack": (payload: { id: string }) => void;
  "agent:typing": (payload: { isTyping: boolean }) => void;
  "tool:start": (payload: ToolProgressPayload) => void;
  "tool:done": (payload: { tool: string; index: number }) => void;
  "tool:failed": (payload: { tool: string; index: number; error: string }) => void;
  "message:chunk": (payload: { id: string; delta: string }) => void;
  "message:complete": (payload: { message: ChatMessage }) => void;
  "message:error": (payload: { id: string; error: string }) => void;
  "agent:interrupt": (payload: InterruptPayload) => void;
}
