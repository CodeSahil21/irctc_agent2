# IRCTC MCP Server — Tool Documentation

## Overview

- **Transport**: Streamable HTTP
- **Base URL**: `http://localhost:3000`
- **MCP Endpoint**: `POST /mcp`
- **Health Check**: `GET /health`

---

## Authentication

Every request to `/mcp` requires these HTTP headers:

| Header           | Required           | Description                                                                       |
| ---------------- | ------------------ | --------------------------------------------------------------------------------- |
| `x-user-email`   | Yes                | Authenticated user's email — scopes all user-specific tools                       |
| `x-user-name`    | No                 | User's display name                                                               |
| `mcp-session-id` | No (first request) | Session ID returned after the first request — must be sent on all subsequent ones |

**First request** — omit `mcp-session-id`. The server creates a new session and returns its ID in the response header `mcp-session-id`. Include it on every request after that.

---

## Reference Values

### Travel Classes

| Code | Name                |
| ---- | ------------------- |
| `SL` | Sleeper             |
| `3A` | AC 3 Tier           |
| `2A` | AC 2 Tier           |
| `1A` | AC First Class      |
| `CC` | AC Chair Car        |
| `EC` | Executive Chair Car |
| `2S` | Second Sitting      |
| `VS` | Vistadome AC        |

### Quota Codes

| Code | Name            |
| ---- | --------------- |
| `GN` | General         |
| `LD` | Ladies          |
| `TQ` | Tatkal          |
| `PT` | Premium Tatkal  |
| `HO` | Higher Official |
| `SS` | Senior Citizen  |

### Booking Statuses

`PENDING` `BOOKED` `RAC` `WL` `CANCELLED` `FAILED`

### Reminder Types

`JOURNEY` `PNR` `BOOKING`

### Gender Values

`MALE` `FEMALE` `OTHER`

### Berth Preferences

`LB` (Lower) `MB` (Middle) `UB` (Upper) `SL` (Side Lower) `SUB` / `SU` (Side Upper) `WS` (Window Seat)

---

## MCP Request Structure

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "<tool_name>",
    "arguments": {}
  }
}
```

---

## Session Flow

```
1. POST /mcp  (no mcp-session-id header)
   → Server creates session, returns mcp-session-id in response header

2. Store mcp-session-id

3. All subsequent requests include mcp-session-id
   → Server routes to existing session

4. DELETE /mcp  (with mcp-session-id)
   → Server closes and removes session
```

---

## Tool Quick Reference

| # | Tool | Category | Side Effects |
|---|------|----------|--------------|
| 1 | `search_trains` | Public | None |
| 2 | `check_availability` | Public | None |
| 3 | `get_fare` | Public | None |
| 4 | `get_seat_map` | Public | None |
| 5 | `get_boarding_points` | Public | None |
| 6 | `get_live_status` | Public | None |
| 7 | `get_platform` | Public | None |
| 8 | `get_train_details` | Public | None |
| 9 | `get_reference_data` | Public | None |
| 10 | `find_station` | Public | None |
| 11 | `recommend_trains` | Public | None |
| 12 | `book_ticket` | User | Creates booking |
| 13 | `cancel_ticket` | User | Cancels booking (irreversible) |
| 14 | `track_booking` | User | Optionally upserts tracking record |
| 15 | `get_booking_history` | User | None |
| 16 | `update_booking` | User | Updates status / boarding point |
| 17 | `manage_reminder` | User | Creates / updates / deletes reminder |
| 18 | `add_saved_passenger` | User | Saves passenger profile |
| 19 | `get_saved_passengers` | User | None |

---

## Typical Booking Flow

```
1. find_station          → resolve city/name to station code (skip if you already have a code)
2. search_trains         → list all trains on the route and date
   — OR —
   recommend_trains      → get top 5 ranked by fastest / cheapest / overnight (includes availability + fare)
3. check_availability    → confirm seats available for chosen train + class + quota
4. get_fare              → get exact fare breakdown
5. book_ticket           → create the booking, receive PNR
6. update_booking        → set status=BOOKED + transactionId after payment
7. manage_reminder       → set a journey reminder (action="create", type="JOURNEY")
8. track_booking         → check current status any time using the PNR
```

---

## Public Tools

---

### 1. `search_trains`

Search all trains running between two stations on a specific date. Primary entry point for "find me a train from X to Y" requests. Returns a list of trains with timing, duration, and available classes — but **not** live availability or fare. Call `check_availability` and `get_fare` separately, or use `recommend_trains` for a ranked shortlist with both already included.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fromStation` | string | Yes | Origin station code (e.g. `NDLS`). Use `find_station` to resolve a name first. |
| `toStation` | string | Yes | Destination station code (e.g. `BCT`). Use `find_station` to resolve a name first. |
| `journeyDate` | string | Yes | Journey date `YYYY-MM-DD`. |
| `quota` | string | No | Quota code. Default: `GN`. Options: `GN` `LD` `TQ` `PT` `HO` `SS`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": { "name": "search_trains", "arguments": {
    "fromStation": "NDLS", "toStation": "BCT", "journeyDate": "2025-08-15", "quota": "GN"
  }}
}
```

**Response fields**: `trainNumber`, `trainName`, `type`, `departure`, `arrival`, `durationMins`, `duration`, `distance`, `classes`, `runsDays`

---

### 2. `check_availability`

Check real-time seat availability (AVAILABLE / RAC / WL and count) for one specific train, class, and quota on a given date. Use after `search_trains` once the user picks a train, or for "is there a seat on train X" questions. Not for comparing multiple trains — use `recommend_trains` for that.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number, e.g. `12951`. |
| `travelClass` | string | Yes | Class code: `SL` `3A` `2A` `1A` `CC` `EC` `2S` `VS`. |
| `quota` | string | Yes | Quota code: `GN` `LD` `TQ` `PT` `HO` `SS`. |
| `journeyDate` | string | Yes | `YYYY-MM-DD`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 2, "method": "tools/call",
  "params": { "name": "check_availability", "arguments": {
    "trainNumber": "12951", "travelClass": "3A", "quota": "GN", "journeyDate": "2025-08-15"
  }}
}
```

**Response fields**: `trainNumber`, `travelClass`, `quota`, `journeyDate`, `status` (`AVAILABLE`/`RAC`/`WL`), `count`, `label`, `available`

---

### 3. `get_fare`

Get the exact fare with full breakdown (base fare, reservation charge, superfast charge, GST, total) for one train, class, and quota between two stations. Use when the user has a specific train+class in mind and asks "how much will it cost". For comparing prices across multiple trains, use `recommend_trains` with `preference="cheapest"` instead.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `travelClass` | string | Yes | Class code. |
| `quota` | string | Yes | Quota code. |
| `fromStation` | string | Yes | Boarding station code. |
| `toStation` | string | Yes | Destination station code. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": { "name": "get_fare", "arguments": {
    "trainNumber": "12951", "travelClass": "SL", "quota": "GN", "fromStation": "NDLS", "toStation": "BCT"
  }}
}
```

**Response fields**: `trainNumber`, `travelClass`, `quota`, `fromStation`, `toStation`, `distance`, `amount`, `currency`, `breakdown` (`baseFare`, `reservationCharge`, `superfastCharge`, `gst`, `total`)

---

### 4. `get_seat_map`

Get a coach-by-coach seat map (total / booked / available seats per coach) for one train, class, and date. Use only when the user wants coach-level detail (e.g. "which coach has the most free seats"). For a simple availability check, use `check_availability` — it's cheaper and usually sufficient.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `travelClass` | string | Yes | Class code. |
| `journeyDate` | string | Yes | `YYYY-MM-DD`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 4, "method": "tools/call",
  "params": { "name": "get_seat_map", "arguments": {
    "trainNumber": "12951", "travelClass": "SL", "journeyDate": "2025-08-15"
  }}
}
```

**Response fields**: `trainNumber`, `travelClass`, `journeyDate`, `coaches[]` — each has `coach`, `totalSeats`, `bookedSeats`, `availableSeats`

---

### 5. `get_boarding_points`

List all valid boarding (pickup) points for a train from the user's intended station. Use when the user asks "can I board from an earlier station" or before calling `update_booking` to change a boarding point, to show valid options first.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `fromStation` | string | Yes | The station code the user currently intends to board from. |
| `journeyDate` | string | Yes | `YYYY-MM-DD`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 5, "method": "tools/call",
  "params": { "name": "get_boarding_points", "arguments": {
    "trainNumber": "12951", "fromStation": "NDLS", "journeyDate": "2025-08-15"
  }}
}
```

**Response fields**: `trainNumber`, `defaultBoardingPoint`, `boardingPoints[]` — each has `stationCode`, `stationName`, `departure`, `day`, `distance`

---

### 6. `get_live_status`

Get the current running status of a train — last station crossed, next station, delay in minutes. Use for "where is my train right now" or "is train X running late" questions. Only meaningful for a train en route on that date — not useful for future planning.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `date` | string | Yes | Date to check, `YYYY-MM-DD`. Usually today unless specified otherwise. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 6, "method": "tools/call",
  "params": { "name": "get_live_status", "arguments": {
    "trainNumber": "12951", "date": "2025-07-23"
  }}
}
```

---

### 7. `get_platform`

Get the platform number a train arrives/departs from at a specific station. Use for "which platform does train X leave from at station Y". Distinct from `get_boarding_points` — this returns a platform number, not a list of alternate boarding stations.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `stationCode` | string | Yes | Station code to check the platform at. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 7, "method": "tools/call",
  "params": { "name": "get_platform", "arguments": {
    "trainNumber": "12951", "stationCode": "NDLS"
  }}
}
```

---

### 8. `get_train_details`

Get info, route, and/or schedule for one train in a single call. Select sections via `include` — only request what you need.

| Section | Returns | When to use |
|---------|---------|-------------|
| `info` (default) | Name, type, classes, origin/destination, stop count | "Tell me about train X" |
| `route` | All stops with arrival/departure/distance | "What stations does it pass through" |
| `schedule` | All stops with halt duration | "Give me the full timetable" |

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Train number, e.g. `12951`. |
| `include` | string[] | No | Any of `"info"` `"route"` `"schedule"`. Default: `["info"]`. |

**Example — info only**

```json
{
  "jsonrpc": "2.0", "id": 8, "method": "tools/call",
  "params": { "name": "get_train_details", "arguments": {
    "trainNumber": "12301", "include": ["info"]
  }}
}
```

**Example — everything**

```json
{
  "jsonrpc": "2.0", "id": 8, "method": "tools/call",
  "params": { "name": "get_train_details", "arguments": {
    "trainNumber": "12301", "include": ["info", "route", "schedule"]
  }}
}
```

**Response**: object with keys matching the requested `include` values.

---

### 9. `get_reference_data`

Get the full list of valid travel class codes and quota codes with human-readable names, in one call. Call this whenever you're unsure which code maps to what the user said (e.g. "AC first class" → `1A`) before passing `travelClass` or `quota` into any other tool.

**Input**: None

**Example**

```json
{
  "jsonrpc": "2.0", "id": 9, "method": "tools/call",
  "params": { "name": "get_reference_data", "arguments": {} }
}
```

**Response fields**: `classes[]` — array of `{ code, name }`, `quotas[]` — array of `{ code, name }`

---

### 10. `find_station`

Resolve a station name, city, or partial text into IRCTC station code(s) — or find stations near a coordinate. **Do not call this if you already have a valid station code** (2–5 uppercase letters like `NDLS`) — pass it directly into other tools.

Three modes — pick exactly one:

| Mode | Params | Returns | When to use |
|------|--------|---------|-------------|
| Text search | `query` only | Up to 10 matches | Ambiguous name, need to show user options |
| Exact lookup | `query` + `exactMatch=true` | Single `{ code, fullName }` | Just need a code to feed into another tool |
| Nearby | `lat` + `lng` | Stations within 50 km | "Stations near me" / location-based |

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | No | Station name, city, or partial code. Omit if using `lat`/`lng`. |
| `lat` | number | No | Latitude. Must be paired with `lng`. |
| `lng` | number | No | Longitude. Must be paired with `lat`. |
| `exactMatch` | boolean | No | `true` = single best match. `false` (default) = up to 10 matches. Ignored if using `lat`/`lng`. |

**Examples**

```json
// Text search
{ "params": { "name": "find_station", "arguments": { "query": "Mumbai" } } }

// Exact code lookup
{ "params": { "name": "find_station", "arguments": { "query": "New Delhi", "exactMatch": true } } }

// Nearby stations
{ "params": { "name": "find_station", "arguments": { "lat": 28.6139, "lng": 77.2090 } } }
```

---

### 11. `recommend_trains`

Get a ranked shortlist (top 5) of trains between two stations, each enriched with availability AND fare in one call. The most efficient tool for "what's my best / cheapest / fastest option" requests — avoids calling `search_trains` + `check_availability` + `get_fare` separately per train.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fromStation` | string | Yes | Origin station code. |
| `toStation` | string | Yes | Destination station code. |
| `journeyDate` | string | Yes | `YYYY-MM-DD`. |
| `preference` | string | Yes | `fastest` = shortest duration · `cheapest` = lowest fare · `overnight` = departs after 6 pm |
| `travelClass` | string | No | Class to price/check against. Default: `SL`. |
| `quota` | string | No | Quota. Default: `GN`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 11, "method": "tools/call",
  "params": { "name": "recommend_trains", "arguments": {
    "fromStation": "NDLS", "toStation": "BCT", "journeyDate": "2025-08-15",
    "preference": "fastest", "travelClass": "3A", "quota": "GN"
  }}
}
```

**Response fields**: `trains[]` — top 5, each with full train info + `availability` + `fare`

---

## User Tools

All user tools require the `x-user-email` header.

---

### 12. `book_ticket`

Book one train ticket for one or more passengers on the same journey. Always call `check_availability` and `get_fare` first — this tool does not re-verify either. Returns the PNR on success. For multiple separate trips, call once per trip.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trainNumber` | string | Yes | Exact train number. |
| `trainName` | string | Yes | Train name. |
| `source` | string | Yes | Boarding station code. |
| `destination` | string | Yes | Destination station code. |
| `journeyDate` | string | Yes | `YYYY-MM-DD`. |
| `travelClass` | string | Yes | Class code. |
| `quota` | string | Yes | Quota code. |
| `fare` | number | Yes | Total fare for all passengers combined (from `get_fare`). |
| `passengers` | array | Yes | Min 1. See passenger object below. |

**Passenger object**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Full name. |
| `age` | integer | Yes | Age in years. |
| `gender` | string | Yes | `MALE` / `FEMALE` / `OTHER` |
| `berthPreference` | string | No | `LB` `MB` `UB` `SL` `SU`/`SUB` `WS`. Omit if no preference. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 12, "method": "tools/call",
  "params": { "name": "book_ticket", "arguments": {
    "trainNumber": "12951", "trainName": "Mumbai Rajdhani Express",
    "source": "NDLS", "destination": "BCT", "journeyDate": "2025-08-15",
    "travelClass": "3A", "quota": "GN", "fare": 1450,
    "passengers": [
      { "name": "Rahul Sharma", "age": 28, "gender": "MALE", "berthPreference": "LB" },
      { "name": "Priya Sharma", "age": 25, "gender": "FEMALE", "berthPreference": "MB" }
    ]
  }}
}
```

**Response fields**: `pnr`, `status`, `bookedAt`, `trainNumber`, `trainName`, `source`, `destination`, `journeyDate`, `travelClass`, `quota`, `fare`, `passengerCount`, `passengers[]`

---

### 13. `cancel_ticket`

Cancel an existing booking by PNR. **Irreversible.** If there's any ambiguity about which booking the user means, call `track_booking` or `get_booking_history` first to confirm the correct PNR.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pnr` | string | Yes | 10-digit PNR to cancel. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 13, "method": "tools/call",
  "params": { "name": "cancel_ticket", "arguments": { "pnr": "4521367890" } }
}
```

---

### 14. `track_booking`

Look up a booking by PNR. Two modes:

- `save=false` — quick one-off lookup, returns the raw booking object with no side effects.
- `save=true` (default) — additionally upserts a tracking record for ongoing status monitoring, returns that tracking record.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pnr` | string | Yes | 10-digit PNR. |
| `save` | boolean | No | `true` (default) = save tracking + return tracking record. `false` = raw booking only. |

**Example — default (with tracking)**

```json
{
  "jsonrpc": "2.0", "id": 14, "method": "tools/call",
  "params": { "name": "track_booking", "arguments": { "pnr": "4521367890" } }
}
```

**Example — raw lookup only**

```json
{
  "jsonrpc": "2.0", "id": 14, "method": "tools/call",
  "params": { "name": "track_booking", "arguments": { "pnr": "4521367890", "save": false } }
}
```

**Response**:
- `save=true`: `id`, `userId`, `pnr`, `lastStatus` (full booking + passenger status), `checkedAt`
- `save=false`: full booking object with `passengers[]`

---

### 15. `get_booking_history`

Get all bookings ever made by the current user. Use for "show me all my bookings" style questions. No filtering — if you need a single booking, use `track_booking` with a specific PNR instead.

**Input**: None

**Example**

```json
{
  "jsonrpc": "2.0", "id": 15, "method": "tools/call",
  "params": { "name": "get_booking_history", "arguments": {} }
}
```

**Response**: array of booking objects with `passengers[]`

---

### 16. `update_booking`

Update an existing booking's status and/or boarding point in one atomic call. At least one of `status` or `newBoardingStation` must be provided. Both can be updated in a single call. Common uses: set `status=BOOKED` + `transactionId` after payment; change boarding point (verify the new station via `get_boarding_points` first).

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pnr` | string | Yes | 10-digit PNR. |
| `status` | string | No | `PENDING` `BOOKED` `RAC` `WL` `CANCELLED` `FAILED` |
| `transactionId` | string | No | Payment transaction ID — pair with `status=BOOKED`. |
| `newBoardingStation` | string | No | New boarding station code. Verify via `get_boarding_points` first. |

**Example — confirm payment**

```json
{
  "jsonrpc": "2.0", "id": 16, "method": "tools/call",
  "params": { "name": "update_booking", "arguments": {
    "pnr": "4521367890", "status": "BOOKED", "transactionId": "TXN123456789"
  }}
}
```

**Example — change boarding point**

```json
{
  "jsonrpc": "2.0", "id": 16, "method": "tools/call",
  "params": { "name": "update_booking", "arguments": {
    "pnr": "4521367890", "newBoardingStation": "MTJ"
  }}
}
```

---

### 17. `manage_reminder`

Create, list, update, or delete one reminder at a time using the `action` field. To set reminders for multiple bookings, call once per reminder.

| action | Required extra fields | Optional fields |
|--------|----------------------|-----------------|
| `create` | `type`, `reminderAt` | `bookingId`, `metadata` |
| `list` | — | — |
| `update` | `reminderId` | `reminderAt`, `type`, `metadata` |
| `delete` | `reminderId` | — |

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `create` `list` `update` `delete` |
| `type` | string | Req. for create | `JOURNEY` `PNR` `BOOKING` |
| `reminderAt` | string | Req. for create | Full ISO datetime, e.g. `2025-08-14T18:00:00.000Z`. Optional for update (to reschedule). |
| `bookingId` | string | No | Booking ID to link (create only). |
| `metadata` | object | No | Free-form extra data, e.g. `{ "note": "..." }`. |
| `reminderId` | string | Req. for update/delete | Get from `action="list"` if unknown. |

**Examples**

```json
// Create
{ "params": { "name": "manage_reminder", "arguments": {
  "action": "create", "type": "JOURNEY", "reminderAt": "2025-08-14T18:00:00.000Z",
  "bookingId": "booking-uuid", "metadata": { "note": "Reach station 1 hour early" }
}}}

// List
{ "params": { "name": "manage_reminder", "arguments": { "action": "list" } } }

// Update
{ "params": { "name": "manage_reminder", "arguments": {
  "action": "update", "reminderId": "reminder-uuid", "reminderAt": "2025-08-14T16:00:00.000Z"
}}}

// Delete
{ "params": { "name": "manage_reminder", "arguments": {
  "action": "delete", "reminderId": "reminder-uuid"
}}}
```

**Response**:
- `create`: `id`, `userId`, `type`, `reminderAt`, `bookingId`, `metadata`, `sent`, `createdAt`
- `list`: array of reminders ordered by `reminderAt` ascending
- `update`: updated reminder object
- `delete`: deleted reminder object

---

### 18. `add_saved_passenger`

Save a passenger profile for reuse in future bookings. Use when the user says "remember this person" or "save my details for next time". Does not create a booking — combine with `get_saved_passengers` when building a `book_ticket` call for a returning passenger.

**Input**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Passenger's full name. |
| `age` | integer | Yes | Age in years. |
| `gender` | string | Yes | `MALE` / `FEMALE` / `OTHER` |
| `berthPreference` | string | No | `LB` `MB` `UB` `SL` `SU`/`SUB` `WS`. |
| `seniorCitizen` | boolean | No | Qualifies for senior citizen quota/discount. Default `false`. |

**Example**

```json
{
  "jsonrpc": "2.0", "id": 18, "method": "tools/call",
  "params": { "name": "add_saved_passenger", "arguments": {
    "name": "Rahul Sharma", "age": 28, "gender": "MALE", "berthPreference": "LB", "seniorCitizen": false
  }}
}
```

**Response fields**: `id`, `userId`, `name`, `age`, `gender`, `berthPreference`, `seniorCitizen`, `createdAt`

---

### 19. `get_saved_passengers`

Get all passenger profiles saved by the current user. Use before `book_ticket` when the user refers to a previously-saved passenger by name so you can pull their exact details rather than asking the user to repeat them.

**Input**: None

**Example**

```json
{
  "jsonrpc": "2.0", "id": 19, "method": "tools/call",
  "params": { "name": "get_saved_passengers", "arguments": {} }
}
```

**Response**: array of passenger profile objects

---

## Error Responses

Tool errors return an MCP content block with `isError: true` and a JSON body:

```json
{
  "error": "Booking '9999999999' not found",
  "code": "NOT_FOUND",
  "jsonRpcCode": -32001
}
```

| `jsonRpcCode` | Meaning | When |
|---------------|---------|------|
| `-32602` | Invalid params | Bad input, fix and retry |
| `-32001` | Not found | Resource doesn't exist, don't retry |
| `-32002` | Forbidden | Resource belongs to another user |
| `-32003` | Upstream error | IRCTC call failed, may retry |
| `-32603` | Internal error | Unexpected server error |

HTTP-level errors (before MCP dispatch):

| HTTP Status | Meaning |
|-------------|---------|
| `401` | Missing `x-user-email` header |
| `403` | Session does not belong to this user |
| `404` | Session not found |
