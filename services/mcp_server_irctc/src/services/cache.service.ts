import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  lazyConnect: true,
  enableOfflineQueue: false,
  maxRetriesPerRequest: 0,
});

// Prevent unhandled 'error' event from crashing the process
redis.on("error", () => { /* Redis unavailable — cache disabled, non-fatal */ });

// TTLs in seconds
const TTL = {
  trainSearch: 600,    // 10 min
  availability: 300,   // 5 min
  fare: 1800,          // 30 min
};

async function get<T>(key: string): Promise<T | null> {
  try {
    const val = await redis.get(key);
    return val ? (JSON.parse(val) as T) : null;
  } catch {
    return null;
  }
}

async function set(key: string, value: unknown, ttl: number): Promise<void> {
  try {
    await redis.set(key, JSON.stringify(value), "EX", ttl);
  } catch {
    // cache write failure is non-fatal
  }
}

// ── Train search ──────────────────────────────────────────────────────────────

export async function getTrainSearchCache(from: string, to: string, date: Date) {
  return get<object>(`trains:${from}:${to}:${date.toISOString().slice(0, 10)}`);
}

export async function setTrainSearchCache(from: string, to: string, date: Date, response: object) {
  await set(`trains:${from}:${to}:${date.toISOString().slice(0, 10)}`, response, TTL.trainSearch);
}

// ── Availability ──────────────────────────────────────────────────────────────

export async function getAvailabilityCache(trainNumber: string, travelClass: string, quota: string, date: Date) {
  return get<object>(`avail:${trainNumber}:${travelClass}:${quota}:${date.toISOString().slice(0, 10)}`);
}

export async function setAvailabilityCache(trainNumber: string, travelClass: string, quota: string, date: Date, response: object) {
  await set(`avail:${trainNumber}:${travelClass}:${quota}:${date.toISOString().slice(0, 10)}`, response, TTL.availability);
}

// ── Fare ──────────────────────────────────────────────────────────────────────

export async function getFareCache(trainNumber: string, travelClass: string, quota: string, from: string, to: string) {
  return get<object>(`fare:${trainNumber}:${travelClass}:${quota}:${from}:${to}`);
}

export async function setFareCache(trainNumber: string, travelClass: string, quota: string, from: string, to: string, response: object) {
  await set(`fare:${trainNumber}:${travelClass}:${quota}:${from}:${to}`, response, TTL.fare);
}
