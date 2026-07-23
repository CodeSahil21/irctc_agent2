# graph/nodes/tool_planner_node.py
import json
from typing import Any, Dict, List

from app.graph.state import TravelState
from app.graph.tool_preconditions import get_precondition
from app.mcp.registry import MCPToolRegistry
from app.memory.context_builder import build_planner_context
from app.services.openai_service import OpenAIService
from app.telemetry.logging import app_logger

_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "create_tool_plan",
        "description": "Create an ordered execution plan of MCP tools to fulfill the user's intent.",
        "parameters": {
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
        }
    }
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
- To update or delete a reminder, first call get_reminders to obtain the reminderId, then use that id.
- For pnr/cancel/booking tools, use the PNR from context if present; otherwise call get_booking_history first.
- check_availability, get_fare, and get_live_status can run in parallel after search_trains.
- If user asks for route/schedule of multiple trains, plan one get_route call per train number.
FLEXIBLE DATE SEARCH — when travel context has date_range (list of dates):
- Plan one search_trains call per date in the list (up to 7 calls).
- Use args: {fromStation, toStation, journeyDate: <each date>, quota, travelClass} for each.
- The ranking_node will merge and sort all results — just plan the searches.
- Set preference in recommend_trains to match user goal: "cheapest", "fastest", or "overnight".
- For "cheapest this week" → use recommend_trains with preference="cheapest" for each date.
- For "fastest this week" → use recommend_trains with preference="fastest" for each date.
- For "available this week" → use search_trains for each date.

- Default quota to "GN" if not specified by user.
- Always call create_tool_plan tool.

PASSENGER RULES — critical, never violate:
- NEVER call add_saved_passenger unless the user explicitly says "add a passenger" or "save a new passenger" AND provides the full details (name, age, gender) themselves.
- NEVER invent passenger details. If the user says "book for new passenger" without providing name/age/gender, do NOT call add_saved_passenger — instead the slot filler will ask for the details.
- For book_ticket: use ONLY passengers from "Selected passengers for booking" in context. NEVER auto-select all saved passengers.
- If "Selected passengers for booking" is empty, do NOT include passengers in the plan — the slot filler already asked the user.
- passengers arg for book_ticket must come from "Selected passengers for booking" only.
- If travel context has save_new_passenger=True, include add_saved_passenger BEFORE book_ticket using the passenger details from "Selected passengers for booking".
- If travel context has save_new_passenger=False, do NOT call add_saved_passenger — just book directly.

CONTEXT USAGE — extract data from cached results instead of asking user:
- If user mentions "my train" / "above train" / "that train" / "this booking" → look in Search results / Booking History / Booking for trainNumber
- If user mentions "my booking" / "rahul's booking" → look in Booking History for the PNR and train details
- If user wants boarding points for a booked train → extract trainNumber from Booking History
- If user wants to change boarding point → extract trainNumber and PNR from Booking / Booking History
- If user mentions passenger names → look in Saved passengers for matching names
- Use data from "Already executed (results cached)" to avoid repeating tool calls

ZERO-INPUT TOOLS — these need NO arguments, call them directly with an empty args object:
- get_saved_passengers  → args: {}
- get_booking_history   → args: {}
- get_reminders         → args: {}
- list_classes          → args: {}
- list_quotas           → args: {}

QUERY TOOLS — set "query" from exactly what the user said, nothing else:
- search_stations       → args: {"query": "<user text>"}
- find_station_code     → args: {"query": "<city or station name>"}

PLANNER-FILLED ARGS — never ask the user for these, derive them from context or conversation:
- trainNumber   → from search_results[0].trainNumber OR Booking History OR Booking in context
- trainName     → from search_results[0].trainName
- fare          → from get_fare result
- passengers    → from get_saved_passengers result or selected_passengers in context
- reminderId    → from get_reminders result
- reminderAt    → parse from user's message (ISO datetime)
- type          → for reminders: JOURNEY / PNR / BOOKING based on context
- status        → for update_booking_status: BOOKED / CANCELLED / etc. based on context
- newBoardingStation → from user message or boarding points result
- preference    → for recommend_trains: fastest / cheapest / overnight based on user goal
- quota         → default "GN" unless user specifies otherwise
- pnr           → from Booking History OR Booking OR travel context (never ask user)"""

# Intents where reflection adds value (data-heavy, multi-field responses)
_REFLECT_INTENTS = {
    "search_trains", "recommend_trains", "check_availability",
    "get_fare", "book_ticket",
}


async def tool_planner_node(
    state: TravelState,
    llm_service: OpenAIService,
    mcp_registry: MCPToolRegistry = None,
) -> Dict[str, Any]:
    available_tools = mcp_registry.get_tool_schemas() if mcp_registry else []
    tools_for_llm = [_PLAN_TOOL] + available_tools if available_tools else [_PLAN_TOOL]

    # Build a compact tools summary for the context message (names + descriptions only)
    tools_summary = json.dumps(
        [{"name": t["function"]["name"], "description": t["function"].get("description", "")} for t in available_tools],
        indent=2,
    )
    full_context = build_planner_context(state, tools_summary)

    # Inject reflection feedback if this is a retry
    feedback = state.get("reflection_feedback") or ""
    if feedback:
        full_context += f"\n\nPrevious attempt feedback (fix this): {feedback}"

    response = await llm_service.chat_raw(
        messages=[{"role": "user", "content": full_context}],
        system=_SYSTEM,
        tools=tools_for_llm,
        tool_choice={"type": "function", "function": {"name": "create_tool_plan"}},
        temperature=0.0,
        max_tokens=2048,
    )

    steps: List[Dict[str, Any]] = []
    if response.choices[0].message.tool_calls:
        tool_result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        raw_steps = tool_result.get("steps", [])
        # Filter valid steps and strip "functions." prefix if present (OpenAI sometimes adds this)
        steps = []
        for s in raw_steps:
            if isinstance(s, dict) and "tool" in s:
                tool_name = s["tool"]
                # Strip "functions." prefix if present
                if tool_name.startswith("functions."):
                    tool_name = tool_name.replace("functions.", "", 1)
                steps.append({"tool": tool_name, "args": s.get("args", {})})

    tool_plan = [s["tool"] for s in steps]
    tool_plan_args = [s.get("args", {}) for s in steps]

    confirmation_required = any(get_precondition(t).requires_confirmation for t in tool_plan)

    # Enable reflection for data-heavy intents — hard-cap at 1 retry
    intent = state.get("intent") or ""
    reflection_retries = state.get("reflection_retries") or 0
    is_reflection_retry = bool(feedback)
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
