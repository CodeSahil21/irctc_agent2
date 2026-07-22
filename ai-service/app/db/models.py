from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessageDoc(BaseModel):
    conversation_id: str
    role: str                        # "user" | "assistant"
    content: str
    intent: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class ConversationDoc(BaseModel):
    conversation_id: str
    user_email: str
    user_name: Optional[str] = None
    title: Optional[str] = None      
    summary: Optional[str] = None    
    turn_count: int = 0
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class UserPreferenceDoc(BaseModel):
    user_email: str
    preferred_class: Optional[str] = None
    preferred_quota: Optional[str] = None
    berth_preference: Optional[str] = None
    senior_citizen: Optional[bool] = None
    updated_at: datetime = Field(default_factory=_now)


class ExecutionLogDoc(BaseModel):
    conversation_id: str
    turn: int
    intent: Optional[str] = None
    user_goal: Optional[str] = None
    tool_history: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    turn_start_time: Optional[float] = None
    total_latency_ms: Optional[float] = None
    claude_calls: Optional[int] = None
    tools_called: Optional[int] = None
    created_at: datetime = Field(default_factory=_now)
