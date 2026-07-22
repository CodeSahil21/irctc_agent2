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
    trains = result.get("ranked_results") or result.get("search_results")
    if trains:
        return {
            "type": "train_list",
            "trains": [_normalize_train(t) for t in trains],
        }

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
