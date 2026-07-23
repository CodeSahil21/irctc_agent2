import json
import re
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
    "update_booking":        ["pnr"],
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
    "add_saved_passenger":   ["name", "age", "gender"],
}

# Human-readable labels for slot names shown in the context block
_SLOT_LABELS: Dict[str, str] = {
    "trainNumber":   "train number",
    "journeyDate":   "journey date (YYYY-MM-DD)",
    "fromStation":   "origin station code",
    "toStation":     "destination station code",
    "travelClass":   "travel class (e.g. SL, 3A, 2A, 1A)",
    "quota":         "quota (default: GN)",
    "passengers":    "passenger details (name, age, gender for each)",
    "pnr":           "PNR number",
    "stationCode":   "station code",
    "query":         "search query",
    "action":        "action (create/update/delete)",
    "reminderType":  "reminder type",
    "reminderTime":  "reminder time",
    "name":          "passenger name",
    "age":           "passenger age",
    "gender":        "passenger gender",
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """\
You are the official IRCTC AI Travel Assistant. You have live tools for train \
search, seat availability, fares, booking, cancellation, reminders, and account \
management.

TODAY'S DATE: {today}
Use this date as the reference for all relative date expressions ("tomorrow", \
"this weekend", "next Monday", "this week", "next week", etc.). \
Always resolve them to an explicit YYYY-MM-DD date before calling any tool. \
NEVER use a date from 2023 or any year other than the current year unless the \
user explicitly provides a past date.

SLOT-FILLING PROTOCOL
When you need to call a tool but one or more required arguments are missing:
1. Check the CURRENT SESSION CONTEXT below — values already collected are listed \
under "Collecting details for <tool>". Do NOT re-ask for anything already there.
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
- Before calling book_ticket, you MUST have ALL of: trainNumber, journeyDate \
(YYYY-MM-DD), fromStation, toStation, travelClass, passengers (name/age/gender \
for each), quota (default GN if not specified). \
- If journeyDate is not in context, call check_availability for the selected train \
first — the response includes journeyDate. \
- If the user says "use my saved passenger" or names a passenger from the saved \
list, use those exact details — do not re-ask. \
- Do NOT ask "shall I proceed?" before booking — the system handles confirmation \
separately after you call book_ticket. Just call it.

CORE RULES
- Use tools to get real data. NEVER invent or guess PNRs, train numbers, fares, \
seat counts, or availability.
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

CONTEXT
{context}
{feedback}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _missing_slots(tool_name: str, collected: Dict[str, Any]) -> List[str]:
    """Return the list of required slot names not yet present in collected."""
    required = _TOOL_REQUIRED_SLOTS.get(tool_name, [])
    return [s for s in required if not collected.get(s)]


def _build_context(state: Dict[str, Any]) -> str:
    lines: List[str] = [f"- Signed in as: {state.get('user_email') or 'unknown'}"]

    prefs = state.get("user_preferences") or {}
    if prefs.get("preferred_class"):
        lines.append(f"- Preferred class: {prefs['preferred_class']}")
    if prefs.get("preferred_quota"):
        lines.append(f"- Preferred quota: {prefs['preferred_quota']}")
    if prefs.get("berth_preference"):
        lines.append(f"- Preferred berth: {prefs['berth_preference']}")
    if prefs.get("senior_citizen"):
        lines.append("- Senior citizen discount applies")

    persistent = state.get("persistent_results") or {}
    history = persistent.get("get_booking_history")
    if history is not None:
        if history:
            lines.append(
                f"- {len(history)} past booking(s) already fetched this session "
                f"(reuse unless the user asks to refresh)."
            )
        else:
            lines.append(
                "- Booking history already fetched this session: no bookings found "
                "(do NOT call get_booking_history again unless the user explicitly asks to refresh)."
            )
    saved = persistent.get("get_saved_passengers")
    if saved:
        names = ", ".join(p.get("name", "?") for p in saved)
        lines.append(f"- Saved passengers: {names}")

    # ── Pending intent — mid-collection state ────────────────────────────────
    pending_intent: Optional[str] = state.get("pending_intent")
    collected: Dict[str, Any] = state.get("collected_slots") or {}
    if pending_intent:
        lines.append("")
        lines.append(f"COLLECTING DETAILS FOR: {pending_intent}")
        lines.append("Already collected (do NOT re-ask for these):")
        if collected:
            for k, v in collected.items():
                label = _SLOT_LABELS.get(k, k)
                lines.append(f"  ✓ {label}: {v}")
        missing = _missing_slots(pending_intent, collected)
        if missing:
            labels = [_SLOT_LABELS.get(s, s) for s in missing]
            lines.append(f"Still needed: {', '.join(labels)}")
            lines.append(
                f"Ask for the FIRST missing field only: {_SLOT_LABELS.get(missing[0], missing[0])}"
            )
        else:
            lines.append(
                "ALL required fields are now collected — call the tool immediately."
            )

    # ── Active travel context ────────────────────────────────────────────────
    lines.append("")
    lines.append("CURRENT SESSION CONTEXT (do not ask the user for these again):")

    trains = state.get("ranked_results") or state.get("search_results") or []
    if trains:
        lines.append(f"- Train search results available: {len(trains)} train(s) found.")
        for t in trains[:5]:
            num   = t.get("trainNumber", "?")
            name  = t.get("trainName", "")
            dep   = t.get("departure", "")
            arr   = t.get("arrival", "")
            dur   = t.get("duration", "")
            frm   = t.get("fromStation", "")
            to    = t.get("toStation", "")
            avail = t.get("availability", {})
            avail_str = ""
            if isinstance(avail, dict):
                if avail.get("available"):
                    avail_str = f" | AVBL-{avail.get('count', '?')}"
                elif avail.get("status") == "WL":
                    avail_str = f" | WL#{avail.get('count', '?')}"
                elif avail.get("status") == "RAC":
                    avail_str = f" | RAC {avail.get('count', '?')}"
                else:
                    avail_str = " | NOT AVBL"
            lines.append(f"  • {num} {name} | {frm} {dep}→{to} {arr} ({dur}){avail_str}")

    sel = state.get("selected_train")
    if not sel and trains and len(trains) == 1:
        sel = trains[0]
    if sel:
        journey_date = sel.get("journeyDate", "")
        date_str = (
            f" | journeyDate={journey_date}"
            if journey_date
            else " | journeyDate=UNKNOWN (call check_availability first)"
        )
        lines.append(
            f"- Selected train: {sel.get('trainNumber')} {sel.get('trainName', '')} "
            f"({sel.get('fromStation')}→{sel.get('toStation')}{date_str}) — "
            f"use these values directly for book_ticket."
        )

    avail = state.get("availability")
    if avail and isinstance(avail, dict):
        status_str = avail.get("status") or ("AVBL" if avail.get("available") else "N/A")
        count = avail.get("count", "")
        cls   = avail.get("travelClass", "")
        lines.append(
            f"- Availability already checked: {cls} {status_str}"
            + (f" ({count} seats)" if count else "")
        )

    fares_map: Dict[str, Any] = persistent.get("fares") or {}
    single_fare = state.get("fare")
    if not fares_map and single_fare and isinstance(single_fare, dict):
        cls = single_fare.get("travelClass") or "?"
        fares_map = {cls: single_fare}
    if fares_map:
        fare_train = ""
        fare_lines = []
        for cls, f in sorted(fares_map.items()):
            if isinstance(f, dict):
                breakdown = f.get("breakdown") or {}
                total = breakdown.get("total") or f.get("amount") or "?"
                fare_train = f.get("trainNumber", fare_train)
                fare_lines.append(f"    {cls}: ₹{total}")
        if fare_lines:
            lines.append(
                f"- Fares already fetched for train {fare_train} "
                f"(do NOT call get_fare again for these classes):"
            )
            lines.extend(fare_lines)

    booking = state.get("booking")
    if booking and isinstance(booking, dict):
        pnr     = booking.get("pnr", "")
        status_b = booking.get("status", "")
        train   = booking.get("trainNumber", "")
        lines.append(f"- Active booking: PNR {pnr} | train {train} | status {status_b}")

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

    # Fill passengers from saved list if user referred to them
    if not collected.get("passengers"):
        saved = (state.get("persistent_results") or {}).get("get_saved_passengers") or []
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

    feedback = state.get("reflection_feedback") or ""
    feedback_block = (
        f"\n[Note: your previous answer was incomplete — {feedback}. Please fix this.]"
        if feedback else ""
    )

    tools: List[Dict[str, Any]] = mcp_registry.get_tool_schemas() if mcp_registry else []

    messages = _build_messages_for_llm(state)
    system = _SYSTEM_TEMPLATE.format(
        today=date.today().isoformat(),
        context=_build_context(state),
        feedback=feedback_block,
    )

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

    reset_fields: Dict[str, Any] = {"tool_history": [], "errors": []} if is_new_turn else {}

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

        # Detect if the reply is asking the user for a missing detail.
        # We preserve pending_intent + collected_slots so the next turn knows
        # where it left off. If there's no active intent, these stay None.
        existing_intent: Optional[str] = state.get("pending_intent")
        existing_slots: Dict[str, Any] = state.get("collected_slots") or {}

        if existing_intent:
            # Still mid-collection — re-derive collected_slots from current state
            # so any new information the user just provided is captured.
            refreshed_slots = _extract_collected_slots(existing_intent, {}, state)
            updates["pending_intent"]  = existing_intent
            updates["collected_slots"] = refreshed_slots
        else:
            # Detect a new collection starting: look for intent keywords in the
            # reply that suggest the agent is asking for booking/cancellation info.
            # We infer from the reply text which tool was being aimed at.
            reply_lower = reply.lower()
            inferred_intent: Optional[str] = None
            if any(w in reply_lower for w in ("book", "booking", "reserve", "ticket")):
                inferred_intent = "book_ticket"
            elif any(w in reply_lower for w in ("cancel", "cancellation")):
                inferred_intent = "cancel_ticket"
            elif any(w in reply_lower for w in ("availability", "available seats", "check seat")):
                inferred_intent = "check_availability"
            elif any(w in reply_lower for w in ("live status", "running status", "train status")):
                inferred_intent = "get_live_status"
            elif any(w in reply_lower for w in ("reminder")):
                inferred_intent = "create_reminder"

            if inferred_intent:
                # Seed collected_slots with what we already know from state
                seed_slots = _extract_collected_slots(inferred_intent, {}, state)
                missing_now = _missing_slots(inferred_intent, seed_slots)
                if missing_now:
                    # Genuinely missing something — start tracking
                    updates["pending_intent"]  = inferred_intent
                    updates["collected_slots"] = seed_slots
                else:
                    updates["pending_intent"]  = None
                    updates["collected_slots"] = None
            else:
                updates["pending_intent"]  = None
                updates["collected_slots"] = None

        if state.get("tool_history") and not state.get("reflection_passed"):
            updates["reflection_required"] = True

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
    missing = _missing_slots(first_tool, resolved_slots)

    slot_updates: Dict[str, Any] = {
        # If the model is calling the tool, intent is being fulfilled — clear it.
        "pending_intent":  None,
        "collected_slots": None,
    }

    # Edge case: model emitted a tool call but args are still incomplete
    # (shouldn't happen after prompt fix, but guard anyway — don't clear intent).
    if missing and first_tool in _TOOL_REQUIRED_SLOTS:
        slot_updates["pending_intent"]  = first_tool
        slot_updates["collected_slots"] = resolved_slots

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
        "pending_tool_calls": pending,
        "agent_loop_count": loop_count,
        **reset_fields,
        **slot_updates,
        **early_updates,
    }
