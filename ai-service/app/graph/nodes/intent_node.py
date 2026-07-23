# graph/nodes/intent_node.py
import json
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState
from app.memory.conversation_memory import format_messages
from app.memory.preference_memory import merge_preferences_into_travel
from app.memory.working_memory import reset_turn_state
from app.services.openai_service import OpenAIService
from app.telemetry.logging import app_logger

# Intents that require zero user input and no planning — executor runs them directly
_DIRECT_EXEC_INTENTS = {
    "get_saved_passengers",
    "get_booking_history",
    "get_reminders",
    "list_classes",
    "list_quotas",
}

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
    if "this week" in v or "anytime" in v:
        return (today + timedelta(days=1)).isoformat()
    if "next week" in v:
        return (today + timedelta(days=7)).isoformat()
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    for day_name, day_num in days.items():
        if day_name in v:
            delta = (day_num - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    if re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", value)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    _MONTHS = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)\s+(\d{4})", v)
    if m:
        month = _MONTHS.get(m.group(2))
        if month:
            return f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}"
    m = re.search(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})", v)
    if m:
        month = _MONTHS.get(m.group(1))
        if month:
            return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", value)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return value


# Keywords that signal a flexible / week-range search
_FLEXIBLE_KEYWORDS = {
    "this week", "next 7 days", "next 7", "anytime this week",
    "flexible", "any day", "any date", "cheapest this week",
    "fastest this week", "available this week", "this weekend",
    "next few days", "coming days", "within a week",
    "best this week", "best available", "any day this week",
    "quick", "quickest", "cheapest", "fastest", "cheapest available",
    "any time", "anytime", "flexible date",
    # standalone replies the user gives when asked "what date?"
    "any", "anytime is fine", "any day is fine", "flexible",
    "this week is fine", "anytime this week is fine",
    "any time this week", "no specific date", "no preference",
}


def _parse_date_range(raw_date: str, goal: str) -> Optional[List[str]]:
    """
    Return a list of ISO dates if the user expressed a flexible/week search.
    Returns None for a fixed single date.
    """
    today = date.today()
    combined = ((raw_date or "") + " " + (goal or "")).lower()

    is_flexible = any(kw in combined for kw in _FLEXIBLE_KEYWORDS)
    if not is_flexible:
        return None

    # "this weekend" → next Saturday + Sunday only
    if "weekend" in combined:
        dates = []
        for delta in range(7):
            d = today + timedelta(days=delta)
            if d.weekday() in (5, 6):  # Sat=5, Sun=6
                dates.append(d.isoformat())
        return dates[:2] if dates else None

    # Default: next 7 days starting tomorrow
    return [(today + timedelta(days=i)).isoformat() for i in range(1, 8)]


_INTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_intent",
        "description": "Classify user intent and extract travel entities from the message.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": INTENTS,
                    "description": (
                        "The primary user intent. Choose the most specific match. Examples:\n"
                        "- 'show my passengers / passenger list / passenger history / saved travellers / my profiles' → get_saved_passengers\n"
                        "- 'my bookings / booking history / past trips / all my tickets / what have I booked' → get_booking_history\n"
                        "- 'my reminders / show reminders / upcoming alerts' → get_reminders\n"
                        "- 'add passenger / save traveller / new passenger profile' → add_saved_passenger\n"
                        "- 'check PNR / PNR status / track booking by PNR' → get_pnr\n"
                        "- 'booking details / show booking / get booking' → get_booking\n"
                        "- 'find trains / search trains / trains from X to Y' → search_trains\n"
                        "- 'recommend / best train / suggest train' → recommend_trains\n"
                        "- 'live status / where is train / running status' → get_live_status\n"
                        "- 'cancel ticket / cancel booking' → cancel_ticket\n"
                        "- 'set reminder / remind me' → create_reminder\n"
                        "- 'what classes are available / list classes' → list_classes\n"
                        "- 'what quotas / list quotas' → list_quotas\n"
                        "- 'boarding points / stops / stations for this/my/above train' → get_boarding_points\n"
                        "- 'change boarding point / update boarding station' → update_boarding_point\n"
                        "- anything else → general_question"
                    ),
                },
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
        }
    }
}

_SYSTEM = """You are an IRCTC travel assistant. Classify the user's intent and extract \
any travel entities explicitly mentioned in the message. Always call the classify_intent tool.

CRITICAL — only extract what the user actually said. Never invent, assume, or fill in values \
the user did not mention. Leave all unmentioned fields absent from the tool call output.

For selected_passenger_names: ONLY extract names that the user explicitly mentioned from their \
saved passenger list. Do NOT extract "new passenger" or any name not in the saved list — \
those cases go through slot filling separately.

These intents require NO input from the user — call them immediately with no clarification:
- get_saved_passengers   (fetches the user's saved passenger list automatically)
- get_booking_history    (fetches the user's full booking history automatically)
- get_reminders          (fetches the user's reminders automatically)
- list_classes           (returns all travel class codes — no user input needed)
- list_quotas            (returns all quota codes — no user input needed)
- search_stations        (query comes from what the user typed — no follow-up needed)
- find_station_code      (query comes from what the user typed — no follow-up needed)
- get_nearby_stations    (location comes from context — no follow-up needed)

For these intents, do NOT ask for PNR, booking ID, passenger ID, or any other field. \
The system retrieves data using the authenticated user's identity automatically."""


async def intent_node(state: TravelState, llm_service: OpenAIService) -> Dict[str, Any]:
    messages = format_messages(state.get("messages", []))

    # Extract the raw user message for new-passenger flow detection
    raw_messages = state.get("messages", [])
    content = ""
    for msg in reversed(raw_messages):
        if hasattr(msg, "content") and msg.__class__.__name__ == "HumanMessage":
            content = str(msg.content)
            break

    response = await llm_service.chat_raw(
        messages=messages,
        system=_SYSTEM,
        tools=[_INTENT_TOOL],
        tool_choice={"type": "function", "function": {"name": "classify_intent"}},
        temperature=0.0,
        max_tokens=512,
    )

    tool_input: Dict[str, Any] = {}
    if response.choices[0].message.tool_calls:
        tool_input = json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    intent = tool_input.get("intent", "general_question")
    user_goal = tool_input.get("user_goal", "")

    # Merge extracted entities into existing travel context
    existing_travel: Dict[str, Any] = dict(state.get("travel") or {})
    for slot in ("from_station", "to_station", "travel_class", "quota", "train_number"):
        value = tool_input.get(slot)
        if value:
            existing_travel[slot] = _normalize_station(value) if slot in ("from_station", "to_station") else value
    if tool_input.get("date"):
        date_range = _parse_date_range(tool_input["date"], user_goal)
        if date_range:
            existing_travel["date_range"] = date_range
            existing_travel.pop("date", None)
        else:
            existing_travel["date"] = _normalize_date(tool_input["date"])
            existing_travel.pop("date_range", None)
    elif not existing_travel.get("date") and not existing_travel.get("date_range"):
        # No date at all — check if goal or raw content implies flexible search
        date_range = _parse_date_range("", user_goal) or _parse_date_range("", content)
        if date_range:
            existing_travel["date_range"] = date_range
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
        if any(w in " ".join(selected_names).lower() for w in ("both", "all")):
            existing_travel["selected_passengers"] = state.get("saved_passengers") or []

    # ── New passenger collection flow ────────────────────────────────────
    # Parse passenger details from the message. Support both:
    #   - All at once:  "Dhruv\n21\nMale\nLower" or "Dhruv, 21, Male, Lower"
    #   - One at a time: just "Dhruv" on one turn, "21" on the next
    new_pax = dict(existing_travel.get("new_passenger_for_booking") or {})

    if new_pax.get("collecting"):
        # Split by lines or commas first — each line is one piece of data
        lines = [l.strip() for l in re.split(r"[\n,]+", content) if l.strip()]

        _GENDER_WORDS = {"male", "m", "man", "boy", "female", "f", "woman", "girl"}
        _BERTH_WORDS = {"upper", "lower", "middle", "side upper", "side lower"}
        _SKIP_LINES = {
            "here", "here are details", "here are my details", "details",
            "my details", "the details", "are details", "here are the details",
        }

        for line in lines:
            line_lower = line.lower().strip().rstrip(".,")

            # Skip filler phrases
            if line_lower in _SKIP_LINES:
                continue

            # Gender
            if not new_pax.get("gender"):
                if line_lower in ("female", "f", "woman", "girl"):
                    new_pax["gender"] = "Female"
                    continue
                elif line_lower in ("male", "m", "man", "boy"):
                    new_pax["gender"] = "Male"
                    continue

            # Berth preference
            if not new_pax.get("berthPreference"):
                if "side upper" in line_lower:
                    new_pax["berthPreference"] = "Side Upper"
                    continue
                elif "side lower" in line_lower:
                    new_pax["berthPreference"] = "Side Lower"
                    continue
                elif line_lower == "upper":
                    new_pax["berthPreference"] = "Upper"
                    continue
                elif line_lower == "lower":
                    new_pax["berthPreference"] = "Lower"
                    continue
                elif line_lower == "middle":
                    new_pax["berthPreference"] = "Middle"
                    continue

            # Age — pure number < 120
            if not new_pax.get("age"):
                digits = re.sub(r"[^\d]", "", line)
                if digits and line.strip().isdigit() and int(digits) < 120:
                    new_pax["age"] = int(digits)
                    continue

            # Name — non-empty line that isn't a number/gender/berth word
            if not new_pax.get("name"):
                is_number = line.strip().isdigit()
                is_gender = line_lower in _GENDER_WORDS
                is_berth = line_lower in _BERTH_WORDS
                is_filler = line_lower in _SKIP_LINES
                if not is_number and not is_gender and not is_berth and not is_filler:
                    # Take max first 2 words as name
                    name_words = line.split()[:2]
                    new_pax["name"] = " ".join(name_words).title()
                    continue

        # Handle save decision if that's what was asked
        if new_pax.get("save_asked") and "should_save" not in new_pax:
            lower = content.lower().strip()
            new_pax["should_save"] = any(
                w in lower for w in ("yes", "y", "sure", "yep", "yeah", "save", "ok")
            )

        existing_travel["new_passenger_for_booking"] = new_pax

    elif intent == "book_ticket":
        # Detect "new passenger" / "someone not in list" signals
        lower_msg = content.lower()
        is_new_pax_request = any(phrase in lower_msg for phrase in (
            "new passenger", "someone else", "another person", "not in list",
            "not saved", "different person", "new person", "other passenger",
            "not from list", "not from saved",
        ))
        if is_new_pax_request:
            existing_travel["new_passenger_for_booking"] = {"collecting": True}

    # ── "yes / proceed" continuity fix ────────────────────────────────────
    # When response_node asks "Would you like to proceed?" and user says "yes",
    # intent_node classifies it as general_question and loses booking context.
    # Detect this and override intent to book_ticket so the flow continues.
    _YES_WORDS = {"yes", "y", "yep", "yeah", "sure", "go ahead", "proceed",
                  "confirm", "ok", "okay", "book it", "do it", "absolutely"}
    content_lower_stripped = content.lower().strip().rstrip("!.").strip()
    is_affirmation = content_lower_stripped in _YES_WORDS or content_lower_stripped.startswith(
        ("yes ", "go ahead", "proceed", "confirm and", "yes confirm", "yes book")
    )

    if is_affirmation and intent == "general_question":
        # Check if there's an active booking context ready to proceed
        has_booking_context = (
            existing_travel.get("from_station")
            and existing_travel.get("to_station")
            and (existing_travel.get("date") or existing_travel.get("date_range"))
            and existing_travel.get("travel_class")
        )
        has_search_results = bool(state.get("search_results") or state.get("ranked_results"))
        has_avail = bool(state.get("availability"))
        has_fare = bool(state.get("fare"))

        if has_booking_context or has_search_results or has_avail or has_fare:
            intent = "book_ticket"
            user_goal = "Book the ticket with the confirmed details"
            app_logger.info("Affirmation detected with booking context — overriding intent to book_ticket")

    prefs = state.get("user_preferences") or {}
    if prefs:
        existing_travel = merge_preferences_into_travel(existing_travel, prefs)

    app_logger.info("Intent classified | intent={intent} | goal={goal}", intent=intent, goal=user_goal)

    patched_state = dict(state)
    patched_state["intent"] = intent
    updates = reset_turn_state(patched_state)
    updates.update({
        "intent": intent,
        "user_goal": user_goal,
        "travel": existing_travel,
        "user_preferences": prefs or state.get("user_preferences"),
    })

    if intent in _DIRECT_EXEC_INTENTS:
        updates["tool_plan"] = [intent]
        updates["tool_plan_args"] = [{}]
        updates["current_tool_index"] = 0
        updates["confirmation_required"] = False
        updates["reflection_required"] = False
        app_logger.info("Direct-exec intent — bypassing planner | intent={intent}", intent=intent)

    return updates
