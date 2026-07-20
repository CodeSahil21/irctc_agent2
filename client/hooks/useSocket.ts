"use client";

import { useEffect, useRef, useState } from "react";
import { getSocket } from "@/lib/socket/socketClient";
import type { ConnectionState } from "@/types/socket";

export function useSocket() {
  const socketRef = useRef(getSocket());
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");

  useEffect(() => {
    const socket = socketRef.current;

    const onConnect = () => setConnectionState("connected");
    const onDisconnect = () => setConnectionState("disconnected");
    const onReconnectAttempt = () => setConnectionState("reconnecting");

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.io.on("reconnect_attempt", onReconnectAttempt);

    if (!socket.connected) socket.connect();

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.io.off("reconnect_attempt", onReconnectAttempt);
    };
  }, []);

  return { socket: socketRef.current, connectionState };
}
