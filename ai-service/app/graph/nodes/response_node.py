# graph/nodes/response_node.py
from typing import Any, Dict

from langchain_core.messages import AIMessage

from app.graph.state import TravelState
from app.memory.context_builder import build_tool_context
from app.memory.conversation_memory import format_for_claude
from app.services.claude import ClaudeService

_SYSTEM = """You are the official IRCTC AI Travel Assistant. Generate a helpful, accurate response \
based on the tool results and travel context provided.

Guidelines:
- Use Markdown tables for train lists.
- Show fare breakdowns clearly with ₹ symbol.
- For bookings, show PNR, train, route, date, passengers, and fare.
- For live status, show delay, last station, and next station.
- If there were errors, explain them in plain English and suggest recovery.
- If asking for missing information, ask only one question at a time.
- Trains are already sorted by relevance — present them in the order given.
- Be concise and professional."""


async def response_node(state: TravelState, claude_service: ClaudeService) -> Dict[str, Any]:
    # Prefer ranked results over raw search results for display
    ranked = state.get("ranked_results")
    if ranked is not None:
        state = dict(state)
        state["search_results"] = ranked

    messages = format_for_claude(state.get("messages", []))

    context = build_tool_context(state)
    if context:
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] += f"\n\n[Tool Results]\n{context}"
        else:
            messages.append({"role": "user", "content": f"[Tool Results]\n{context}"})

    # Inject reflection feedback as a hint if present
    feedback = state.get("reflection_feedback") or ""
    if feedback and messages:
        messages[-1]["content"] += f"\n\n[Quality note]: {feedback}"

    raw_response = await claude_service.chat_raw(
        messages=messages,
        system=_SYSTEM,
        temperature=0.7,
        max_tokens=2048,
        cache_system=True,
    )

    reply = "".join(
        block.text for block in raw_response.content
        if getattr(block, "type", None) == "text"
    )

    return {"messages": [AIMessage(content=reply)]}
