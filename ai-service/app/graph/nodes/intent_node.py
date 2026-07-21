# graph/nodes/intent_node.py
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
        },
        "required": ["intent", "user_goal"],
    },
}

_SYSTEM = (
    "You are an IRCTC travel assistant. Classify the user's intent and extract "
    "any travel entities from their message. Always call the classify_intent tool."
)


async def intent_node(state: TravelState, claude_service: ClaudeService) -> Dict[str, Any]:
    # Layer 2 — windowed conversation messages
    messages = format_for_claude(state.get("messages", []))

    response = await claude_service.chat_raw(
        messages=messages,
        system=_SYSTEM,
        tools=[_INTENT_TOOL],
        tool_choice={"type": "tool", "name": "classify_intent"},
        temperature=0.0,
        max_tokens=512,
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
    for slot in ("from_station", "to_station", "date", "travel_class", "quota", "train_number"):
        value = tool_input.get(slot)
        if value:
            existing_travel[slot] = value
    if tool_input.get("pnr"):
        existing_travel["pnr"] = tool_input["pnr"]

    # Layer 3 — load user preferences and apply to travel context
    user_email = state.get("user_email") or ""
    prefs = get_preferences(user_email) if user_email else {}
    if prefs:
        existing_travel = merge_preferences_into_travel(existing_travel, prefs)

    app_logger.info("Intent classified | intent={intent} | goal={goal}", intent=intent, goal=user_goal)

    # Reset per-turn working memory fields
    updates = reset_turn_state(state)
    updates.update({
        "intent": intent,
        "user_goal": user_goal,
        "travel": existing_travel,
        "user_preferences": prefs or state.get("user_preferences"),
    })

    return updates
