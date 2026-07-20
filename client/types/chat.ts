export type MessageRole = "user" | "agent" | "system";
export type MessageStatus = "sending" | "sent" | "streaming" | "error";

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

// ── Widget descriptors ────────────────────────────────────────────────────────

export interface DatePickerWidget {
  type: "date_picker";
  label: string;
  /** ISO date string for min selectable date, defaults to today */
  minDate?: string;
}

export interface StationPickerWidget {
  type: "station_picker";
  label: string;
  /** "from" | "to" — used to build the submit string */
  field: "from" | "to";
}

export interface ClassSelectorWidget {
  type: "class_selector";
  label: string;
  options: string[];
}

export interface PassengerCountWidget {
  type: "passenger_count";
  label: string;
  min: number;
  max: number;
}

export interface QuickReplyWidget {
  type: "quick_reply";
  label: string;
  options: string[];
}

export type ChatWidget =
  | DatePickerWidget
  | StationPickerWidget
  | ClassSelectorWidget
  | PassengerCountWidget
  | QuickReplyWidget;

// ── Attachments ───────────────────────────────────────────────────────────────

export type AgentAttachment =
  | { type: "pnr_status"; pnr: string; status: string; chart: string }
  | { type: "train_list"; trains: TrainResult[] }
  | { type: "widget"; widget: ChatWidget }
  | { type: "none" };

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  createdAt: number;
  attachment?: AgentAttachment;
}
