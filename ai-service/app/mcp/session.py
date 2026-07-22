import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MCPSession:
    """
    Holds the state for one MCP server session scoped to a user.

    The MCP server creates a session on the first request and returns
    mcp-session-id in the response header. We store it here and send
    it on every subsequent request.
    """
    user_email: str
    user_name: Optional[str] = None
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)

    # Metrics
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0

    def touch(self) -> None:
        self.last_used_at = time.time()

    def record_success(self) -> None:
        self.total_calls += 1
        self.successful_calls += 1
        self.touch()

    def record_failure(self) -> None:
        self.total_calls += 1
        self.failed_calls += 1
        self.touch()

    @property
    def is_established(self) -> bool:
        return self.session_id is not None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_used_at

    def health_summary(self) -> dict:
        return {
            "user_email": self.user_email,
            "session_id": self.session_id,
            "established": self.is_established,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "age_seconds": round(self.age_seconds, 1),
            "idle_seconds": round(self.idle_seconds, 1),
        }
