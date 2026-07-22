from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ToolPrecondition:
    required_slots: List[str] = field(default_factory=list)
    optional_slots: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    max_retries: int = 2
    cacheable: bool = False
    cache_key: Optional[str] = None
    # Tools sharing the same non-None group tag run concurrently
    parallel_group: Optional[str] = None
    timeout_seconds: float = 15.0


TOOL_PRECONDITIONS: Dict[str, ToolPrecondition] = {
    # ── Public / Search ───────────────────────────────────────────────
    "search_trains": ToolPrecondition(
        required_slots=["from_station", "to_station", "date"],
        optional_slots=["quota"],
        cacheable=True,
        cache_key="search_results",
        timeout_seconds=15.0,
    ),
    "recommend_trains": ToolPrecondition(
        required_slots=["from_station", "to_station", "date"],
        optional_slots=["travel_class", "quota"],
        cacheable=True,
        cache_key="search_results",
        timeout_seconds=15.0,
    ),
    "check_availability": ToolPrecondition(
        required_slots=["train_number", "travel_class", "quota", "date"],
        cacheable=True,
        cache_key="availability",
        parallel_group="post_search",
        timeout_seconds=10.0,
    ),
    "get_fare": ToolPrecondition(
        required_slots=["train_number", "travel_class", "quota", "from_station", "to_station"],
        cacheable=True,
        cache_key="fare",
        parallel_group="post_search",
        timeout_seconds=10.0,
    ),
    "get_live_status": ToolPrecondition(
        required_slots=["train_number", "date"],
        parallel_group="post_search",
        timeout_seconds=12.0,
    ),
    "get_route": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
        timeout_seconds=10.0,
    ),
    "get_seat_map": ToolPrecondition(
        required_slots=["train_number", "travel_class", "date"],
        timeout_seconds=10.0,
    ),
    "get_boarding_points": ToolPrecondition(
        required_slots=["train_number", "from_station", "date"],
        timeout_seconds=10.0,
    ),
    "search_train_by_number": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
        timeout_seconds=10.0,
    ),
    "get_train_schedule": ToolPrecondition(
        required_slots=["train_number"],
        cacheable=True,
        timeout_seconds=10.0,
    ),
    "get_platform": ToolPrecondition(
        required_slots=["train_number"],
        optional_slots=["from_station"],
        timeout_seconds=10.0,
    ),
    "search_stations": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "find_station_code": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "get_nearby_stations": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "list_classes": ToolPrecondition(cacheable=True, timeout_seconds=5.0),
    "list_quotas": ToolPrecondition(cacheable=True, timeout_seconds=5.0),

    # ── Booking ───────────────────────────────────────────────────────
    "book_ticket": ToolPrecondition(
        required_slots=["train_number", "from_station", "to_station", "date", "travel_class", "quota"],
        requires_confirmation=True,
        max_retries=1,
        timeout_seconds=20.0,
    ),
    "cancel_ticket": ToolPrecondition(
        required_slots=["pnr"],
        requires_confirmation=True,
        max_retries=1,
        timeout_seconds=20.0,
    ),
    "get_pnr": ToolPrecondition(required_slots=["pnr"], timeout_seconds=10.0),
    "get_booking": ToolPrecondition(required_slots=["pnr"], timeout_seconds=10.0),
    "get_booking_history": ToolPrecondition(cacheable=True, timeout_seconds=10.0),
    "update_booking_status": ToolPrecondition(
        required_slots=["pnr"],
        requires_confirmation=True,
        timeout_seconds=15.0,
    ),
    "update_boarding_point": ToolPrecondition(
        required_slots=["pnr"],
        requires_confirmation=True,
        timeout_seconds=15.0,
    ),

    # ── Reminders ─────────────────────────────────────────────────────
    "create_reminder": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "get_reminders": ToolPrecondition(cacheable=True, cache_key="reminders", timeout_seconds=10.0),
    "update_reminder": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "delete_reminder": ToolPrecondition(
        required_slots=[],
        requires_confirmation=True,
        timeout_seconds=10.0,
    ),

    # ── Passengers ────────────────────────────────────────────────────
    "add_saved_passenger": ToolPrecondition(required_slots=[], timeout_seconds=10.0),
    "get_saved_passengers": ToolPrecondition(
        cacheable=True,
        cache_key="saved_passengers",
        timeout_seconds=10.0,
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
    "pnr": "Could you share the 10-digit PNR number?",
}
