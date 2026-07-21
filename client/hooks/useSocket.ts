"use client";

import { getSocket } from "@/lib/socket/socketClient";
import type { ConnectionState } from "@/types/socket";
import { useEffect, useState } from "react";

export function useSocket() {
    const socket = getSocket();

    const [connectionState, setConnectionState] = useState<ConnectionState>(
        socket.connected ? "connected" : "connecting",
    );

    useEffect(() => {
        const onConnect = () => setConnectionState("connected");
        const onDisconnect = () => setConnectionState("disconnected");
        const onReconnectAttempt = () => setConnectionState("reconnecting");

        socket.on("connect", onConnect);
        socket.on("disconnect", onDisconnect);
        socket.io.on("reconnect_attempt", onReconnectAttempt);

        if (!socket.connected) {
            socket.connect();
        }

        return () => {
            socket.off("connect", onConnect);
            socket.off("disconnect", onDisconnect);
            socket.io.off("reconnect_attempt", onReconnectAttempt);
        };
    }, [socket]);

    return {
        socket,
        connectionState,
    };
}
