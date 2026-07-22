# graph/arg_patcher.py
"""
Deterministic tool-argument resolution.

Tool plans (and their arguments) are produced by Claude at *plan time*, before
any tool has run. For deterministic chains — e.g. search_trains → check_availability
→ get_fare → book_ticket — the arguments of later tools depend on the *results* of
earlier ones (the train number comes from the search result, the fare from get_fare,
etc.). Rather than trusting the planner to have guessed those, we re-resolve each
tool's arguments from live graph state immediately before execution.

Rules:
  * We only ever FILL BLANKS. Any value the planner (or the user, via a specific
    request like "check availability on 12951") already set is preserved.
  * Argument keys use the MCP server's camelCase schema names; travel context uses
    snake_case internally, so this layer bridges the two.
  * Unknown / unhandled tools are returned unchanged.
"""
from typing import Any, Dict, List

_DEFAULT_QUOTA = "GN"


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _top_train(state: Dict[str, Any]) -> Dict[str, Any]:
    results = state.get("search_results") or []
    return results[0] if results else {}


def patch_tool_args(
    tool_name: str,
    tool_args: Dict[str, Any],
    state: Dict[str, Any],
    travel: Dict[str, Any],
) -> Dict[str, Any]:
    """Return a copy of tool_args with blanks filled from live state/travel."""
    args = dict(tool_args or {})
    top = _top_train(state)

    def fill(key: str, value: Any) -> None:
        if not _is_empty(value) and _is_empty(args.get(key)):
            args[key] = value

    train_number = travel.get("train_number") or top.get("trainNumber")

    if tool_name in ("search_trains", "recommend_trains"):
        fill("fromStation", travel.get("from_station"))
        fill("toStation", travel.get("to_station"))
        fill("journeyDate", travel.get("date"))
        fill("quota", travel.get("quota") or _DEFAULT_QUOTA)
        if tool_name == "recommend_trains":
            fill("travelClass", travel.get("travel_class"))

    elif tool_name == "check_availability":
        fill("trainNumber", train_number)
        fill("travelClass", travel.get("travel_class"))
        fill("quota", travel.get("quota") or _DEFAULT_QUOTA)
        fill("journeyDate", travel.get("date"))

    elif tool_name == "get_fare":
        fill("trainNumber", train_number)
        fill("travelClass", travel.get("travel_class"))
        fill("quota", travel.get("quota") or _DEFAULT_QUOTA)
        fill("fromStation", travel.get("from_station"))
        fill("toStation", travel.get("to_station"))

    elif tool_name == "get_live_status":
        fill("trainNumber", train_number)
        fill("date", travel.get("date"))

    elif tool_name == "get_seat_map":
        fill("trainNumber", train_number)
        fill("travelClass", travel.get("travel_class"))
        fill("journeyDate", travel.get("date"))

    elif tool_name == "get_boarding_points":
        fill("trainNumber", train_number)
        fill("fromStation", travel.get("from_station"))
        fill("journeyDate", travel.get("date"))

    elif tool_name in ("get_route", "get_train_schedule", "search_train_by_number"):
        fill("trainNumber", train_number)

    elif tool_name == "get_platform":
        fill("trainNumber", train_number)
        fill("stationCode", travel.get("from_station"))

    elif tool_name == "book_ticket":
        fill("trainNumber", train_number)
        fill("trainName", travel.get("train_name") or top.get("trainName"))
        fill("source", travel.get("from_station"))
        fill("destination", travel.get("to_station"))
        fill("journeyDate", travel.get("date"))
        fill("travelClass", travel.get("travel_class"))
        fill("quota", travel.get("quota") or _DEFAULT_QUOTA)
        fare_data = state.get("fare") or {}
        if isinstance(fare_data, dict) and fare_data.get("amount") is not None:
            fill("fare", fare_data["amount"])
        resolved_passengers = _resolve_passengers(args.get("passengers"), state, travel)
        if resolved_passengers:
            args["passengers"] = resolved_passengers
        else:
            # Leave the key absent so the registry rejects book_ticket as missing a
            # required field rather than calling it with an empty passenger list.
            args.pop("passengers", None)

    elif tool_name in ("cancel_ticket", "get_pnr", "get_booking"):
        fill("pnr", travel.get("pnr"))

    elif tool_name == "update_boarding_point":
        fill("pnr", travel.get("pnr"))

    elif tool_name == "update_booking_status":
        fill("pnr", travel.get("pnr"))

    elif tool_name == "create_reminder":
        booking = state.get("booking") or {}
        if isinstance(booking, dict):
            fill("bookingId", booking.get("id") or booking.get("bookingId"))

    elif tool_name in ("update_reminder", "delete_reminder"):
        reminders = state.get("reminders") or []
        # Only auto-fill when there is exactly one candidate — otherwise leave
        # blank so the tool errors and the agent asks the user which reminder.
        if len(reminders) == 1 and isinstance(reminders[0], dict):
            fill("reminderId", reminders[0].get("id") or reminders[0].get("reminderId"))

    return args


def _resolve_passengers(
    passengers: Any,
    state: Dict[str, Any],
    travel: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Resolve the booking passenger list from live state.

    We NEVER fabricate a placeholder passenger — booking with a made-up traveller
    is worse than failing. If none can be resolved we return an empty list, which
    the MCP registry rejects as a missing required field, and the agent asks the
    user to provide/select passengers.
    """
    if isinstance(passengers, list) and passengers:
        return passengers

    selected = travel.get("selected_passengers") or state.get("saved_passengers") or []
    resolved: List[Dict[str, Any]] = []
    for p in selected:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        entry = {
            "name": p.get("name"),
            "age": p.get("age"),
            "gender": p.get("gender"),
        }
        if p.get("berthPreference"):
            entry["berthPreference"] = p["berthPreference"]
        resolved.append(entry)
    return resolved
