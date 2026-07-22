import * as authApi from "@/lib/api/authApi";
import type { AuthUser, LoginBody, RegisterBody } from "@/types/auth";
import { createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AuthState {
    user: AuthUser | null;
    accessToken: string | null; // JWT for socket auth (fetched via /api/token)
    status: "idle" | "loading" | "succeeded" | "failed";
    error: string | null;
    initialized: boolean;
}

const initialState: AuthState = {
    user: null,
    accessToken: null,
    status: "idle",
    error: null,
    initialized: false,
};

// ── Thunks ────────────────────────────────────────────────────────────────────

export const registerUser = createAsyncThunk(
    "auth/register",
    async (body: RegisterBody, { rejectWithValue }) => {
        try {
            const data = await authApi.register(body);
            return data.user;
        } catch (err: unknown) {
            return rejectWithValue(
                err instanceof Error ? err.message : "Registration failed",
            );
        }
    },
);

export const loginUser = createAsyncThunk(
    "auth/login",
    async (body: LoginBody, { rejectWithValue }) => {
        try {
            const data = await authApi.login(body);
            return data.user;
        } catch (err: unknown) {
            return rejectWithValue(
                err instanceof Error ? err.message : "Login failed",
            );
        }
    },
);

export const fetchMe = createAsyncThunk(
    "auth/me",
    async (_, { rejectWithValue }) => {
        try {
            const data = await authApi.getMe();
            return data.user;
        } catch {
            return rejectWithValue(null); // not authenticated — silent fail
        }
    },
);

export const refreshSession = createAsyncThunk(
    "auth/refresh",
    async (_, { rejectWithValue }) => {
        try {
            await authApi.refresh();
        } catch (err: unknown) {
            return rejectWithValue(
                err instanceof Error ? err.message : "Refresh failed",
            );
        }
    },
);

export const logoutUser = createAsyncThunk(
    "auth/logout",
    async (_, { rejectWithValue }) => {
        try {
            await authApi.logout();
        } catch (err: unknown) {
            return rejectWithValue(
                err instanceof Error ? err.message : "Logout failed",
            );
        }
    },
);

export const logoutAllDevices = createAsyncThunk(
    "auth/logoutAll",
    async (_, { rejectWithValue }) => {
        try {
            await authApi.logoutAll();
        } catch (err: unknown) {
            return rejectWithValue(
                err instanceof Error ? err.message : "Logout all failed",
            );
        }
    },
);

// Fetches the raw JWT from our server-side /api/token route (reads httpOnly cookie)
export const fetchAccessToken = createAsyncThunk(
    "auth/fetchAccessToken",
    async (_, { rejectWithValue }) => {
        try {
            const res = await fetch("/api/token", { credentials: "include" });
            if (!res.ok) return rejectWithValue(null);
            const { token } = await res.json();
            return token as string;
        } catch {
            return rejectWithValue(null);
        }
    },
);

// ── Slice ─────────────────────────────────────────────────────────────────────

const authSlice = createSlice({
    name: "auth",
    initialState,
    reducers: {
        clearError(state) {
            state.error = null;
        },
    },
    extraReducers: (builder) => {
        // register
        builder
            .addCase(registerUser.pending, (state) => {
                state.status = "loading";
                state.error = null;
            })
            .addCase(
                registerUser.fulfilled,
                (state, action: PayloadAction<AuthUser>) => {
                    state.status = "succeeded";
                    state.user = action.payload;
                    state.initialized = true;
                },
            )
            .addCase(registerUser.rejected, (state, action) => {
                state.status = "failed";
                state.error = action.payload as string;
            });

        // login
        builder
            .addCase(loginUser.pending, (state) => {
                state.status = "loading";
                state.error = null;
            })
            .addCase(
                loginUser.fulfilled,
                (state, action: PayloadAction<AuthUser>) => {
                    state.status = "succeeded";
                    state.user = action.payload;
                    state.initialized = true;
                },
            )
            .addCase(loginUser.rejected, (state, action) => {
                state.status = "failed";
                state.error = action.payload as string;
            });

        // me
        builder
            .addCase(
                fetchMe.fulfilled,
                (state, action: PayloadAction<AuthUser>) => {
                    state.user = action.payload;
                    state.status = "succeeded";
                    state.initialized = true;
                },
            )
            .addCase(fetchMe.rejected, (state) => {
                state.user = null;
                state.initialized = true;
            });

        // accessToken
        builder
            .addCase(
                fetchAccessToken.fulfilled,
                (state, action: PayloadAction<string>) => {
                    state.accessToken = action.payload;
                },
            )
            .addCase(fetchAccessToken.rejected, (state) => {
                state.accessToken = null;
            });

        // logout + logoutAll — clear user and token on success or failure
        const clearUser = (state: AuthState) => {
            state.user = null;
            state.accessToken = null;
            state.status = "idle";
            state.error = null;
        };
        builder
            .addCase(logoutUser.fulfilled, clearUser)
            .addCase(logoutUser.rejected, clearUser)
            .addCase(logoutAllDevices.fulfilled, clearUser)
            .addCase(logoutAllDevices.rejected, clearUser);
    },
});

export const { clearError } = authSlice.actions;
export default authSlice.reducer;
