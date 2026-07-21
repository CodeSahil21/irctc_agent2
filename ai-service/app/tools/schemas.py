TOOLS_SCHEMA = [
    {
        "name": "search_trains",
        "description": "Search trains between two stations on a given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fromStation": {"type": "string", "description": "Origin station code e.g. NDLS"},
                "toStation": {"type": "string", "description": "Destination station code e.g. BCT"},
                "journeyDate": {"type": "string", "description": "YYYY-MM-DD"},
                "quota": {"type": "string", "description": "Quota code. Default: GN"}
            },
            "required": ["fromStation", "toStation", "journeyDate"]
        }
    },
    {
        "name": "check_availability",
        "description": "Check seat availability for a train on a given date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "travelClass": {"type": "string"},
                "quota": {"type": "string"},
                "journeyDate": {"type": "string"}
            },
            "required": ["trainNumber", "travelClass", "quota", "journeyDate"]
        }
    },
    {
        "name": "get_fare",
        "description": "Get fare for a train between two stations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "travelClass": {"type": "string"},
                "quota": {"type": "string"},
                "fromStation": {"type": "string"},
                "toStation": {"type": "string"}
            },
            "required": ["trainNumber", "travelClass", "quota", "fromStation", "toStation"]
        }
    },
    {
        "name": "get_route",
        "description": "Get full route and all stops of a train.",
        "input_schema": {
            "type": "object",
            "properties": {"trainNumber": {"type": "string"}},
            "required": ["trainNumber"]
        }
    },
    {
        "name": "get_seat_map",
        "description": "Get coach-wise seat availability map for a train.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "travelClass": {"type": "string"},
                "journeyDate": {"type": "string"}
            },
            "required": ["trainNumber", "travelClass", "journeyDate"]
        }
    },
    {
        "name": "get_boarding_points",
        "description": "Get available boarding points for a train from a station.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "fromStation": {"type": "string"},
                "journeyDate": {"type": "string"}
            },
            "required": ["trainNumber", "fromStation", "journeyDate"]
        }
    },
    {
        "name": "search_train_by_number",
        "description": "Get train details by train number.",
        "input_schema": {
            "type": "object",
            "properties": {"trainNumber": {"type": "string"}},
            "required": ["trainNumber"]
        }
    },
    {
        "name": "get_live_status",
        "description": "Get live running status of a train.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "date": {"type": "string"}
            },
            "required": ["trainNumber", "date"]
        }
    },
    {
        "name": "get_train_schedule",
        "description": "Get full timetable/schedule of a train.",
        "input_schema": {
            "type": "object",
            "properties": {"trainNumber": {"type": "string"}},
            "required": ["trainNumber"]
        }
    },
    {
        "name": "get_platform",
        "description": "Get platform number for a train at a station.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "stationCode": {"type": "string"}
            },
            "required": ["trainNumber", "stationCode"]
        }
    },
    {
        "name": "search_stations",
        "description": "Search stations by name, code or city.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "find_station_code",
        "description": "Find station code from station name or city.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_nearby_stations",
        "description": "Get railway stations near a geographic location (within 50km).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"}
            },
            "required": ["lat", "lng"]
        }
    },
    {
        "name": "list_classes",
        "description": "List all available travel classes.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_quotas",
        "description": "List all available booking quotas.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "recommend_trains",
        "description": "Get train recommendations ranked by preference.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fromStation": {"type": "string"},
                "toStation": {"type": "string"},
                "journeyDate": {"type": "string"},
                "preference": {"type": "string", "enum": ["fastest", "cheapest", "overnight"]},
                "travelClass": {"type": "string"},
                "quota": {"type": "string"}
            },
            "required": ["fromStation", "toStation", "journeyDate", "preference"]
        }
    },
    {
        "name": "book_ticket",
        "description": "Book a train ticket for the authenticated user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trainNumber": {"type": "string"},
                "trainName": {"type": "string"},
                "source": {"type": "string"},
                "destination": {"type": "string"},
                "journeyDate": {"type": "string"},
                "travelClass": {"type": "string"},
                "quota": {"type": "string"},
                "fare": {"type": "number"},
                "passengers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "gender": {"type": "string", "enum": ["MALE", "FEMALE", "OTHER"]},
                            "berthPreference": {"type": "string"}
                        },
                        "required": ["name", "age", "gender"]
                    }
                }
            },
            "required": ["trainNumber", "trainName", "source", "destination", "journeyDate", "travelClass", "quota", "fare", "passengers"]
        }
    },
    {
        "name": "cancel_ticket",
        "description": "Cancel a booked ticket by PNR.",
        "input_schema": {
            "type": "object",
            "properties": {"pnr": {"type": "string"}},
            "required": ["pnr"]
        }
    },
    {
        "name": "get_pnr",
        "description": "Track and save PNR status for the authenticated user.",
        "input_schema": {
            "type": "object",
            "properties": {"pnr": {"type": "string"}},
            "required": ["pnr"]
        }
    },
    {
        "name": "get_booking",
        "description": "Get full booking details by PNR.",
        "input_schema": {
            "type": "object",
            "properties": {"pnr": {"type": "string"}},
            "required": ["pnr"]
        }
    },
    {
        "name": "get_booking_history",
        "description": "Get all bookings for the authenticated user.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "update_booking_status",
        "description": "Update the status of a booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pnr": {"type": "string"},
                "status": {"type": "string", "enum": ["PENDING", "BOOKED", "RAC", "WL", "CANCELLED", "FAILED"]},
                "transactionId": {"type": "string"}
            },
            "required": ["pnr", "status"]
        }
    },
    {
        "name": "update_boarding_point",
        "description": "Change the boarding point for a booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pnr": {"type": "string"},
                "newBoardingStation": {"type": "string"}
            },
            "required": ["pnr", "newBoardingStation"]
        }
    },
    {
        "name": "create_reminder",
        "description": "Create a journey, PNR or booking reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["JOURNEY", "PNR", "BOOKING"]},
                "reminderAt": {"type": "string"},
                "bookingId": {"type": "string"},
                "metadata": {"type": "object"}
            },
            "required": ["type", "reminderAt"]
        }
    },
    {
        "name": "get_reminders",
        "description": "Get all reminders for the authenticated user.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "update_reminder",
        "description": "Update an existing reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reminderId": {"type": "string"},
                "reminderAt": {"type": "string"},
                "type": {"type": "string"},
                "metadata": {"type": "object"}
            },
            "required": ["reminderId"]
        }
    },
    {
        "name": "delete_reminder",
        "description": "Delete a reminder.",
        "input_schema": {
            "type": "object",
            "properties": {"reminderId": {"type": "string"}},
            "required": ["reminderId"]
        }
    },
    {
        "name": "add_saved_passenger",
        "description": "Save a passenger profile for future bookings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "gender": {"type": "string", "enum": ["MALE", "FEMALE", "OTHER"]},
                "berthPreference": {"type": "string"},
                "seniorCitizen": {"type": "boolean"}
            },
            "required": ["name", "age", "gender"]
        }
    },
    {
        "name": "get_saved_passengers",
        "description": "Get all saved passenger profiles for the authenticated user.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

PARSER_TOOL_SCHEMA = {
    "name": "parse_user_intent",
    "description": "Extract structured intent and normalized parameters from freeform user queries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "search_trains",
                    "check_availability",
                    "get_fare",
                    "get_live_status",
                    "book_ticket",
                    "cancel_ticket",
                    "get_pnr_status",
                    "manage_reminders",
                    "manage_passengers",
                    "unknown"
                ],
                "description": "The high-level user goal classification."
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0"
            },
            "entities": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Origin city or station name/code"},
                    "destination": {"type": "string", "description": "Destination city or station name/code"},
                    "train_number": {"type": "string", "description": "5-digit train number if provided"},
                    "pnr": {"type": "string", "description": "10-digit PNR number if provided"},
                    "date": {"type": "string", "description": "Normalized date or relative reference e.g., 'tomorrow', '2026-08-15'"},
                    "travel_class": {"type": "string", "description": "Class code e.g. 3A, 2A, SL, CC"},
                    "quota": {"type": "string", "description": "Quota code e.g. GN, TQ, LD"}
                }
            },
            "missing_required_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List parameters that are mandatory for this intent but missing from user input."
            }
        },
        "required": ["intent", "confidence", "entities", "missing_required_fields"]
    }
}