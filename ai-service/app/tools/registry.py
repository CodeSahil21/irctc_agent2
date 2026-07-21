import json
from typing import Any, Dict
from . import implementations
from langsmith import traceable

# Complete mapping for all 29 tool implementations
TOOL_REGISTRY = {
    "search_trains": implementations.search_trains,
    "check_availability": implementations.check_availability,
    "get_fare": implementations.get_fare,
    "get_route": implementations.get_route,
    "get_seat_map": implementations.get_seat_map,
    "get_boarding_points": implementations.get_boarding_points,
    "search_train_by_number": implementations.search_train_by_number,
    "get_live_status": implementations.get_live_status,
    "get_train_schedule": implementations.get_train_schedule,
    "get_platform": implementations.get_platform,
    "search_stations": implementations.search_stations,
    "find_station_code": implementations.find_station_code,
    "get_nearby_stations": implementations.get_nearby_stations,
    "list_classes": implementations.list_classes,
    "list_quotas": implementations.list_quotas,
    "recommend_trains": implementations.recommend_trains,
    "book_ticket": implementations.book_ticket,
    "cancel_ticket": implementations.cancel_ticket,
    "get_pnr": implementations.get_pnr,
    "get_booking": implementations.get_booking,
    "get_booking_history": implementations.get_booking_history,
    "update_booking_status": implementations.update_booking_status,
    "update_boarding_point": implementations.update_boarding_point,
    "create_reminder": implementations.create_reminder,
    "get_reminders": implementations.get_reminders,
    "update_reminder": implementations.update_reminder,
    "delete_reminder": implementations.delete_reminder,
    "add_saved_passenger": implementations.add_saved_passenger,
    "get_saved_passengers": implementations.get_saved_passengers,
}

@traceable(name="execute_tool", run_type="tool")
def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    Executes a tool by name with complete exception handling (Step 6).
    Returns a structured JSON string so Claude understands any failure gracefully.
    """
    # Scenario 3: Claude requests a non-existent or unregistered tool
    if tool_name not in TOOL_REGISTRY:
        return json.dumps({
            "status": "error",
            "error_type": "UNKNOWN_TOOL",
            "message": f"Tool '{tool_name}' is not registered or supported in this system."
        })

    tool_fn = TOOL_REGISTRY[tool_name]

    try:
        # Execute tool function with unpacking
        result = tool_fn(**tool_input)

        # Scenario 2: Tool returns invalid data (None, empty string, or non-container type)
        if result is None or not isinstance(result, (dict, list)):
            return json.dumps({
                "status": "error",
                "error_type": "INVALID_TOOL_RESPONSE",
                "message": f"Tool '{tool_name}' executed but returned an invalid data format."
            })

        # Successful Execution Payload
        return json.dumps({
            "status": "success",
            "data": result
        })

    # Scenario 4: Parameter mismatch (missing required arguments or unexpected keys)
    except TypeError as te:
        return json.dumps({
            "status": "error",
            "error_type": "INVALID_ARGUMENTS",
            "message": f"Parameter error when invoking '{tool_name}': {str(te)}"
        })

    # Scenario 1: Tool throws an internal runtime exception
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "EXECUTION_FAILURE",
            "message": f"Internal error during execution of tool '{tool_name}': {str(e)}"
        })