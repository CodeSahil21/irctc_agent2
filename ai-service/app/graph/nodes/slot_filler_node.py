"""
Schema-driven slot filler.

Once an intent is classified we look up the primary MCP tool's *live* input schema
(discovered from the server, not hardcoded) and check whether every required
parameter can be satisfied. The philosophy is "auto-resolve first, ask only what's
truly missing":

  1. A required field is SATISFIED when its value already exists in travel context,
     OR it has a safe default (quota → GN), OR it will be produced by another step
     (e.g. a train number resolvable from an upcoming search), OR it is an internal
     field the planner/executor fills (passengers, reminderAt, ...).
  2. Only genuinely user-provided journey fields that cannot be resolved are asked
     for — one question per turn, phrased from the schema where possible.

This keeps the agent from nagging while guaranteeing tools are never called with
missing required parameters. Falls back to the static preconditions when the MCP
schema is unavailable (e.g. discovery not yet run in a unit test).
"""
import re
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState
from app.graph.tool_preconditions import SLOT_QUESTIONS, TOOL_PRECONDITIONS, get_precondition
from app.telemetry.logging import app_logger

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# MCP camelCase required field → internal travel-context slot
_FIELD_TO_SLOT: Dict[str, str] = {
    "fromStation": "from_station",
    "toStation": "to_station",
    "source": "from_station",
    "destination": "to_station",
    "stationCode": "from_station",
    "journeyDate": "date",
    "date": "date",
    "trainNumber": "train_number",
    "trainName": "train_name",
    "travelClass": "travel_class",
    "quota": "quota",
    "pnr": "pnr",
}

# Slots we may ask the user about. Everything else is auto-resolved or planner-filled.
_ASKABLE_SLOTS = {"from_station", "to_station", "date", "travel_class", "train_number", "pnr"}


def _slot_filled(slot: str, value: Any) -> bool:
    """Return True only if the slot value is genuinely usable."""
    if not value:
        return False
    if slot == "date":
        # Must be a proper ISO date — reject vague strings like "this week"
        return bool(_ISO_DATE_RE.match(str(value)))
    return True


def _is_satisfied(field: str, slot: str, travel: Dict[str, Any], state: TravelState) -> bool:
    """Whether a required schema field can be satisfied without asking the user."""
    if _slot_filled(slot, travel.get(slot)):
        return True
    if field == "quota":
        return True  # safe default (GN) applied by arg_patcher
    if slot == "train_number":
        # Resolvable if we already have a train, prior search results, or enough
        # to run a search first (from + to + date).
        if travel.get("train_number") or state.get("search_results"):
            return True
        if (
            travel.get("from_station")
            and travel.get("to_station")
            and _slot_filled("date", travel.get("date"))
        ):
            return True
        return False
    return False


def _question_for(slot: str, field: str, properties: Dict[str, Any]) -> str:
    if slot in SLOT_QUESTIONS:
        return SLOT_QUESTIONS[slot]
    desc = (properties.get(field) or {}).get("description")
    if desc:
        return f"Could you provide the {field}? ({desc})"
    return f"Could you provide your {slot.replace('_', ' ')}?"


def _schema_missing_slots(
    tool_name: str,
    schema: Dict[str, Any],
    travel: Dict[str, Any],
    state: TravelState,
) -> tuple[List[str], Optional[str]]:
    """Return (missing_slots, question) derived from the live MCP schema."""
    input_schema = schema.get("input_schema", {}) or {}
    required = input_schema.get("required", []) or []
    properties = input_schema.get("properties", {}) or {}

    missing: List[str] = []
    question: Optional[str] = None
    for field in required:
        slot = _FIELD_TO_SLOT.get(field)
        if slot is None or slot not in _ASKABLE_SLOTS:
            continue  # internal/planner-filled field — not a user question
        if _is_satisfied(field, slot, travel, state):
            continue
        if slot not in missing:
            missing.append(slot)
            if question is None:
                question = _question_for(slot, field, properties)
    return missing, question


def _static_missing_slots(tool_name: str, travel: Dict[str, Any]) -> tuple[List[str], Optional[str]]:
    """Fallback when the MCP schema is unavailable — uses static preconditions."""
    precondition = get_precondition(tool_name)
    missing = [s for s in precondition.required_slots if not _slot_filled(s, travel.get(s))]
    question = SLOT_QUESTIONS.get(missing[0], f"Could you provide your {missing[0]}?") if missing else None
    return missing, question


def slot_filler_node(state: TravelState, mcp_registry=None) -> Dict[str, Any]:
    intent = state.get("intent", "general_question")
    travel = dict(state.get("travel") or {})

    # Intent names map 1:1 to MCP tool names. Non-tool intents (general_question)
    # have no required user slots.
    tool_name = intent
    schema = None
    if mcp_registry is not None and mcp_registry.is_known(tool_name):
        schema = mcp_registry.get_tool_schema(tool_name)
    elif tool_name not in TOOL_PRECONDITIONS:
        return {"missing_slots": [], "pending_question": None}

    if schema:
        missing, question = _schema_missing_slots(tool_name, schema, travel, state)
    else:
        missing, question = _static_missing_slots(tool_name, travel)

    if missing:
        app_logger.info(
            "Slot filling required | intent={intent} | missing={missing}",
            intent=intent,
            missing=missing,
        )
        return {"missing_slots": missing, "pending_question": question}

    return {"missing_slots": [], "pending_question": None}
