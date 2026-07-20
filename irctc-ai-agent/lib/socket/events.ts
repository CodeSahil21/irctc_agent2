export const SOCKET_EVENTS = {
  QUERY_SEND: "query:send",
  QUERY_ACK: "query:ack",
  MESSAGE_CHUNK: "message:chunk",
  MESSAGE_COMPLETE: "message:complete",
  MESSAGE_ERROR: "message:error",
  AGENT_TYPING: "agent:typing",
  TYPING_START: "typing:start",
  TYPING_STOP: "typing:stop",
} as const;
