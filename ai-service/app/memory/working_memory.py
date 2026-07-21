# memory/working_memory.py
"""
Layer 1 — Working Memory

Lives entirely inside TravelState for the duration of one agent execution.
Destroyed (or checkpointed) when the graph reaches END.

Responsibilities:
- Extract the current execution snapshot for context building
- Reset per-turn planning fields at the start of each new turn
- Track execution metrics
"""
import time
from typing import Any, Dict, Optional

from app.graph.state import ExecutionMetrics, TravelState


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
    """
    return {
        "tool_plan": None,
        "tool_plan_args": None,
        "current_tool_index": None,
        "confirmation_required": None,
        "confirmed": None,
        "missing_slots": None,
        "pending_question": None,
        "errors": [],
        "retries": 0,
        "execution_metrics": ExecutionMetrics(
            turn_start_time=time.time(),
            tools_called=0,
            total_latency_ms=0.0,
            claude_calls=0,
        ),
        "turn_count": (state.get("turn_count") or 0) + 1,
    }


def increment_tool_metric(state: TravelState, latency_ms: float) -> ExecutionMetrics:
    """Return updated execution metrics after a tool call."""
    m = dict(state.get("execution_metrics") or {})
    m["tools_called"] = (m.get("tools_called") or 0) + 1
    m["total_latency_ms"] = (m.get("total_latency_ms") or 0.0) + latency_ms
    return ExecutionMetrics(**m)
