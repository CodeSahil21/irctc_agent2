# websocket/connections.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class SocketSession:
    sid: str
    conversation_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    pending_user_message: Optional[str] = None
    pending_message_id: Optional[str] = None
    interrupted: bool = False  # True when graph is paused at human_approval_node
    processing: bool = False   # True while a query is in-flight — blocks concurrent requests


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
