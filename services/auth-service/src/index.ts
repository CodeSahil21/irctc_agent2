import "dotenv/config";
import express from "express";
import cookieParser from "cookie-parser";
import authRoutes from "./routes/auth.routes";
import { csrfProtect, generateToken } from "./middleware/csrf";

const required = ["ACCESS_TOKEN_SECRET", "REFRESH_TOKEN_SECRET", "DATABASE_URL"];
for (const key of required) {
  if (!process.env[key]) throw new Error(`Missing required env var: ${key}`);
}

const app = express();
const PORT = parseInt(process.env.PORT ?? "4000", 10);

app.use(express.json());
app.use(cookieParser());
app.use(csrfProtect); // must be after json() and cookieParser()

// CSRF token endpoint — clients call this first to get a token
app.get("/csrf-token", (req, res) => {
  res.json({ csrfToken: generateToken(req, res) });
});

// Routes
app.use("/auth", authRoutes);

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "auth" });
});

app.listen(PORT, () => {
  console.log(`Auth Service running on http://localhost:${PORT}`);
});
