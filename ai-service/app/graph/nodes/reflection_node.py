# graph/nodes/reflection_node.py
"""
reflection_node — optional quality-check pass after agent_node produces a
final answer.

Triggered only when:
  - At least one tool ran this turn  (there is real data to cross-check)
  - reflection_required=True
  - reflection_retries < 1           (hard cap — at most one retry)

Fast path: if any tool failed (recorded in errors or tool_history status),
skip the LLM call and immediately mark reflection as failed with the error
text as feedback.  This avoids wasting a call when the answer is obviously
incomplete.

On the retry path agent_node receives reflection_feedback in the system
prompt and regenerates its answer.
"""
import json
from typing import Any, Dict

_REFLECT_TOOL = {
    "type": "function",
    "function": {
        "name": "reflect_on_results",
        "description": (
            "Evaluate whether the assistant's draft reply is complete and "
            "consistent with the tool results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "satisfied": {
                    "type": "boolean",
                    "description": "True if the reply fully addresses the user's request.",
                },
                "feedback": {
                    "type": "string",
                    "description": (
                        "If not satisfied, explain concisely what is missing "
                        "or incorrect so the assistant can fix it."
                    ),
                },
            },
            "required": ["satisfied"],
        },
    },
}

_REFLECT_SYSTEM = (
    "You are a quality-check step for an IRCTC travel assistant. "
    "Given the assistant's draft reply and the tool calls that were made this turn, "
    "decide if the reply is complete and does not contradict the tool results. "
    "Be strict but fair — a brief reply is fine as long as it answers the question. "
    "Always call reflect_on_results."
)


async def reflection_node(
    state: Dict[str, Any],
    llm_service,
) -> Dict[str, Any]:
    errors: list = state.get("errors") or []
    tool_history: list = state.get("tool_history") or []
    retries: int = state.get("reflection_retries") or 0

    # Use the snapshot (tools relevant to the current reply) when available.
    # Falls back to full tool_history for backward compatibility.
    relevant_tools: list = state.get("reflection_tool_snapshot") or tool_history

    # ── Fast path: deterministic failure when any tool errored ──────────────
    has_failures = bool(errors) or any(
        h.get("status") == "failed" for h in relevant_tools
    )
    if has_failures:
        feedback = "; ".join(errors) if errors else "One or more tools failed."
        return {
            "reflection_passed": False,
            "reflection_feedback": feedback,
            "reflection_required": False,
            "reflection_retries": retries + 1,
            "reflection_tool_snapshot": None,
        }

    # ── LLM quality check ────────────────────────────────────────────────────
    # Find the last AIMessage text (the draft answer we are checking)
    last_ai_content = ""
    for m in reversed(state.get("messages", [])):
        if m.__class__.__name__ == "AIMessage":
            last_ai_content = getattr(m, "content", "") or ""
            if last_ai_content.strip():
                break

    # Compact summary — only the tools relevant to this reply
    summary = [
        {"tool": h["tool"], "status": h["status"]}
        for h in relevant_tools[-6:]
    ]
    prompt = (
        f"Draft reply:\n{last_ai_content}\n\n"
        f"Tool calls for this reply:\n{json.dumps(summary, indent=2)}\n\n"
        "Is the reply complete and consistent with these results? "
        "A brief reply is fine — it does not need to repeat all tool data, "
        "only address what the user asked."
    )

    try:
        response = await llm_service.chat_raw(
            messages=[{"role": "user", "content": prompt}],
            system=_REFLECT_SYSTEM,
            tools=[_REFLECT_TOOL],
            tool_choice={"type": "function", "function": {"name": "reflect_on_results"}},
            temperature=0.0,
            max_tokens=300,
        )

        tool_input: Dict[str, Any] = {}
        if response.choices[0].message.tool_calls:
            tool_input = json.loads(
                response.choices[0].message.tool_calls[0].function.arguments
            )

        satisfied = bool(tool_input.get("satisfied", True))
        feedback = tool_input.get("feedback", "")

        return {
            "reflection_passed": satisfied,
            "reflection_feedback": feedback,
            "reflection_required": False,
            "reflection_retries": retries + 1,
            "reflection_tool_snapshot": None,
        }

    except Exception:
        # Reflection must never block the final answer
        return {
            "reflection_passed": True,
            "reflection_required": False,
            "reflection_feedback": "",
            "reflection_retries": retries + 1,
            "reflection_tool_snapshot": None,
        }
