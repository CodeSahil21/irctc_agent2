# memory/context_builder.py
"""
Context Builder

Assembles the Claude context from all three memory layers:
  Layer 1 — Working Memory  (current goal, tool state, results)
  Layer 2 — Conversation    (windowed messages — handled separately by nodes)
  Layer 3 — Preferences     (user preferences summary)

Instead of dumping 200 messages + all state as raw JSON,
we build a structured, token-efficient context block.

Used by: response_node, tool_planner_node
"""
import json
from typing import Any, Dict, Optional

from app.graph.state import TravelState
from app.memory.preference_memory import preferences_summary


def build_tool_context(state: TravelState) -> str:
    """
    Build the [Tool Results] block injected into the last user message
    for response_node. Only includes fields that have data.
    """
    parts = []

    if state.get("search_results"):
        parts.append(f"Search results:\n{json.dumps(state['search_results'], indent=2)}")
    if state.get("availability"):
        parts.append(f"Availability:\n{json.dumps(state['availability'], indent=2)}")
    if state.get("fare"):
        parts.append(f"Fare:\n{json.dumps(state['fare'], indent=2)}")
    if state.get("booking"):
        parts.append(f"Booking:\n{json.dumps(state['booking'], indent=2)}")
    if state.get("reminders"):
        parts.append(f"Reminders:\n{json.dumps(state['reminders'], indent=2)}")
    if state.get("saved_passengers"):
        parts.append(f"Saved passengers:\n{json.dumps(state['saved_passengers'], indent=2)}")
    if state.get("errors"):
        parts.append("Errors encountered:\n" + "\n".join(state["errors"]))
    if state.get("pending_question"):
        parts.append(f"Ask the user: {state['pending_question']}")
    if state.get("confirmed") is False:
        parts.append("User declined the action. Acknowledge and offer alternatives.")

    return "\n\n".join(parts) if parts else ""


def build_planner_context(state: TravelState, tools_summary: str) -> str:
    """
    Build the full context message for tool_planner_node.
    Includes: intent, goal, travel context, cached results, preferences, available tools.
    """
    travel = state.get("travel") or {}
    parts = [
        f"Intent: {state.get('intent')}",
        f"Goal: {state.get('user_goal')}",
    ]

    if travel:
        parts.append(f"Travel context: {json.dumps(travel)}")

    # Cached results — tell planner what's already done
    if state.get("search_results"):
        parts.append("Search results: already available in state")
    if state.get("selected_train"):
        parts.append(f"Selected train: {json.dumps(state['selected_train'])}")
    if state.get("availability"):
        parts.append("Availability: already checked")
    if state.get("fare"):
        parts.append("Fare: already fetched")
    if state.get("passengers"):
        parts.append(f"Passengers: {len(state['passengers'])} passenger(s) ready")

    # User preferences
    prefs = state.get("user_preferences") or {}
    pref_str = preferences_summary(prefs)
    if pref_str:
        parts.append(f"User preferences: {pref_str}")

    # Turn context
    if state.get("turn_count"):
        parts.append(f"Turn: {state['turn_count']}")

    parts.append(f"\nAvailable tools:\n{tools_summary}")

    return "\n".join(parts)
