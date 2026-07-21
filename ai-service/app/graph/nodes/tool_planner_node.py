# graph/nodes/tool_planner_node.py
import json
from typing import Any, Dict, List

from app.graph.state import TravelState
from app.graph.tool_preconditions import get_precondition
from app.mcp.registry import MCPToolRegistry
from app.memory.context_builder import build_planner_context
from app.services.claude import ClaudeService
from app.telemetry.logging import app_logger

_PLAN_TOOL = {
    "name": "create_tool_plan",
    "description": "Create an ordered execution plan of MCP tools to fulfill the user's intent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "description": "Ordered list of tool calls to execute.",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Tool name from the registry."},
                        "args": {"type": "object", "description": "Arguments for this tool call."},
                    },
                    "required": ["tool", "args"],
                },
            },
        },
        "required": ["steps"],
    },
}

_SYSTEM = """You are an IRCTC travel agent planner. Given the user's intent and current travel context, 
produce an ordered list of tool calls needed to fulfill the request.

Rules:
- Use station codes (e.g. NDLS, BCT) not city names in tool args.
- If station codes are unknown, start with find_station_code.
- For booking: search_trains → check_availability → get_fare → book_ticket.
- For live status: search_train_by_number → get_live_status.
- Never include book_ticket, cancel_ticket, update_boarding_point, delete_reminder without prior steps.
- Use cached context from TravelState — do not repeat already-completed steps.
- For recommend_trains, set preference to "fastest", "cheapest", or "overnight" based on user goal.
- For create_reminder and update_reminder, use param name "type" (values: JOURNEY, PNR, BOOKING).
- Always call create_tool_plan tool."""


def _build_context_summary(state: TravelState) -> str:
    travel = state.get("travel") or {}
    parts = [f"Intent: {state.get('intent')}", f"Goal: {state.get('user_goal')}"]
    if travel:
        parts.append(f"Travel context: {json.dumps(travel)}")
    if state.get("search_results"):
        parts.append("Search results: already available in state")
    if state.get("selected_train"):
        parts.append(f"Selected train: {json.dumps(state['selected_train'])}")
    if state.get("availability"):
        parts.append("Availability: already checked")
    if state.get("fare"):
        parts.append("Fare: already fetched")
    if state.get("passengers"):
        parts.append(f"Passengers: {len(state['passengers'])} passenger(s) ready")
    return "\n".join(parts)


async def tool_planner_node(
    state: TravelState,
    claude_service: ClaudeService,
    mcp_registry: MCPToolRegistry = None,
) -> Dict[str, Any]:
    available_tools = mcp_registry.get_schemas_for_claude() if mcp_registry else []
    tools_summary = json.dumps(
        [{"name": t["name"], "description": t.get("description", "")} for t in available_tools],
        indent=2,
    )
    # Use context_builder for token-efficient planner context
    full_context = build_planner_context(state, tools_summary)

    response = await claude_service.chat_raw(
        messages=[{"role": "user", "content": full_context}],
        system=_SYSTEM,
        tools=[_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "create_tool_plan"},
        temperature=0.0,
        max_tokens=1024,
    )

    steps: List[Dict[str, Any]] = []
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            steps = block.input.get("steps", [])
            break

    tool_plan = [s["tool"] for s in steps]
    tool_plan_args = [s.get("args", {}) for s in steps]

    # Check if any planned tool requires confirmation
    confirmation_required = any(
        get_precondition(t).requires_confirmation for t in tool_plan
    )

    app_logger.info(
        "Tool plan created | steps={steps} | confirmation_required={conf}",
        steps=tool_plan,
        conf=confirmation_required,
    )

    return {
        "tool_plan": tool_plan,
        "tool_plan_args": tool_plan_args,
        "current_tool_index": 0,
        "confirmation_required": confirmation_required,
        "tool_history": [],
        "retries": 0,
        "errors": [],
    }
