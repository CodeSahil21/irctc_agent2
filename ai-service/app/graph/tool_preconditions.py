# graph/tool_preconditions.py
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ToolPrecondition:
    required_slots: List[str] = field(default_factory=list)
    optional_slots: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    max_retries: int = 2
    cacheable: bool = False
    # Which TravelState key holds a cached result for this tool
    cache_key: Optional[str] = None


# Maps tool name → precondition config
TOOL_PRECONDITIONS: Dict[str, ToolPrecondition] = {
    # ── Public / Search ───────────────────────────────────────────────
    "search_trains": ToolPrecondition(
        required_slots=["from_station", "to_station", "date"],
        optional_slots=["quota"],
        cacheable=True,
        cache_key="search_results",
    ),
    "recommend_trains": ToolPrecondition(
        required_slots=["from_station", "to_station", "date"],
        optional_slots=["travel_class", "quota"],
        cacheable=True,
        cache_key="search_results",
    ),
    "check_availability": ToolPrecondition(
        required_slots=["train_number", "travel_class", "quota", "date"],
        cacheable=True,
        cache_key="availability",
    ),
    "get_fare": ToolPrecondition(
        required_slots=["train_number", "travel_class", "quota", "from_station", "to_station"],
        cacheable=True,
        cache_key="fare",
    ),
    "get_route": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
    ),
    "get_seat_map": ToolPrecondition(
        required_slots=["train_number", "travel_class", "date"],
    ),
    "get_boarding_points": ToolPrecondition(
        required_slots=["train_number", "from_station", "date"],
    ),
    "search_train_by_number": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
    ),
    "get_live_status": ToolPrecondition(
        required_slots=["train_number", "date"],
    ),
    "get_train_schedule": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
    ),
    "get_platform": ToolPrecondition(
        required_slots=["train_number"],
        optional_slots=["from_station"],
    ),
    "search_stations": ToolPrecondition(
        required_slots=[],
    ),
    "find_station_code": ToolPrecondition(
        required_slots=[],
    ),
    "get_nearby_stations": ToolPrecondition(
        required_slots=[],
    ),
    "list_classes": ToolPrecondition(cacheable=True),
    "list_quotas": ToolPrecondition(cacheable=True),

    # ── Booking ───────────────────────────────────────────────────────
    "book_ticket": ToolPrecondition(
        required_slots=["train_number", "from_station", "to_station", "date", "travel_class", "quota"],
        requires_confirmation=True,
        max_retries=1,
    ),
    "cancel_ticket": ToolPrecondition(
        required_slots=[],
        requires_confirmation=True,
        max_retries=1,
    ),
    "get_pnr": ToolPrecondition(required_slots=[]),
    "get_booking": ToolPrecondition(required_slots=[]),
    "get_booking_history": ToolPrecondition(cacheable=True),
    "update_booking_status": ToolPrecondition(
        required_slots=[],
        requires_confirmation=True,
    ),
    "update_boarding_point": ToolPrecondition(
        required_slots=[],
        requires_confirmation=True,
    ),

    # ── Reminders ─────────────────────────────────────────────────────
    "create_reminder": ToolPrecondition(required_slots=[]),
    "get_reminders": ToolPrecondition(cacheable=True, cache_key="reminders"),
    "update_reminder": ToolPrecondition(required_slots=[]),
    "delete_reminder": ToolPrecondition(
        required_slots=[],
        requires_confirmation=True,
    ),

    # ── Passengers ────────────────────────────────────────────────────
    "add_saved_passenger": ToolPrecondition(required_slots=[]),
    "get_saved_passengers": ToolPrecondition(
        cacheable=True,
        cache_key="saved_passengers",
    ),
}


def get_precondition(tool_name: str) -> ToolPrecondition:
    return TOOL_PRECONDITIONS.get(tool_name, ToolPrecondition())


# Slot → human-readable question for the slot filler
SLOT_QUESTIONS: Dict[str, str] = {
    "from_station": "Which station are you travelling from?",
    "to_station": "Which station are you travelling to?",
    "date": "What date would you like to travel? (e.g. tomorrow, 2026-08-15)",
    "travel_class": "Which travel class do you prefer? (e.g. SL, 3A, 2A, 1A, CC)",
    "quota": "Which quota would you like? (GN for General, TQ for Tatkal, etc.)",
    "train_number": "Could you provide the train number?",
    "train_name": "Could you provide the train name?",
}
