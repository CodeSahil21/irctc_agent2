"use client";

import { disconnectSocket, initSocket } from "@/lib/socket/socketClient";
import { store } from "@/store";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchAccessToken, fetchMe } from "@/store/slices/authSlice";
import { useEffect } from "react";
import { Provider } from "react-redux";

function AuthInitializer({ children }: { children: React.ReactNode }) {
    const dispatch = useAppDispatch();
    const { user, initialized, accessToken } = useAppSelector(
        (state) => state.auth,
    );

    useEffect(() => {
        // Rehydrate auth state from httpOnly cookie on every page load
        dispatch(fetchMe());
    }, [dispatch]);

    useEffect(() => {
        if (initialized && user && !accessToken) {
            dispatch(fetchAccessToken());
        }
    }, [dispatch, initialized, user, accessToken]);

    useEffect(() => {
        if (accessToken) {
            initSocket(accessToken);
        } else {
            disconnectSocket();
        }
    }, [accessToken]);

    return <>{children}</>;
}

export default function StoreProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <Provider store={store}>
            <AuthInitializer>{children}</AuthInitializer>
        </Provider>
    );
}
