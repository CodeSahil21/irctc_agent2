# graph/nodes/slot_filler_node.py
from typing import Any, Dict, List

from app.graph.state import TravelState
from app.graph.tool_preconditions import SLOT_QUESTIONS, get_precondition
from app.telemetry.logging import app_logger

# Intent → primary tool whose slots we validate
_INTENT_TO_TOOL: Dict[str, str] = {
    "search_trains": "search_trains",
    "recommend_trains": "recommend_trains",
    "check_availability": "check_availability",
    "get_fare": "get_fare",
    "get_route": "get_route",
    "get_train_schedule": "get_train_schedule",
    "get_live_status": "get_live_status",
    "get_platform": "get_platform",
    "get_seat_map": "get_seat_map",
    "get_boarding_points": "get_boarding_points",
    "search_train_by_number": "search_train_by_number",
    "book_ticket": "book_ticket",
    "cancel_ticket": "cancel_ticket",
}


def slot_filler_node(state: TravelState) -> Dict[str, Any]:
    intent = state.get("intent", "general_question")
    travel = dict(state.get("travel") or {})

    primary_tool = _INTENT_TO_TOOL.get(intent)
    if not primary_tool:
        # No slot validation needed for this intent
        return {"missing_slots": [], "pending_question": None}

    precondition = get_precondition(primary_tool)
    missing: List[str] = []

    for slot in precondition.required_slots:
        if not travel.get(slot):
            missing.append(slot)

    if missing:
        # Ask only the first missing slot
        question = SLOT_QUESTIONS.get(missing[0], f"Could you provide your {missing[0]}?")
        app_logger.info(
            "Slot filling required | intent={intent} | missing={missing}",
            intent=intent,
            missing=missing,
        )
        return {"missing_slots": missing, "pending_question": question}

    return {"missing_slots": [], "pending_question": None}
