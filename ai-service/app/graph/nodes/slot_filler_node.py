"""
Schema-driven slot filler.

Once an intent is classified we look up the primary MCP tool's *live* input schema
(discovered from the server, not hardcoded) and check whether every required
parameter can be satisfied. The philosophy is "auto-resolve first, ask only what's
truly missing":

  1. A required field is SATISFIED when its value already exists in travel context,
     OR it has a safe default (quota → GN), OR it will be produced by another step
     (e.g. a train number resolvable from an upcoming search), OR it is an internal
     field the planner/executor fills (passengers, reminderAt, ...).
  2. Only genuinely user-provided journey fields that cannot be resolved are asked
     for — one question per turn, phrased from the schema where possible.

This keeps the agent from nagging while guaranteeing tools are never called with
missing required parameters. Falls back to the static preconditions when the MCP
schema is unavailable (e.g. discovery not yet run in a unit test).
"""
import re
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState
from app.graph.tool_preconditions import SLOT_QUESTIONS, TOOL_PRECONDITIONS, get_precondition
from app.telemetry.logging import app_logger

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# MCP camelCase required field → internal travel-context slot
# Only fields that map to a slot we might ask the user about are listed here.
# Fields that are always auto-resolved (planner-filled, arg_patcher-filled, or
# user-auth-scoped) are intentionally ABSENT so the slot filler never asks for them.
_FIELD_TO_SLOT: Dict[str, str] = {
    "fromStation": "from_station",
    "toStation": "to_station",
    "source": "from_station",
    "destination": "to_station",
    "journeyDate": "date",
    "date": "date",
    "trainNumber": "train_number",
    "travelClass": "travel_class",
    "pnr": "pnr",
    # "stationCode"  → intentionally omitted: arg_patcher fills from travel.from_station
    # "quota"        → intentionally omitted: safe default GN always applied
    # "trainName"    → intentionally omitted: arg_patcher fills from search results
    # "preference"   → intentionally omitted: planner-filled (fastest/cheapest/overnight)
    # "reminderId"   → intentionally omitted: arg_patcher fills from reminders state
    # "reminderAt"   → intentionally omitted: planner-filled from conversation
    # "type"         → intentionally omitted: planner-filled (JOURNEY/PNR/BOOKING)
    # "status"       → intentionally omitted: planner-filled (BOOKED/CANCELLED/etc)
    # "newBoardingStation" → intentionally omitted: planner-filled from context
    # "name"/"age"/"gender" → intentionally omitted: planner-filled from conversation
    # "query"        → intentionally omitted: planner-filled from user message
    # "lat"/"lng"    → intentionally omitted: planner-filled
    # "bookingId"    → intentionally omitted: arg_patcher fills from booking state
    # "fare"         → intentionally omitted: arg_patcher fills from fare state
    # "passengers"   → intentionally omitted: arg_patcher fills from saved_passengers
}

# Slots we may ask the user about. Everything else is auto-resolved or planner-filled.
_ASKABLE_SLOTS = {"from_station", "to_station", "date", "travel_class", "train_number", "pnr", "passengers"}

# Tools that require zero user input — they are scoped to the authenticated user
# and need no slot filling at all. Bypassed immediately.
_ZERO_INPUT_TOOLS = {
    "get_saved_passengers",
    "get_booking_history",
    "get_reminders",
    "list_classes",
    "list_quotas",
    "search_stations",    # query is planner-filled from user message
    "find_station_code",  # query is planner-filled from user message
    "get_nearby_stations", # lat/lng are planner-filled
}


def _slot_filled(slot: str, value: Any) -> bool:
    """Return True only if the slot value is genuinely usable."""
    if not value:
        return False
    if slot == "date":
        # Accept ISO date OR a non-empty date_range list (flexible search)
        if isinstance(value, list):
            return len(value) > 0
        return bool(_ISO_DATE_RE.match(str(value)))
    return True


def _extract_from_booking_history(state: TravelState) -> Dict[str, Any]:
    """
    Extract train_number, from_station, date from booking history or booking in state.
    Returns a dict of whatever could be found.
    """
    extracted: Dict[str, Any] = {}

    # Check tool_results["get_booking_history"]
    tool_results = state.get("tool_results") or {}
    history = tool_results.get("get_booking_history") or []
    if isinstance(history, list) and history:
        booking = history[0]
        if booking.get("trainNumber"):
            extracted["train_number"] = str(booking["trainNumber"])
        if booking.get("source"):
            extracted["from_station"] = booking["source"]
        if booking.get("journeyDate"):
            extracted["date"] = booking["journeyDate"][:10] if booking["journeyDate"] else None

    # Also check state.booking directly
    booking = state.get("booking") or {}
    if isinstance(booking, dict):
        if not extracted.get("train_number") and booking.get("trainNumber"):
            extracted["train_number"] = str(booking["trainNumber"])
        if not extracted.get("from_station") and booking.get("source"):
            extracted["from_station"] = booking["source"]
        if not extracted.get("date") and booking.get("journeyDate"):
            extracted["date"] = booking["journeyDate"][:10] if booking["journeyDate"] else None

    return extracted


def _is_satisfied(field: str, slot: str, travel: Dict[str, Any], state: TravelState) -> bool:
    """Whether a required schema field can be satisfied without asking the user."""
    if _slot_filled(slot, travel.get(slot)):
        return True
    # date_range counts as a satisfied date slot
    if slot == "date" and travel.get("date_range"):
        return True
    if field == "quota":
        return True  # safe default (GN) applied by arg_patcher
    if slot == "station_code":
        return bool(travel.get("from_station"))
    if slot == "train_number":
        # Check travel context first
        if travel.get("train_number") or state.get("search_results"):
            return True
        # Check booking history / tool_results
        booking_data = _extract_from_booking_history(state)
        if booking_data.get("train_number"):
            return True
        # Resolvable if we have enough to search first
        if (
            travel.get("from_station")
            and travel.get("to_station")
            and _slot_filled("date", travel.get("date"))
        ):
            return True
        return False
    if slot == "from_station":
        # For tools like get_boarding_points, from_station can come from booking history
        booking_data = _extract_from_booking_history(state)
        if booking_data.get("from_station"):
            return True
        return False
    if slot == "date":
        # For tools like get_boarding_points, date can come from booking history
        booking_data = _extract_from_booking_history(state)
        if booking_data.get("date"):
            return True
        return False
    return False


def _question_for(slot: str, field: str, properties: Dict[str, Any]) -> str:
    if slot in SLOT_QUESTIONS:
        return SLOT_QUESTIONS[slot]
    desc = (properties.get(field) or {}).get("description")
    if desc:
        return f"Could you provide the {field}? ({desc})"
    return f"Could you provide your {slot.replace('_', ' ')}?"


def _schema_missing_slots(
    tool_name: str,
    schema: Dict[str, Any],
    travel: Dict[str, Any],
    state: TravelState,
) -> tuple[List[str], Optional[str]]:
    """Return (missing_slots, question) derived from the live MCP schema."""
    input_schema = schema.get("input_schema", {}) or {}
    required = input_schema.get("required", []) or []
    properties = input_schema.get("properties", {}) or {}

    missing: List[str] = []
    question: Optional[str] = None
    for field in required:
        slot = _FIELD_TO_SLOT.get(field)
        if slot is None or slot not in _ASKABLE_SLOTS:
            continue  # internal/planner-filled field — not a user question
        if _is_satisfied(field, slot, travel, state):
            continue
        if slot not in missing:
            missing.append(slot)
            if question is None:
                question = _question_for(slot, field, properties)
    return missing, question


def _static_missing_slots(tool_name: str, travel: Dict[str, Any]) -> tuple[List[str], Optional[str]]:
    """Fallback when the MCP schema is unavailable — uses static preconditions."""
    precondition = get_precondition(tool_name)
    missing = [s for s in precondition.required_slots if not _slot_filled(s, travel.get(s))]
    question = SLOT_QUESTIONS.get(missing[0], f"Could you provide your {missing[0]}?") if missing else None
    return missing, question


def slot_filler_node(state: TravelState, mcp_registry=None) -> Dict[str, Any]:
    intent = state.get("intent", "general_question")
    travel = dict(state.get("travel") or {})

    # Zero-input tools: scoped to authenticated user, planner fills all args.
    # Never ask the user for anything — go straight to planning.
    if intent in _ZERO_INPUT_TOOLS:
        return {"missing_slots": [], "pending_question": None}

    # ── Passenger selection gate for book_ticket ───────────────────────────
    # Stages:
    #  0 → collecting=True but no name → ask for name
    #  1 → has name but no age        → ask for age
    #  2 → has name+age but no gender → ask for gender
    #  3 → all details, save not asked → ask save?
    #  4 → save_asked AND should_save known → promote to selected_passengers
    #  5 → no passenger at all + >1 saved → ask who to book for
    if intent == "book_ticket":
        selected = travel.get("selected_passengers") or []
        saved = state.get("saved_passengers") or []
        new_pax = dict(travel.get("new_passenger_for_booking") or {})

        # Stage 4 — save decision has been made, promote to selected_passengers
        if (new_pax.get("name") and new_pax.get("age") and new_pax.get("gender")
                and new_pax.get("save_asked") and "should_save" in new_pax):
            travel["selected_passengers"] = [{
                "name": new_pax["name"],
                "age": new_pax["age"],
                "gender": new_pax["gender"],
                "berthPreference": new_pax.get("berthPreference", "Lower"),
            }]
            travel["save_new_passenger"] = new_pax.get("should_save", False)
            travel["new_passenger_for_booking"] = {}
            selected = travel["selected_passengers"]
            # fall through to rest of slot checks with passenger now set

        # Stage 3 — all details collected, haven't asked about saving yet
        elif (new_pax.get("name") and new_pax.get("age") and new_pax.get("gender")
              and not new_pax.get("save_asked")):
            new_pax["save_asked"] = True
            travel["new_passenger_for_booking"] = new_pax
            return {
                "missing_slots": ["passengers"],
                "pending_question": (
                    f"Got it — **{new_pax['name']}**, {new_pax['age']}, {new_pax['gender']}. "
                    f"Would you like to save them to your passenger list for future bookings? (yes / no)"
                ),
                "travel": travel,
            }

        # Stage 2 — has name+age, missing gender
        elif new_pax.get("name") and new_pax.get("age") and not new_pax.get("gender"):
            return {
                "missing_slots": ["passengers"],
                "pending_question": f"What is {new_pax['name']}'s gender? (Male / Female)",
                "travel": travel,
            }

        # Stage 1 — has name, missing age
        elif new_pax.get("name") and not new_pax.get("age"):
            return {
                "missing_slots": ["passengers"],
                "pending_question": f"What is {new_pax['name']}'s age?",
                "travel": travel,
            }

        # Stage 0 — collecting started but no name yet
        elif new_pax.get("collecting") and not new_pax.get("name"):
            return {
                "missing_slots": ["passengers"],
                "pending_question": "What is the passenger's full name?",
                "travel": travel,
            }

        # Stage 5 — no passenger selected, show saved list
        if not selected:
            if len(saved) > 1:
                names = ", ".join(p.get("name", "?") for p in saved)
                return {
                    "missing_slots": ["passengers"],
                    "pending_question": (
                        f"Who would you like to book for? Your saved passengers: **{names}**. "
                        f"Say the name(s), 'all', or 'new passenger' to add someone not in the list."
                    ),
                    "travel": travel,
                }
            elif len(saved) == 1:
                # Only one saved passenger — auto-select
                travel["selected_passengers"] = saved
                selected = saved

    # Intent names map 1:1 to MCP tool names. Unknown intents have no required slots.
    tool_name = intent
    schema = None
    if mcp_registry is not None and mcp_registry.is_known(tool_name):
        schema = mcp_registry.get_tool_schema(tool_name)
    elif tool_name not in TOOL_PRECONDITIONS:
        return {"missing_slots": [], "pending_question": None}

    if schema:
        missing, question = _schema_missing_slots(tool_name, schema, travel, state)
    else:
        missing, question = _static_missing_slots(tool_name, travel)

    if missing:
        app_logger.info(
            "Slot filling required | intent={intent} | missing={missing}",
            intent=intent,
            missing=missing,
        )
        return {"missing_slots": missing, "pending_question": question}

    return {"missing_slots": [], "pending_question": None, "travel": travel}
