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
import { seatMapTool } from "./tools/seatMap";
import { availableBoardingPointsTool } from "./tools/availableBoardingPoints";
import { liveStatusTool } from "./tools/liveStatus";
import { platformTool } from "./tools/platform";
import { recommendTrainsTool } from "./tools/recommendTrains";
import { bookTicketTool } from "./tools/bookTicket";
import { cancelTicketTool } from "./tools/cancelTicket";
import { bookingHistoryTool } from "./tools/bookingHistory";
import { addSavedPassengerTool } from "./tools/addSavedPassenger";
import { savedPassengersTool } from "./tools/savedPassengers";
// ── merged tools ──────────────────────────────────────────────────────────────
import { getTrainDetailsTool } from "./tools/getTrainDetails";
import { getReferenceDataTool } from "./tools/getReferenceData";
import { trackBookingTool } from "./tools/trackBooking";
import { updateBookingTool } from "./tools/updateBooking";
import { manageReminderTool } from "./tools/manageReminder";
import { findStationTool } from "./tools/findStation";
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
    description:
      "Search all trains running between two stations on a specific date. This is the primary entry point for " +
      "'find me a train from X to Y' style requests. Returns a LIST of trains with basic timing/duration/class info " +
      "but NOT live seat availability or fare — call check_availability and get_fare separately per train if the user " +
      "wants those, or use recommend_trains instead if the user wants a ranked shortlist with availability+fare already merged in. " +
      "fromStation/toStation accept exact station codes (e.g. NDLS). If you only have a city/station name, call find_station first to resolve it.",
    inputSchema: {
      fromStation: z.string().describe("Origin station code, e.g. 'NDLS' for New Delhi. Must be a code, not a name — use find_station to resolve a name first."),
      toStation: z.string().describe("Destination station code, e.g. 'BCT' for Mumbai Central. Must be a code, not a name — use find_station to resolve a name first."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format, e.g. '2025-08-15'."),
      quota: z.string().optional().describe("Quota code — GN (General, default), LD (Ladies), TQ (Tatkal), PT (Premium Tatkal), HO (Higher Official), SS (Senior Citizen). Omit for General."),
    },
  }, async ({ fromStation, toStation, journeyDate, quota }) =>
    logToolExecution("search_trains", sanitize({ fromStation, toStation, journeyDate, quota }) as object, () =>
      searchTrainsTool({ fromStation, toStation, journeyDate, quota }).then(ok)
    )
  );

  server.registerTool("check_availability", {
    description:
      "Check real-time seat availability (AVAILABLE / RAC / WL and count) for ONE specific train, class, and quota combination " +
      "on a given date. Use this after search_trains once the user has picked a specific train, or when they ask 'is there a seat on train X'. " +
      "Requires an exact trainNumber — get one from search_trains or get_train_details first if you only have a train name.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number, e.g. '12951'."),
      travelClass: z.string().describe("Class code — SL, 3A, 2A, 1A, CC, EC, 2S, or VS. Call get_reference_data if unsure which code matches what the user asked for (e.g. 'AC 3 tier' → 3A)."),
      quota: z.string().describe("Quota code — GN, LD, TQ, PT, HO, or SS. Call get_reference_data if unsure."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format."),
    },
  }, async ({ trainNumber, travelClass, quota, journeyDate }) =>
    logToolExecution("check_availability", sanitize({ trainNumber, travelClass, quota, journeyDate }) as object, () =>
      checkAvailabilityTool({ trainNumber, travelClass, quota, journeyDate }).then(ok)
    )
  );

  server.registerTool("get_fare", {
    description:
      "Get the exact fare (with breakdown: base fare, reservation charge, superfast charge, GST, total) for ONE train, " +
      "class, and quota between two stations. Use once the user has a specific train+class in mind and asks 'how much will it cost'. " +
      "For comparing prices across multiple trains at once, use recommend_trains with preference='cheapest' instead of calling this repeatedly.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number, e.g. '12951'."),
      travelClass: z.string().describe("Class code — SL, 3A, 2A, 1A, CC, EC, 2S, or VS."),
      quota: z.string().describe("Quota code — GN, LD, TQ, PT, HO, or SS."),
      fromStation: z.string().describe("Boarding station code."),
      toStation: z.string().describe("Destination station code."),
    },
  }, async (params) =>
    logToolExecution("get_fare", sanitize(params) as object, () => fareTool(params).then(ok))
  );

  server.registerTool("get_seat_map", {
    description:
      "Get a coach-by-coach seat map (total/booked/available seats per coach) for one train, class, and date. " +
      "Use this only when the user specifically wants to see coach-level detail (e.g. 'which coach has the most free seats') — " +
      "for a simple yes/no or count-based availability check, use check_availability instead, it's cheaper and usually sufficient.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number."),
      travelClass: z.string().describe("Class code — SL, 3A, 2A, 1A, CC, EC, 2S, or VS."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format."),
    },
  }, async (params) =>
    logToolExecution("get_seat_map", sanitize(params) as object, () => seatMapTool(params).then(ok))
  );

  server.registerTool("get_boarding_points", {
    description:
      "List all valid boarding (pickup) points for a train, given the station the user currently plans to board from. " +
      "Use this when the user asks 'can I board from a different/earlier station' or before calling update_booking to change " +
      "a boarding point, to show them valid options first.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number."),
      fromStation: z.string().describe("The station code the user currently intends to board from."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format."),
    },
  }, async (params) =>
    logToolExecution("get_boarding_points", sanitize(params) as object, () =>
      availableBoardingPointsTool(params).then(ok)
    )
  );

  server.registerTool("get_live_status", {
    description:
      "Get the current running status of a train on a specific date — last station crossed, next station, delay in minutes. " +
      "Use this for 'where is my train right now' / 'is train X running late' style questions. Only meaningful for a train that " +
      "is currently en route or scheduled for that date — not useful for far-future planning questions.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number."),
      date: z.string().describe("Date to check status for, in YYYY-MM-DD format. Usually today's date unless the user specifies otherwise."),
    },
  }, async ({ trainNumber, date }) =>
    logToolExecution("get_live_status", sanitize({ trainNumber, date }) as object, () =>
      liveStatusTool(trainNumber, date).then(ok)
    )
  );

  server.registerTool("get_platform", {
    description:
      "Get the platform number a train will arrive/depart from at a specific station. Use for 'which platform does train X leave from at station Y' — " +
      "a narrow, single-purpose lookup distinct from get_boarding_points (which lists valid boarding stations, not platform numbers).",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number."),
      stationCode: z.string().describe("Station code to check the platform at."),
    },
  }, async ({ trainNumber, stationCode }) =>
    logToolExecution("get_platform", sanitize({ trainNumber, stationCode }) as object, () =>
      platformTool(trainNumber, stationCode).then(ok)
    )
  );

  server.registerTool("get_train_details", {
    description:
      "Get info, route (all stops), and/or schedule for ONE train by its number — three sections in one call, chosen via 'include'. " +
      "Only request the sections you actually need; each adds a DB lookup. " +
      "include:['info'] (default) — name, type, classes offered, origin/destination, total stop count. Use for general 'tell me about train X'. " +
      "include:['route'] — full stop-by-stop list with arrival/departure/distance. Use for 'what stations does it pass through'. " +
      "include:['schedule'] — same stops but with halt duration at each. Use for 'give me the full timetable'. " +
      "Combine sections (e.g. ['info','route']) only if the question spans both — don't request all three by default.",
    inputSchema: {
      trainNumber: z.string().describe("Train number, e.g. '12951'."),
      include: z.array(z.enum(["info", "route", "schedule"]))
        .optional()
        .describe("Which sections to return. Default ['info']. Only add 'route' or 'schedule' if the user actually asked about stops or timings."),
    },
  }, async ({ trainNumber, include }) =>
    logToolExecution("get_train_details", sanitize({ trainNumber, include }) as object, () =>
      getTrainDetailsTool({ trainNumber, include }).then(ok)
    )
  );

  server.registerTool("get_reference_data", {
    description:
      "Get the full static list of valid travel class codes (SL, 3A, 2A, 1A, CC, EC, 2S, VS) and quota codes (GN, LD, TQ, PT, HO, SS) " +
      "with their human-readable names, in one call. Call this whenever you're unsure which code corresponds to what the user said " +
      "(e.g. user says 'AC first class' — look it up here rather than guessing) before passing travelClass/quota into any other tool.",
    inputSchema: {},
  }, async () =>
    logToolExecution("get_reference_data", {}, async () => ok(getReferenceDataTool()))
  );

  server.registerTool("find_station", {
    description:
      "Resolve a station name, city, or partial text into IRCTC station code(s) — or find stations near a coordinate. " +
      "Do NOT call this if the user already gave a valid station code (2-5 uppercase letters, e.g. NDLS) — pass that straight into " +
      "search_trains/get_fare/etc. instead. Three modes based on which params you pass, pick exactly one: " +
      "(1) query only → up to 10 fuzzy matches with full details. Use when the name could be ambiguous (e.g. 'Delhi' matches several stations) " +
      "and you need to show the user options or aren't sure which one they mean. " +
      "(2) query + exactMatch=true → a single best-match { code, fullName }. Use when you just need one code to feed into another tool " +
      "and don't need to double check with the user. " +
      "(3) lat + lng (no query) → stations within 50km. Use for 'stations near me' or 'nearest station to this location'.",
    inputSchema: {
      query: z.string().optional().describe("Station name, city, or partial code, e.g. 'Mumbai' or 'New Delhi'. Omit if using lat/lng."),
      lat: z.number().optional().describe("Latitude, for nearby-station search. Must be paired with lng."),
      lng: z.number().optional().describe("Longitude, for nearby-station search. Must be paired with lat."),
      exactMatch: z.boolean().optional().describe("true = return one single best match (code + fullName). false/omitted = return up to 10 matches. Ignored if lat/lng are set."),
    },
  }, async (params) =>
    logToolExecution("find_station", sanitize(params) as object, () =>
      findStationTool(params).then(ok)
    )
  );

  server.registerTool("recommend_trains", {
    description:
      "Get a ranked shortlist (top 5) of trains between two stations, each already enriched with availability AND fare in one call — " +
      "the most efficient tool for 'what's my best/cheapest/fastest option' style requests, since it avoids calling search_trains + " +
      "check_availability + get_fare separately per train. Use preference='cheapest' for lowest fare first, 'fastest' for shortest duration, " +
      "'overnight' to prioritize trains departing 6pm or later (for sleeper-friendly overnight travel).",
    inputSchema: {
      fromStation: z.string().describe("Origin station code."),
      toStation: z.string().describe("Destination station code."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format."),
      preference: z.enum(["fastest", "cheapest", "overnight"]).describe("Ranking preference: 'fastest' = shortest duration, 'cheapest' = lowest fare, 'overnight' = prioritizes trains departing after 6pm."),
      travelClass: z.string().optional().describe("Class code to price/check availability against. Default: SL."),
      quota: z.string().optional().describe("Quota code. Default: GN."),
    },
  }, async (params) =>
    logToolExecution("recommend_trains", sanitize(params) as object, () =>
      recommendTrainsTool(params).then(ok)
    )
  );

  // ── User tools ──────────────────────────────────────────────────────────────

  server.registerTool("book_ticket", {
    description:
      "Book ONE train ticket, covering one or more passengers traveling together on the SAME journey (train/date/class/quota). " +
      "This tool books a single journey only — if the user wants tickets for multiple separate trips, call this once per trip, " +
      "not once per passenger. Always confirm trainNumber, journeyDate, travelClass, quota, and fare with check_availability/get_fare " +
      "BEFORE calling this, since booking does not itself re-verify availability or price. Returns the PNR on success.",
    inputSchema: {
      trainNumber: z.string().describe("Exact train number."),
      trainName: z.string().describe("Train name, e.g. 'Mumbai Rajdhani Express'."),
      source: z.string().describe("Boarding station code."),
      destination: z.string().describe("Destination station code."),
      journeyDate: z.string().describe("Journey date in YYYY-MM-DD format."),
      travelClass: z.string().describe("Class code — SL, 3A, 2A, 1A, CC, EC, 2S, or VS."),
      quota: z.string().describe("Quota code — GN, LD, TQ, PT, HO, or SS."),
      fare: z.number().describe("Total fare for all passengers combined, as confirmed via get_fare beforehand."),
      passengers: z.array(z.object({
        name: z.string().describe("Passenger's full name."),
        age: z.number().int().describe("Passenger's age in years."),
        gender: z.enum(["MALE", "FEMALE", "OTHER"]),
        berthPreference: z.string().optional().describe("Preferred berth: LB (lower), MB (middle), UB (upper), SL (side lower), SU or SUB (side upper), WS (window seat). Optional — omit if the passenger has no preference."),
      })).min(1).describe("One entry per passenger on this booking. Minimum 1."),
    },
  }, async (params) =>
    logToolExecution("book_ticket", sanitize({ ...params, user: user.email }) as object, () =>
      bookTicketTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("cancel_ticket", {
    description:
      "Cancel an existing booking by its PNR. This is destructive and cannot be undone — if there's any ambiguity about which " +
      "booking the user means, use track_booking or get_booking_history first to confirm the correct PNR before calling this.",
    inputSchema: { pnr: z.string().describe("The 10-digit PNR of the booking to cancel.") },
  }, async ({ pnr }) =>
    logToolExecution("cancel_ticket", sanitize({ pnr, user: user.email }) as object, () =>
      cancelTicketTool({ user, pnr }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("track_booking", {
    description:
      "Look up a booking by PNR. Use save=false for a quick one-off lookup ('what's the status of PNR X') that returns just the " +
      "raw booking object. Use save=true (the default) when the user wants ongoing PNR tracking — this additionally records/updates " +
      "a tracking entry so status changes can be checked again later, and returns that tracking record instead of the raw booking.",
    inputSchema: {
      pnr: z.string().describe("The 10-digit PNR to look up."),
      save: z.boolean().optional().describe("true (default): save/update a tracking record and return it. false: return the raw booking object only, no tracking side-effect."),
    },
  }, async ({ pnr, save }) =>
    logToolExecution("track_booking", sanitize({ pnr, save, user: user.email }) as object, () =>
      trackBookingTool({ user, pnr, save }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_booking_history", {
    description:
      "Get every booking ever made by the current user, most useful for 'show me all my bookings' or 'have I booked anything to " +
      "Mumbai before' style questions. No filtering params — if you need just one booking, use track_booking with a specific PNR instead.",
    inputSchema: {},
  }, async () =>
    logToolExecution("get_booking_history", sanitize({ user: user.email }) as object, () =>
      bookingHistoryTool(user).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("update_booking", {
    description:
      "Update an existing booking's status and/or boarding point. Provide at least one of status or newBoardingStation — you can " +
      "set both in a single call if needed. Common uses: status='BOOKED' with transactionId after payment confirms; " +
      "status='CANCELLED' behaves like cancel_ticket (prefer cancel_ticket for that specific case, it's clearer intent). " +
      "For changing where the passenger boards, check get_boarding_points first to confirm newBoardingStation is a valid stop on this train.",
    inputSchema: {
      pnr: z.string().describe("The 10-digit PNR of the booking to update."),
      status: z.enum(["PENDING", "BOOKED", "RAC", "WL", "CANCELLED", "FAILED"]).optional().describe("New booking status, if changing it."),
      transactionId: z.string().optional().describe("Payment transaction ID — relevant when setting status to BOOKED after payment."),
      newBoardingStation: z.string().optional().describe("New boarding station code, if changing the boarding point. Verify it's a valid stop via get_boarding_points first."),
    },
  }, async (params) =>
    logToolExecution("update_booking", sanitize({ ...params, user: user.email }) as object, () =>
      updateBookingTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("manage_reminder", {
    description:
      "Create, list, update, or delete ONE reminder at a time, selected via 'action'. This tool does not accept multiple reminders " +
      "in a single call — to set reminders for several bookings, call it once per reminder. " +
      "action='create': requires type + reminderAt (full ISO datetime, not just a date). type='JOURNEY' for pre-trip reminders, " +
      "'PNR' for PNR-status check reminders, 'BOOKING' for booking-related reminders. Optionally link to a booking via bookingId. " +
      "action='list': no other params needed — returns all reminders for this user, soonest first. Call this first if you need a " +
      "reminderId for update/delete and don't already have one. " +
      "action='update' / 'delete': require reminderId.",
    inputSchema: {
      action: z.enum(["create", "list", "update", "delete"]).describe("Which operation to perform."),
      type: z.enum(["JOURNEY", "PNR", "BOOKING"]).optional().describe("Reminder type. Required for action='create'."),
      reminderAt: z.string().optional().describe("Full ISO datetime, e.g. '2025-08-14T18:00:00.000Z'. Required for action='create'; optional for action='update' to reschedule."),
      bookingId: z.string().optional().describe("Booking ID to link this reminder to. Optional, action='create' only."),
      metadata: z.record(z.string(), z.unknown()).optional().describe("Free-form extra data, e.g. a note. Optional for create/update."),
      reminderId: z.string().optional().describe("ID of the reminder to change. Required for action='update' and action='delete' — get it from action='list' if you don't have it."),
    },
  }, async (params) =>
    logToolExecution("manage_reminder", sanitize({ ...params, user: user.email }) as object, () =>
      manageReminderTool({ ...params, user, metadata: params.metadata as object | undefined }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("add_saved_passenger", {
    description:
      "Save a passenger's details for reuse across future bookings, so the user doesn't have to repeat name/age/gender/berth preference " +
      "every time. Use when the user says something like 'remember this passenger' or 'save my details for next time'. " +
      "Does not itself book anything — combine with get_saved_passengers when building a book_ticket call for a returning passenger.",
    inputSchema: {
      name: z.string().describe("Passenger's full name."),
      age: z.number().int().describe("Passenger's age in years."),
      gender: z.enum(["MALE", "FEMALE", "OTHER"]),
      berthPreference: z.string().optional().describe("Preferred berth: LB, MB, UB, SL, SU/SUB, or WS. Optional."),
      seniorCitizen: z.boolean().optional().describe("Whether this passenger qualifies for senior citizen quota/discount. Default false."),
    },
  }, async (params) =>
    logToolExecution("add_saved_passenger", sanitize({ ...params, user: user.email }) as object, () =>
      addSavedPassengerTool({ ...params, user }).then(ok),
      { userId: user.email }
    )
  );

  server.registerTool("get_saved_passengers", {
    description:
      "Get all passenger profiles the user previously saved via add_saved_passenger. Use this before book_ticket when the user " +
      "refers to a previously-saved passenger by name (e.g. 'book a ticket for my usual co-traveler') so you can pull their exact " +
      "age/gender/berth preference rather than asking the user to repeat it.",
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