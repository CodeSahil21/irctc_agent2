# graph/nodes/tool_executor_node.py
"""
tool_executor_node — executes every pending tool call concurrently, then
returns results as ToolMessages so the model can see them on the next loop.

Responsibilities
----------------
- Run all pending_tool_calls via asyncio.gather (native parallel execution).
- Apply ranking inline when search_trains or recommend_trains returns a list.
- Write long-lived results (booking history, saved passengers) into
  persistent_results so agent_node can reference them in the context block
  without re-fetching.
- Populate the backward-compat top-level state fields (search_results, fare,
  availability, booking) that chat.py reads from the final result.
- Append a ToolCall record to tool_history for reflection and metrics.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import ToolMessage

from app.graph.ranking import detect_mode, rank_trains

# Tools whose results should survive across turns
_PERSISTENT_TOOLS = {"get_booking_history", "get_saved_passengers"}

# Large sub-fields that add token bloat without helping the model
_TRAIN_DROP_KEYS = frozenset({
    "stations", "schedule", "stoppages", "halts",
    "route", "coaches", "coachComposition", "runningDays",
    # These embed a single class's fare/availability chosen by the MCP server —
    # stripping them prevents the LLM from pre-deciding the travel class.
    # The agent should show all available classes or ask the user.
    "fare", "availability",
})

_TIMEOUT_SECONDS = 15.0


def _normalize_empty_result(tool_name: str, data: Any) -> Any:
    """
    Normalize empty results ([], None, {}) into human-readable messages
    so the LLM has something meaningful to say instead of silence.
    """
    if tool_name == "get_saved_passengers":
        if not data or (isinstance(data, list) and len(data) == 0):
            return {
                "status": "success",
                "message": "You don't have any saved passengers yet. You can add one using the add_saved_passenger tool.",
                "passengers": [],
            }
    
    if tool_name == "get_booking_history":
        if not data or (isinstance(data, list) and len(data) == 0):
            return {
                "status": "success",
                "message": "You don't have any past bookings yet.",
                "bookings": [],
            }
    
    if tool_name in ("search_trains", "recommend_trains"):
        if isinstance(data, list) and len(data) == 0:
            return {
                "status": "success",
                "message": "No trains found for the specified route and date. Try a different date or nearby stations.",
                "trains": [],
            }
        if isinstance(data, dict) and not data.get("trains"):
            return {
                "status": "success",
                "message": "No trains found for the specified route and date. Try a different date or nearby stations.",
                "trains": [],
            }
    
    if tool_name == "check_availability":
        if not data or not isinstance(data, dict):
            return {
                "status": "success",
                "message": "Availability information is not available for this train and date.",
                "available": False,
            }
    
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slim_train(t: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in t.items() if k not in _TRAIN_DROP_KEYS}


def _slim_booking(b: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the fields needed for cross-turn PNR / route resolution."""
    keep = (
        "pnr", "trainNumber", "trainName", "source", "destination",
        "journeyDate", "travelClass", "status", "passengers",
    )
    return {k: b[k] for k in keep if k in b}


def _dedup_trains(trains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate a merged list of trains that may contain the same train number
    across multiple journey dates (from parallel date-range calls).

    Strategy: for each trainNumber keep the entry whose availability has the
    highest seat count.  This surfaces the most bookable option to the model
    while eliminating the visual clutter of 7 identical rows.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for t in trains:
        num = t.get("trainNumber") or t.get("train_number") or ""
        if not num:
            continue
        if num not in seen:
            seen[num] = t
            continue
        # Prefer whichever entry has more available seats
        def _seats(entry: Dict[str, Any]) -> int:
            avail = entry.get("availability")
            if isinstance(avail, dict):
                count = avail.get("count")
                if isinstance(count, int):
                    return count
                if avail.get("available") is True:
                    return 1
            return 0
        if _seats(t) > _seats(seen[num]):
            seen[num] = t
    return list(seen.values())


def _latest_user_text(state: Dict[str, Any]) -> str:
    for msg in reversed(state.get("messages", [])):
        if msg.__class__.__name__ == "HumanMessage":
            return str(msg.content)
    return ""


def _pin_selected_train(
    state: Dict[str, Any],
    compat: Dict[str, Any],
    payload: Dict[str, Any],
) -> None:
    """
    Write selected_train into compat when availability or fare is checked for
    a specific train.  Pulls the full train record (name, stations, times) from
    search_results so book_ticket has everything it needs without re-fetching.

    Only sets selected_train if it isn't already pinned to a different train —
    this prevents concurrent multi-class fare calls from clobbering each other.
    """
    train_number = (
        payload.get("trainNumber")
        or payload.get("train_number")
        or payload.get("number")
    )
    if not train_number:
        return

    # Don't overwrite if already pinned to a different train
    existing = compat.get("selected_train") or state.get("selected_train")
    if existing and existing.get("trainNumber") and existing["trainNumber"] != train_number:
        return

    # Find the matching train record from search results for full details
    all_trains = (
        compat.get("search_results")
        or compat.get("ranked_results")
        or state.get("ranked_results")
        or state.get("search_results")
        or []
    )
    base = next(
        (t for t in all_trains if str(t.get("trainNumber")) == str(train_number)),
        None,
    )

    journey_date = (
        payload.get("journeyDate")
        or payload.get("date")
        or (base or {}).get("journeyDate")
        or (existing or {}).get("journeyDate")
    )

    selected: Dict[str, Any] = {
        "trainNumber": train_number,
        "trainName":   (base or {}).get("trainName") or (existing or {}).get("trainName") or "",
        "fromStation": (
            payload.get("fromStation")
            or (base or {}).get("fromStation")
            or (existing or {}).get("fromStation")
            or ""
        ),
        "toStation": (
            payload.get("toStation")
            or (base or {}).get("toStation")
            or (existing or {}).get("toStation")
            or ""
        ),
        "departure":   (base or {}).get("departure") or "",
        "arrival":     (base or {}).get("arrival") or "",
        "duration":    (base or {}).get("duration") or "",
        "classes":     (base or {}).get("classes") or [],
    }
    if journey_date:
        selected["journeyDate"] = journey_date

    compat["selected_train"] = selected


async def _execute_one(
    tool_name: str,
    args: Dict[str, Any],
    user_email: str,
    user_name: Optional[str],
    mcp_registry,
) -> Dict[str, Any]:
    """Execute a single MCP tool with timeout. Always returns a dict."""
    try:
        raw = await asyncio.wait_for(
            mcp_registry.execute(
                tool_name=tool_name,
                arguments=args,
                user_email=user_email,
                user_name=user_name,
            ),
            timeout=_TIMEOUT_SECONDS,
        )
        return json.loads(raw)
    except asyncio.TimeoutError:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' timed out after {_TIMEOUT_SECONDS}s.",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def tool_executor_node(
    state: Dict[str, Any],
    mcp_registry,
) -> Dict[str, Any]:
    pending: List[Dict[str, Any]] = state.get("pending_tool_calls") or []
    if not pending:
        return {"pending_tool_calls": []}

    user_email: str = state.get("user_email") or "anonymous@irctc-agent.internal"
    user_name: Optional[str] = state.get("user_name")

    # ── Execute all pending calls concurrently ───────────────────────────────
    t0 = time.perf_counter()
    raw_results = await asyncio.gather(*[
        _execute_one(p["name"], p["args"], user_email, user_name, mcp_registry)
        for p in pending
    ])
    total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # ── Ranking mode — detected once from the latest user message ────────────
    mode: Optional[str] = None

    # ── Accumulate results ───────────────────────────────────────────────────
    tool_messages: List[ToolMessage] = []
    tool_history: List[Dict[str, Any]] = list(state.get("tool_history") or [])
    persistent: Dict[str, Any] = dict(state.get("persistent_results") or {})
    errors: List[str] = list(state.get("errors") or [])

    # Backward-compat top-level fields (latest write wins within a turn)
    compat: Dict[str, Any] = {}

    for p, parsed in zip(pending, raw_results):
        name = p["name"]
        args = p["args"]
        call_id = p["id"]
        status = parsed.get("status", "error")
        data = parsed.get("data")

        if status == "error":
            errors.append(f"{name}: {parsed.get('message', 'unknown error')}")
            tool_history.append({
                "id": call_id,
                "tool": name,
                "args": args,
                "result": parsed,
                "status": "failed",
                "latency_ms": total_latency_ms,
            })
            tool_messages.append(ToolMessage(
                content=json.dumps(parsed),
                tool_call_id=call_id,
            ))
            continue

        # ── Normalize empty results into readable messages ───────────────────
        data = _normalize_empty_result(name, data)

        # ── Post-process successful results ─────────────────────────────────
        payload = data

        if name == "search_trains" and isinstance(data, list):
            trains = [_slim_train(t) for t in data]
            if mode is None:
                mode = detect_mode(_latest_user_text(state))
            payload = rank_trains(trains, mode)
            # Merge with any prior search results in the same turn (date-range searches)
            existing = compat.get("search_results") or state.get("search_results") or []
            compat["search_results"] = existing + payload
            compat["ranked_results"] = payload  # single-date: ranked = search

        elif name == "recommend_trains" and isinstance(data, dict):
            trains = data.get("trains") or []
            slimmed = [_slim_train(t) for t in trains]
            payload = {**data, "trains": slimmed}
            # Accumulate across concurrent date-range calls — do NOT overwrite.
            # Each parallel recommend_trains call covers a different date; we
            # merge all results so the model and the response have the full picture.
            if mode is None:
                mode = detect_mode(_latest_user_text(state))
            existing = compat.get("search_results") or state.get("search_results") or []
            merged = _dedup_trains(existing + slimmed)
            ranked = rank_trains(merged, mode)
            compat["search_results"] = merged
            compat["ranked_results"] = ranked
            # If this call returned exactly one train (focused search for a
            # specific train number), pin it as selected_train immediately.
            # The availability/fare inline in the result also carries journeyDate.
            if len(slimmed) == 1:
                t = slimmed[0]
                avail = t.get("availability") or {}
                journey_date = avail.get("journeyDate") or data.get("journeyDate")
                pin_payload = {**t}
                if journey_date:
                    pin_payload["journeyDate"] = journey_date
                _pin_selected_train(state, compat, pin_payload)

        elif name == "check_availability":
            compat["availability"] = payload
            # Derive selected_train from the availability result so book_ticket
            # has trainNumber, journeyDate, fromStation, toStation without re-asking.
            if isinstance(payload, dict):
                _pin_selected_train(state, compat, payload)

        elif name == "get_fare":
            # Always write the latest fare to the compat field so the response
            # serialiser has something to return.
            compat["fare"] = payload
            # Also accumulate ALL fares fetched this session into persistent_results
            # keyed by travelClass — this survives concurrent multi-class calls where
            # last-write-wins on compat["fare"] would otherwise lose 2 of 3 results.
            if isinstance(payload, dict):
                cls = payload.get("travelClass") or payload.get("class") or "UNKNOWN"
                fares_map = dict(persistent.get("fares") or {})
                fares_map[cls] = payload
                persistent["fares"] = fares_map
                # Pin selected_train if not already set
                _pin_selected_train(state, compat, payload)

        elif name in (
            "book_ticket", "cancel_ticket", "get_booking", "get_pnr",
            "update_booking", "update_booking_status", "update_boarding_point",
        ):
            compat["booking"] = payload
            # Also persist a slim copy of the booking so the PNR survives
            # across turns (state["booking"] is cleared at new-turn reset).
            # This lets cancel/update flows find the PNR without re-fetching
            # booking history.
            if name == "book_ticket" and isinstance(payload, dict) and payload.get("pnr"):
                persistent["last_booking"] = _slim_booking(payload)

        elif name == "get_booking_history":
            raw_list = payload if isinstance(payload, list) else (payload.get("bookings") if isinstance(payload, dict) else [])
            slim_list = [_slim_booking(b) for b in (raw_list or []) if isinstance(b, dict)]
            persistent["get_booking_history"] = slim_list
            payload = payload if isinstance(payload, dict) else slim_list  # keep normalized message if present

        elif name == "get_saved_passengers":
            raw_list = payload if isinstance(payload, list) else (payload.get("passengers") if isinstance(payload, dict) else [])
            result_list = raw_list or []
            persistent["get_saved_passengers"] = result_list

        # Persist long-lived results by tool name — always store the raw list,
        # not the normalized dict, so session context iteration stays consistent.
        # Note: get_booking_history and get_saved_passengers are already persisted
        # correctly in their elif branches above with the raw list — no need to
        # overwrite them here with potentially-normalized dict payloads.

        tool_history.append({
            "id": call_id,
            "tool": name,
            "args": args,
            "result": payload,
            "status": "success",
            "latency_ms": total_latency_ms,
        })
        tool_messages.append(ToolMessage(
            content=json.dumps(payload, default=str),
            tool_call_id=call_id,
        ))

    return {
        "messages": tool_messages,
        "pending_tool_calls": [],
        "tool_history": tool_history,
        # Record how many tools existed before this batch so reflection_node
        # can slice tool_history[offset:] to get only the current loop's tools.
        "reflection_tool_offset": len(tool_history) - len(pending),
        "persistent_results": persistent,
        "errors": errors,
        **compat,
    }
