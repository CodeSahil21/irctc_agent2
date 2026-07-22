# graph/nodes/human_approval_node.py
import json
from typing import Any, Dict

from langgraph.types import interrupt

from app.graph.state import TravelState
from app.telemetry.logging import app_logger


def _build_confirmation_prompt(state: TravelState) -> str:
    intent = state.get("intent", "")
    travel = state.get("travel") or {}
    fare = state.get("fare") or {}
    booking = state.get("booking") or {}

    # Prefer explicitly selected passengers, fall back to all saved
    passengers = travel.get("selected_passengers") or state.get("saved_passengers") or []

    lines = ["**Please confirm the following action:**\n"]

    if intent == "book_ticket":
        lines.append(f"- Train: {travel.get('train_number', '?')} — {travel.get('train_name', '')}")
        lines.append(f"- Route: {travel.get('from_station', '?')} → {travel.get('to_station', '?')}")
        lines.append(f"- Date: {travel.get('date', '?')}")
        lines.append(f"- Class: {travel.get('travel_class', '?')} | Quota: {travel.get('quota', '?')}")
        if fare:
            lines.append(f"- Total Fare: ₹{fare.get('amount', '?')}")
        if passengers:
            lines.append(f"- Passengers: {len(passengers)}")
            for p in passengers:
                lines.append(f"  • {p.get('name')} ({p.get('age')}, {p.get('gender')})")

    elif intent == "cancel_ticket":
        pnr = travel.get("pnr") or booking.get("pnr", "?")
        lines.append(f"- Cancel booking with PNR: **{pnr}**")
        lines.append("- This action cannot be undone.")

    elif intent == "update_boarding_point":
        lines.append(f"- Change boarding point for PNR: {travel.get('pnr', '?')}")

    elif intent == "delete_reminder":
        lines.append("- Delete the selected reminder.")

    else:
        lines.append(f"- Action: {intent}")

    lines.append("\nReply **yes** to proceed or **no** to cancel.")
    return "\n".join(lines)


def human_approval_node(state: TravelState) -> Dict[str, Any]:
    prompt = _build_confirmation_prompt(state)
    app_logger.info("Human approval required | intent={intent}", intent=state.get("intent"))

    # LangGraph interrupt — pauses graph execution and surfaces the prompt to the caller
    # Resume value can be a boolean (from client) or a string like "yes"/"no"
    user_response = interrupt({"confirmation_prompt": prompt})

    if isinstance(user_response, bool):
        confirmed = user_response
    else:
        confirmed = str(user_response).strip().lower() in ("yes", "y", "confirm", "ok", "proceed", "true")
    app_logger.info("Human approval response | confirmed={confirmed}", confirmed=confirmed)

    return {
        "confirmed": confirmed,
        "confirmation_prompt": prompt,
    }
