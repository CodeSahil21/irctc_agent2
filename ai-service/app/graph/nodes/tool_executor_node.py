# graph/nodes/tool_executor_node.py
import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from app.graph.arg_patcher import patch_tool_args
from app.graph.state import TravelState
from app.graph.tool_preconditions import get_precondition
from app.mcp.registry import MCPToolRegistry
from app.telemetry.logging import app_logger


async def _execute_one(
    tool_name: str,
    tool_args: Dict[str, Any],
    user_email: str,
    user_name: Optional[str],
    mcp_registry: MCPToolRegistry,
    timeout: float,
) -> Dict[str, Any]:
    """Execute a single tool with timeout. Returns parsed result dict."""
    try:
        raw = await asyncio.wait_for(
            mcp_registry.execute(
                tool_name=tool_name,
                arguments=tool_args,
                user_email=user_email,
                user_name=user_name,
            ),
            timeout=timeout,
        )
        return json.loads(raw)
    except asyncio.TimeoutError:
        app_logger.warning("Tool timed out | tool={tool} | timeout={t}s", tool=tool_name, t=timeout)
        return {"status": "error", "error_type": "TIMEOUT", "message": f"Tool '{tool_name}' timed out after {timeout}s"}
    except Exception as e:
        app_logger.error("Tool raised exception | tool={tool} | error={e}", tool=tool_name, e=str(e))
        return {"status": "error", "error_type": "EXCEPTION", "message": str(e)}


def _downstream_has_destructive(tool_plan: List[str], after_index: int) -> bool:
    """True if any tool after `after_index` requires confirmation (booking/cancel/etc)."""
    return any(
        get_precondition(t).requires_confirmation
        for t in tool_plan[after_index + 1:]
    )


def _slim_train(t: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep only the fields needed for display + downstream tool args.
    Drops per-station schedule arrays and other large nested blobs.
    """
    return {k: v for k, v in t.items() if k not in (
        "stations", "schedule", "stoppages", "halts", "route",
        "coaches", "coachComposition", "runningDays",
    )}


def _slim_booking(b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep only fields needed for cross-turn arg resolution.
    Full booking detail is fetched fresh on demand via get_booking/get_pnr.
    """
    return {k: b[k] for k in (
        "pnr", "trainNumber", "trainName", "source", "destination",
        "journeyDate", "travelClass", "status", "passengers",
    ) if k in b}


def _apply_result(
    tool_name: str,
    result_data: Any,
    updates: Dict[str, Any],
    travel: Dict[str, Any],
) -> None:
    """Merge a successful tool result into the updates dict."""
    if tool_name in ("search_trains", "recommend_trains"):
        if isinstance(result_data, list):
            trains = result_data
        elif isinstance(result_data, dict):
            trains = result_data.get("trains", [])
        else:
            trains = []
        # Slim each train before storing — drops large schedule arrays
        slim = [_slim_train(t) for t in trains]
        # Merge with existing search_results when doing a multi-date range search
        existing_results = updates.get("search_results") or []
        updates["search_results"] = existing_results + slim
        if trains and not (updates.get("travel", {}) or {}).get("train_number"):
            travel["train_number"] = trains[0].get("trainNumber", travel.get("train_number"))
            travel["train_name"] = trains[0].get("trainName", travel.get("train_name"))
    elif tool_name == "check_availability":
        updates["availability"] = result_data
    elif tool_name == "get_fare":
        updates["fare"] = result_data
    elif tool_name in ("book_ticket", "cancel_ticket", "get_booking", "get_pnr", "update_booking_status", "update_boarding_point"):
        updates["booking"] = result_data
        # Persist PNR into travel context for follow-up tools
        if isinstance(result_data, dict) and result_data.get("pnr"):
            travel["pnr"] = result_data["pnr"]
    elif tool_name == "get_booking_history":
        raw_list = result_data if isinstance(result_data, list) else []
        # Slim each booking — only keep fields needed for cross-turn resolution
        slim_list = [_slim_booking(b) for b in raw_list if isinstance(b, dict)]
        existing = dict(updates.get("tool_results") or {})
        existing["get_booking_history"] = slim_list
        updates["tool_results"] = existing
    elif tool_name == "get_reminders":
        result_list = result_data if isinstance(result_data, list) else []
        updates["reminders"] = result_list
        # Also persist in tool_results so it carries forward across turns
        # (needed for update_reminder / delete_reminder in a later turn)
        existing = dict(updates.get("tool_results") or {})
        existing["get_reminders"] = result_list
        updates["tool_results"] = existing
    elif tool_name in ("list_classes", "list_quotas"):
        existing = dict(updates.get("tool_results") or {})
        existing[tool_name] = result_data
        updates["tool_results"] = existing
    elif tool_name == "get_saved_passengers":
        result_list = result_data if isinstance(result_data, list) else []
        updates["saved_passengers"] = result_list
        # Also persist in tool_results so it carries forward across turns
        existing = dict(updates.get("tool_results") or {})
        existing["get_saved_passengers"] = result_list
        updates["tool_results"] = existing
    elif tool_name == "find_station_code" and isinstance(result_data, dict):
        code = result_data.get("code")
        if code:
            if not travel.get("from_station") or len(travel.get("from_station", "")) > 5:
                travel["from_station"] = code
            elif not travel.get("to_station") or len(travel.get("to_station", "")) > 5:
                travel["to_station"] = code
        # Always store full result so response_node can show the station name
        existing = dict(updates.get("tool_results") or {})
        existing[tool_name] = result_data
        updates["tool_results"] = existing
    else:
        # All other tools: store result in the generic tool_results bucket
        existing = dict(updates.get("tool_results") or {})
        existing[tool_name] = result_data
        updates["tool_results"] = existing
        # Populate travel context from search_train_by_number result
        if tool_name == "search_train_by_number" and isinstance(result_data, dict):
            if result_data.get("trainNumber"):
                travel["train_number"] = result_data["trainNumber"]
            if result_data.get("trainName"):
                travel["train_name"] = result_data["trainName"]


async def _execute_parallel_group(
    group_indices: List[int],
    tool_plan: List[str],
    tool_plan_args: List[Dict[str, Any]],
    user_email: str,
    user_name: Optional[str],
    mcp_registry: MCPToolRegistry,
    tool_history: List[Dict[str, Any]],
    errors: List[str],
    travel: Dict[str, Any],
    parallel_results: Dict[str, Any],
    state: TravelState,
) -> Dict[str, Any]:
    """Fire all tools in the group concurrently, merge results."""
    named_tasks = [
        (
            tool_plan[idx],
            patch_tool_args(
                tool_plan[idx],
                tool_plan_args[idx] if idx < len(tool_plan_args) else {},
                state,
                travel,
            ),
        )
        for idx in group_indices
    ]

    app_logger.info("Executing parallel group | tools={tools}", tools=[n for n, _ in named_tasks])

    t0 = time.perf_counter()
    results = await asyncio.gather(*[
        _execute_one(name, args, user_email, user_name, mcp_registry, get_precondition(name).timeout_seconds)
        for name, args in named_tasks
    ])
    group_latency = round((time.perf_counter() - t0) * 1000, 2)

    updates: Dict[str, Any] = {"current_tool_index": group_indices[-1] + 1, "retries": 0}

    group_had_failure = False
    for (name, args), parsed in zip(named_tasks, results):
        status = parsed.get("status", "error")
        result_data = parsed.get("data")
        if status == "error":
            group_had_failure = True
            errors.append(f"{name}: {parsed.get('message')}")
            tool_history.append({"tool": name, "args": args, "result": parsed, "status": "failed", "retries": 0, "latency_ms": group_latency})
            app_logger.warning("Parallel tool failed | tool={tool}", tool=name)
        else:
            tool_history.append({"tool": name, "args": args, "result": result_data, "status": "success", "retries": 0, "latency_ms": group_latency})
            parallel_results[name] = result_data
            _apply_result(name, result_data, updates, travel)
            app_logger.info("Parallel tool succeeded | tool={tool}", tool=name)

    # A failed prerequisite (e.g. availability/fare) must not lead to a downstream
    # destructive step (e.g. book_ticket) running with missing data — abort the plan.
    if group_had_failure and _downstream_has_destructive(tool_plan, group_indices[-1]):
        app_logger.warning("Aborting plan — prerequisite failed before a destructive step")
        updates["current_tool_index"] = len(tool_plan)

    updates["tool_history"] = tool_history
    updates["errors"] = errors
    updates["travel"] = travel
    updates["parallel_results"] = parallel_results
    app_logger.info("Parallel group done | latency={ms}ms", ms=group_latency)
    return updates


async def tool_executor_node(state: TravelState, mcp_registry: MCPToolRegistry) -> Dict[str, Any]:
    tool_plan: List[str] = state.get("tool_plan") or []
    tool_plan_args: List[Dict[str, Any]] = state.get("tool_plan_args") or []
    current_index: int = state.get("current_tool_index") or 0
    tool_history: List[Dict[str, Any]] = list(state.get("tool_history") or [])
    retries: int = state.get("retries") or 0
    errors: List[str] = list(state.get("errors") or [])
    travel: Dict[str, Any] = dict(state.get("travel") or {})
    parallel_results: Dict[str, Any] = dict(state.get("parallel_results") or {})

    user_email: str = state.get("user_email") or "anonymous@irctc-agent.internal"
    user_name: Optional[str] = state.get("user_name")

    if current_index >= len(tool_plan):
        return {"current_tool_index": current_index}

    tool_name = tool_plan[current_index]
    precondition = get_precondition(tool_name)

    # ── Parallel group detection ──────────────────────────────────────
    group = precondition.parallel_group
    if group:
        group_indices = [current_index]
        i = current_index + 1
        while i < len(tool_plan) and get_precondition(tool_plan[i]).parallel_group == group:
            group_indices.append(i)
            i += 1
        if len(group_indices) > 1:
            return await _execute_parallel_group(
                group_indices, tool_plan, tool_plan_args,
                user_email, user_name, mcp_registry,
                tool_history, errors, travel, parallel_results, state,
            )

    # ── Sequential single tool ────────────────────────────────────────
    tool_args = dict(tool_plan_args[current_index]) if current_index < len(tool_plan_args) else {}

    # Re-resolve arguments from live state so deterministic chains
    # (search → check_availability → get_fare → book_ticket) don't depend on
    # the planner having guessed train numbers, fares, or the route.
    tool_args = patch_tool_args(tool_name, tool_args, state, travel)

    app_logger.info(
        "Executing tool | tool={tool} | index={idx}/{total}",
        tool=tool_name, idx=current_index + 1, total=len(tool_plan),
    )

    t0 = time.perf_counter()
    parsed = await _execute_one(tool_name, tool_args, user_email, user_name, mcp_registry, precondition.timeout_seconds)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    status = parsed.get("status", "error")
    error_type = parsed.get("error_type", "")
    result_data = parsed.get("data")
    error_msg = parsed.get("message")

    if status == "error":
        errors.append(f"{tool_name}: {error_msg}")
        
        # Avoid retrying if failure is due to schema validation / missing parameters
        is_schema_error = error_type in ("INVALID_PARAMETERS", "UNKNOWN_TOOL")

        if retries < precondition.max_retries and not is_schema_error:
            app_logger.warning("Tool failed, retrying | tool={tool} | attempt={n}", tool=tool_name, n=retries + 1)
            tool_history.append({"tool": tool_name, "args": tool_args, "result": parsed, "status": "error", "retries": retries + 1, "latency_ms": latency_ms})
            return {"tool_history": tool_history, "retries": retries + 1, "errors": errors}

        app_logger.error("Tool failed permanently or exhausted retries | tool={tool}", tool=tool_name)
        tool_history.append({"tool": tool_name, "args": tool_args, "result": parsed, "status": "failed", "retries": retries, "latency_ms": latency_ms})
        # Don't let a downstream destructive step (e.g. book_ticket) run after a
        # failed prerequisite — abort the rest of the plan.
        next_index = len(tool_plan) if _downstream_has_destructive(tool_plan, current_index) else current_index + 1
        if next_index == len(tool_plan) and next_index != current_index + 1:
            app_logger.warning("Aborting plan — prerequisite failed before a destructive step")
        return {"tool_history": tool_history, "current_tool_index": next_index, "retries": 0, "errors": errors}

    tool_history.append({"tool": tool_name, "args": tool_args, "result": result_data, "status": "success", "retries": retries, "latency_ms": latency_ms})
    updates: Dict[str, Any] = {"tool_history": tool_history, "current_tool_index": current_index + 1, "retries": 0, "errors": errors}
    _apply_result(tool_name, result_data, updates, travel)
    updates["travel"] = travel
    app_logger.info("Tool succeeded | tool={tool} | latency={ms}ms", tool=tool_name, ms=latency_ms)
    return updates