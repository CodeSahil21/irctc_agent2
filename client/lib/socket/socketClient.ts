import type {
  ClientToServerEvents,
  ServerToClientEvents,
} from "@/types/socket";
import { io, type Socket } from "socket.io-client";

let socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;

const SOCKET_URL =
    process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://localhost:8001";

export function initSocket(
    token: string,
): Socket<ServerToClientEvents, ClientToServerEvents> {
    if (socket) return socket;

    socket = io(SOCKET_URL, {
        autoConnect: false,
        transports: ["websocket"],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 800,
        reconnectionDelayMax: 5000,
        auth: { token },
    });

    return socket;
}

export function getSocket(): Socket<
    ServerToClientEvents,
    ClientToServerEvents
> | null {
    return socket;
}

export function disconnectSocket() {
    socket?.disconnect();
    socket = null;
}
