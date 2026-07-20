"use client";

import { useEffect, useRef, useState } from "react";
import { getSocket } from "@/lib/socket/socketClient";
import type { ConnectionState } from "@/types/socket";

/**
 * Owns the socket connection lifecycle for the lifetime of the component
 * that calls it. Returns the socket ref plus a live connection state
 * so the UI can reflect connecting / reconnecting / offline.
 */
export function useSocket() {
  const socketRef = useRef(getSocket());
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");

  useEffect(() => {
    const socket = socketRef.current;

    const handleConnect = () => setConnectionState("connected");
    const handleDisconnect = () => setConnectionState("disconnected");
    const handleReconnectAttempt = () => setConnectionState("reconnecting");

    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.io.on("reconnect_attempt", handleReconnectAttempt);

    if (!socket.connected) {
      socket.connect();
    }

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.io.off("reconnect_attempt", handleReconnectAttempt);
    };
  }, []);

  return { socket: socketRef.current, connectionState };
}
