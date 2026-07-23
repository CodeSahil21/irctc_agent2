import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import openai
from openai import AsyncOpenAI

from app.core.exceptions import (
    AuthenticationException,
    ModelProviderException,
    RateLimitException,
    ServiceUnavailableException,
    ValidationException,
)
from app.telemetry.logging import app_logger


class OpenAIService:
    """SDK wrapper for OpenAI API with error normalization and privacy-safe logging."""

    def __init__(
        self,
        client: AsyncOpenAI,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        self.client = client
        self.default_model = default_model

    async def chat_raw(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        # Accept and ignore cache_system — kept for call-site compatibility
        cache_system: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Executes a chat completion request with latency tracking and token telemetry."""
        target_model = model or self.default_model

        # OpenAI: system prompt is the first message in the messages list
        final_messages: List[Dict[str, Any]] = []
        if system:
            final_messages.append({"role": "system", "content": system})
        final_messages.extend(messages)

        params: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": final_messages,
            "temperature": temperature,
        }

        if stop_sequences:
            params["stop"] = stop_sequences
        if tools:
            params["tools"] = tools
        if tool_choice is not None:
            params["tool_choice"] = tool_choice

        start_time = time.perf_counter()

        app_logger.info(
            "OpenAI request started | model={model} | message_count={count}",
            model=target_model,
            count=len(final_messages),
        )

        try:
            response = await self.client.chat.completions.create(**params)

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            prompt_tokens = getattr(response.usage, "prompt_tokens", 0) if hasattr(response, "usage") else 0
            completion_tokens = getattr(response.usage, "completion_tokens", 0) if hasattr(response, "usage") else 0
            finish_reason = response.choices[0].finish_reason if response.choices else None

            app_logger.info(
                "OpenAI request finished | model={model} | latency_ms={latency}ms"
                " | prompt_tokens={prompt} | completion_tokens={completion} | finish_reason={finish}",
                model=target_model,
                latency=latency_ms,
                prompt=prompt_tokens,
                completion=completion_tokens,
                finish=finish_reason,
            )
            return response

        except openai.BadRequestError as e:
            app_logger.error("OpenAI BadRequestError: {error}", error=str(e))
            raw = str(getattr(e, "message", str(e)))
            if "billing" in raw.lower() or "quota" in raw.lower() or "credit" in raw.lower():
                raise ServiceUnavailableException(
                    message="The AI service is temporarily unavailable. Please try again later."
                ) from e
            raise ValidationException(message="The request could not be processed. Please try again.") from e
        except openai.AuthenticationError as e:
            app_logger.error("OpenAI AuthenticationError: {error}", error=str(e))
            raise AuthenticationException() from e
        except openai.RateLimitError as e:
            app_logger.warning("OpenAI RateLimitError: {error}", error=str(e))
            raise RateLimitException() from e
        except openai.APIConnectionError as e:
            app_logger.error("OpenAI APIConnectionError: {error}", error=str(e))
            raise ServiceUnavailableException() from e
        except openai.APIError as e:
            app_logger.error("OpenAI APIError: {error}", error=str(e))
            raise ModelProviderException(message="The AI provider returned an error. Please try again.") from e
        except Exception as e:
            app_logger.error("Unexpected error in OpenAIService: {error}", error=str(e), exc_info=True)
            raise ModelProviderException(message="An unexpected error occurred while calling the AI service.") from e

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streams text deltas from OpenAI with exception mapping."""
        target_model = model or self.default_model

        final_messages: List[Dict[str, Any]] = []
        if system:
            final_messages.append({"role": "system", "content": system})
        final_messages.extend(messages)

        params: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": final_messages,
            "temperature": temperature,
            "stream": True,
        }

        if stop_sequences:
            params["stop"] = stop_sequences

        start_time = time.perf_counter()
        app_logger.info(
            "OpenAI stream started | model={model} | message_count={count}",
            model=target_model,
            count=len(final_messages),
        )

        try:
            stream = await self.client.chat.completions.create(**params)
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            app_logger.info(
                "OpenAI stream finished | model={model} | latency_ms={latency}ms",
                model=target_model,
                latency=latency_ms,
            )

        except openai.BadRequestError as e:
            app_logger.error("OpenAI Stream BadRequestError: {error}", error=str(e))
            raw = str(getattr(e, "message", str(e)))
            if "billing" in raw.lower() or "quota" in raw.lower() or "credit" in raw.lower():
                raise ServiceUnavailableException(
                    message="The AI service is temporarily unavailable. Please try again later."
                ) from e
            raise ValidationException(message="The request could not be processed. Please try again.") from e
        except openai.AuthenticationError as e:
            app_logger.error("OpenAI Stream AuthenticationError: {error}", error=str(e))
            raise AuthenticationException() from e
        except openai.RateLimitError as e:
            app_logger.warning("OpenAI Stream RateLimitError: {error}", error=str(e))
            raise RateLimitException() from e
        except openai.APIConnectionError as e:
            app_logger.error("OpenAI Stream ConnectionError: {error}", error=str(e))
            raise ServiceUnavailableException() from e
        except openai.APIError as e:
            app_logger.error("OpenAI Stream APIError: {error}", error=str(e))
            raise ModelProviderException(message="The AI provider returned an error. Please try again.") from e

    async def close(self) -> None:
        """Gracefully closes underlying client HTTP connection pools."""
        await self.client.close()
