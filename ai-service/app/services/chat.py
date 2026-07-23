from typing import Any, AsyncGenerator, Dict, List, Optional
from app.schemas.chat import ChatResponse, UsageInfo
from app.services.openai_service import OpenAIService
from app.telemetry.logging import app_logger


class ChatService:
    """Decoupled Chat Orchestration Service."""

    def __init__(self, llm_service: OpenAIService) -> None:
        self.llm_service = llm_service

    def _normalize_history(
        self, conversation_history: Optional[List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Safely normalize Pydantic ChatMessage models or raw dicts
        into plain dictionaries for the OpenAI SDK.
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
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        messages = self._normalize_history(conversation_history)
        messages.append({"role": "user", "content": message.strip()})

        app_logger.debug(
            "ChatService processing | message_count={count}",
            count=len(messages),
        )

        raw_response = await self.llm_service.chat_raw(
            messages=messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        reply_text = raw_response.choices[0].message.content or ""

        usage_data = None
        if hasattr(raw_response, "usage") and raw_response.usage:
            usage_data = UsageInfo(
                input_tokens=getattr(raw_response.usage, "prompt_tokens", 0),
                output_tokens=getattr(raw_response.usage, "completion_tokens", 0),
            )

        return ChatResponse(
            message=reply_text,
            model=getattr(raw_response, "model", self.llm_service.default_model),
            conversation_id=conversation_id,
            usage=usage_data,
            stop_reason=getattr(raw_response.choices[0], "finish_reason", None) if raw_response.choices else None,
        )

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
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        messages = self._normalize_history(conversation_history)
        messages.append({"role": "user", "content": message.strip()})

        app_logger.debug(
            "ChatService streaming | message_count={count}",
            count=len(messages),
        )

        async for chunk in self.llm_service.stream_chat(
            messages=messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk