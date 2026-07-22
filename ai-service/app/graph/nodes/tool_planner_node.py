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
- Check each tool's schema properties before creating args. Only include parameters defined in the schema.
- Use station codes (e.g. NDLS, BCT) not city names in tool args.
- If station codes are unknown, start with find_station_code.
- NEVER ask the user for data you can fetch via a tool. Auto-fetch:
  - saved passengers → get_saved_passengers (before book_ticket if no passengers in context)
  - boarding points → get_boarding_points (if user asks which stop to board)
  - station code → find_station_code
- For booking: if search_results already in context, skip search and go straight to check_availability → get_fare → book_ticket.
- For booking: search_trains → check_availability → get_fare → book_ticket.
- For live status: search_train_by_number → get_live_status.
- Never include book_ticket, cancel_ticket, update_boarding_point, delete_reminder without prior steps.
- Use cached context from TravelState — do not repeat already-completed steps.
- For recommend_trains, set preference to "fastest", "cheapest", or "overnight" based on user goal.
- For create_reminder and update_reminder, use param name "type" (values: JOURNEY, PNR, BOOKING).
- check_availability, get_fare, and get_live_status can run in parallel after search_trains.
- If user asks for route/schedule of multiple trains, plan one get_route call per train number.
- Default quota to "GN" if not specified by user.
- Always call create_tool_plan tool."""

# Intents where reflection adds value (data-heavy responses)
_REFLECT_INTENTS = {
    "search_trains", "recommend_trains", "check_availability",
    "get_fare", "book_ticket", "get_pnr", "get_booking_history",
}


async def tool_planner_node(
    state: TravelState,
    claude_service: ClaudeService,
    mcp_registry: MCPToolRegistry = None,
) -> Dict[str, Any]:
    available_tools = mcp_registry.get_schemas_for_claude() if mcp_registry else []

    # Add cache_control to the last tool in the list so Claude caches the entire
    # tool block (all tools up to and including the marked one are cached together).
    # The MCP tool list is static per-startup — ideal for caching.
    tools_for_claude = [_PLAN_TOOL]
    if available_tools:
        cached_tools = [dict(t) for t in available_tools]
        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}
        tools_for_claude = [_PLAN_TOOL] + cached_tools

    # Build a compact tools summary for the context message (names + descriptions only)
    tools_summary = json.dumps(
        [{"name": t["name"], "description": t.get("description", "")} for t in available_tools],
        indent=2,
    )
    full_context = build_planner_context(state, tools_summary)

    # Inject reflection feedback if this is a retry
    feedback = state.get("reflection_feedback") or ""
    if feedback:
        full_context += f"\n\nPrevious attempt feedback (fix this): {feedback}"

    response = await claude_service.chat_raw(
        messages=[{"role": "user", "content": full_context}],
        system=_SYSTEM,
        tools=tools_for_claude,
        tool_choice={"type": "tool", "name": "create_tool_plan"},
        temperature=0.0,
        max_tokens=2048,
        cache_system=True,
    )

    steps: List[Dict[str, Any]] = []
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            raw_steps = block.input.get("steps", [])
            # Guard against Claude returning steps as strings instead of dicts
            # (happens when output is truncated due to max_tokens)
            steps = [s for s in raw_steps if isinstance(s, dict) and "tool" in s]
            break

    tool_plan = [s["tool"] for s in steps]
    tool_plan_args = [s.get("args", {}) for s in steps]

    confirmation_required = any(get_precondition(t).requires_confirmation for t in tool_plan)

    # Enable reflection for data-heavy intents — hard-cap at 1 retry
    intent = state.get("intent") or ""
    reflection_retries = state.get("reflection_retries") or 0
    is_reflection_retry = bool(feedback)  # feedback set means we're on a retry pass
    reflection_required = intent in _REFLECT_INTENTS and reflection_retries < 1
    next_reflection_retries = (reflection_retries + 1) if is_reflection_retry else 0

    app_logger.info(
        "Tool plan created | steps={steps} | confirmation={conf} | reflection={ref}",
        steps=tool_plan, conf=confirmation_required, ref=reflection_required,
    )

    return {
        "tool_plan": tool_plan,
        "tool_plan_args": tool_plan_args,
        "current_tool_index": 0,
        "confirmation_required": confirmation_required,
        "reflection_required": reflection_required,
        "reflection_feedback": "",
        "reflection_retries": next_reflection_retries,
        "tool_history": [],
        "retries": 0,
        "errors": [],
    }
