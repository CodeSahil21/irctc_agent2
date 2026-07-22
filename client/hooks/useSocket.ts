"use client";

import {
    disconnectSocket,
    getSocket,
    initSocket,
} from "@/lib/socket/socketClient";
import { useAppSelector } from "@/store/hooks";
import type { ConnectionState } from "@/types/socket";
import { useEffect, useState } from "react";

export function useSocket() {
    const accessToken = useAppSelector((state) => state.auth.accessToken);
    const [socket, setSocket] = useState(getSocket());

    const [connectionState, setConnectionState] = useState<ConnectionState>(
        socket?.connected ? "connected" : "connecting",
    );

    useEffect(() => {
        if (!accessToken) {
            disconnectSocket();
            setSocket(null);
            setConnectionState("connecting");
            return;
        }

        const nextSocket = initSocket(accessToken);
        setSocket(nextSocket);
        setConnectionState(nextSocket.connected ? "connected" : "connecting");
    }, [accessToken]);

    useEffect(() => {
        if (!socket) return;
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

    return { socket, connectionState };
}
