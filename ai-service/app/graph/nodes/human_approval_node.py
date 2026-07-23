# graph/nodes/human_approval_node.py
"""
human_approval_node — interrupts graph execution to ask the user to confirm
a destructive action (booking, cancellation, etc.).

LangGraph's interrupt() suspends the graph and surfaces the prompt to the
caller via the interrupt snapshot.  The graph resumes when the caller sends
a Command(resume=<value>).

Resume value:
  bool  → used directly as confirmed
  str   → normalised against an affirmative word list
"""
import json
from typing import Any, Dict, List

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from app.graph.tool_meta import build_confirmation_prompt, is_destructive


def human_approval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    pending: List[Dict[str, Any]] = state.get("pending_tool_calls") or []

    # Build a combined prompt for all destructive calls in this batch
    prompts = [
        build_confirmation_prompt(p["name"], p["args"])
        for p in pending
        if is_destructive(p["name"], p["args"])
    ]
    if len(prompts) > 1:
        prompt = "\n\n".join(prompts)
    elif prompts:
        prompt = prompts[0]
    else:
        prompt = "Shall I proceed? (yes / no)"

    # Suspend here — caller receives {"confirmation_prompt": prompt}
    user_response = interrupt({"confirmation_prompt": prompt})

    # Normalise the resume value
    if isinstance(user_response, bool):
        confirmed = user_response
    else:
        confirmed = str(user_response).strip().lower() in (
            "yes", "y", "confirm", "ok", "proceed", "true",
            "sure", "go ahead", "yep", "yeah",
        )

    if confirmed:
        return {
            "confirmed": True,
            "confirmation_prompt": prompt,
            "confirmation_required": True,
        }

    # User declined — inject cancelled ToolMessages so the model understands
    # what happened and can relay it in plain language.
    cancelled_msgs = [
        ToolMessage(
            content=json.dumps({
                "status": "cancelled",
                "message": "User did not confirm this action.",
            }),
            tool_call_id=p["id"],
        )
        for p in pending
    ]
    return {
        "confirmed": False,
        "confirmation_prompt": prompt,
        "confirmation_required": True,
        "pending_tool_calls": [],
        "messages": cancelled_msgs,
    }
