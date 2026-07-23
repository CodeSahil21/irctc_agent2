# memory/context_builder.py
"""
Context builder helpers.

build_tool_context  — formats tool results into a human-readable block.
                      Used by tests and by any code that needs to summarise
                      the graph result for display/logging.

build_planner_context — REMOVED (tool_planner_node no longer exists).
                        A stub is provided so any lingering import doesn't
                        crash at startup.
"""
import json
from typing import Any, Dict

from app.graph.state import TravelState


def build_tool_context(state: TravelState) -> str:
    """
    Build a readable summary of tool results from the current graph state.
    Includes both top-level compat fields and persistent_results.
    Used for logging, debugging, and external context summaries.
    """
    parts = []

    # Top-level compat fields (written by tool_executor_node)
    if state.get("search_results"):
        parts.append(f"Search results:\n{json.dumps(state['search_results'], indent=2)}")
    if state.get("ranked_results"):
        parts.append(f"Ranked results:\n{json.dumps(state['ranked_results'], indent=2)}")
    if state.get("availability"):
        parts.append(f"Availability:\n{json.dumps(state['availability'], indent=2)}")
    if state.get("fare"):
        parts.append(f"Fare:\n{json.dumps(state['fare'], indent=2)}")
    if state.get("booking"):
        parts.append(f"Booking:\n{json.dumps(state['booking'], indent=2)}")

    # Persistent results (booking history, saved passengers)
    persistent = state.get("persistent_results") or {}
    if persistent.get("get_booking_history"):
        parts.append(
            f"Booking History:\n{json.dumps(persistent['get_booking_history'], indent=2)}"
        )
    if persistent.get("get_saved_passengers"):
        parts.append(
            f"Saved Passengers:\n{json.dumps(persistent['get_saved_passengers'], indent=2)}"
        )

    if state.get("errors"):
        parts.append("Errors encountered:\n" + "\n".join(state["errors"]))

    if state.get("confirmed") is False and state.get("confirmation_prompt"):
        parts.append("User declined the action. Acknowledge and offer alternatives.")

    return "\n\n".join(parts) if parts else ""


def build_planner_context(state: Any, tools_summary: str = "") -> str:  # noqa: ARG001
    """
    Stub — tool_planner_node has been removed.
    Returns an empty string so any stray call-site doesn't crash.
    """
    return ""
