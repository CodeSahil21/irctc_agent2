# graph/nodes/response_node.py
import json
import re
from typing import Any, Dict, Set

from langchain_core.messages import AIMessage

from app.graph.state import TravelState
from app.memory.context_builder import build_tool_context
from app.memory.conversation_memory import format_messages
from app.services.openai_service import OpenAIService
from app.telemetry.logging import app_logger

# Indian Railways PNRs are 10 digits. Guard against the model surfacing any PNR
# that is not present verbatim in the grounded tool data.
_PNR_RE = re.compile(r"\b\d{10}\b")


def _grounded_pnrs(state: TravelState) -> Set[str]:
    # Scan every state field that can legitimately contain a PNR.
    blob = json.dumps(
        {
            "booking": state.get("booking"),
            "travel": state.get("travel"),
            "tool_results": state.get("tool_results"),
            "search_results": state.get("search_results"),
            "availability": state.get("availability"),
            "reminders": state.get("reminders"),
            "saved_passengers": state.get("saved_passengers"),
        },
        default=str,
    )
    return set(_PNR_RE.findall(blob))


def _ground_response(reply: str, state: TravelState) -> str:
    """Redact any 10-digit PNR the model emits that isn't in the tool data."""
    allowed = _grounded_pnrs(state)

    def _replace(match: "re.Match[str]") -> str:
        token = match.group(0)
        if token in allowed:
            return token
        app_logger.warning("Redacted ungrounded PNR from response | pnr={pnr}", pnr=token)
        return "[PNR unavailable]"

    return _PNR_RE.sub(_replace, reply)

_SYSTEM = """You are the official IRCTC AI Travel Assistant. Generate a helpful, accurate response \
based on the tool results and travel context provided.

CRITICAL RULES:
- NEVER invent, guess, or fabricate any data — PNRs, train numbers, fares, seat numbers, or availability.
- ONLY show PNR numbers that appear verbatim in the [Tool Results] block. If no booking result is present, do NOT show any PNR.
- NEVER tell the user to visit www.irctc.co.in or any external website. All data comes from this system.
- If tool results are missing or empty, tell the user you could not retrieve the data and ask them to try again.
- NEVER ask the user for a PNR, booking ID, or passenger ID to fetch their saved passengers, booking history, or reminders — these are fetched automatically using their account. If these results are empty, say "no saved passengers found" etc., not "please provide your PNR".
- NEVER ask "Would you like to proceed?", "Shall I book?", "Would you like to confirm?", or any booking confirmation question — the booking confirmation is handled automatically by the system. Just present the data clearly.
- NEVER ask "how many passengers?" — passenger selection is handled separately by the system.

Guidelines:
- Use Markdown tables for train lists.
- Show fare breakdowns clearly with ₹ symbol.
- For availability results, show seat count, class, and fare breakdown. End with a clear summary — do NOT ask for confirmation.
- For bookings, show PNR, train, route, date, passengers, and fare — all taken directly from tool results.
- For live status, show delay, last station, and next station.
- If there were errors, explain them in plain English and suggest recovery.
- If asking for missing information, ask only one question at a time.
- Trains are already sorted by relevance — present them in the order given.
- Be concise and professional."""


async def response_node(state: TravelState, llm_service: OpenAIService) -> Dict[str, Any]:
    # Prefer ranked results over raw search results for display
    ranked = state.get("ranked_results")
    if ranked is not None:
        state = dict(state)
        state["search_results"] = ranked

    messages = format_messages(state.get("messages", []))

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

    raw_response = await llm_service.chat_raw(
        messages=messages,
        system=_SYSTEM,
        temperature=0.7,
        max_tokens=2048,
    )

    reply = raw_response.choices[0].message.content or ""
    reply = _ground_response(reply, state)

    return {"messages": [AIMessage(content=reply)]}
