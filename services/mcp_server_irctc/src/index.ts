import "dotenv/config";
import express from "express";
import { randomUUID } from "crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";
// ── tools ─────────────────────────────────────────────────────────────────────
import { searchTrainsTool } from "./tools/searchTrains";
import { checkAvailabilityTool } from "./tools/checkAvailability";
import { fareTool } from "./tools/fare";
import { getRouteTool } from "./tools/getRoute";
import { seatMapTool } from "./tools/seatMap";
import { availableBoardingPointsTool } from "./tools/availableBoardingPoints";
import { searchTrainByNumberTool } from "./tools/searchTrainByNumber";
import { liveStatusTool } from "./tools/liveStatus";
import { trainScheduleTool } from "./tools/trainSchedule";
import { platformTool } from "./tools/platform";
import { stationsTool } from "./tools/stations";
import { findStationCodeTool } from "./tools/findStationCode";
import { nearbyStationTool } from "./tools/nearbyStation";
import { listClassesTool } from "./tools/listClasses";
import { listQuotasTool } from "./tools/listQuotas";
import { recommendTrainsTool } from "./tools/recommendTrains";
import { bookTicketTool } from "./tools/bookTicket";
import { cancelTicketTool } from "./tools/cancelTicket";
import { getPnrTool } from "./tools/getPNR";
import { getBookingTool } from "./tools/getBooking";
import { bookingHistoryTool } from "./tools/bookingHistory";
import { updateBookingStatusTool } from "./tools/updateBookingStatus";
import { updateBoardingPointTool } from "./tools/updateBoardingPoint";
import { remindersTool } from "./tools/reminders";
import { getRemindersTool } from "./tools/getReminders";
import { updateReminderTool } from "./tools/updateReminder";
import { deleteReminderTool } from "./tools/deleteReminder";
import { addSavedPassengerTool } from "./tools/addSavedPassenger";
import { savedPassengersTool } from "./tools/savedPassengers";
import { logToolExecution } from "./utils/logger";

// ── helpers ───────────────────────────────────────────────────────────────────

function ok(data: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
}

// Sanitize user input before logging — strips newlines to prevent log injection (CWE-117)
function sanitize(input: unknown): unknown {
  if (typeof input === "string") return input.replace(/[\r\n]/g, " ").slice(0, 500);
  if (typeof input === "object" && input !== null) {
    return Object.fromEntries(
      Object.entries(input as Record<string, unknown>).map(([k, v]) => [k, sanitize(v)])
    );
  }
  return input;
}

// ── MCP server factory ────────────────────────────────────────────────────────

function createMcpServer(userEmail: string, userName?: string) {
  const server = new McpServer({ name: "irctc-mcp-server", version: "1.0.0" });
  const user = { email: userEmail, name: userName };

  // ── Public tools ────────────────────────────────────────────────────────────

  server.registerTool("search_trains", {
    description: "Search trains between two stations on a given date",
    inputSchema: {
      fromStation: z.string().describe("Origin station code e.g. NDLS"),
      toStation: z.string().describe("Destination station code e.g. BCT"),
      journeyDate: z.string().describe("Journey date YYYY-MM-DD"),
      quota: z.string().optional().describe("Quota code e.g. GN, TQ, PT"),
    },
  }, async ({ fromStation, toStation, journeyDate, quota }) =>
    logToolExecution("search_trains", sanitize({ fromStation, toStation, journeyDate, quota }) as object, () =>
      searchTrainsTool({ fromStation, toStation, journeyDate, quota }).then(ok)
    )
  );

  server.registerTool("check_availability", {
    description: "Check seat availability for a train on a given date",
    inputSchema: {
      trainNumber: z.string(),
      travelClass: z.string().describe("e.g. SL, 3A, 2A, 1A"),
      quota: z.string().describe("e.g. GN, TQ"),
      journeyDate: z.string().describe("YYYY-MM-DD"),
    },
  }, async ({ trainNumber, travelClass, quota, journeyDate }) =>
    logToolExecution("check_availability", sanitize({ trainNumber, travelClass, quota, journeyDate }) as object, () =>
      checkAvailabilityTool({ trainNumber, travelClass, quota, journeyDate }).then(ok)
    )
  );

  server.registerTool("get_fare", {
    description: "Get fare for a train between two stations",
    inputSchema: {
      trainNumber: z.string(),
      travelClass: z.string(),
      quota: z.string(),
      fromStation: z.string(),
      toStation: z.string(),
    },
  }, async (params) =>
    logToolExecution("get_fare", sanitize(params) as object, () => fareTool(params).then(ok))
  );

  server.registerTool("get_route", {
    description: "Get full route and stops of a train",
    inputSchema: { trainNumber: z.string() },
  }, async ({ trainNumber }) =>
    logToolExecution("get_route", sanitize({ trainNumber }) as object, () =>
      getRouteTool({ trainNumber }).then(ok)
    )
  );

  server.registerTool("get_seat_map", {
    description: "Get coach-wise seat availability map for a train",
    inputSchema: {
      trainNumber: z.string(),
      travelClass: z.string(),
      journeyDate: z.string(),
    },
  }, async (params) =>
    logToolExecution("get_seat_map", sanitize(params) as object, () => seatMapTool(params).then(ok))
  );

  server.registerTool("get_boarding_points", {
    description: "Get available boarding points for a train from a station",
    inputSchema: {
      trainNumber: z.string(),
      fromStation: z.string(),
      journeyDate: z.string(),
    },
  }, async (params) =>
    logToolExecution("get_boarding_points", sanitize(params) as object, () =>
      availableBoardingPointsTool(params).then(ok)
    )
  );

  server.registerTool("search_train_by_number", {
    description: "Get train details by train number",
    inputSchema: { trainNumber: z.string() },
  }, async ({ trainNumber }) =>
    logToolExecution("search_train_by_number", sanitize({ trainNumber }) as object, () =>
      searchTrainByNumberTool(trainNumber).then(ok)
    )
  );

  server.registerTool("get_live_status", {
    description: "Get live running status of a train",
    inputSchema: {
      trainNumber: z.string(),
      date: z.string().describe("YYYY-MM-DD"),
    },
  }, async ({ trainNumber, date }) =>
    logToolExecution("get_live_status", sanitize({ trainNumber, date }) as object, () =>
      liveStatusTool(trainNumber, date).then(ok)
    )
  );

  server.registerTool("get_train_schedule", {
    description: "Get full timetable/schedule of a train",
    inputSchema: { trainNumber: z.string() },
  }, async ({ trainNumber }) =>
    logToolExecution("get_train_schedule", sanitize({ trainNumber }) as object, () =>
      trainScheduleTool(trainNumber).then(ok)
    )
  );

  server.registerTool("get_platform", {
    description: "Get platform number for a train at a station",
    inputSchema: {
      trainNumber: z.string(),
      stationCode: z.string(),
    },
  }, async ({ trainNumber, stationCode }) =>
    logToolExecution("get_platform", sanitize({ trainNumber, stationCode }) as object, () =>
      platformTool(trainNumber, stationCode).then(ok)
    )
  );

  server.registerTool("search_stations", {
    description: "Search stations by name, code or city",
    inputSchema: { query: z.string() },
  }, async ({ query }) =>
    logToolExecution("search_stations", sanitize({ query }) as object, () =>
      stationsTool(query).then(ok)
    )
  );

  server.registerTool("find_station_code", {
    description: "Find station code from station name or city",
    inputSchema: { query: z.string() },
  }, async ({ query }) =>
    logToolExecution("find_station_code", sanitize({ query }) as object, () =>
      findStationCodeTool(query).then(ok)
    )
  );

  server.registerTool("get_nearby_stations", {
    description: "Get railway stations near a geographic location",
    inputSchema: {
      lat: z.number().describe("Latitude"),
      lng: z.number().describe("Longitude"),
    },
  }, async ({ lat, lng }) =>
    logToolExecution("get_nearby_stations", sanitize({ lat, lng }) as object, () =>
      nearbyStationTool(lat, lng).then(ok)
    )
  );

  server.registerTool("list_classes", {
    description: "List all available travel classes",
    inputSchema: {},
  }, async () =>
    logToolExecution("list_classes", {}, async () => ok(listClassesTool()))
  );

  server.registerTool("list_quotas", {
    description: "List all available booking quotas",
    inputSchema: {},
  }, async () =>
    logToolExecution("list_quotas", {}, async () => ok(listQuotasTool()))
  );

  server.registerTool("recommend_trains", {
    description: "Get train recommendations ranked by fastest, cheapest or overnight",
    inputSchema: {
      fromStation: z.string(),
      toStation: z.string(),
      journeyDate: z.string(),
      preference: z.enum(["fastest", "cheapest", "overnight"]),
      travelClass: z.string().optional(),
      quota: z.string().optional(),
    },
  }, async (params) =>
    logToolExecution("recommend_trains", sanitize(params) as object, () =>
      recommendTrainsTool(params).then(ok)
    )
  );

  // ── User tools ──────────────────────────────────────────────────────────────

  server.registerTool("book_ticket", {
    description: "Book a train ticket for the authenticated user",
    inputSchema: {
      trainNumber: z.string(),
      trainName: z.string(),
      source: z.string(),
      destination: z.string(),
      journeyDate: z.string(),
      travelClass: z.string(),
      quota: z.string(),
      fare: z.number(),
      passengers: z.array(z.object({
        name: z.string(),
        age: z.number().int(),
        gender: z.enum(["MALE", "FEMALE", "OTHER"]),
        berthPreference: z.string().optional(),
      })).min(1),
    },
  }, async (params) =>
    logToolExecution("book_ticket", sanitize({ ...params, user: user.email }) as object, () =>
      bookTicketTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("cancel_ticket", {
    description: "Cancel a booked ticket by PNR",
    inputSchema: { pnr: z.string() },
  }, async ({ pnr }) =>
    logToolExecution("cancel_ticket", sanitize({ pnr, user: user.email }) as object, () =>
      cancelTicketTool({ user, pnr }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_pnr", {
    description: "Track PNR status for the authenticated user",
    inputSchema: { pnr: z.string() },
  }, async ({ pnr }) =>
    logToolExecution("get_pnr", sanitize({ pnr, user: user.email }) as object, () =>
      getPnrTool({ user, pnr }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_booking", {
    description: "Get booking details by PNR",
    inputSchema: { pnr: z.string() },
  }, async ({ pnr }) =>
    logToolExecution("get_booking", sanitize({ pnr, user: user.email }) as object, () =>
      getBookingTool({ user, pnr }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_booking_history", {
    description: "Get all bookings for the authenticated user",
    inputSchema: {},
  }, async () =>
    logToolExecution("get_booking_history", sanitize({ user: user.email }) as object, () =>
      bookingHistoryTool(user).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("update_booking_status", {
    description: "Update the status of a booking",
    inputSchema: {
      pnr: z.string(),
      status: z.enum(["PENDING", "BOOKED", "RAC", "WL", "CANCELLED", "FAILED"]),
      transactionId: z.string().optional(),
    },
  }, async (params) =>
    logToolExecution("update_booking_status", sanitize({ ...params, user: user.email }) as object, () =>
      updateBookingStatusTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("update_boarding_point", {
    description: "Change the boarding point for a booking",
    inputSchema: {
      pnr: z.string(),
      newBoardingStation: z.string(),
    },
  }, async (params) =>
    logToolExecution("update_boarding_point", sanitize({ ...params, user: user.email }) as object, () =>
      updateBoardingPointTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("create_reminder", {
    description: "Create a journey/PNR/booking reminder",
    inputSchema: {
      type: z.enum(["JOURNEY", "PNR", "BOOKING"]),
      reminderAt: z.string().describe("ISO datetime string"),
      bookingId: z.string().optional(),
      metadata: z.record(z.string(), z.unknown()).optional(),
    },
  }, async (params) =>
    logToolExecution("create_reminder", sanitize({ ...params, user: user.email }) as object, () =>
      remindersTool({ ...params, user, metadata: params.metadata as object | undefined }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_reminders", {
    description: "Get all reminders for the authenticated user",
    inputSchema: {},
  }, async () =>
    logToolExecution("get_reminders", sanitize({ user: user.email }) as object, () =>
      getRemindersTool(user).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("update_reminder", {
    description: "Update an existing reminder",
    inputSchema: {
      reminderId: z.string(),
      reminderAt: z.string().optional(),
      type: z.enum(["JOURNEY", "PNR", "BOOKING"]).optional(),
      metadata: z.record(z.string(), z.unknown()).optional(),
    },
  }, async (params) =>
    logToolExecution("update_reminder", sanitize({ ...params, user: user.email }) as object, () =>
      updateReminderTool({ ...params, user, metadata: params.metadata as object | undefined }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("delete_reminder", {
    description: "Delete a reminder",
    inputSchema: { reminderId: z.string() },
  }, async ({ reminderId }) =>
    logToolExecution("delete_reminder", sanitize({ reminderId, user: user.email }) as object, () =>
      deleteReminderTool({ user, reminderId }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("add_saved_passenger", {
    description: "Save a passenger profile for future bookings",
    inputSchema: {
      name: z.string(),
      age: z.number().int(),
      gender: z.enum(["MALE", "FEMALE", "OTHER"]),
      berthPreference: z.string().optional(),
      seniorCitizen: z.boolean().optional(),
    },
  }, async (params) =>
    logToolExecution("add_saved_passenger", sanitize({ ...params, user: user.email }) as object, () =>
      addSavedPassengerTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_saved_passengers", {
    description: "Get all saved passenger profiles for the authenticated user",
    inputSchema: {},
  }, async () =>
    logToolExecution("get_saved_passengers", sanitize({ user: user.email }) as object, () =>
      savedPassengersTool(user).then(ok),
      { userId: user.email }
    )
  );

  return server;
}

// ── Express + Streamable HTTP ─────────────────────────────────────────────────

const app = express();
app.use(express.json());

const PORT = parseInt(process.env.PORT ?? "3000", 10);

// sessionId -> { transport, userEmail } for session ownership validation
const sessions = new Map<string, { transport: StreamableHTTPServerTransport; userEmail: string }>();

// CSRF guard: non-init POST/DELETE must carry a valid mcp-session-id that belongs to the same user
function csrfGuard(req: express.Request, res: express.Response): boolean {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  const userEmail = req.headers["x-user-email"] as string | undefined;
  if (!sessionId) return true; // new session init — no CSRF check needed
  const session = sessions.get(sessionId);
  if (!session) {
    res.status(404).json({ error: "Session not found" });
    return false;
  }
  if (session.userEmail !== userEmail) {
    res.status(403).json({ error: "Session does not belong to this user" });
    return false;
  }
  return true;
}

app.post("/mcp", async (req, res) => {
  const userEmail = (req.headers["x-user-email"] as string | undefined)?.replace(/[\r\n]/g, "");
  const userName  = (req.headers["x-user-name"]  as string | undefined)?.replace(/[\r\n]/g, "");

  if (!userEmail) {
    res.status(401).json({ error: "Missing x-user-email header" });
    return;
  }

  if (!csrfGuard(req, res)) return;

  const sessionId = req.headers["mcp-session-id"] as string | undefined;

  if (sessionId && sessions.has(sessionId)) {
    await sessions.get(sessionId)!.transport.handleRequest(req, res, req.body);
    return;
  }

  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: () => randomUUID(),
  });

  transport.onclose = () => {
    if (transport.sessionId) sessions.delete(transport.sessionId);
  };

  const server = createMcpServer(userEmail, userName);
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);

  if (transport.sessionId) sessions.set(transport.sessionId, { transport, userEmail });
});

app.get("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !sessions.has(sessionId)) {
    res.status(404).json({ error: "Session not found" });
    return;
  }
  await sessions.get(sessionId)!.transport.handleRequest(req, res);
});

app.delete("/mcp", async (req, res) => {
  if (!csrfGuard(req, res)) return;
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (sessionId && sessions.has(sessionId)) {
    await sessions.get(sessionId)!.transport.close();
    sessions.delete(sessionId);
  }
  res.status(200).json({ ok: true });
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", sessions: sessions.size });
});

app.listen(PORT, () => {
  console.log(`IRCTC MCP Server running on http://localhost:${PORT}/mcp`);
});
