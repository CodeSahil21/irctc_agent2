# graph/edges.py
"""
Routing functions for the new agent-loop graph.

Graph shape:
    START → agent_node
              │ has pending tool calls + any destructive?
              ├─► human_approval_node
              │         │ confirmed?
              │         ├─► tool_executor_node → agent_node  (loop)
              │         └─► agent_node          (tell user it was cancelled)
              │ has pending tool calls, none destructive?
              ├─► tool_executor_node → agent_node  (loop)
              │ no tool calls + reflection needed?
              ├─► reflection_node
              │         │ passed / retries exhausted?
              │         ├─► END
              │         └─► agent_node  (one retry with feedback)
              └─► END   (plain-text final answer)
"""
from typing import Any, Dict

from app.graph.tool_meta import is_destructive


def route_after_agent(state: Dict[str, Any]) -> str:
    """
    Called after every agent_node invocation.

    Priority:
      1. Pending tool calls + at least one is destructive → human_approval_node
      2. Pending tool calls, none destructive              → tool_executor_node
      3. No pending calls + reflection needed              → reflection_node
      4. No pending calls                                  → END
    """
    pending = state.get("pending_tool_calls") or []

    if pending:
        if any(is_destructive(p["name"], p["args"]) for p in pending):
            return "human_approval_node"
        return "tool_executor_node"

    if state.get("reflection_required") and not state.get("reflection_passed"):
        return "reflection_node"

    return "END"


def route_after_human_approval(state: Dict[str, Any]) -> str:
    """
    After the user responds to a confirmation prompt:
      - confirmed  → run the tools
      - declined   → back to agent so it can relay the cancellation in plain text
    """
    return "tool_executor_node" if state.get("confirmed") else "agent_node"


def route_after_tool_executor(_state: Dict[str, Any]) -> str:
    """
    After tools finish, always return to agent_node so the model can
    interpret the results and either call more tools or produce a final answer.
    """
    return "agent_node"


def route_after_reflection(state: Dict[str, Any]) -> str:
    """
    After the reflection check:
      - passed                       → END  (answer is good)
      - failed but retries exhausted → END  (give up gracefully)
      - failed, retries remaining    → agent_node  (one retry with feedback)
    """
    if state.get("reflection_passed"):
        return "END"
    if (state.get("reflection_retries") or 0) >= 1:
        return "END"
    return "agent_node"
