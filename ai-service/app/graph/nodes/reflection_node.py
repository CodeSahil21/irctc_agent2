# graph/nodes/reflection_node.py
"""
Phase 12 — Reflection

Claude inspects the tool results against the user goal and decides:
  - satisfied  → continue to response_node
  - unsatisfied → set reflection_feedback, route back to tool_planner_node for a retry

Reflection is only triggered when reflection_required=True in state.
Capped at 1 reflection cycle to prevent infinite loops.
"""
import json
from typing import Any, Dict

from app.graph.state import TravelState
from app.services.claude import ClaudeService
from app.telemetry.logging import app_logger

_REFLECT_TOOL = {
    "name": "reflect_on_results",
    "description": "Evaluate whether the tool results satisfy the user's goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "satisfied": {
                "type": "boolean",
                "description": "True if the results fully answer the user's goal.",
            },
            "feedback": {
                "type": "string",
                "description": "If not satisfied, explain what is missing or wrong and what should be retried.",
            },
        },
        "required": ["satisfied"],
    },
}

_SYSTEM = (
    "You are a quality-check agent for an IRCTC travel assistant. "
    "Given the user's goal and the tool results, decide if the results are sufficient. "
    "Be strict: if key data is missing, empty, or clearly wrong, mark as not satisfied. "
    "Always call reflect_on_results."
)


async def reflection_node(state: TravelState, claude_service: ClaudeService) -> Dict[str, Any]:
    user_goal = state.get("user_goal") or ""
    tool_history = state.get("tool_history") or []
    errors = state.get("errors") or []

    # Build a compact summary of what was executed and what came back
    results_summary = []
    for entry in tool_history:
        results_summary.append({
            "tool": entry["tool"],
            "status": entry["status"],
            "result": entry.get("result") if entry["status"] == "success" else entry.get("result", {}).get("message"),
        })

    prompt = (
        f"User goal: {user_goal}\n\n"
        f"Tool execution results:\n{json.dumps(results_summary, indent=2)}\n\n"
        f"Errors: {errors if errors else 'none'}\n\n"
        "Did the tool results fully satisfy the user's goal?"
    )

    try:
        response = await claude_service.chat_raw(
            messages=[{"role": "user", "content": prompt}],
            system=_SYSTEM,
            tools=[_REFLECT_TOOL],
            tool_choice={"type": "tool", "name": "reflect_on_results"},
            temperature=0.0,
            max_tokens=256,
            cache_system=True,
        )

        tool_input: Dict[str, Any] = {}
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_input = block.input or {}
                break

        satisfied = bool(tool_input.get("satisfied", True))
        feedback = tool_input.get("feedback", "")

        app_logger.info(
            "Reflection complete | satisfied={s} | feedback={f}",
            s=satisfied, f=feedback or "none",
        )

        return {
            "reflection_passed": satisfied,
            "reflection_feedback": feedback,
            # Clear reflection_required so we don't loop more than once
            "reflection_required": False,
        }

    except Exception as e:
        # Reflection failure must never block the response
        app_logger.error("Reflection failed: {e}", e=str(e), exc_info=True)
        return {"reflection_passed": True, "reflection_required": False, "reflection_feedback": ""}
