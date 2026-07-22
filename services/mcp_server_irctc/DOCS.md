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
| `x-user-email`   | Yes                | Authenticated user's email — used to scope all user tools                         |
| `x-user-name`    | No                 | User's display name                                                               |
| `mcp-session-id` | No (first request) | Session ID returned after first request — must be sent on all subsequent requests |

**First request** — do not send `mcp-session-id`. The server creates a new session and returns the session ID in the response headers as `mcp-session-id`. Send it on every request after that.

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

### Booking Status Values

`PENDING` `BOOKED` `RAC` `WL` `CANCELLED` `FAILED`

### Reminder Types

`JOURNEY` `PNR` `BOOKING`

### Gender Values

`MALE` `FEMALE` `OTHER`

---

## MCP JSON Request Structure

Every tool call follows this structure:

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

## Tools

---

### 1. `search_trains`

Search trains between two stations on a given date.

**Category**: Public

**Input**

| Field         | Type   | Required | Description                         |
| ------------- | ------ | -------- | ----------------------------------- |
| `fromStation` | string | Yes      | Origin station code e.g. `NDLS`     |
| `toStation`   | string | Yes      | Destination station code e.g. `BCT` |
| `journeyDate` | string | Yes      | Journey date in `YYYY-MM-DD` format |
| `quota`       | string | No       | Quota code. Default: `GN`           |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_trains",
        "arguments": {
            "fromStation": "NDLS",
            "toStation": "BCT",
            "journeyDate": "2025-08-15",
            "quota": "GN"
        }
    }
}
```

**Response fields**: `trainNumber`, `trainName`, `type`, `departure`, `arrival`, `durationMins`, `duration`, `distance`, `classes`, `runsDays`

---

### 2. `check_availability`

Check seat availability for a train on a given date.

**Category**: Public

**Input**

| Field         | Type   | Required | Description                            |
| ------------- | ------ | -------- | -------------------------------------- |
| `trainNumber` | string | Yes      | Train number e.g. `12951`              |
| `travelClass` | string | Yes      | Class code e.g. `SL`, `3A`, `2A`, `1A` |
| `quota`       | string | Yes      | Quota code e.g. `GN`, `TQ`             |
| `journeyDate` | string | Yes      | `YYYY-MM-DD`                           |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "check_availability",
        "arguments": {
            "trainNumber": "12951",
            "travelClass": "3A",
            "quota": "GN",
            "journeyDate": "2025-08-15"
        }
    }
}
```

**Response fields**: `trainNumber`, `travelClass`, `quota`, `journeyDate`, `status` (`AVAILABLE`/`RAC`/`WL`), `count`, `label`, `available`

---

### 3. `get_fare`

Get fare for a train between two stations.

**Category**: Public

**Input**

| Field         | Type   | Required | Description              |
| ------------- | ------ | -------- | ------------------------ |
| `trainNumber` | string | Yes      | Train number             |
| `travelClass` | string | Yes      | Class code               |
| `quota`       | string | Yes      | Quota code               |
| `fromStation` | string | Yes      | Origin station code      |
| `toStation`   | string | Yes      | Destination station code |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "get_fare",
        "arguments": {
            "trainNumber": "12951",
            "travelClass": "SL",
            "quota": "GN",
            "fromStation": "NDLS",
            "toStation": "BCT"
        }
    }
}
```

**Response fields**: `trainNumber`, `travelClass`, `quota`, `fromStation`, `toStation`, `distance`, `amount`, `currency`, `breakdown` (`baseFare`, `reservationCharge`, `superfastCharge`, `gst`, `total`)

---

### 4. `get_route`

Get full route and all stops of a train.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "get_route",
        "arguments": {
            "trainNumber": "12301"
        }
    }
}
```

**Response fields**: `trainNumber`, `stops[]` — each stop has `stopNumber`, `stationCode`, `stationName`, `city`, `arrival`, `departure`, `day`, `distance`

---

### 5. `get_seat_map`

Get coach-wise seat availability map for a train.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |
| `travelClass` | string | Yes      | Class code   |
| `journeyDate` | string | Yes      | `YYYY-MM-DD` |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
        "name": "get_seat_map",
        "arguments": {
            "trainNumber": "12951",
            "travelClass": "SL",
            "journeyDate": "2025-08-15"
        }
    }
}
```

**Response fields**: `trainNumber`, `travelClass`, `journeyDate`, `coaches[]` — each coach has `coach`, `totalSeats`, `bookedSeats`, `availableSeats`

---

### 6. `get_boarding_points`

Get available boarding points for a train from a station.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |
| `fromStation` | string | Yes      | Station code |
| `journeyDate` | string | Yes      | `YYYY-MM-DD` |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
        "name": "get_boarding_points",
        "arguments": {
            "trainNumber": "12951",
            "fromStation": "NDLS",
            "journeyDate": "2025-08-15"
        }
    }
}
```

**Response fields**: `trainNumber`, `defaultBoardingPoint`, `boardingPoints[]` — each has `stationCode`, `stationName`, `departure`, `day`, `distance`

---

### 7. `search_train_by_number`

Get train details by train number.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
        "name": "search_train_by_number",
        "arguments": {
            "trainNumber": "12301"
        }
    }
}
```

**Response fields**: `trainNumber`, `trainName`, `type`, `runsDays`, `classes[]`, `origin`, `destination`, `departure`, `arrival`, `totalStops`

---

### 8. `get_live_status`

Get live running status of a train.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |
| `date`        | string | Yes      | `YYYY-MM-DD` |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 8,
    "method": "tools/call",
    "params": {
        "name": "get_live_status",
        "arguments": {
            "trainNumber": "12301",
            "date": "2025-08-15"
        }
    }
}
```

**Response fields**: `trainNumber`, `date`, `currentStatus`, `delayMins`, `lastCrossedStation` (`code`, `name`, `at`), `nextStation` (`code`, `name`, `expectedArrival`)

---

### 9. `get_train_schedule`

Get full timetable/schedule of a train.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 9,
    "method": "tools/call",
    "params": {
        "name": "get_train_schedule",
        "arguments": {
            "trainNumber": "12621"
        }
    }
}
```

**Response fields**: `trainNumber`, `trainName`, `runsDays`, `schedule[]` — each stop has `stopNumber`, `stationCode`, `stationName`, `arrival`, `departure`, `day`, `haltMins`, `distance`

---

### 10. `get_platform`

Get platform number for a train at a station.

**Category**: Public

**Input**

| Field         | Type   | Required | Description  |
| ------------- | ------ | -------- | ------------ |
| `trainNumber` | string | Yes      | Train number |
| `stationCode` | string | Yes      | Station code |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
        "name": "get_platform",
        "arguments": {
            "trainNumber": "12301",
            "stationCode": "NDLS"
        }
    }
}
```

**Response fields**: `trainNumber`, `stationCode`, `stationName`, `platform`, `scheduledArrival`, `scheduledDeparture`

---

### 11. `search_stations`

Search stations by name, code or city.

**Category**: Public

**Input**

| Field   | Type   | Required | Description                                          |
| ------- | ------ | -------- | ---------------------------------------------------- |
| `query` | string | Yes      | Station name, code or city — partial match supported |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 11,
    "method": "tools/call",
    "params": {
        "name": "search_stations",
        "arguments": {
            "query": "Mumbai"
        }
    }
}
```

**Response fields**: `stations[]` — each has `code`, `name`, `city`, `state`

---

### 12. `find_station_code`

Find station code from station name or city.

**Category**: Public

**Input**

| Field   | Type   | Required | Description          |
| ------- | ------ | -------- | -------------------- |
| `query` | string | Yes      | Station name or city |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 12,
    "method": "tools/call",
    "params": {
        "name": "find_station_code",
        "arguments": {
            "query": "New Delhi"
        }
    }
}
```

**Response fields**: `code`, `fullName`

---

### 13. `get_nearby_stations`

Get railway stations near a geographic location (within 50km).

**Category**: Public

**Input**

| Field | Type   | Required | Description |
| ----- | ------ | -------- | ----------- |
| `lat` | number | Yes      | Latitude    |
| `lng` | number | Yes      | Longitude   |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 13,
    "method": "tools/call",
    "params": {
        "name": "get_nearby_stations",
        "arguments": {
            "lat": 28.6139,
            "lng": 77.209
        }
    }
}
```

**Response fields**: `lat`, `lng`, `stations[]` — each has `code`, `name`, `city`, `state`, `distKm`

---

### 14. `list_classes`

List all available travel classes.

**Category**: Public

**Input**: None

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 14,
    "method": "tools/call",
    "params": {
        "name": "list_classes",
        "arguments": {}
    }
}
```

**Response fields**: array of `{ code, name }`

---

### 15. `list_quotas`

List all available booking quotas.

**Category**: Public

**Input**: None

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 15,
    "method": "tools/call",
    "params": {
        "name": "list_quotas",
        "arguments": {}
    }
}
```

**Response fields**: array of `{ code, name }`

---

### 16. `recommend_trains`

Get train recommendations ranked by preference.

**Category**: Public

**Input**

| Field         | Type   | Required | Description                          |
| ------------- | ------ | -------- | ------------------------------------ |
| `fromStation` | string | Yes      | Origin station code                  |
| `toStation`   | string | Yes      | Destination station code             |
| `journeyDate` | string | Yes      | `YYYY-MM-DD`                         |
| `preference`  | string | Yes      | `fastest` / `cheapest` / `overnight` |
| `travelClass` | string | No       | Class code. Default: `SL`            |
| `quota`       | string | No       | Quota code. Default: `GN`            |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 16,
    "method": "tools/call",
    "params": {
        "name": "recommend_trains",
        "arguments": {
            "fromStation": "NDLS",
            "toStation": "BCT",
            "journeyDate": "2025-08-15",
            "preference": "fastest",
            "travelClass": "3A",
            "quota": "GN"
        }
    }
}
```

**Response fields**: `trains[]` — top 5 trains each with full train info + `availability` + `fare`

---

### 17. `book_ticket`

Book a train ticket for the authenticated user.

**Category**: User (requires `x-user-email` header)

**Input**

| Field         | Type   | Required | Description                                 |
| ------------- | ------ | -------- | ------------------------------------------- |
| `trainNumber` | string | Yes      | Train number                                |
| `trainName`   | string | Yes      | Train name                                  |
| `source`      | string | Yes      | Boarding station code                       |
| `destination` | string | Yes      | Destination station code                    |
| `journeyDate` | string | Yes      | `YYYY-MM-DD`                                |
| `travelClass` | string | Yes      | Class code                                  |
| `quota`       | string | Yes      | Quota code                                  |
| `fare`        | number | Yes      | Total fare amount                           |
| `passengers`  | array  | Yes      | Min 1 passenger. See passenger object below |

**Passenger object**

| Field             | Type    | Required | Description                       |
| ----------------- | ------- | -------- | --------------------------------- |
| `name`            | string  | Yes      | Passenger full name               |
| `age`             | integer | Yes      | Age in years                      |
| `gender`          | string  | Yes      | `MALE` / `FEMALE` / `OTHER`       |
| `berthPreference` | string  | No       | e.g. `LB`, `MB`, `UB`, `SL`, `SU` |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 17,
    "method": "tools/call",
    "params": {
        "name": "book_ticket",
        "arguments": {
            "trainNumber": "12951",
            "trainName": "Mumbai Rajdhani Express",
            "source": "NDLS",
            "destination": "BCT",
            "journeyDate": "2025-08-15",
            "travelClass": "3A",
            "quota": "GN",
            "fare": 1450,
            "passengers": [
                {
                    "name": "Rahul Sharma",
                    "age": 28,
                    "gender": "MALE",
                    "berthPreference": "LB"
                },
                {
                    "name": "Priya Sharma",
                    "age": 25,
                    "gender": "FEMALE",
                    "berthPreference": "MB"
                }
            ]
        }
    }
}
```

**Response fields**: full booking object with `id`, `pnr`, `status`, `trainNumber`, `trainName`, `source`, `destination`, `journeyDate`, `travelClass`, `quota`, `fare`, `passengerCount`, `passengers[]`

---

### 18. `cancel_ticket`

Cancel a booked ticket by PNR.

**Category**: User (requires `x-user-email` header)

**Input**

| Field | Type   | Required | Description                         |
| ----- | ------ | -------- | ----------------------------------- |
| `pnr` | string | Yes      | PNR number of the booking to cancel |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 18,
    "method": "tools/call",
    "params": {
        "name": "cancel_ticket",
        "arguments": {
            "pnr": "4521367890"
        }
    }
}
```

**Response fields**: update count confirming cancellation

---

### 19. `get_pnr`

Track and save PNR status for the authenticated user.

**Category**: User (requires `x-user-email` header)

**Input**

| Field | Type   | Required | Description         |
| ----- | ------ | -------- | ------------------- |
| `pnr` | string | Yes      | PNR number to track |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 19,
    "method": "tools/call",
    "params": {
        "name": "get_pnr",
        "arguments": {
            "pnr": "4521367890"
        }
    }
}
```

**Response fields**: `id`, `userId`, `pnr`, `lastStatus`, `checkedAt`

---

### 20. `get_booking`

Get full booking details by PNR.

**Category**: User (requires `x-user-email` header)

**Input**

| Field | Type   | Required | Description |
| ----- | ------ | -------- | ----------- |
| `pnr` | string | Yes      | PNR number  |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 20,
    "method": "tools/call",
    "params": {
        "name": "get_booking",
        "arguments": {
            "pnr": "4521367890"
        }
    }
}
```

**Response fields**: full booking object including `passengers[]`

---

### 21. `get_booking_history`

Get all bookings for the authenticated user.

**Category**: User (requires `x-user-email` header)

**Input**: None

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 21,
    "method": "tools/call",
    "params": {
        "name": "get_booking_history",
        "arguments": {}
    }
}
```

**Response fields**: array of all booking objects with `passengers[]`

---

### 22. `update_booking_status`

Update the status of a booking.

**Category**: User (requires `x-user-email` header)

**Input**

| Field           | Type   | Required | Description                                                  |
| --------------- | ------ | -------- | ------------------------------------------------------------ |
| `pnr`           | string | Yes      | PNR number                                                   |
| `status`        | string | Yes      | `PENDING` / `BOOKED` / `RAC` / `WL` / `CANCELLED` / `FAILED` |
| `transactionId` | string | No       | Payment transaction ID                                       |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 22,
    "method": "tools/call",
    "params": {
        "name": "update_booking_status",
        "arguments": {
            "pnr": "4521367890",
            "status": "BOOKED",
            "transactionId": "TXN123456789"
        }
    }
}
```

**Response fields**: update count

---

### 23. `update_boarding_point`

Change the boarding point for a booking.

**Category**: User (requires `x-user-email` header)

**Input**

| Field                | Type   | Required | Description               |
| -------------------- | ------ | -------- | ------------------------- |
| `pnr`                | string | Yes      | PNR number                |
| `newBoardingStation` | string | Yes      | New boarding station code |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 23,
    "method": "tools/call",
    "params": {
        "name": "update_boarding_point",
        "arguments": {
            "pnr": "4521367890",
            "newBoardingStation": "MTJ"
        }
    }
}
```

**Response fields**: updated booking object

---

### 24. `create_reminder`

Create a journey, PNR or booking reminder.

**Category**: User (requires `x-user-email` header)

**Input**

| Field        | Type   | Required | Description                                         |
| ------------ | ------ | -------- | --------------------------------------------------- |
| `type`       | string | Yes      | `JOURNEY` / `PNR` / `BOOKING`                       |
| `reminderAt` | string | Yes      | ISO datetime string e.g. `2025-08-14T18:00:00.000Z` |
| `bookingId`  | string | No       | Booking ID to link reminder to                      |
| `metadata`   | object | No       | Any extra key-value data                            |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 24,
    "method": "tools/call",
    "params": {
        "name": "create_reminder",
        "arguments": {
            "type": "JOURNEY",
            "reminderAt": "2025-08-14T18:00:00.000Z",
            "bookingId": "booking-uuid-here",
            "metadata": {
                "note": "Reach station 1 hour early"
            }
        }
    }
}
```

**Response fields**: `id`, `userId`, `type`, `reminderAt`, `bookingId`, `metadata`, `sent`, `createdAt`

---

### 25. `get_reminders`

Get all reminders for the authenticated user.

**Category**: User (requires `x-user-email` header)

**Input**: None

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 25,
    "method": "tools/call",
    "params": {
        "name": "get_reminders",
        "arguments": {}
    }
}
```

**Response fields**: array of reminder objects ordered by `reminderAt` ascending

---

### 26. `update_reminder`

Update an existing reminder.

**Category**: User (requires `x-user-email` header)

**Input**

| Field        | Type   | Required | Description                   |
| ------------ | ------ | -------- | ----------------------------- |
| `reminderId` | string | Yes      | Reminder ID to update         |
| `reminderAt` | string | No       | New ISO datetime string       |
| `type`       | string | No       | `JOURNEY` / `PNR` / `BOOKING` |
| `metadata`   | object | No       | Updated metadata              |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 26,
    "method": "tools/call",
    "params": {
        "name": "update_reminder",
        "arguments": {
            "reminderId": "reminder-uuid-here",
            "reminderAt": "2025-08-14T16:00:00.000Z",
            "metadata": {
                "note": "Updated — reach 2 hours early"
            }
        }
    }
}
```

**Response fields**: updated reminder object

---

### 27. `delete_reminder`

Delete a reminder.

**Category**: User (requires `x-user-email` header)

**Input**

| Field        | Type   | Required | Description           |
| ------------ | ------ | -------- | --------------------- |
| `reminderId` | string | Yes      | Reminder ID to delete |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 27,
    "method": "tools/call",
    "params": {
        "name": "delete_reminder",
        "arguments": {
            "reminderId": "reminder-uuid-here"
        }
    }
}
```

**Response fields**: deleted reminder object

---

### 28. `add_saved_passenger`

Save a passenger profile for future bookings.

**Category**: User (requires `x-user-email` header)

**Input**

| Field             | Type    | Required | Description                 |
| ----------------- | ------- | -------- | --------------------------- |
| `name`            | string  | Yes      | Passenger full name         |
| `age`             | integer | Yes      | Age in years                |
| `gender`          | string  | Yes      | `MALE` / `FEMALE` / `OTHER` |
| `berthPreference` | string  | No       | Preferred berth type        |
| `seniorCitizen`   | boolean | No       | Default: `false`            |

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 28,
    "method": "tools/call",
    "params": {
        "name": "add_saved_passenger",
        "arguments": {
            "name": "Rahul Sharma",
            "age": 28,
            "gender": "MALE",
            "berthPreference": "LB",
            "seniorCitizen": false
        }
    }
}
```

**Response fields**: `id`, `userId`, `name`, `age`, `gender`, `berthPreference`, `seniorCitizen`, `createdAt`

---

### 29. `get_saved_passengers`

Get all saved passenger profiles for the authenticated user.

**Category**: User (requires `x-user-email` header)

**Input**: None

**Example**

```json
{
    "jsonrpc": "2.0",
    "id": 29,
    "method": "tools/call",
    "params": {
        "name": "get_saved_passengers",
        "arguments": {}
    }
}
```

**Response fields**: array of passenger profile objects

---

## Error Responses

All errors follow this structure:

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32000,
        "message": "Error message here"
    }
}
```

| HTTP Status | Meaning                                |
| ----------- | -------------------------------------- |
| `401`       | Missing `x-user-email` header          |
| `403`       | Session does not belong to this user   |
| `404`       | Session not found / resource not found |
| `500`       | Internal server error                  |

---

## Session Flow

```
1. Client sends POST /mcp (no mcp-session-id)
   → Server creates session, returns mcp-session-id in response header

2. Client stores mcp-session-id

3. All subsequent requests include mcp-session-id header
   → Server routes to existing session

4. Client sends DELETE /mcp with mcp-session-id
   → Server closes and removes session
```

---

## Quick Start — Full Booking Flow

```
1. find_station_code        → get NDLS, BCT codes
2. search_trains            → find trains NDLS→BCT on date
3. check_availability       → confirm seats available
4. get_fare                 → get fare amount
5. book_ticket              → create booking, get PNR
6. update_booking_status    → mark as BOOKED after payment
7. create_reminder          → set journey reminder
8. get_booking              → fetch booking details anytime
```
