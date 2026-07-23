/**
 * tools.ts — Canonical tool manifest for the IRCTC MCP Server.
 *
 * This file mirrors every tool registered in mcp_server_irctc/src/index.ts and
 * serves as the authoritative reference for tool names, categories, input schemas,
 * and descriptions. Import `TOOLS` or `TOOL_MAP` wherever you need a programmatic
 * list without spinning up the MCP server.
 *
 * Categories:
 *   "public" — no authentication required
 *   "user"   — requires x-user-email header (scoped to authenticated user)
 */

// ── Enum constants ────────────────────────────────────────────────────────────

export const TRAVEL_CLASSES = ["SL", "3A", "2A", "1A", "CC", "EC", "2S", "VS"] as const;
export type TravelClass = (typeof TRAVEL_CLASSES)[number];

export const QUOTA_CODES = ["GN", "LD", "TQ", "PT", "HO", "SS"] as const;
export type QuotaCode = (typeof QUOTA_CODES)[number];

export const BOOKING_STATUSES = ["PENDING", "BOOKED", "RAC", "WL", "CANCELLED", "FAILED"] as const;
export type BookingStatus = (typeof BOOKING_STATUSES)[number];

export const REMINDER_TYPES = ["JOURNEY", "PNR", "BOOKING"] as const;
export type ReminderType = (typeof REMINDER_TYPES)[number];

export const GENDERS = ["MALE", "FEMALE", "OTHER"] as const;
export type Gender = (typeof GENDERS)[number];

export const BERTH_PREFERENCES = ["LB", "MB", "UB", "SL", "SUB", "WS"] as const;
export type BerthPreference = (typeof BERTH_PREFERENCES)[number];

// ── Field descriptor ──────────────────────────────────────────────────────────

export interface FieldDef {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  description: string;
  required: boolean;
  enum?: readonly string[];
  items?: FieldDef;
  properties?: Record<string, FieldDef>;
  minItems?: number;
}

// ── Tool descriptor ───────────────────────────────────────────────────────────

export type ToolCategory = "public" | "user";

export interface ToolDef {
  name: string;
  description: string;
  category: ToolCategory;
  /**
   * readOnly=true  — tool only reads data, has no side-effects.
   * readOnly=false — tool writes data (booking, cancel, update, etc.).
   */
  readOnly: boolean;
  /**
   * destructive=true — tool permanently alters state (cancel, delete).
   * Should be confirmed with the user before calling.
   */
  destructive: boolean;
  inputSchema: Record<string, FieldDef>;
}

// ── Tool definitions ──────────────────────────────────────────────────────────

export const TOOLS: ToolDef[] = [
  // ── Public tools ────────────────────────────────────────────────────────────

  {
    name: "search_trains",
    description: "Search trains between two stations on a given date.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      fromStation: {
        type: "string",
        description: "Origin station code e.g. NDLS",
        required: true,
      },
      toStation: {
        type: "string",
        description: "Destination station code e.g. BCT",
        required: true,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
      quota: {
        type: "string",
        description: "Quota code. Default: GN",
        required: false,
        enum: QUOTA_CODES,
      },
    },
  },

  {
    name: "check_availability",
    description: "Check seat availability for a train on a given date.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number e.g. 12951",
        required: true,
      },
      travelClass: {
        type: "string",
        description: "Class code e.g. SL, 3A, 2A, 1A",
        required: true,
        enum: TRAVEL_CLASSES,
      },
      quota: {
        type: "string",
        description: "Quota code e.g. GN, TQ",
        required: true,
        enum: QUOTA_CODES,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
    },
  },

  {
    name: "get_fare",
    description: "Get fare for a train between two stations.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      travelClass: {
        type: "string",
        description: "Class code e.g. SL, 3A, 2A, 1A",
        required: true,
        enum: TRAVEL_CLASSES,
      },
      quota: {
        type: "string",
        description: "Quota code e.g. GN, TQ",
        required: true,
        enum: QUOTA_CODES,
      },
      fromStation: {
        type: "string",
        description: "Origin station code",
        required: true,
      },
      toStation: {
        type: "string",
        description: "Destination station code",
        required: true,
      },
    },
  },

  {
    name: "get_seat_map",
    description: "Get coach-wise seat availability map for a train.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      travelClass: {
        type: "string",
        description: "Class code e.g. SL, 3A",
        required: true,
        enum: TRAVEL_CLASSES,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
    },
  },

  {
    name: "get_boarding_points",
    description: "Get available boarding points for a train from a station.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      fromStation: {
        type: "string",
        description: "Origin station code",
        required: true,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
    },
  },

  {
    name: "get_live_status",
    description: "Get live running status of a train.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      date: {
        type: "string",
        description: "Date in YYYY-MM-DD format",
        required: true,
      },
    },
  },

  {
    name: "get_platform",
    description: "Get platform number for a train at a station.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      stationCode: {
        type: "string",
        description: "Station code e.g. NDLS",
        required: true,
      },
    },
  },

  {
    name: "get_train_details",
    description:
      "Get train info, route, and/or schedule by train number. Use include to select which sections to return.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number e.g. 12951",
        required: true,
      },
      include: {
        type: "array",
        description:
          "Sections to include. Default: ['info']. Pass ['info','route','schedule'] for everything.",
        required: false,
        items: {
          type: "string",
          description: "Section name",
          required: true,
          enum: ["info", "route", "schedule"],
        },
      },
    },
  },

  {
    name: "get_reference_data",
    description: "Get all travel classes and quota codes in one call.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {},
  },

  {
    name: "find_station",
    description:
      "Find stations by text query (name/code/city) or by lat/lng for nearby stations. Set exactMatch=true to get a single best-match code lookup.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      query: {
        type: "string",
        description:
          "Station name, code or city — partial match supported. Required if lat/lng not provided.",
        required: false,
      },
      lat: {
        type: "number",
        description: "Latitude for nearby search. Must be paired with lng.",
        required: false,
      },
      lng: {
        type: "number",
        description: "Longitude for nearby search. Must be paired with lat.",
        required: false,
      },
      exactMatch: {
        type: "boolean",
        description:
          "true = return single best-match { code, fullName }; false (default) = return up to 10 matches.",
        required: false,
      },
    },
  },

  {
    name: "recommend_trains",
    description: "Get train recommendations ranked by fastest, cheapest or overnight.",
    category: "public",
    readOnly: true,
    destructive: false,
    inputSchema: {
      fromStation: {
        type: "string",
        description: "Origin station code",
        required: true,
      },
      toStation: {
        type: "string",
        description: "Destination station code",
        required: true,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
      preference: {
        type: "string",
        description: "Ranking preference",
        required: true,
        enum: ["fastest", "cheapest", "overnight"],
      },
      travelClass: {
        type: "string",
        description: "Class code. Default: SL",
        required: false,
        enum: TRAVEL_CLASSES,
      },
      quota: {
        type: "string",
        description: "Quota code. Default: GN",
        required: false,
        enum: QUOTA_CODES,
      },
    },
  },

  // ── User tools ───────────────────────────────────────────────────────────────

  {
    name: "book_ticket",
    description: "Book a train ticket for the authenticated user.",
    category: "user",
    readOnly: false,
    destructive: false,
    inputSchema: {
      trainNumber: {
        type: "string",
        description: "Train number",
        required: true,
      },
      trainName: {
        type: "string",
        description: "Train name",
        required: true,
      },
      source: {
        type: "string",
        description: "Boarding station code",
        required: true,
      },
      destination: {
        type: "string",
        description: "Destination station code",
        required: true,
      },
      journeyDate: {
        type: "string",
        description: "Journey date in YYYY-MM-DD format",
        required: true,
      },
      travelClass: {
        type: "string",
        description: "Class code e.g. SL, 3A, 2A, 1A",
        required: true,
        enum: TRAVEL_CLASSES,
      },
      quota: {
        type: "string",
        description: "Quota code e.g. GN, TQ",
        required: true,
        enum: QUOTA_CODES,
      },
      fare: {
        type: "number",
        description: "Total fare amount in INR",
        required: true,
      },
      passengers: {
        type: "array",
        description: "List of passengers. Minimum 1 required.",
        required: true,
        minItems: 1,
        items: {
          type: "object",
          description: "Passenger details",
          required: true,
          properties: {
            name: {
              type: "string",
              description: "Passenger full name",
              required: true,
            },
            age: {
              type: "integer",
              description: "Age in years",
              required: true,
            },
            gender: {
              type: "string",
              description: "Gender",
              required: true,
              enum: GENDERS,
            },
            berthPreference: {
              type: "string",
              description: "Preferred berth type",
              required: false,
              enum: BERTH_PREFERENCES,
            },
          },
        },
      },
      idempotencyKey: {
        type: "string",
        description:
          "Optional client-generated UUID for this booking intent. If a booking with this key already exists for the user, it is returned instead of creating a duplicate. Use to safely retry on timeout without double-booking.",
        required: false,
      },
    },
  },

  {
    name: "cancel_ticket",
    description: "Cancel a booked ticket by PNR.",
    category: "user",
    readOnly: false,
    destructive: true,
    inputSchema: {
      pnr: {
        type: "string",
        description: "PNR number of the booking to cancel",
        required: true,
      },
    },
  },

  {
    name: "track_booking",
    description:
      "Get booking details by PNR. Set save=true (default) to also save PNR tracking history and return the tracking record. Set save=false to return the raw booking object only.",
    category: "user",
    readOnly: true,
    destructive: false,
    inputSchema: {
      pnr: {
        type: "string",
        description: "PNR number",
        required: true,
      },
      save: {
        type: "boolean",
        description:
          "true (default) = save tracking + return tracking record; false = return booking object only.",
        required: false,
      },
    },
  },

  {
    name: "get_booking_history",
    description: "Get all bookings for the authenticated user.",
    category: "user",
    readOnly: true,
    destructive: false,
    inputSchema: {},
  },

  {
    name: "update_booking",
    description:
      "Update status and/or boarding point for a booking. At least one of status or newBoardingStation must be provided.",
    category: "user",
    readOnly: false,
    destructive: false,
    inputSchema: {
      pnr: {
        type: "string",
        description: "PNR number",
        required: true,
      },
      status: {
        type: "string",
        description: "New booking status",
        required: false,
        enum: BOOKING_STATUSES,
      },
      transactionId: {
        type: "string",
        description: "Payment transaction ID (pair with status update)",
        required: false,
      },
      newBoardingStation: {
        type: "string",
        description: "New boarding station code",
        required: false,
      },
    },
  },

  {
    name: "manage_reminder",
    description:
      "Create, list, update or delete reminders. Use action to specify the operation.",
    category: "user",
    readOnly: false,
    destructive: false,
    inputSchema: {
      action: {
        type: "string",
        description: "Operation to perform",
        required: true,
        enum: ["create", "list", "update", "delete"],
      },
      type: {
        type: "string",
        description: "Reminder type. Required for create.",
        required: false,
        enum: REMINDER_TYPES,
      },
      reminderAt: {
        type: "string",
        description:
          "ISO datetime e.g. 2025-08-14T18:00:00.000Z. Required for create; optional for update.",
        required: false,
      },
      bookingId: {
        type: "string",
        description: "Booking ID to link (create only).",
        required: false,
      },
      metadata: {
        type: "object",
        description: "Any extra key-value data.",
        required: false,
      },
      reminderId: {
        type: "string",
        description: "Reminder ID. Required for update and delete.",
        required: false,
      },
    },
  },

  {
    name: "add_saved_passenger",
    description: "Save a passenger profile for future bookings.",
    category: "user",
    readOnly: false,
    destructive: false,
    inputSchema: {
      name: {
        type: "string",
        description: "Passenger full name",
        required: true,
      },
      age: {
        type: "integer",
        description: "Age in years",
        required: true,
      },
      gender: {
        type: "string",
        description: "Gender",
        required: true,
        enum: GENDERS,
      },
      berthPreference: {
        type: "string",
        description: "Preferred berth type",
        required: false,
        enum: BERTH_PREFERENCES,
      },
      seniorCitizen: {
        type: "boolean",
        description: "Whether the passenger qualifies for senior citizen quota. Default: false.",
        required: false,
      },
    },
  },

  {
    name: "get_saved_passengers",
    description: "Get all saved passenger profiles for the authenticated user.",
    category: "user",
    readOnly: true,
    destructive: false,
    inputSchema: {},
  },
];

// ── Convenience lookup ────────────────────────────────────────────────────────

/** O(1) lookup by tool name. */
export const TOOL_MAP: Readonly<Record<string, ToolDef>> = Object.freeze(
  Object.fromEntries(TOOLS.map((t) => [t.name, t]))
);

/** All public tool names (no auth required). */
export const PUBLIC_TOOLS: readonly string[] = TOOLS
  .filter((t) => t.category === "public")
  .map((t) => t.name);

/** All user-scoped tool names (require x-user-email). */
export const USER_TOOLS: readonly string[] = TOOLS
  .filter((t) => t.category === "user")
  .map((t) => t.name);

/** Tools that write or mutate state. */
export const WRITE_TOOLS: readonly string[] = TOOLS
  .filter((t) => !t.readOnly)
  .map((t) => t.name);

/** Tools that are destructive (cancel, delete). Confirm before calling. */
export const DESTRUCTIVE_TOOLS: readonly string[] = TOOLS
  .filter((t) => t.destructive)
  .map((t) => t.name);
