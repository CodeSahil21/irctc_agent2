# graph/state.py
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TravelContext(TypedDict, total=False):
    from_station: Optional[str]
    to_station: Optional[str]
    date: Optional[str]
    travel_class: Optional[str]
    quota: Optional[str]
    train_number: Optional[str]
    train_name: Optional[str]
    pnr: Optional[str]


class UserPreferences(TypedDict, total=False):
    preferred_class: Optional[str]       # e.g. "3A"
    preferred_quota: Optional[str]       # e.g. "GN"
    berth_preference: Optional[str]      # e.g. "LB"
    senior_citizen: Optional[bool]


class ExecutionMetrics(TypedDict, total=False):
    turn_start_time: Optional[float]
    tools_called: Optional[int]
    total_latency_ms: Optional[float]
    claude_calls: Optional[int]


class ToolCall(TypedDict):
    tool: str
    args: Dict[str, Any]
    result: Optional[Any]
    status: str  # "pending" | "success" | "error" | "failed"
    retries: int
    latency_ms: Optional[float]


class TravelState(TypedDict):
    # ── Conversation ──────────────────────────────────────────────────
    messages: Annotated[List[BaseMessage], add_messages]
    conversation_id: Optional[str]
    turn_count: Optional[int]

    # ── Intent & Planning ─────────────────────────────────────────────
    intent: Optional[str]
    user_goal: Optional[str]

    # ── Travel Context (persisted across turns via checkpointer) ──────
    travel: Optional[TravelContext]

    # ── Search / Booking Results ──────────────────────────────────────
    search_results: Optional[List[Dict[str, Any]]]
    selected_train: Optional[Dict[str, Any]]
    availability: Optional[Dict[str, Any]]
    fare: Optional[Dict[str, Any]]
    passengers: Optional[List[Dict[str, Any]]]
    booking: Optional[Dict[str, Any]]
    reminders: Optional[List[Dict[str, Any]]]
    saved_passengers: Optional[List[Dict[str, Any]]]
    # Generic bucket for tool results not covered by dedicated fields
    # (route, seat_map, live_status, platform, schedule, stations, etc.)
    tool_results: Optional[Dict[str, Any]]

    # ── Slot Filling ──────────────────────────────────────────────────
    missing_slots: Optional[List[str]]
    pending_question: Optional[str]

    # ── Tool Execution ────────────────────────────────────────────────
    tool_plan: Optional[List[str]]
    tool_plan_args: Optional[List[Dict[str, Any]]]
    tool_history: Optional[List[ToolCall]]
    current_tool_index: Optional[int]
    parallel_results: Optional[Dict[str, Any]]   # tool_name → result for parallel group

    # ── Reflection ────────────────────────────────────────────────────
    reflection_required: Optional[bool]
    reflection_passed: Optional[bool]
    reflection_feedback: Optional[str]
    reflection_retries: Optional[int]

    # ── Ranking ───────────────────────────────────────────────────────
    ranked_results: Optional[List[Dict[str, Any]]]  # sorted search results

    # ── Human Approval / Interrupt Gate ──────────────────────────────
    confirmation_required: Optional[bool]
    confirmation_prompt: Optional[str]
    confirmed: Optional[bool]

    # ── Error / Retry ─────────────────────────────────────────────────
    retries: Optional[int]
    errors: Optional[List[str]]

    # ── User Identity ─────────────────────────────────────────────────
    user_email: Optional[str]
    user_name: Optional[str]

    # ── User Preferences (Layer 3 memory — long-lived) ────────────────
    user_preferences: Optional[UserPreferences]

    # ── Execution Metrics ─────────────────────────────────────────────
    execution_metrics: Optional[ExecutionMetrics]
