import json
import re
from datetime import date
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

_MAX_LOOP = 8

# Grounding: Indian Railways PNRs are exactly 10 digits.
_PNR_RE = re.compile(r"\b\d{10}\b")

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

BOOKING RULES
- Before calling book_ticket, you MUST have ALL of these: trainNumber, \
journeyDate (YYYY-MM-DD), fromStation, toStation, travelClass, passengers list, quota. \
- If journeyDate is not in the session context, call check_availability for the \
selected train first — the response will include journeyDate. \
- Never guess or omit journeyDate. If you truly cannot determine it, ask the user \
for the exact travel date before proceeding. \
- When the user picks a train from search results, call check_availability for that \
train (with the class they want) before calling book_ticket — this confirms seats \
and captures the journey date in one step. \
- Passengers: if the user says "use my saved passenger" or refers to a passenger by \
name from the saved list, use those exact details. Do not ask for details already in context.

CORE RULES
- Use tools to get real data. NEVER invent or guess PNRs, train numbers, fares, \
seat counts, or availability.
- If you need a piece of information to proceed (origin station, date, which train, \
passenger details, PNR) and it is not already in the conversation or tool results — \
ask the user in plain text, one question at a time. Never call a tool with a guessed \
or placeholder value.
- Resolve station names/cities to codes with find_station before using them \
elsewhere, unless you already have a valid 2–5 letter station code.
- When comparing several trains (fares, availability, etc.), emit all relevant tool \
calls IN THE SAME response turn — the system executes them concurrently.
- Prefer recommend_trains over manually chaining search_trains + check_availability \
+ get_fare when the user just wants a ranked shortlist.
- Do NOT ask "shall I proceed?" before booking, cancelling, or deleting — the \
system handles confirmation separately right after you call that tool. Just call it.
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
    # Use `is not None` so an empty list is still surfaced — the model needs to
    # know the tool was already called and returned no results, otherwise it
    # will either skip the tool (and hallucinate) or call it again unnecessarily.
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

    # ── Active travel context ────────────────────────────────────────────────
    # Surfaces whatever the agent already knows from prior turns so the model
    # never has to re-ask for information it already has.
    lines.append("")
    lines.append("CURRENT SESSION CONTEXT (do not ask the user for these again):")

    # Search results / ranked trains from this session
    trains = state.get("ranked_results") or state.get("search_results") or []
    if trains:
        lines.append(f"- Train search results available: {len(trains)} train(s) found.")
        for t in trains[:5]:  # cap at 5 to avoid bloating the prompt
            num  = t.get("trainNumber", "?")
            name = t.get("trainName", "")
            dep  = t.get("departure", "")
            arr  = t.get("arrival", "")
            dur  = t.get("duration", "")
            frm  = t.get("fromStation", "")
            to   = t.get("toStation", "")
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

    # Selected / focused train — from explicit state or inferred from search results
    # when the conversation has narrowed to a single train
    sel = state.get("selected_train")
    if not sel and trains and len(trains) == 1:
        sel = trains[0]
    if sel:
        journey_date = sel.get("journeyDate", "")
        date_str = f" | journeyDate={journey_date}" if journey_date else " | journeyDate=UNKNOWN (call check_availability first)"
        lines.append(
            f"- Selected train: {sel.get('trainNumber')} {sel.get('trainName', '')} "
            f"({sel.get('fromStation')}→{sel.get('toStation')}{date_str}) — "
            f"use these values directly for book_ticket."
        )

    # Availability checked
    avail = state.get("availability")
    if avail and isinstance(avail, dict):
        status_str = avail.get("status") or ("AVBL" if avail.get("available") else "N/A")
        count = avail.get("count", "")
        cls   = avail.get("travelClass", "")
        lines.append(
            f"- Availability already checked: {cls} {status_str}"
            + (f" ({count} seats)" if count else "")
        )

    # Fares fetched — show all classes stored in persistent_results["fares"],
    # falling back to the single compat fare field for older state shapes.
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

    # Active booking
    booking = state.get("booking")
    if booking and isinstance(booking, dict):
        pnr    = booking.get("pnr", "")
        status_b = booking.get("status", "")
        train  = booking.get("trainNumber", "")
        lines.append(f"- Active booking: PNR {pnr} | train {train} | status {status_b}")

    return "\n".join(lines)


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

    Key difference from the old format_messages() helper: we DO include
    AIMessages that carry tool_calls and the subsequent ToolMessages, because
    the model needs that context to continue the loop correctly.

    We apply a sliding window (last 30 messages) to keep prompt size bounded,
    always anchoring the first human message.

    IMPORTANT — OpenAI hard rule:
    Every tool_call_id emitted in an assistant message must have a matching
    tool-role response in the same history.  When the sliding window trims
    the tail of a prior turn, an AIMessage with tool_calls can end up without
    its ToolMessages.  We guard against this in two ways:

    1. After windowing, collect all tool_call_ids that have a ToolMessage
       present in the window.
    2. For any AIMessage whose tool_calls are NOT fully covered, strip the
       tool_calls field (keeping the text content if any) so OpenAI never
       sees an unmatched call_id.
    """
    raw: List[Any] = state.get("messages", [])

    # Sliding window — keep first HumanMessage + last 30 messages
    _WINDOW = 30
    if len(raw) > _WINDOW:
        first_human = next(
            (m for m in raw if isinstance(m, HumanMessage)), None
        )
        windowed = raw[-_WINDOW:]
        if first_human and first_human not in windowed:
            windowed = [first_human] + windowed
    else:
        windowed = list(raw)

    # Collect all tool_call_ids that have a ToolMessage present in the window
    covered_ids: set = {
        msg.tool_call_id
        for msg in windowed
        if isinstance(msg, ToolMessage)
    }

    # Collect all tool_call_ids that are declared by an AIMessage in the window.
    # ToolMessages whose parent AIMessage was trimmed must also be dropped —
    # OpenAI requires the assistant message to precede its tool responses.
    declared_ids: set = {
        c["id"]
        for msg in windowed
        if isinstance(msg, AIMessage)
        for c in (getattr(msg, "tool_calls", None) or [])
    }
    # Only keep ToolMessages that have their parent AIMessage present
    valid_tool_ids: set = covered_ids & declared_ids

    result: List[Dict[str, Any]] = []
    for msg in windowed:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": str(msg.content)})

        elif isinstance(msg, AIMessage):
            entry: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            tc = getattr(msg, "tool_calls", None)
            if tc:
                # Only include tool_calls whose ToolMessage responses are
                # also present in the window. If none are covered, emit only
                # text; if some are covered, include only the covered subset
                # (the rest were already responded to in an earlier window).
                covered_calls = [
                    c for c in tc if c["id"] in valid_tool_ids
                ]
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
                # If no covered calls, tool_calls is simply omitted — the
                # assistant message becomes a plain text entry, which is
                # valid even if content is empty string.
            result.append(entry)

        elif isinstance(msg, ToolMessage):
            # Drop ToolMessages whose parent AIMessage was trimmed from window
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

    # Hard loop guard
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
        }

    # Reflection feedback injection
    feedback = state.get("reflection_feedback") or ""
    feedback_block = (
        f"\n[Note: your previous answer was incomplete — {feedback}. Please fix this.]"
        if feedback else ""
    )

    # Fetch live tool schemas from the registry
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

    # Fields reset at the start of each new user turn
    reset_fields: Dict[str, Any] = {"tool_history": [], "errors": []} if is_new_turn else {}

    # ── No tool calls → final answer ────────────────────────────────────────
    if not raw_tool_calls:
        reply = _ground_reply(msg.content or "", state)
        updates: Dict[str, Any] = {
            "messages": [AIMessage(content=reply)],
            "pending_tool_calls": [],
            "agent_loop_count": 0,
            "reflection_feedback": "",
            **reset_fields,
        }
        # Trigger reflection if tools ran this turn and we haven't checked yet
        if state.get("tool_history") and not state.get("reflection_passed"):
            updates["reflection_required"] = True
        return updates

    # ── Tool calls → parse and stage ────────────────────────────────────────
    pending: List[Dict[str, Any]] = []
    for tc in raw_tool_calls:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        pending.append({
            "id": tc.id,
            "name": tc.function.name,
            "args": args,
        })

    # Persist the AIMessage with tool_calls so the loop history is coherent
    ai_msg = AIMessage(
        content=msg.content or "",
        tool_calls=[
            {"id": p["id"], "name": p["name"], "args": p["args"]}
            for p in pending
        ],
    )

    # Early-pin selected_train when the agent targets a specific train.
    # This ensures the train card collapses to one entry and journeyDate is
    # available in state even before tool_executor_node runs.
    early_updates: Dict[str, Any] = {}
    if not state.get("selected_train"):
        # Find any pending call that unambiguously references one train number
        focused_num = None
        focused_date = None
        for p in pending:
            args = p.get("args") or {}
            num = args.get("trainNumber") or args.get("train_number")
            dt  = args.get("journeyDate") or args.get("date")
            if num:
                if focused_num is None:
                    focused_num = str(num)
                    focused_date = dt
                elif focused_num != str(num):
                    # Multiple different trains targeted — don't pin yet
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
                    "trainNumber":  focused_num,
                    "trainName":    base.get("trainName", ""),
                    "fromStation":  base.get("fromStation", ""),
                    "toStation":    base.get("toStation", ""),
                    "departure":    base.get("departure", ""),
                    "arrival":      base.get("arrival", ""),
                    "duration":     base.get("duration", ""),
                    "classes":      base.get("classes", []),
                }
                if focused_date:
                    sel["journeyDate"] = focused_date
                early_updates["selected_train"] = sel

    return {
        "messages": [ai_msg],
        "pending_tool_calls": pending,
        "agent_loop_count": loop_count,
        **reset_fields,
        **early_updates,
    }
