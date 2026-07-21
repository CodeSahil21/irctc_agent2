# graph/edges.py
from app.graph.state import TravelState

# Intents that need no tools — answered directly from static knowledge or simple lookup
_NO_TOOL_INTENTS = {"general_question", "list_classes", "list_quotas"}


def route_after_intent(state: TravelState) -> str:
    intent = state.get("intent", "general_question")
    if intent in _NO_TOOL_INTENTS:
        return "response_node"
    return "slot_filler_node"


def route_after_slot_filler(state: TravelState) -> str:
    missing = state.get("missing_slots") or []
    if missing:
        return "response_node"  # Ask the user for the missing slot
    return "tool_planner_node"


def route_after_tool_planner(state: TravelState) -> str:
    tool_plan = state.get("tool_plan") or []
    if not tool_plan:
        return "response_node"
    if state.get("confirmation_required"):
        return "human_approval_node"
    return "tool_executor_node"


def route_after_human_approval(state: TravelState) -> str:
    if state.get("confirmed"):
        return "tool_executor_node"
    return "response_node"  # User declined — explain and offer alternatives


def route_after_tool_executor(state: TravelState) -> str:
    tool_plan = state.get("tool_plan") or []
    current_index = state.get("current_tool_index") or 0
    retries = state.get("retries") or 0

    # Still have retries pending for the current tool
    if retries > 0 and current_index < len(tool_plan):
        return "tool_executor_node"

    # More tools in the plan
    if current_index < len(tool_plan):
        return "tool_executor_node"

    # All tools done
    return "response_node"
