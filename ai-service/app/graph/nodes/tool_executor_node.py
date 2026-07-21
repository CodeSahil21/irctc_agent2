# graph/nodes/tool_executor_node.py
import json
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState, ToolCall
from app.graph.tool_preconditions import get_precondition
from app.mcp.registry import MCPToolRegistry
from app.telemetry.logging import app_logger


def _merge_travel_context(travel: Dict[str, Any], tool: str, result_data: Any) -> Dict[str, Any]:
    updated = dict(travel)
    if tool in ("search_trains", "recommend_trains") and isinstance(result_data, dict):
        trains = result_data.get("trains", [])
        if trains:
            updated["train_number"] = trains[0].get("trainNumber", updated.get("train_number"))
            updated["train_name"] = trains[0].get("trainName", updated.get("train_name"))
    elif tool == "find_station_code" and isinstance(result_data, dict):
        code = result_data.get("code")
        if code:
            if not updated.get("from_station") or len(updated.get("from_station", "")) > 5:
                updated["from_station"] = code
            elif not updated.get("to_station") or len(updated.get("to_station", "")) > 5:
                updated["to_station"] = code
    return updated


async def tool_executor_node(state: TravelState, mcp_registry: MCPToolRegistry) -> Dict[str, Any]:
    tool_plan: List[str] = state.get("tool_plan") or []
    tool_plan_args: List[Dict[str, Any]] = state.get("tool_plan_args") or []
    current_index: int = state.get("current_tool_index") or 0
    tool_history: List[ToolCall] = list(state.get("tool_history") or [])
    retries: int = state.get("retries") or 0
    errors: List[str] = list(state.get("errors") or [])
    travel: Dict[str, Any] = dict(state.get("travel") or {})

    user_email: str = state.get("user_email") or "anonymous@irctc-agent.internal"
    user_name: Optional[str] = state.get("user_name")

    if current_index >= len(tool_plan):
        return {"current_tool_index": current_index}

    tool_name = tool_plan[current_index]
    tool_args = tool_plan_args[current_index] if current_index < len(tool_plan_args) else {}
    precondition = get_precondition(tool_name)

    app_logger.info(
        "Executing tool | tool={tool} | index={idx}/{total}",
        tool=tool_name,
        idx=current_index + 1,
        total=len(tool_plan),
    )

    raw_result = await mcp_registry.execute(
        tool_name=tool_name,
        arguments=tool_args,
        user_email=user_email,
        user_name=user_name,
    )
    parsed = json.loads(raw_result)
    status = parsed.get("status", "error")
    result_data = parsed.get("data")
    error_msg = parsed.get("message")

    if status == "error":
        errors.append(f"{tool_name}: {error_msg}")
        if retries < precondition.max_retries:
            app_logger.warning(
                "Tool failed, retrying | tool={tool} | attempt={attempt}",
                tool=tool_name,
                attempt=retries + 1,
            )
            tool_history.append(ToolCall(
                tool=tool_name, args=tool_args,
                result=parsed, status="error", retries=retries + 1,
            ))
            return {"tool_history": tool_history, "retries": retries + 1, "errors": errors}
        else:
            app_logger.error("Tool exhausted retries | tool={tool}", tool=tool_name)
            tool_history.append(ToolCall(
                tool=tool_name, args=tool_args,
                result=parsed, status="failed", retries=retries,
            ))
            return {
                "tool_history": tool_history,
                "current_tool_index": current_index + 1,
                "retries": 0,
                "errors": errors,
            }

    # Success
    tool_history.append(ToolCall(
        tool=tool_name, args=tool_args,
        result=result_data, status="success", retries=retries,
    ))

    updates: Dict[str, Any] = {
        "tool_history": tool_history,
        "current_tool_index": current_index + 1,
        "retries": 0,
        "errors": errors,
    }

    if tool_name in ("search_trains", "recommend_trains"):
        updates["search_results"] = result_data.get("trains", []) if isinstance(result_data, dict) else []
        if updates["search_results"]:
            first = updates["search_results"][0]
            travel["train_number"] = first.get("trainNumber", travel.get("train_number"))
            travel["train_name"] = first.get("trainName", travel.get("train_name"))
    elif tool_name == "check_availability":
        updates["availability"] = result_data
    elif tool_name == "get_fare":
        updates["fare"] = result_data
    elif tool_name == "book_ticket":
        updates["booking"] = result_data
    elif tool_name in ("get_reminders", "list_classes", "list_quotas"):
        updates["reminders"] = result_data if isinstance(result_data, list) else []
    elif tool_name == "get_saved_passengers":
        updates["saved_passengers"] = result_data if isinstance(result_data, list) else []
    elif tool_name in ("get_booking_history", "get_booking", "get_pnr"):
        updates["booking"] = result_data
    elif tool_name == "find_station_code" and isinstance(result_data, dict):
        travel = _merge_travel_context(travel, tool_name, result_data)

    updates["travel"] = travel
    app_logger.info("Tool succeeded | tool={tool}", tool=tool_name)
    return updates
