import time
from typing import Any, Dict


def build_complete_message(
    msg_id: str,
    content: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the payload for message:complete that matches the frontend ChatMessage type.
    Attaches structured data (train list, pnr) as an attachment.
    """
    return {
        "id": msg_id,
        "role": "agent",
        "content": content,
        "status": "sent",
        "createdAt": int(time.time() * 1000),
        "attachment": _build_attachment(result),
        "intent": result.get("intent"),
        "travelContext": result.get("travel"),
        "errors": result.get("errors") or [],
    }


def _build_attachment(result: Dict[str, Any]) -> Dict[str, Any]:
    # If a booking was made, show the PNR card
    booking = result.get("booking")
    if booking and isinstance(booking, dict):
        pnr = booking.get("pnr") or booking.get("PNR") or ""
        if pnr:
            return {
                "type": "pnr_status",
                "pnr": pnr,
                "status": booking.get("status", ""),
                "chart": booking.get("chartStatus", ""),
            }

    # If a single train is selected/focused, show only that one
    selected = result.get("selected_train")
    if selected and isinstance(selected, dict):
        return {
            "type": "train_list",
            "trains": [_normalize_train(selected)],
        }

    trains = result.get("ranked_results") or result.get("search_results")
    if trains:
        # If the conversation has narrowed to a specific train number (via
        # travel_context or a single-match search), filter the list down to
        # just that train so the UI doesn't keep showing all results.
        focused_number = None
        tc = result.get("travel_context") or result.get("travel") or {}
        if isinstance(tc, dict):
            focused_number = tc.get("trainNumber") or tc.get("train_number")

        if focused_number:
            focused = [t for t in trains if str(t.get("trainNumber", "")) == str(focused_number)]
            if focused:
                return {
                    "type": "train_list",
                    "trains": [_normalize_train(focused[0])],
                }

        # Fall back to full list (initial search response)
        return {
            "type": "train_list",
            "trains": [_normalize_train(t) for t in trains],
        }

    return {"type": "none"}


def _normalize_train(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "number": t.get("trainNumber") or t.get("number", ""),
        "name": t.get("trainName") or t.get("name", ""),
        "from": t.get("fromStation") or t.get("from", ""),
        "to": t.get("toStation") or t.get("to", ""),
        "departure": t.get("departureTime") or t.get("departure", ""),
        "arrival": t.get("arrivalTime") or t.get("arrival", ""),
        "duration": t.get("duration", ""),
        "classes": t.get("classes") or t.get("availableClasses") or [],
    }
