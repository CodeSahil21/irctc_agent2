import json
import re
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

_MAX_LOOP = 8

# Grounding: Indian Railways PNRs are exactly 10 digits.
_PNR_RE = re.compile(r"\b\d{10}\b")

# ---------------------------------------------------------------------------
# Required slots per tool — used to detect mid-collection state and tell the
# model exactly which fields are still missing so it asks the right question.
# ---------------------------------------------------------------------------

_TOOL_REQUIRED_SLOTS: Dict[str, List[str]] = {
    "book_ticket": [
        "trainNumber", "journeyDate", "fromStation", "toStation",
        "travelClass", "quota", "passengers",
    ],
    "cancel_ticket":         ["pnr"],
    "check_availability":    ["trainNumber", "journeyDate", "fromStation", "toStation", "travelClass"],
    "get_fare":              ["trainNumber", "journeyDate", "fromStation", "toStation", "travelClass"],
    "get_pnr":               ["pnr"],
    "get_booking":           ["pnr"],
    "update_booking":        ["pnr", "newBoardingStation"],
    "get_live_status":       ["trainNumber", "journeyDate"],
    "get_route":             ["trainNumber"],
    "get_train_schedule":    ["trainNumber"],
    "get_platform":          ["trainNumber", "stationCode"],
    "get_seat_map":          ["trainNumber", "journeyDate", "travelClass"],
    "get_boarding_points":   ["trainNumber", "journeyDate", "fromStation"],
    "search_trains":         ["fromStation", "toStation", "journeyDate"],
    "search_stations":       ["query"],
    "find_station":          ["query"],
    "create_reminder":       ["trainNumber", "reminderType", "reminderTime"],
    "manage_reminder":       ["action"],
    "add_saved_passenger":   ["name", "age", "gender", "berthPreference"],
}

# Human-readable labels for slot names shown in the context block
_SLOT_LABELS: Dict[str, str] = {
    "trainNumber":   "train number",
    "journeyDate":   "journey date (YYYY-MM-DD)",
    "fromStation":   "origin station code",
    "toStation":     "destination station code",
    "travelClass":   "travel class (e.g. SL, 3A, 2A, 1A)",
    "quota":         "quota (default: GN)",
    "passengers":    "passenger details (name, age, gender, berth preference for each)",
    "pnr":           "PNR number",
    "stationCode":   "station code",
    "query":         "search query",
    "action":        "action (create/update/delete)",
    "reminderType":  "reminder type",
    "reminderTime":  "reminder time",
    "name":          "passenger name",
    "age":           "passenger age",
    "gender":        "passenger gender (MALE / FEMALE / OTHER)",
    "berthPreference": "berth preference (LB = lower, MB = middle, UB = upper, SL = side lower, SUB = side upper, WS = window seat)",
    "newBoardingStation": "new boarding station code",
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """\
You are the official IRCTC AI Travel Assistant. You have live tools for train \
search, seat availability, fares, booking, cancellation, reminders, and account \
management.

INTENT GATE — READ THIS BEFORE CALLING ANY TOOL
You must ONLY call a tool when the user has explicitly requested the corresponding \
action in their current or recent message. Do NOT infer, anticipate, or pre-emptively \
call tools the user did not ask for.

STRICT EXAMPLES:
- User asks "are there trains from Mumbai to Delhi?" → call find_station / \
recommend_trains. Do NOT call book_ticket or add_saved_passenger.
- User asks "what is the fare for Rajdhani?" → call get_fare. Do NOT call book_ticket.
- User asks "check availability" → call check_availability. Do NOT call book_ticket.
- User asks "book a ticket" or "I want to book" → THEN start the book_ticket flow.
- User says "I want to go with Golden Temple Mail" or "I'll take Rajdhani" or \
"let's go with Paschim Express" → THEN start the book_ticket flow for that train.
- User asks "save this passenger" or "add passenger" → THEN start add_saved_passenger flow.
- User asks "cancel my ticket" → THEN start the cancel_ticket flow.

If the user has NOT said anything resembling "book", "reserve", "add passenger", \
"save passenger", "cancel", etc., you MUST NOT call book_ticket, add_saved_passenger, \
cancel_ticket, or any other write/mutating tool. Calling a mutating tool without an \
explicit request is a critical error.

SLOT-FILLING PROTOCOL
When you need to call a tool but one or more required arguments are missing:
1. Check the session context message at the top of the conversation — values already \
collected are listed under "Collecting details for <tool>". Do NOT re-ask for anything \
already there.
2. Ask the user for exactly ONE missing field at a time. Be specific: tell them \
what you need and why (e.g. "Which travel class would you like — SL, 3A, 2A or 1A?").
3. As soon as ALL required fields are available (from context + conversation), \
call the tool immediately — do NOT ask for confirmation or summarise first.
4. If the user refuses to provide a required field after being asked explicitly, \
tell them clearly: "I cannot proceed with [action] without [field]. Please provide \
it when you're ready." Then stop — do not guess or use a placeholder value.
5. Never call a tool with a guessed, placeholder, or incomplete argument. \
A wrong booking is worse than no booking.

BOOKING RULES
- Only start the book_ticket flow when the user explicitly says they want to book \
(e.g. "book this", "I want to book", "reserve a seat", "book the Rajdhani").
- Before calling book_ticket, you MUST have ALL of: trainNumber, journeyDate \
(YYYY-MM-DD), fromStation, toStation, travelClass, passengers (name/age/gender/berthPreference \
for each), quota (default GN if not specified). \
- For each passenger, collect name, age, gender ONE AT A TIME. Then ask for berth \
preference: "What berth preference for [name]? (LB = lower, MB = middle, UB = upper, \
SL = side lower, SUB = side upper, WS = window seat, NP = no preference)". \
- If journeyDate is not in context, call check_availability for the selected train \
first — the response includes journeyDate. \
- If the user says "use my saved passenger" or names a passenger from the saved \
list, use those exact details — do not re-ask. \
- Do NOT ask "shall I proceed?" before booking — the system handles confirmation \
separately after you call book_ticket. Just call it.

PASSENGER MANAGEMENT RULES
- Only call add_saved_passenger when the user explicitly asks to save or add a \
passenger (e.g. "save this passenger", "add passenger", "add Ryan to my list").
- Collect name, age, gender, and berthPreference ONE AT A TIME before calling \
add_saved_passenger. Ask for each missing field separately — never re-show all \
fields at once if some are already collected.
- If name, age, and gender are already collected but berthPreference is missing, \
ask ONLY: "What berth preference should I save for [name]? \
(LB = lower, MB = middle, UB = upper, SL = side lower, SUB = side upper, WS = window seat)" \
— do not ask for any other field.
- Do not invent or reuse values from a previous booking context \
unless the user explicitly refers to them.

CORE RULES
- Use tools to get real data. NEVER invent or guess PNRs, train numbers, fares, \
seat counts, or availability.
- NEVER pre-select a travel class (SL, 3A, 2A, 1A etc.) on behalf of the user. \
If the user has not specified a class: either ask "Which class would you prefer — \
SL, 3A, 2A, or 1A?" OR show availability/fare for all classes so the user can choose.
- NEVER assume quota (GN, TQ, LD etc.) — use GN as default only when booking, \
never when searching or checking availability.
- If the user provides a PNR directly in their message, use it immediately for \
cancel_ticket or update_booking — do NOT call get_booking_history to "verify" it. \
The user knows their own PNR.
- If a PNR is already shown in the session context (under "PNRs:" or \
"Last booking"), use it directly — do NOT call get_booking_history again.
- Only call get_booking_history when the user has NOT provided a PNR and you \
genuinely need to look one up (e.g. "cancel my most recent booking").
- Resolve station names/cities to codes with find_station before using them \
elsewhere, unless you already have a valid 2–5 letter station code.
- When comparing several trains (fares, availability, etc.), emit all relevant tool \
calls IN THE SAME response turn — the system executes them concurrently.
- Prefer recommend_trains over manually chaining search_trains + check_availability \
+ get_fare when the user just wants a ranked shortlist.
- If the result shows the user declined to confirm, tell them plainly it was not \
performed. Do not retry without a new explicit request.
- Use Markdown tables for lists of trains. Show fares with ₹ and include the fare \
breakdown when available.
- Never tell the user to visit irctc.co.in or any external website — you have live \
tools for everything.
- Be concise and professional.

DATE HANDLING
- Use relative date expressions ("tomorrow", "this weekend", "next Monday", etc.) \
based on the current date provided in the session context.
- Always resolve them to an explicit YYYY-MM-DD date before calling any tool.
- NEVER use a date from 2023 or any year other than the current year unless the \
user explicitly provides a past date.
{feedback}
"""


# ---------------------------------------------------------------------------
# Per-request schema cache
# ---------------------------------------------------------------------------

class SchemaCache:
    """
    Request-scoped cache for MCP tool schemas.

    Created once at the top of agent_node(), used throughout the call,
    then garbage-collected automatically — no manual invalidation needed.

    - get_tool_list()  → fetches all schemas once, returns the same list
    - get(tool_name)   → fetches a single tool schema once, caches per-tool
    """

    def __init__(self, mcp_registry) -> None:
        self._registry = mcp_registry
        self._tool_list: Optional[List[Dict[str, Any]]] = None
        self._by_name: Dict[str, Optional[Dict[str, Any]]] = {}

    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Fetched from registry exactly once per request."""
        if self._tool_list is None:
            self._tool_list = self._registry.get_tool_schemas() if self._registry else []
        return self._tool_list

    def get(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Fetched from registry at most once per tool per request."""
        if tool_name not in self._by_name:
            self._by_name[tool_name] = (
                self._registry.get_tool_schema(tool_name) if self._registry else None
            )
        return self._by_name[tool_name]

    def known_tool_names(self) -> set:
        return {t["function"]["name"] for t in self.get_tool_list()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _required_slots_for(tool_name: str, cache: Optional["SchemaCache"] = None) -> List[str]:
    """
    Return the required slot names for a tool.

    Priority order:
    1. Live MCP schema (input_schema.required) — dynamically reflects the real
       tool contract so any change on the MCP server is picked up automatically.
    2. Hardcoded _TOOL_REQUIRED_SLOTS fallback — used when cache is not
       available (e.g. during tests or before startup discovery completes).
    """
    if cache is not None:
        schema_info = cache.get(tool_name)
        if schema_info:
            mcp_required = (schema_info.get("input_schema") or {}).get("required", [])
            if mcp_required:
                return mcp_required
    return _TOOL_REQUIRED_SLOTS.get(tool_name, [])


def _slot_label_from_schema(slot_name: str, tool_name: str,
                             cache: Optional["SchemaCache"] = None) -> str:
    """
    Return a human-readable label for a slot.

    Checks _SLOT_LABELS first (curated, user-friendly phrasing).
    Falls back to the MCP schema property description, then the raw slot name.
    The schema is already in the per-request cache so this is a dict lookup.
    """
    if slot_name in _SLOT_LABELS:
        return _SLOT_LABELS[slot_name]
    if cache is not None:
        schema_info = cache.get(tool_name)   # cache hit — no registry call
        if schema_info:
            props = (schema_info.get("input_schema") or {}).get("properties") or {}
            prop = props.get(slot_name, {})
            desc = prop.get("description") or prop.get("title")
            if desc:
                return desc.split(".")[0][:80]
    return slot_name.replace("_", " ")


def _missing_slots(tool_name: str, collected: Dict[str, Any],
                   cache: Optional["SchemaCache"] = None) -> List[str]:
    """Return the list of required slot names not yet present in collected."""
    required = _required_slots_for(tool_name, cache)
    return [s for s in required if not collected.get(s)]


def _build_session_context_message(
    state: Dict[str, Any],
    cache: Optional["SchemaCache"] = None,
    last_turn_summary: str = "",
) -> str:
    """
    Build a per-turn session context block — pure facts, no instructions.

    Think of this as the agent's notepad: who the user is, what we know
    about them, what happened this conversation. The agent decides what
    to do with this information — no "do not call" or "use this directly"
    directives here.
    """
    today = date.today().isoformat()
    user_email = state.get("user_email") or "unknown"
    user_name  = state.get("user_name")
    user_label = f"{user_name} ({user_email})" if user_name else user_email

    lines: List[str] = [
        "[SESSION CONTEXT]",
        f"Date: {today}",
        f"User: {user_label}",
    ]

    # ── User preferences ─────────────────────────────────────────────────────
    prefs = state.get("user_preferences") or {}
    pref_parts = []
    if prefs.get("preferred_class"):
        pref_parts.append(f"class={prefs['preferred_class']}")
    if prefs.get("preferred_quota"):
        pref_parts.append(f"quota={prefs['preferred_quota']}")
    if prefs.get("berth_preference"):
        pref_parts.append(f"berth={prefs['berth_preference']}")
    if prefs.get("senior_citizen"):
        pref_parts.append("senior_citizen=yes")
    if pref_parts:
        lines.append(f"Preferences: {', '.join(pref_parts)}")

    persistent = state.get("persistent_results") or {}

    # ── Saved passengers ──────────────────────────────────────────────────────
    saved = persistent.get("get_saved_passengers")
    if isinstance(saved, dict):
        saved = saved.get("passengers") or []
    if isinstance(saved, list):
        if saved:
            pax_lines = []
            for p in saved:
                if not isinstance(p, dict):
                    continue
                parts = [p.get("name", "?")]
                if p.get("age"):   parts.append(f"age {p['age']}")
                if p.get("gender"): parts.append(p["gender"])
                if p.get("berthPreference"): parts.append(f"berth={p['berthPreference']}")
                pax_lines.append(", ".join(parts))
            lines.append(f"Saved passengers: {' | '.join(pax_lines)}")
        else:
            lines.append("Saved passengers: none")

    # ── Past bookings ─────────────────────────────────────────────────────────
    last_booking = persistent.get("last_booking") or {}
    if last_booking.get("pnr"):
        lines.append(
            f"Most recent booking: PNR {last_booking['pnr']} | "
            f"train {last_booking.get('trainNumber', '?')} | "
            f"date {last_booking.get('journeyDate', '?')} | "
            f"status {last_booking.get('status', '?')}"
        )

    history = persistent.get("get_booking_history")
    if isinstance(history, list) and history:
        pnr_list = ", ".join(b.get("pnr", "?") for b in history if isinstance(b, dict) and b.get("pnr"))
        lines.append(f"Past bookings this session ({len(history)}): {pnr_list}")

    # ── This conversation's travel context ────────────────────────────────────
    trains = state.get("ranked_results") or state.get("search_results") or []
    if trains:
        lines.append(f"Trains found this session ({len(trains)}):")
        for t in trains[:5]:
            num  = t.get("trainNumber", "?")
            name = t.get("trainName", "")
            frm  = t.get("fromStation", "")
            to   = t.get("toStation", "")
            dep  = t.get("departure", "")
            arr  = t.get("arrival", "")
            dur  = t.get("duration", "")
            lines.append(f"  {num} {name} | {frm} {dep} → {to} {arr} ({dur})")

    sel = state.get("selected_train")
    if not sel and trains and len(trains) == 1:
        sel = trains[0]
    if sel:
        journey_date = sel.get("journeyDate", "")
        lines.append(
            f"Selected train: {sel.get('trainNumber')} {sel.get('trainName', '')} "
            f"({sel.get('fromStation')} → {sel.get('toStation')}"
            + (f", {journey_date}" if journey_date else "")
            + ")"
        )

    avail = state.get("availability")
    if avail and isinstance(avail, dict):
        status_str = avail.get("status") or ("available" if avail.get("available") else "not available")
        count = avail.get("count", "")
        cls   = avail.get("travelClass", "")
        lines.append(
            f"Availability checked: {cls} {status_str}"
            + (f", {count} seats" if count else "")
        )

    fares_map: Dict[str, Any] = persistent.get("fares") or {}
    single_fare = state.get("fare")
    if not fares_map and single_fare and isinstance(single_fare, dict):
        cls = single_fare.get("travelClass") or "?"
        fares_map = {cls: single_fare}
    if fares_map:
        fare_parts = []
        for cls, f in sorted(fares_map.items()):
            if isinstance(f, dict):
                breakdown = f.get("breakdown") or {}
                total = breakdown.get("total") or f.get("amount") or "?"
                fare_parts.append(f"{cls}=₹{total}")
        if fare_parts:
            fare_train = next(
                (f.get("trainNumber") for f in fares_map.values() if isinstance(f, dict) and f.get("trainNumber")),
                "?"
            )
            lines.append(f"Fares for train {fare_train}: {', '.join(fare_parts)}")

    booking = state.get("booking")
    pending_intent: Optional[str] = state.get("pending_intent")
    if booking and isinstance(booking, dict):
        suppress = pending_intent in ("cancel_ticket", "update_booking")
        if not suppress and booking.get("pnr"):
            lines.append(
                f"Last booking result: PNR {booking['pnr']} | "
                f"train {booking.get('trainNumber', '?')} | "
                f"status {booking.get('status', '?')}"
            )
        elif suppress and booking.get("pnr"):
            lines.append(f"Booking to act on: PNR {booking['pnr']}")

    # ── Mid-collection state ──────────────────────────────────────────────────
    collected: Dict[str, Any] = state.get("collected_slots") or {}
    if pending_intent:
        lines.append(f"Currently collecting details for: {pending_intent}")
        if collected:
            for k, v in collected.items():
                label = _slot_label_from_schema(k, pending_intent, cache)
                lines.append(f"  Already have — {label}: {v}")
        missing = _missing_slots(pending_intent, collected, cache)
        if missing:
            labels = [_slot_label_from_schema(s, pending_intent, cache) for s in missing]
            lines.append(f"  Still needed: {', '.join(labels)}")

    # ── Previous turn tool summary ────────────────────────────────────────────
    if last_turn_summary:
        lines.append(last_turn_summary)

    return "\n".join(lines)


def _extract_collected_slots(
    tool_name: str,
    args: Dict[str, Any],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge the tool args the model just produced with everything already known
    from state (selected_train, availability, fare, saved passengers) to build
    the most complete collected_slots possible.
    """
    collected: Dict[str, Any] = dict(state.get("collected_slots") or {})

    # Start from what the model gave us
    for k, v in args.items():
        if v is not None and v != "":
            collected[k] = v

    # Fill from selected_train
    sel = state.get("selected_train") or {}
    for slot, field in [
        ("trainNumber",  "trainNumber"),
        ("fromStation",  "fromStation"),
        ("toStation",    "toStation"),
        ("journeyDate",  "journeyDate"),
    ]:
        if not collected.get(slot) and sel.get(field):
            collected[slot] = sel[field]

    # Fill quota default
    if not collected.get("quota"):
        collected["quota"] = "GN"

    # Fill pnr from the most recent booking (for cancel/update flows)
    if not collected.get("pnr"):
        # 1. Try the most recent booking result in state (may be None after turn reset)
        booking = state.get("booking") or {}
        if booking.get("pnr"):
            collected["pnr"] = booking["pnr"]
        # 2. Try persistent last_booking (survives turn resets)
        if not collected.get("pnr"):
            last = (state.get("persistent_results") or {}).get("last_booking") or {}
            if last.get("pnr"):
                collected["pnr"] = last["pnr"]
        # 3. Try scanning the latest user message for a 10-digit PNR
        #    — handles "cancel PNR 1234567890" without needing history fetch
        if not collected.get("pnr"):
            for msg in reversed(state.get("messages", [])):
                if msg.__class__.__name__ == "HumanMessage":
                    m = re.search(r"\b(\d{10})\b", str(msg.content))
                    if m:
                        collected["pnr"] = m.group(1)
                    break
        # 4. Fallback: booking history when there's exactly one booking
        if not collected.get("pnr"):
            history = (state.get("persistent_results") or {}).get("get_booking_history") or []
            if len(history) == 1:
                collected["pnr"] = history[0].get("pnr", "")

    # Fill passengers from saved list if user referred to them
    if not collected.get("passengers"):
        saved = (state.get("persistent_results") or {}).get("get_saved_passengers") or []
        # Defensive: handle dict stored in checkpoint from old code version
        if isinstance(saved, dict):
            saved = saved.get("passengers") or []
        if len(saved) == 1:
            # Only one saved passenger — use automatically
            p = saved[0]
            collected["passengers"] = [{
                "name":   p.get("name", ""),
                "age":    p.get("age", ""),
                "gender": p.get("gender", ""),
                "berthPreference": p.get("berthPreference", ""),
            }]

    return collected


# ---------------------------------------------------------------------------
# Conversation-history slot extraction
# ---------------------------------------------------------------------------

# Simple patterns for extracting passenger / travel slot values from plain
# user text.  These cover the most common "Kevin 22 MALE" style responses
# without requiring the model to re-run just to parse them.

_GENDER_RE  = re.compile(r"\b(male|female|other|m|f)\b", re.IGNORECASE)
_AGE_RE     = re.compile(r"\b(\d{1,3})\b")
_CLASS_RE   = re.compile(r"\b(SL|2S|CC|3E|3A|2A|1A|EC)\b", re.IGNORECASE)
_DATE_RE    = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_STATION_RE = re.compile(r"\b([A-Z]{2,5})\b")   # station codes like BRC, NDLS, KOTA

# Berth preference aliases → normalised IRCTC codes
_BERTH_ALIASES: Dict[str, str] = {
    "lb": "LB", "lower": "LB", "lower berth": "LB",
    "mb": "MB", "middle": "MB", "middle berth": "MB",
    "ub": "UB", "upper": "UB", "upper berth": "UB",
    "sl": "SL", "side lower": "SL", "side lower berth": "SL",
    "sub": "SUB", "su": "SUB", "side upper": "SUB", "side upper berth": "SUB",
    "ws": "WS", "window": "WS", "window seat": "WS",
    "no preference": "LB",  # treat "no preference" as LB (common default)
}
# Regex that matches any of the alias keys (longest first to avoid short hits)
_BERTH_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_BERTH_ALIASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _gender_normalised(raw: str) -> str:
    raw = raw.strip().upper()
    if raw in ("M", "MALE"):
        return "MALE"
    if raw in ("F", "FEMALE"):
        return "FEMALE"
    return "OTHER"


def _extract_slots_from_messages(
    tool_name: str,
    collected: Dict[str, Any],
    messages: List[Any],
    cache: Optional["SchemaCache"] = None,
) -> Dict[str, Any]:
    """
    Scan the last few HumanMessages to fill any still-missing slots for
    tool_name.  This handles cases like the user replying "Kevin 22 MALE"
    after being asked for passenger details — the model sees those values
    in the conversation, but collected_slots may not yet reflect them.

    Only writes slots that are genuinely missing so existing values are
    never overwritten.
    """
    missing = set(_missing_slots(tool_name, collected, cache))
    if not missing:
        return collected

    updated = dict(collected)

    # Walk the last 6 messages (3 exchanges) newest-first
    recent_human: List[str] = []
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            recent_human.append(str(m.content))
            if len(recent_human) >= 3:
                break

    # ── add_saved_passenger / passenger slot filling ─────────────────────────
    if tool_name in ("add_saved_passenger", "book_ticket") and (
        "name" in missing or "age" in missing or "gender" in missing
        or "passengers" in missing
    ):
        for text in recent_human:
            words = text.strip().split()

            # Gender
            if "gender" in missing or "passengers" in missing:
                gm = _GENDER_RE.search(text)
                if gm:
                    updated.setdefault("_parsed_gender", _gender_normalised(gm.group(1)))

            # Age — first standalone number in range [1,120]
            if "age" in missing or "passengers" in missing:
                for match in _AGE_RE.finditer(text):
                    val = int(match.group(1))
                    if 1 <= val <= 120:
                        updated.setdefault("_parsed_age", val)
                        break

            # Name — first capitalised token that isn't a keyword
            _SKIP = {"MALE", "FEMALE", "OTHER", "SL", "3A", "2A", "1A", "EC",
                     "3E", "2S", "CC", "GN", "YES", "NO", "OK"}
            if "name" in missing or "passengers" in missing:
                for w in words:
                    clean = w.strip(".,!?").upper()
                    if (
                        clean not in _SKIP
                        and not clean.isdigit()
                        and len(clean) >= 2
                        and w[0].isupper()
                    ):
                        updated.setdefault("_parsed_name", w.strip(".,!?"))
                        break

            # Stop scanning if we have everything
            if all(k in updated for k in ("_parsed_name", "_parsed_age", "_parsed_gender")):
                break

        # Promote parsed values into proper slots
        if tool_name == "add_saved_passenger":
            if "name" in missing and "_parsed_name" in updated:
                updated["name"] = updated.pop("_parsed_name")
            if "age" in missing and "_parsed_age" in updated:
                updated["age"] = updated.pop("_parsed_age")
            if "gender" in missing and "_parsed_gender" in updated:
                updated["gender"] = updated.pop("_parsed_gender")
        elif tool_name == "book_ticket" and "passengers" in missing:
            pname   = updated.pop("_parsed_name", None)
            page    = updated.pop("_parsed_age", None)
            pgender = updated.pop("_parsed_gender", None)
            if pname and page and pgender:
                updated["passengers"] = [{
                    "name":   pname,
                    "age":    page,
                    "gender": pgender,
                }]
        # Clean up any leftover _parsed_* keys
        for k in ("_parsed_name", "_parsed_age", "_parsed_gender"):
            updated.pop(k, None)

    # ── Travel class ─────────────────────────────────────────────────────────
    if "travelClass" in missing:
        for text in recent_human:
            cm = _CLASS_RE.search(text)
            if cm:
                updated["travelClass"] = cm.group(1).upper()
                break

    # ── Berth preference (add_saved_passenger) ───────────────────────────────
    if tool_name == "add_saved_passenger" and "berthPreference" in missing:
        for text in recent_human:
            bm = _BERTH_RE.search(text)
            if bm:
                updated["berthPreference"] = _BERTH_ALIASES[bm.group(1).lower()]
                break

    # ── Journey date ─────────────────────────────────────────────────────────
    if "journeyDate" in missing:
        for text in recent_human:
            dm = _DATE_RE.search(text)
            if dm:
                updated["journeyDate"] = dm.group(1)
                break

    # ── Boarding station (update_booking) ────────────────────────────────────
    # Words to skip when looking for a station code in a short reply like "BRC"
    _STATION_SKIP = {"SL", "2S", "CC", "3E", "3A", "2A", "1A", "EC", "GN",
                     "YES", "NO", "OK", "M", "F"}
    if "newBoardingStation" in missing:
        for text in recent_human:
            text_up = text.strip().upper()
            # Accept if the entire message is a short station code
            if re.match(r'^[A-Z]{2,5}$', text_up) and text_up not in _STATION_SKIP:
                updated["newBoardingStation"] = text_up
                break
            # Otherwise look for an isolated code
            for m in _STATION_RE.finditer(text_up):
                code = m.group(1)
                if code not in _STATION_SKIP and len(code) >= 2:
                    updated["newBoardingStation"] = code
                    break
            if updated.get("newBoardingStation"):
                break

    # ── PNR (cancel / update_booking) ────────────────────────────────────────
    if "pnr" in missing:
        pnr_match = re.search(r'\b(\d{10})\b', " ".join(recent_human))
        if pnr_match:
            updated["pnr"] = pnr_match.group(1)

    return updated


def _grounded_pnrs(state: Dict[str, Any]) -> set:
    """Collect every PNR that appears verbatim in tool results this session."""
    blob = json.dumps(
        {
            "persistent_results": state.get("persistent_results"),
            "tool_history": [h.get("result") for h in (state.get("tool_history") or [])],
            "booking": state.get("booking"),
        },
        default=str,
    )
    return set(_PNR_RE.findall(blob))


def _summarize_last_turn_tools(state: Dict[str, Any]) -> str:
    """
    Summarize tool results from the previous turn into a compact text block.
    
    This preserves useful context (train numbers, PNRs, availability) without
    sending full JSON payloads to the LLM every turn.
    
    Returns empty string if no tools were called in the last turn.
    """
    tool_history = state.get("tool_history") or []
    if not tool_history:
        return ""
    
    lines = ["Previous turn summary:"]
    
    for h in tool_history[-6:]:  # Last 6 tools only
        tool = h.get("tool", "?")
        status = h.get("status", "unknown")
        result = h.get("result")
        
        if status == "failed":
            lines.append(f"  - {tool}: failed")
            continue
        
        # Tool-specific summarization
        if tool == "search_trains" or tool == "recommend_trains":
            if isinstance(result, list) and result:
                count = len(result)
                train_nums = ", ".join(str(t.get("trainNumber", "?")) for t in result[:3])
                lines.append(f"  - {tool}: found {count} trains ({train_nums}...)")
            elif isinstance(result, dict) and result.get("trains"):
                trains = result["trains"]
                count = len(trains)
                train_nums = ", ".join(str(t.get("trainNumber", "?")) for t in trains[:3])
                lines.append(f"  - {tool}: found {count} trains ({train_nums}...)")
            else:
                lines.append(f"  - {tool}: no trains found")
        
        elif tool == "check_availability":
            if isinstance(result, dict):
                status_str = "available" if result.get("available") else "not available"
                cls = result.get("travelClass", "?")
                count = result.get("count", "")
                lines.append(f"  - {tool}: {cls} {status_str}" + (f" ({count} seats)" if count else ""))
        
        elif tool == "get_fare":
            if isinstance(result, dict):
                amount = result.get("amount") or (result.get("breakdown") or {}).get("total")
                cls = result.get("travelClass", "?")
                lines.append(f"  - {tool}: {cls} ₹{amount}")
        
        elif tool == "book_ticket":
            if isinstance(result, dict) and result.get("pnr"):
                pnr = result["pnr"]
                train = result.get("trainNumber", "?")
                lines.append(f"  - {tool}: booked PNR {pnr} on train {train}")
        
        elif tool == "get_booking_history":
            if isinstance(result, list):
                if result:
                    count = len(result)
                    pnrs = ", ".join(b.get("pnr", "?") for b in result[:3])
                    lines.append(f"  - {tool}: {count} past bookings ({pnrs}...)")
                else:
                    lines.append(f"  - {tool}: no past bookings")
        
        elif tool == "get_saved_passengers":
            if isinstance(result, list):
                if result:
                    names = ", ".join(p.get("name", "?") for p in result)
                    lines.append(f"  - {tool}: {len(result)} saved ({names})")
                else:
                    lines.append(f"  - {tool}: no saved passengers")
        
        else:
            # Generic summary for other tools
            lines.append(f"  - {tool}: success")
    
    return "\n".join(lines) if len(lines) > 1 else ""


def _ground_reply(reply: str, state: Dict[str, Any]) -> str:
    """Redact any 10-digit PNR the model emits that is not in tool data."""
    allowed = _grounded_pnrs(state)
    return _PNR_RE.sub(
        lambda m: m.group(0) if m.group(0) in allowed else "[PNR unavailable]",
        reply,
    )


def _build_messages_for_llm(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert the LangGraph message list into the OpenAI messages format.

    Applies a sliding window (last 30 messages), always anchoring the first
    HumanMessage.

    IMPORTANT — OpenAI hard rule:
    Every tool_call_id in an assistant message must have a matching tool-role
    response. After windowing, any AIMessage whose ToolMessages were trimmed has
    its tool_calls field stripped so OpenAI never sees an unmatched call_id.
    """
    raw: List[Any] = state.get("messages", [])

    _WINDOW = 30
    if len(raw) > _WINDOW:
        first_human = next((m for m in raw if isinstance(m, HumanMessage)), None)
        windowed = raw[-_WINDOW:]
        if first_human and first_human not in windowed:
            windowed = [first_human] + windowed
    else:
        windowed = list(raw)

    covered_ids: set = {
        msg.tool_call_id
        for msg in windowed
        if isinstance(msg, ToolMessage)
    }
    declared_ids: set = {
        c["id"]
        for msg in windowed
        if isinstance(msg, AIMessage)
        for c in (getattr(msg, "tool_calls", None) or [])
    }
    valid_tool_ids: set = covered_ids & declared_ids

    result: List[Dict[str, Any]] = []
    for msg in windowed:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": str(msg.content)})

        elif isinstance(msg, AIMessage):
            entry: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            tc = getattr(msg, "tool_calls", None)
            if tc:
                covered_calls = [c for c in tc if c["id"] in valid_tool_ids]
                if covered_calls:
                    entry["tool_calls"] = [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": json.dumps(c["args"]),
                            },
                        }
                        for c in covered_calls
                    ]
            result.append(entry)

        elif isinstance(msg, ToolMessage):
            if msg.tool_call_id in valid_tool_ids:
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": str(msg.content),
                })

    return result or [{"role": "user", "content": "Hello"}]


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def agent_node(
    state: Dict[str, Any],
    llm_service,
    mcp_registry,
) -> Dict[str, Any]:
    prior_loop = state.get("agent_loop_count") or 0
    is_new_turn = prior_loop == 0
    loop_count = prior_loop + 1

    if loop_count > _MAX_LOOP:
        return {
            "messages": [AIMessage(content=(
                "I'm having trouble completing this request — "
                "could you rephrase or simplify it?"
            ))],
            "pending_tool_calls": [],
            "agent_loop_count": 0,
            "tool_history": [],
            "errors": [],
            "pending_intent": None,
            "collected_slots": None,
        }

    # ── Compress message history at the start of a new user turn ────────────
    # Instead of dropping all tool call history (which loses useful context),
    # we:
    # 1. Summarize the previous turn's tool results into a compact text block
    # 2. Keep HumanMessages and text-only AIMessages (final answers)
    # 3. Drop raw ToolMessages and AIMessages that are pure tool_call stubs
    #    (empty content + tool_calls) — these confuse the LLM with orphaned
    #    call IDs and raw JSON that is already summarized in the context block
    last_turn_summary = ""
    if is_new_turn:
        messages_raw = state.get("messages", [])

        # Build a compact summary of what tools ran last turn BEFORE stripping.
        # Stored in a local var — injected into the session context message
        # (not back into the message list) so chat.py never picks it up as a reply.
        last_turn_summary = _summarize_last_turn_tools(state)

        cleaned = []
        for msg in messages_raw:
            if isinstance(msg, HumanMessage):
                cleaned.append(msg)
            elif isinstance(msg, AIMessage):
                content = getattr(msg, "content", None)
                if content and str(content).strip():
                    # Final answer message — keep text only, drop tool_calls
                    cleaned.append(AIMessage(
                        content=str(content).strip(),
                        id=getattr(msg, "id", None),
                    ))
                # Pure tool-dispatch AIMessages (no content) are dropped
            # ToolMessages are dropped — their data lives in persistent_results
            # and is surfaced via the session context block if still relevant

        state = {**state, "messages": cleaned}

    feedback = state.get("reflection_feedback") or ""
    feedback_block = (
        f"\n[Note: your previous answer was incomplete — {feedback}. Please fix this.]"
        if feedback else ""
    )

    # ── Per-request schema cache ─────────────────────────────────────────────
    # Built once here, used by every helper below, discarded when this call
    # returns.  No cross-request state, no manual invalidation needed.
    cache = SchemaCache(mcp_registry)

    # ── Pre-enrich collected_slots from conversation history ─────────────────
    active_intent_pre: Optional[str] = state.get("pending_intent")
    if active_intent_pre:
        pre_slots = _extract_collected_slots(active_intent_pre, {}, state)
        pre_slots = _extract_slots_from_messages(
            active_intent_pre, pre_slots, state.get("messages", []), cache
        )
        # Temporarily patch state view for context building only — we do NOT
        # write back to state here; that happens in the no-tool-calls branch.
        state = {**state, "collected_slots": pre_slots}

    tools: List[Dict[str, Any]] = cache.get_tool_list()

    messages = _build_messages_for_llm(state)

    # Prepend a session context message so dynamic data (date, user email,
    # session state) stays OUT of the static system prompt and is visible
    # in LangSmith traces as a separate, clearly-labelled context message.
    # We inject this as a system-role message so it doesn't pollute the
    # assistant turn history and can never be mistaken for a real reply.
    session_ctx = _build_session_context_message(state, cache, last_turn_summary=last_turn_summary)
    messages = [{"role": "system", "content": session_ctx}, *messages]

    system = _SYSTEM_TEMPLATE.format(feedback=feedback_block)

    response = await llm_service.chat_raw(
        messages=messages,
        system=system,
        tools=tools if tools else None,
        tool_choice="auto" if tools else None,
        temperature=0.3,
        max_tokens=2048,
    )

    msg = response.choices[0].message
    raw_tool_calls = msg.tool_calls or []

    reset_fields: Dict[str, Any] = {
        "tool_history": [],
        "errors": [],
        "reflection_required": False,
        "reflection_passed": False,
        "reflection_feedback": "",
        "reflection_retries": 0,
        "reflection_tool_offset": 0,
        "reflection_tool_snapshot": None,
        # ── Turn-scoped travel context ────────────────────────────────────────
        # Clear all search/booking context at the start of every new user turn.
        # These fields belong to the previous intent and must not bleed into the
        # next one (e.g. booking search results polluting a cancel flow).
        # persistent_results (booking history, saved passengers) is intentionally
        # NOT cleared — it survives the full conversation by design.
        "search_results":  None,
        "ranked_results":  None,
        "selected_train":  None,
        "availability":    None,
        "fare":            None,
        "booking":         None,  # last booking result — clear so old bookings don't pollute new intents
        "pending_intent":  None,
        "collected_slots": None,
        "pending_tool_calls":  [],
        "confirmed":           None,
        "confirmation_prompt": None,  # clear stale prompt so cancel/update flows never show the previous booking prompt
    } if is_new_turn else {}

    # ── Intent guardrail — block only clear hallucinations ───────────────────
    # The LLM already understands user intent from the conversation — we don't
    # re-evaluate it with keyword matching here.  The only thing we guard
    # against is a write tool being called on loop_count > 1 when there is no
    # active pending_intent (i.e. the model spontaneously re-fires a write tool
    # mid-loop without the user asking again).  Mid-collection calls are always
    # allowed because the user IS providing the requested information.
    if raw_tool_calls and loop_count > 1:
        active_intent: Optional[str] = state.get("pending_intent")
        _WRITE_TOOLS = {
            "book_ticket", "cancel_ticket",
            "add_saved_passenger", "delete_saved_passenger",
            "update_booking",
        }
        raw_tool_calls = [
            tc for tc in raw_tool_calls
            if tc.function.name not in _WRITE_TOOLS
            or active_intent == tc.function.name
        ]

    # ── No tool calls → question or final answer ─────────────────────────────
    if not raw_tool_calls:
        reply = _ground_reply(msg.content or "", state)

        updates: Dict[str, Any] = {
            "messages": [AIMessage(content=reply)],
            "pending_tool_calls": [],
            "agent_loop_count": 0,
            "reflection_feedback": "",
            **reset_fields,
        }

        # ── Slot-filling state management ──────────────────────────────────────
        # When the agent asks for a missing detail it produces a text reply
        # (no tool call).  We must keep pending_intent alive across that turn
        # so the *next* turn — where the user answers — still knows what it's
        # collecting toward.
        #
        # KEY DESIGN: when we detect that all slots are now filled (from the
        # conversation history), we synthesize the tool call directly rather
        # than waiting for the LLM to be re-invoked. This avoids an extra
        # round-trip and ensures the tool actually gets called.
        existing_intent: Optional[str] = state.get("pending_intent")

        if existing_intent:
            # Re-derive collected_slots and try to pick up values the user
            # just provided (e.g. "Kevin 22 MALE" after being asked for name).
            refreshed_slots = _extract_collected_slots(existing_intent, {}, state)
            refreshed_slots = _extract_slots_from_messages(
                existing_intent, refreshed_slots, state.get("messages", []), cache
            )
            missing_now = _missing_slots(existing_intent, refreshed_slots, cache)
            if missing_now:
                # Still waiting for more info — keep intent alive.
                updates["pending_intent"]  = existing_intent
                updates["collected_slots"] = refreshed_slots
            else:
                # All slots filled — synthesize the pending tool call so the
                # graph routes to tool_executor_node (or human_approval_node)
                # on this same turn, without needing another LLM round-trip.
                synthetic_id   = f"synth_{uuid.uuid4().hex[:12]}"
                synthetic_call = {
                    "id":   synthetic_id,
                    "name": existing_intent,
                    "args": refreshed_slots,
                }
                ai_tool_msg = AIMessage(
                    content=reply,
                    tool_calls=[{
                        "id":   synthetic_id,
                        "name": existing_intent,
                        "args": refreshed_slots,
                    }],
                )
                return {
                    **updates,
                    "messages":          [ai_tool_msg],
                    "pending_tool_calls": [synthetic_call],
                    "agent_loop_count":   loop_count,
                    "pending_intent":     None,
                    "collected_slots":    None,
                }
        else:
            # No active intent — the LLM produced a text reply on a fresh turn.
            # Derive the intended tool directly from what the LLM tried to call
            # (if it made a tool call that got stripped by the guardrail, or if
            # it asked a clarifying question before calling anything).
            # We read this from the raw OpenAI response's tool_calls before the
            # guardrail may have emptied raw_tool_calls.
            # Since we're in the no-tool-calls branch, check the original msg.
            inferred_intent: Optional[str] = None
            _WRITE_TOOLS_SET = {
                "book_ticket", "cancel_ticket",
                "add_saved_passenger", "delete_saved_passenger",
                "update_booking", "check_availability", "get_live_status",
                "create_reminder",
            }
            # The LLM may have emitted a partial tool call before asking — check
            # the original message tool_calls (msg.tool_calls, not raw_tool_calls
            # which may have been filtered).
            original_calls = msg.tool_calls or []
            for tc in original_calls:
                if tc.function.name in _WRITE_TOOLS_SET:
                    inferred_intent = tc.function.name
                    break

            if inferred_intent:
                seed_slots = _extract_collected_slots(inferred_intent, {}, state)
                seed_slots  = _extract_slots_from_messages(
                    inferred_intent, seed_slots, state.get("messages", []), cache
                )
                missing_now = _missing_slots(inferred_intent, seed_slots, cache)
                if missing_now:
                    updates["pending_intent"]  = inferred_intent
                    updates["collected_slots"] = seed_slots
                else:
                    updates["pending_intent"]  = None
                    updates["collected_slots"] = None
            else:
                updates["pending_intent"]  = None
                updates["collected_slots"] = None

        # Only trigger reflection when:
        # 1. Tools actually ran this turn (tool_history is non-empty)
        # 2. The agent produced a genuine text reply (reply is non-empty)
        # 3. Reflection hasn't already passed this turn
        # Do NOT trigger if reply is empty — that means the agent is mid-flow
        # (e.g. just produced a slot-filling clarification with no real answer yet)
        tool_history_now: list = state.get("tool_history") or []
        if tool_history_now and reply and not state.get("reflection_passed"):
            updates["reflection_required"] = True
            # Tell reflection_node exactly which tools are relevant to this
            # final reply — only the most recent batch (last executor run),
            # not all tools accumulated across the whole turn.
            # We identify the last batch as entries added after the previous
            # agent loop count, tracked via reflection_tool_offset.
            offset = state.get("reflection_tool_offset") or 0
            updates["reflection_tool_snapshot"] = tool_history_now[offset:]

        return updates

    # ── Tool calls → parse, collect slots, stage ─────────────────────────────
    pending: List[Dict[str, Any]] = []
    for tc in raw_tool_calls:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        pending.append({
            "id":   tc.id,
            "name": tc.function.name,
            "args": args,
        })

    ai_msg = AIMessage(
        content=msg.content or "",
        tool_calls=[
            {"id": p["id"], "name": p["name"], "args": p["args"]}
            for p in pending
        ],
    )

    # When tool calls fire, the intent is being executed — clear pending_intent.
    # Also update collected_slots with what the model resolved so future turns
    # can resume correctly if this tool call only partially satisfies the intent.
    first_tool = pending[0]["name"]
    resolved_slots = _extract_collected_slots(
        first_tool, pending[0]["args"], state
    )
    missing = _missing_slots(first_tool, resolved_slots, cache)

    slot_updates: Dict[str, Any] = {
        "pending_intent":  None,
        "collected_slots": None,
    }

    # Edge case: model emitted a tool call but args are still incomplete
    if missing and first_tool in cache.known_tool_names():
        slot_updates["pending_intent"]  = first_tool
        slot_updates["collected_slots"] = resolved_slots

    # If an active booking/passenger intent exists but the tool being called is
    # a different (read-only) tool (e.g. check_availability fired mid-booking,
    # or get_saved_passengers fired mid-add-passenger), do NOT wipe pending_intent.
    # The booking/passenger flow must survive intermediate read-only tool calls.
    _WRITE_INTENTS = {"book_ticket", "cancel_ticket", "add_saved_passenger",
                      "delete_saved_passenger", "update_booking", "manage_reminder"}
    existing_pi = state.get("pending_intent")
    if existing_pi in _WRITE_INTENTS and first_tool != existing_pi:
        # Preserve the pending intent and merge slot data from conversation
        surviving_slots = _extract_collected_slots(existing_pi, {}, state)
        surviving_slots = _extract_slots_from_messages(
            existing_pi, surviving_slots, state.get("messages", []), cache
        )
        slot_updates["pending_intent"]  = existing_pi
        slot_updates["collected_slots"] = surviving_slots

    # ── Early-pin selected_train when a single train is targeted ─────────────
    early_updates: Dict[str, Any] = {}
    if not state.get("selected_train"):
        focused_num: Optional[str] = None
        focused_date: Optional[str] = None
        for p in pending:
            args = p.get("args") or {}
            num = args.get("trainNumber") or args.get("train_number")
            dt  = args.get("journeyDate") or args.get("date")
            if num:
                if focused_num is None:
                    focused_num = str(num)
                    focused_date = dt
                elif focused_num != str(num):
                    focused_num = None
                    break
        if focused_num:
            all_trains = state.get("ranked_results") or state.get("search_results") or []
            base = next(
                (t for t in all_trains if str(t.get("trainNumber")) == focused_num),
                None,
            )
            if base:
                sel: Dict[str, Any] = {
                    "trainNumber": focused_num,
                    "trainName":   base.get("trainName", ""),
                    "fromStation": base.get("fromStation", ""),
                    "toStation":   base.get("toStation", ""),
                    "departure":   base.get("departure", ""),
                    "arrival":     base.get("arrival", ""),
                    "duration":    base.get("duration", ""),
                    "classes":     base.get("classes", []),
                }
                if focused_date:
                    sel["journeyDate"] = focused_date
                early_updates["selected_train"] = sel

    return {
        "messages": [ai_msg],
        **reset_fields,
        **slot_updates,
        **early_updates,
        # These must come last — reset_fields contains "pending_tool_calls": []
        # which would overwrite the real pending list if it came after.
        "pending_tool_calls": pending,
        "agent_loop_count": loop_count,
    }
