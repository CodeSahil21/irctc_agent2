# graph/edges.py
from app.graph.state import TravelState

# Intents that need no tools — answered directly from static knowledge or simple lookup
_NO_TOOL_INTENTS = {"general_question", "list_classes", "list_quotas"}

# Intents that produce ranked search results
_RANKING_INTENTS = {"search_trains", "recommend_trains"}


def route_after_intent(state: TravelState) -> str:
    intent = state.get("intent", "general_question")
    if intent in _NO_TOOL_INTENTS:
        return "response_node"
    return "slot_filler_node"


def route_after_slot_filler(state: TravelState) -> str:
    missing = state.get("missing_slots") or []
    if missing:
        return "response_node"
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
    return "response_node"


def route_after_tool_executor(state: TravelState) -> str:
    tool_plan = state.get("tool_plan") or []
    current_index = state.get("current_tool_index") or 0
    retries = state.get("retries") or 0

    if retries > 0 and current_index < len(tool_plan):
        return "tool_executor_node"
    if current_index < len(tool_plan):
        return "tool_executor_node"

    # All tools done — rank if applicable, else reflect or respond
    intent = state.get("intent") or ""
    if intent in _RANKING_INTENTS and state.get("search_results"):
        return "ranking_node"
    if state.get("reflection_required"):
        return "reflection_node"
    return "response_node"


def route_after_ranking(state: TravelState) -> str:
    if state.get("reflection_required"):
        return "reflection_node"
    return "response_node"


def route_after_reflection(state: TravelState) -> str:
    if state.get("reflection_passed"):
        return "response_node"
    # Reflection failed — re-plan with feedback
    return "tool_planner_node"
