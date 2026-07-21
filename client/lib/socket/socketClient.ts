import { io, type Socket } from "socket.io-client";
import type { ClientToServerEvents, ServerToClientEvents } from "@/types/socket";

let socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://localhost:8000";

export interface SocketAuth {
  conversationId?: string;
  userEmail?: string;
  userName?: string;
}

export function getSocket(auth?: SocketAuth): Socket<ServerToClientEvents, ClientToServerEvents> {
  if (socket) return socket;

  socket = io(SOCKET_URL, {
    autoConnect: false,
    transports: ["websocket"],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 800,
    reconnectionDelayMax: 5000,
    auth: auth ?? {},
  });

  return socket;
}

export function disconnectSocket() {
  socket?.disconnect();
  socket = null;
}
