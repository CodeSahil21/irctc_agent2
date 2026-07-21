# websocket/connections.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SocketSession:
    sid: str
    conversation_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None


# sid → SocketSession
_sessions: dict[str, SocketSession] = {}


def create_session(sid: str) -> SocketSession:
    s = SocketSession(sid=sid)
    _sessions[sid] = s
    return s


def get_session(sid: str) -> Optional[SocketSession]:
    return _sessions.get(sid)


def remove_session(sid: str) -> None:
    _sessions.pop(sid, None)
