import cookieParser from "cookie-parser";
import cors from "cors";
import "dotenv/config";
import express from "express";
import authRoutes from "./routes/auth.routes";

const required = [
    "ACCESS_TOKEN_SECRET",
    "REFRESH_TOKEN_SECRET",
    "DATABASE_URL",
];
for (const key of required) {
    if (!process.env[key]) throw new Error(`Missing required env var: ${key}`);
}

const app = express();
app.use(
    cors({
        origin: process.env.ALLOWED_ORIGINS,
        credentials: true,
    }),
);
const PORT = parseInt(process.env.PORT ?? "4000", 10);

app.use(express.json());
app.use(cookieParser());

// Routes
app.use("/auth", authRoutes);

// Health check
app.get("/health", (_req, res) => {
    res.json({ status: "ok", service: "auth" });
});

app.listen(PORT, () => {
    console.log(`Auth Service running on http://localhost:${PORT}`);
});
