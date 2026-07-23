import json

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

    tool_results = state.get("tool_results") or {}
    for tool_name, result in tool_results.items():
        label = tool_name.replace("_", " ").title()
        if tool_name == "get_booking_history":
            parts.append(f"Booking History:\n{json.dumps(result, indent=2)}")
        elif tool_name == "get_saved_passengers":
            # already shown above via saved_passengers if set, avoid duplicate
            if not state.get("saved_passengers"):
                parts.append(f"Saved Passengers:\n{json.dumps(result, indent=2)}")
        else:
            parts.append(f"{label}:\n{json.dumps(result, indent=2)}")

    if state.get("errors"):
        parts.append("Errors encountered:\n" + "\n".join(state["errors"]))
    if state.get("pending_question"):
        parts.append(f"Ask the user: {state['pending_question']}")
    if state.get("confirmed") is False and state.get("confirmation_prompt"):
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
    if travel.get("date_range"):
        parts.append(
            f"FLEXIBLE DATE SEARCH — search across these dates and merge results: {travel['date_range']}\n"
            f"Plan one search_trains call per date. Pick the best results across all dates for the user."
        )

    # ── Cross-turn persistent data ─────────────────────────────────────────
    # These were fetched in earlier turns and carried forward — use them to
    # resolve args without asking the user again.
    tool_results = state.get("tool_results") or {}

    booking_history = tool_results.get("get_booking_history")
    if booking_history:
        parts.append(
            f"Booking history (fetched earlier — extract trainNumber/pnr/source/date from here):\n"
            f"{json.dumps(booking_history, indent=2)}"
        )

    saved_passengers = state.get("saved_passengers") or tool_results.get("get_saved_passengers")
    if saved_passengers:
        parts.append(f"Saved passengers (fetched earlier): {json.dumps(saved_passengers)}")

    persisted_reminders = tool_results.get("get_reminders")
    if persisted_reminders and not state.get("reminders"):
        parts.append(f"Reminders (fetched earlier — use IDs for update/delete):\n{json.dumps(persisted_reminders, indent=2)}")

    # ── Current-turn results ───────────────────────────────────────────────
    results = state.get("search_results") or state.get("ranked_results")
    if results:
        parts.append(f"Search results (already fetched):\n{json.dumps(results, indent=2)}")
    if state.get("selected_train"):
        parts.append(f"Selected train: {json.dumps(state['selected_train'])}")
    if state.get("availability"):
        parts.append(f"Availability (already checked): {json.dumps(state['availability'])}")
    if state.get("fare"):
        parts.append(f"Fare (already fetched): {json.dumps(state['fare'])}")
    if travel.get("pnr"):
        parts.append(f"PNR in context: {travel['pnr']} (use for pnr/booking tools)")
    if state.get("booking"):
        parts.append(f"Booking (already fetched): {json.dumps(state['booking'])}")
    if state.get("reminders"):
        parts.append(f"Reminders (with IDs):\n{json.dumps(state['reminders'], indent=2)}")
    if state.get("passengers"):
        parts.append(f"Passengers: {len(state['passengers'])} passenger(s) ready")
    if travel.get("selected_passengers"):
        parts.append(f"Selected passengers for booking: {json.dumps(travel['selected_passengers'])}")
    if travel.get("save_new_passenger") is True:
        parts.append("save_new_passenger=True — call add_saved_passenger BEFORE book_ticket with these passenger details")
    elif travel.get("save_new_passenger") is False:
        parts.append("save_new_passenger=False — do NOT call add_saved_passenger, book directly")

    # Other tool results this turn (route, live_status, etc.)
    other_results = {
        k: v for k, v in tool_results.items()
        if k not in ("get_booking_history", "get_saved_passengers", "get_reminders")
    }
    if other_results:
        done = ", ".join(other_results.keys())
        parts.append(f"Already executed this turn (results cached): {done}")

    # User preferences
    prefs = state.get("user_preferences") or {}
    pref_str = preferences_summary(prefs)
    if pref_str:
        parts.append(f"User preferences: {pref_str}")

    if state.get("turn_count"):
        parts.append(f"Turn: {state['turn_count']}")

    parts.append(f"\nAvailable tools:\n{tools_summary}")

    return "\n".join(parts)
