# memory/working_memory.py
"""
Working memory helpers for the new agent-loop graph.

The old reset_turn_state / get_working_snapshot were tightly coupled to the
removed intent/slot/planner pipeline (tool_plan, current_tool_index,
missing_slots, parallel_results, etc.). Those fields no longer exist in
TravelState. This module retains only the utilities that are still valid:

  - get_working_snapshot  — compact summary of the current turn used for logging
  - reset_turn_state      — no longer used by any graph node; kept as a no-op
                            stub so imports in non-graph code don't break during
                            the transition period
"""
import time
from typing import Any, Dict

from app.graph.state import TravelState


def get_working_snapshot(state: TravelState) -> Dict[str, Any]:
    """
    Return a compact dict of the current working state.
    Used by context_builder / logging to summarise what the agent is doing.
    """
    tool_history = state.get("tool_history") or []
    completed = [h["tool"] for h in tool_history if h.get("status") == "success"]
    failed = [h["tool"] for h in tool_history if h.get("status") == "failed"]

    return {
        "agent_loop_count": state.get("agent_loop_count") or 0,
        "pending_tool_calls": len(state.get("pending_tool_calls") or []),
        "completed_tools": completed,
        "failed_tools": failed,
        "confirmation_pending": state.get("confirmation_required", False),
        "errors": state.get("errors") or [],
    }


def reset_turn_state(_state: TravelState) -> Dict[str, Any]:
    """
    Stub retained for import compatibility.

    In the new architecture agent_node resets turn-scoped fields directly
    (tool_history, errors) at the start of each new user turn when
    agent_loop_count == 0. There is no longer a separate reset step.
    """
    return {}
