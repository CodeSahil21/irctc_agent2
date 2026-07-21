from typing import Any, AsyncGenerator, Dict, List, Optional
from app.schemas.chat import ChatResponse, UsageInfo
from app.services.claude import ClaudeService
from app.telemetry.logging import app_logger
from langsmith import traceable


class ChatService:
    """Decoupled Chat Orchestration Service."""

    def __init__(self, claude_service: ClaudeService) -> None:
        self.claude_service = claude_service

    def _normalize_history(
        self, conversation_history: Optional[List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Safely normalize Pydantic ChatMessage models or raw dicts
        into plain dictionaries for the Anthropic SDK.
        """
        if not conversation_history:
            return []

        formatted_history: List[Dict[str, Any]] = []
        for msg in conversation_history:
            if hasattr(msg, "model_dump"):
                formatted_history.append(msg.model_dump())
            elif hasattr(msg, "dict"):
                formatted_history.append(msg.dict())
            elif isinstance(msg, dict):
                formatted_history.append(dict(msg))

        return formatted_history

    @traceable(name="ChatService.send_message", run_type="chain")
    async def send_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ChatResponse:
        """Sends a message, captures SDK response metadata, and returns a ChatResponse schema."""
        messages = self._normalize_history(conversation_history)
        messages.append({"role": "user", "content": message})

        app_logger.debug(
            "ChatService processing | message_count={count}",
            count=len(messages),
        )

        raw_response = await self.claude_service.chat_raw(
            messages=messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        reply_text = "".join(
            block.text for block in raw_response.content if getattr(block, "type", None) == "text"
        )

        usage_data = None
        if hasattr(raw_response, "usage") and raw_response.usage:
            usage_data = UsageInfo(
                input_tokens=getattr(raw_response.usage, "input_tokens", 0),
                output_tokens=getattr(raw_response.usage, "output_tokens", 0),
            )

        return ChatResponse(
            message=reply_text,
            model=getattr(raw_response, "model", self.claude_service.default_model),
            conversation_id=conversation_id,
            usage=usage_data,
            stop_reason=getattr(raw_response, "stop_reason", None),
        )

    @traceable(name="ChatService.stream_message", run_type="chain")
    async def stream_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streams text chunks token-by-token."""
        messages = self._normalize_history(conversation_history)
        messages.append({"role": "user", "content": message})

        app_logger.debug(
            "ChatService streaming | message_count={count}",
            count=len(messages),
        )

        async for chunk in self.claude_service.stream_chat(
            messages=messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk