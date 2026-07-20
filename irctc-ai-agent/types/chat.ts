export type MessageRole = "user" | "agent" | "system";

export type MessageStatus = "sending" | "sent" | "streaming" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  createdAt: number;
  /** Optional structured data the agent returns, e.g. PNR status, train list */
  attachment?: AgentAttachment;
}

export type AgentAttachment =
  | { type: "pnr_status"; pnr: string; status: string; chart: string }
  | { type: "train_list"; trains: TrainResult[] }
  | { type: "none" };

export interface TrainResult {
  number: string;
  name: string;
  from: string;
  to: string;
  departure: string;
  arrival: string;
  duration: string;
  classes: string[];
}

export interface ChatState {
  messages: ChatMessage[];
  isAgentTyping: boolean;
}
