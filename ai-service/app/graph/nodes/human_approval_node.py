# graph/nodes/human_approval_node.py
from typing import Any, Dict

from langgraph.types import interrupt

from app.graph.state import TravelState
from app.telemetry.logging import app_logger


def _build_confirmation_prompt(state: TravelState) -> str:
    """
    Build a natural conversational confirmation message — not a form.
    The agent asks as a human travel agent would, summarising what it's about to do
    and asking for a simple yes/no.
    """
    intent = state.get("intent", "")
    travel = state.get("travel") or {}
    fare = state.get("fare") or {}
    booking = state.get("booking") or {}
    passengers = travel.get("selected_passengers") or []

    if intent == "book_ticket":
        train = f"{travel.get('train_number', '?')} {travel.get('train_name', '')}".strip()
        route = f"{travel.get('from_station', '?')} → {travel.get('to_station', '?')}"
        date = travel.get("date", "?")
        cls = travel.get("travel_class", "?")
        quota = travel.get("quota", "GN")
        fare_str = f"₹{fare.get('amount', '?')}" if fare else "fare TBD"

        pax_str = ""
        if passengers:
            names = ", ".join(p.get("name", "?") for p in passengers)
            pax_str = f" for {names}"

        return (
            f"Just to confirm — I'll book **{train}** on **{date}** "
            f"({route}), **{cls}** class, {quota} quota, {fare_str}{pax_str}. "
            f"Shall I go ahead? (yes / no)"
        )

    if intent == "cancel_ticket":
        pnr = travel.get("pnr") or booking.get("pnr", "?")
        return (
            f"Are you sure you want to cancel the booking with PNR **{pnr}**? "
            f"This cannot be undone. (yes / no)"
        )

    if intent == "update_boarding_point":
        pnr = travel.get("pnr", "?")
        return (
            f"I'll update the boarding point for PNR **{pnr}**. "
            f"Shall I proceed? (yes / no)"
        )

    if intent == "delete_reminder":
        return "I'll delete that reminder. Are you sure? (yes / no)"

    if intent == "update_booking_status":
        return "I'll update the booking status. Shall I proceed? (yes / no)"

    return f"I'm about to perform: **{intent.replace('_', ' ')}**. Shall I proceed? (yes / no)"


def human_approval_node(state: TravelState) -> Dict[str, Any]:
    prompt = _build_confirmation_prompt(state)
    app_logger.info("Human approval required | intent={intent}", intent=state.get("intent"))

    # LangGraph interrupt — pauses graph, surfaces prompt to caller.
    # Resume value: bool (from socket client) or "yes"/"no" string (from HTTP client).
    user_response = interrupt({"confirmation_prompt": prompt})

    if isinstance(user_response, bool):
        confirmed = user_response
    else:
        confirmed = str(user_response).strip().lower() in ("yes", "y", "confirm", "ok", "proceed", "true", "sure", "go ahead", "yep", "yeah")

    app_logger.info("Human approval response | confirmed={confirmed}", confirmed=confirmed)

    return {
        "confirmed": confirmed,
        "confirmation_prompt": prompt,
    }
