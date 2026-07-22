import time
from typing import Any, Dict

from app.graph.state import TravelState


def get_working_snapshot(state: TravelState) -> Dict[str, Any]:
    """
    Return a compact dict of the current working state.
    Used by context_builder to summarize what the agent is doing right now.
    """
    tool_plan = state.get("tool_plan") or []
    current_index = state.get("current_tool_index") or 0
    tool_history = state.get("tool_history") or []

    current_tool = tool_plan[current_index] if current_index < len(tool_plan) else None
    completed_tools = [t["tool"] for t in tool_history if t.get("status") == "success"]
    failed_tools = [t["tool"] for t in tool_history if t.get("status") in ("error", "failed")]

    return {
        "intent": state.get("intent"),
        "user_goal": state.get("user_goal"),
        "current_tool": current_tool,
        "tools_remaining": len(tool_plan) - current_index,
        "completed_tools": completed_tools,
        "failed_tools": failed_tools,
        "confirmation_pending": state.get("confirmation_required", False),
        "missing_slots": state.get("missing_slots") or [],
        "errors": state.get("errors") or [],
    }


def reset_turn_state(state: TravelState) -> Dict[str, Any]:
    """
    Returns the fields that should be reset at the start of each new user turn.
    Called by intent_node to clear stale planning state.

    Continuity rules:
    - travel context (from_station, to_station, date, train_number, pnr) always persists
      via the checkpointer — NOT reset here.
    - search_results, availability, fare persist only when the new intent is a
      continuation of the current search/booking flow. They are cleared when the
      user starts a new search (new stations or date detected by intent_node) so
      the planner doesn't reuse stale results for a different journey.
    - tool_results (generic bucket) is always cleared — it's turn-scoped data
      (route, live_status, platform etc.) that is not reusable across turns.
    - booking and reminders are cleared — they are surfaced per-turn in response_node.
    - saved_passengers intentionally persists — fetched once per session, reused for booking.
    """
    # Intents that are continuations of a search — keep search_results/fare/availability
    _CONTINUATION_INTENTS = {
        "check_availability", "get_fare", "book_ticket",
        "get_seat_map", "get_boarding_points", "get_route",
        "get_train_schedule", "get_live_status", "get_platform",
    }
    current_intent = state.get("intent") or ""
    is_continuation = current_intent in _CONTINUATION_INTENTS

    resets: Dict[str, Any] = {
        "tool_plan": None,
        "tool_plan_args": None,
        "current_tool_index": None,
        "confirmation_required": None,
        "confirmed": None,
        "missing_slots": None,
        "pending_question": None,
        "errors": [],
        "retries": 0,
        "parallel_results": {},
        "tool_results": {},           # always cleared — turn-scoped
        "reflection_required": None,
        "reflection_passed": None,
        "reflection_feedback": "",
        "booking": None,              # cleared — surfaced fresh each turn
        "reminders": None,            # cleared — fetched fresh when needed
        "execution_metrics": {
            "turn_start_time": time.time(),
            "tools_called": 0,
            "total_latency_ms": 0.0,
            "claude_calls": 0,
        },
        "turn_count": (state.get("turn_count") or 0) + 1,
    }

    if not is_continuation:
        # New search or unrelated intent — clear stale search pipeline results
        # so the planner doesn't reuse them for a different journey
        resets["search_results"] = None
        resets["ranked_results"] = None
        resets["availability"] = None
        resets["fare"] = None
    else:
        # Continuation — only clear ranked_results (re-ranked each time)
        resets["ranked_results"] = None

    return resets


def increment_tool_metric(state: TravelState, latency_ms: float) -> dict:
    """Return updated execution metrics after a tool call."""
    m = dict(state.get("execution_metrics") or {})
    m["tools_called"] = (m.get("tools_called") or 0) + 1
    m["total_latency_ms"] = (m.get("total_latency_ms") or 0.0) + latency_ms
    return m
