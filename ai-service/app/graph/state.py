# graph/state.py
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class UserPreferences(TypedDict, total=False):
    preferred_class: Optional[str]
    preferred_quota: Optional[str]
    berth_preference: Optional[str]
    senior_citizen: Optional[bool]


class ExecutionMetrics(TypedDict, total=False):
    turn_start_time: Optional[float]
    tools_called: Optional[int]
    total_latency_ms: Optional[float]
    llm_calls: Optional[int]


class ToolCall(TypedDict, total=False):
    id: str
    tool: str
    args: Dict[str, Any]
    result: Optional[Any]
    status: str          # "success" | "failed"
    latency_ms: Optional[float]


class TravelState(TypedDict):
    # ── Conversation ──────────────────────────────────────────────────
    messages: Annotated[List[BaseMessage], add_messages]
    conversation_id: Optional[str]
    turn_count: Optional[int]

    # ── User Identity ─────────────────────────────────────────────────
    user_email: Optional[str]
    user_name: Optional[str]

    # ── User Preferences (long-lived) ─────────────────────────────────
    user_preferences: Optional[UserPreferences]

    # ── Agent loop ────────────────────────────────────────────────────
    # tool_calls emitted by agent_node, awaiting approval/execution
    pending_tool_calls: Optional[List[Dict[str, Any]]]

    # increments each time agent_node is re-entered this turn; reset to 0 on
    # final answer or at the start of a new user turn
    agent_loop_count: Optional[int]

    # ── Tool Execution ────────────────────────────────────────────────
    # accumulates within a single user turn; reset at the start of each new turn
    tool_history: Optional[List[ToolCall]]

    # survives across turns for the life of the conversation:
    #   "get_booking_history" → list of slim booking dicts
    #   "get_saved_passengers" → list of passenger dicts
    persistent_results: Optional[Dict[str, Any]]

    # ── Reflection ────────────────────────────────────────────────────
    reflection_required: Optional[bool]
    reflection_passed: Optional[bool]
    reflection_feedback: Optional[str]
    reflection_retries: Optional[int]

    # ── Human Approval / Interrupt Gate ──────────────────────────────
    confirmation_required: Optional[bool]
    confirmation_prompt: Optional[str]
    confirmed: Optional[bool]

    # ── Error tracking ────────────────────────────────────────────────
    errors: Optional[List[str]]

    # ── Slot-filling / pending intent tracking ────────────────────────
    # When the agent asks the user for a missing detail mid-booking/action,
    # these fields survive in the checkpoint so the next turn knows exactly
    # what it was building toward and what it has already collected.
    pending_intent: Optional[str]          # e.g. "book_ticket", "cancel_ticket"
    collected_slots: Optional[Dict[str, Any]]  # args collected so far for pending_intent

    # ── Execution Metrics ─────────────────────────────────────────────
    execution_metrics: Optional[ExecutionMetrics]

    # ── Backward-compat fields read by chat.py response serialiser ────
    # These are kept so the /agent endpoint response contract is unchanged.
    # agent_node writes them into persistent_results; chat.py also reads
    # them directly, so we expose the most recent values at the top level.
    intent: Optional[str]            # last inferred intent (informational only)
    travel: Optional[Dict[str, Any]] # last extracted travel context (informational)
    search_results: Optional[List[Dict[str, Any]]]
    ranked_results: Optional[List[Dict[str, Any]]]
    selected_train: Optional[Dict[str, Any]]
    availability: Optional[Dict[str, Any]]
    fare: Optional[Dict[str, Any]]
    booking: Optional[Dict[str, Any]]
    passengers: Optional[List[Dict[str, Any]]]
