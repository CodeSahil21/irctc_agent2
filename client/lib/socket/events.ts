export const SOCKET_EVENTS = {
  // Client → Server
  QUERY_SEND: "query:send",
  RESUME: "resume",
  TYPING_START: "typing:start",
  TYPING_STOP: "typing:stop",
  // Server → Client
  QUERY_ACK: "query:ack",
  AGENT_TYPING: "agent:typing",
  TOOL_START: "tool:start",
  TOOL_DONE: "tool:done",
  TOOL_FAILED: "tool:failed",
  MESSAGE_CHUNK: "message:chunk",
  MESSAGE_COMPLETE: "message:complete",
  MESSAGE_ERROR: "message:error",
  INTERRUPT: "agent:interrupt",
} as const;
