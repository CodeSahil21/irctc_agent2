# memory/conversation_memory.py
"""
Layer 2 — Conversation Memory

Manages the message history that gets sent to Claude.
Applies a sliding window so we never blow the context window with 200 messages.

Strategy:
- Keep the last WINDOW_SIZE message pairs (user + assistant)
- Always keep the very first user message (establishes context)
- Trim from the middle, never from the end
"""
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Max messages to send to Claude (user + assistant pairs)
_WINDOW_SIZE = 20  # 10 turns = 20 messages


def get_windowed_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Apply sliding window to message list.
    Always keeps the first HumanMessage + last WINDOW_SIZE messages.
    """
    if len(messages) <= _WINDOW_SIZE:
        return messages

    # Always anchor the first user message for context
    first = messages[0]
    recent = messages[-(_WINDOW_SIZE - 1):]

    # Avoid duplicating if first message is already in the window
    if messages[0] in recent:
        return recent

    return [first] + recent


def format_for_claude(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """
    Convert LangChain BaseMessage list → Anthropic SDK message dicts.
    Applies sliding window before formatting.
    Skips ToolMessages — those are surfaced via context_builder instead.
    """
    windowed = get_windowed_messages(messages)
    result = []
    for msg in windowed:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            result.append({"role": "assistant", "content": str(msg.content)})
    return result or [{"role": "user", "content": "Hello"}]


def message_count(messages: List[BaseMessage]) -> int:
    return len(messages)
