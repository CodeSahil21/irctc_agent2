# graph/nodes/intent_node.py
import re
from datetime import date, timedelta
from typing import Any, Dict

from app.graph.state import TravelState
from app.memory.conversation_memory import format_for_claude
from app.memory.preference_memory import get_preferences, merge_preferences_into_travel
from app.memory.working_memory import reset_turn_state
from app.services.claude import ClaudeService
from app.telemetry.logging import app_logger

INTENTS = [
    "search_trains", "recommend_trains", "check_availability", "get_fare",
    "get_route", "get_train_schedule", "get_live_status", "get_platform",
    "get_seat_map", "get_boarding_points", "search_train_by_number",
    "search_stations", "find_station_code", "get_nearby_stations",
    "list_classes", "list_quotas",
    "book_ticket", "cancel_ticket", "get_pnr", "get_booking",
    "get_booking_history", "update_booking_status", "update_boarding_point",
    "create_reminder", "get_reminders", "update_reminder", "delete_reminder",
    "add_saved_passenger", "get_saved_passengers",
    "general_question",
]

# Common city → station code mappings
_CITY_TO_CODE: Dict[str, str] = {
    "delhi": "NDLS", "new delhi": "NDLS", "ndls": "NDLS",
    "mumbai": "BCT", "bombay": "BCT", "mumbai central": "BCT", "bct": "BCT",
    "kolkata": "HWH", "calcutta": "HWH", "howrah": "HWH", "hwh": "HWH",
    "chennai": "MAS", "madras": "MAS", "mas": "MAS",
    "bangalore": "SBC", "bengaluru": "SBC", "sbc": "SBC",
    "hyderabad": "HYB", "hyb": "HYB",
    "pune": "PUNE", "ahmedabad": "ADI", "adi": "ADI",
    "jaipur": "JP", "jp": "JP",
    "lucknow": "LKO", "lko": "LKO",
    "patna": "PNBE", "pnbe": "PNBE",
    "bhopal": "BPL", "bpl": "BPL",
    "nagpur": "NGP", "ngp": "NGP",
    "secunderabad": "SC", "sc": "SC",
    "agra": "AGC", "agc": "AGC",
    "mathura": "MTJ", "mtj": "MTJ",
    "gwalior": "GWL", "gwl": "GWL",
    "vadodara": "BRC", "baroda": "BRC", "brc": "BRC",
    "visakhapatnam": "VSKP", "vizag": "VSKP", "vskp": "VSKP",
    "vijayawada": "BZA", "bza": "BZA",
    "coimbatore": "CBE", "cbe": "CBE",
    "madurai": "MDU", "mdu": "MDU",
    "thiruvananthapuram": "TVC", "trivandrum": "TVC", "tvc": "TVC",
    "kochi": "ERS", "ernakulam": "ERS", "ers": "ERS",
}


def _normalize_station(value: str) -> str:
    """Return station code if city name is recognized, else return value uppercased."""
    return _CITY_TO_CODE.get(value.lower().strip(), value.upper().strip())


def _normalize_date(value: str) -> str:
    """Convert relative date expressions to YYYY-MM-DD. Returns original if unrecognized."""
    today = date.today()
    v = value.lower().strip()
    if v in ("today",):
        return today.isoformat()
    if v in ("tomorrow",):
        return (today + timedelta(days=1)).isoformat()
    if "day after" in v:
        return (today + timedelta(days=2)).isoformat()
    # "this week" / "anytime this week" / "next week" → nearest upcoming date (tomorrow)
    if "this week" in v or "next week" in v or "anytime" in v:
        return (today + timedelta(days=1)).isoformat()
    # "next monday" etc.
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    for day_name, day_num in days.items():
        if day_name in v:
            delta = (day_num - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    # Already YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value
    # DD-MM-YYYY
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", value)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return value


_INTENT_TOOL = {
    "name": "classify_intent",
    "description": "Classify user intent and extract travel entities from the message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": INTENTS, "description": "The primary user intent."},
            "user_goal": {"type": "string", "description": "One-sentence summary of what the user wants."},
            "from_station": {"type": "string", "description": "Origin station name or code if mentioned."},
            "to_station": {"type": "string", "description": "Destination station name or code if mentioned."},
            "date": {"type": "string", "description": "Travel date if mentioned (raw text is fine)."},
            "travel_class": {"type": "string", "description": "Class code if mentioned (SL, 3A, 2A, 1A, CC, EC, 2S, VS)."},
            "quota": {"type": "string", "description": "Quota code if mentioned (GN, TQ, LD, PT, HO, SS)."},
            "train_number": {"type": "string", "description": "Train number if mentioned."},
            "pnr": {"type": "string", "description": "PNR number if mentioned."},
            "selected_passenger_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of passengers the user selected for booking (e.g. ['Sahil', 'Rahul Sharma']). Extract when user says 'only X', 'book for X', 'both', etc.",
            },
        },
        "required": ["intent", "user_goal"],
    },
    "cache_control": {"type": "ephemeral"},
}

_SYSTEM = (
    "You are an IRCTC travel assistant. Classify the user's intent and extract "
    "any travel entities from their message. Always call the classify_intent tool."
)


async def intent_node(state: TravelState, claude_service: ClaudeService) -> Dict[str, Any]:
    messages = format_for_claude(state.get("messages", []))

    response = await claude_service.chat_raw(
        messages=messages,
        system=_SYSTEM,
        tools=[_INTENT_TOOL],
        tool_choice={"type": "tool", "name": "classify_intent"},
        temperature=0.0,
        max_tokens=512,
        cache_system=True,
    )

    tool_input: Dict[str, Any] = {}
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            tool_input = block.input or {}
            break

    intent = tool_input.get("intent", "general_question")
    user_goal = tool_input.get("user_goal", "")

    # Merge extracted entities into existing travel context
    existing_travel: Dict[str, Any] = dict(state.get("travel") or {})
    for slot in ("from_station", "to_station", "travel_class", "quota", "train_number"):
        value = tool_input.get(slot)
        if value:
            existing_travel[slot] = _normalize_station(value) if slot in ("from_station", "to_station") else value
    if tool_input.get("date"):
        existing_travel["date"] = _normalize_date(tool_input["date"])
    if tool_input.get("pnr"):
        existing_travel["pnr"] = tool_input["pnr"]

    # Resolve selected passenger names against saved passengers in state
    selected_names = tool_input.get("selected_passenger_names") or []
    if selected_names:
        saved = state.get("saved_passengers") or []
        if saved:
            names_lower = [n.lower() for n in selected_names]
            matched = [p for p in saved if p.get("name", "").lower() in names_lower]
            if matched:
                existing_travel["selected_passengers"] = matched
        # "both" / "all" → keep all saved passengers
        if any(w in " ".join(selected_names).lower() for w in ("both", "all")):
            existing_travel["selected_passengers"] = state.get("saved_passengers") or []

    # Layer 3 — load user preferences and apply to travel context
    user_email = state.get("user_email") or ""
    prefs = get_preferences(user_email) if user_email else {}
    if prefs:
        existing_travel = merge_preferences_into_travel(existing_travel, prefs)

    app_logger.info("Intent classified | intent={intent} | goal={goal}", intent=intent, goal=user_goal)

    updates = reset_turn_state(state)
    updates.update({
        "intent": intent,
        "user_goal": user_goal,
        "travel": existing_travel,
        "user_preferences": prefs or state.get("user_preferences"),
    })

    return updates
