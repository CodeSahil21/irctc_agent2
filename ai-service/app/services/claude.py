import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import anthropic
from anthropic import AsyncAnthropic

from app.core.exceptions import (
    AuthenticationException,
    ModelProviderException,
    RateLimitException,
    ServiceUnavailableException,
    ValidationException,
)
from app.telemetry.logging import app_logger


class ClaudeService:
    """SDK wrapper for Anthropic API with error normalization and privacy-safe logging."""

    def __init__(
        self,
        client: AsyncAnthropic,
        default_model: str = "claude-haiku-4-5",
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
        cache_system: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Executes a message request with latency tracking and token telemetry."""
        target_model = model or self.default_model
        params: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        if system:
            if cache_system:
                params["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                params["system"] = system
        if stop_sequences:
            params["stop_sequences"] = stop_sequences
        if tools:
            params["tools"] = tools

        start_time = time.perf_counter()

        app_logger.info(
            "Claude request started | model={model} | message_count={count}",
            model=target_model,
            count=len(messages),
        )

        try:
            response = await self.client.messages.create(**params)

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            input_tokens = getattr(response.usage, "input_tokens", 0) if hasattr(response, "usage") else 0
            output_tokens = getattr(response.usage, "output_tokens", 0) if hasattr(response, "usage") else 0

            app_logger.info(
                "Claude request finished | model={model} | latency_ms={latency}ms"
                " | input_tokens={input} | output_tokens={output} | stop_reason={stop}",
                model=target_model,
                latency=latency_ms,
                input=input_tokens,
                output=output_tokens,
                stop=getattr(response, "stop_reason", None),
            )
            return response

        except anthropic.BadRequestError as e:
            app_logger.error("Claude BadRequestError: {error}", error=str(e))
            raw = str(getattr(e, "message", str(e)))
            # Billing / credit-balance errors come back as 400 BadRequestError.
            # Never surface raw API messages (they contain account info) to the caller.
            if "credit balance" in raw.lower() or "billing" in raw.lower():
                raise ServiceUnavailableException(
                    message="The AI service is temporarily unavailable. Please try again later."
                ) from e
            raise ValidationException(message="The request could not be processed. Please try again.") from e
        except anthropic.AuthenticationError as e:
            app_logger.error("Claude AuthenticationError: {error}", error=str(e))
            raise AuthenticationException() from e
        except anthropic.RateLimitError as e:
            app_logger.warning("Claude RateLimitError: {error}", error=str(e))
            raise RateLimitException() from e
        except anthropic.APIConnectionError as e:
            app_logger.error("Claude APIConnectionError: {error}", error=str(e))
            raise ServiceUnavailableException() from e
        except anthropic.APIError as e:
            app_logger.error("Claude Provider APIError: {error}", error=str(e))
            raise ModelProviderException(message="The AI provider returned an error. Please try again.") from e
        except Exception as e:
            app_logger.error("Unexpected error in ClaudeService: {error}", error=str(e), exc_info=True)
            raise ModelProviderException(message="An unexpected error occurred while calling Claude.") from e

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
        """Streams text deltas from Claude with exception mapping."""
        target_model = model or self.default_model
        params: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        if system:
            params["system"] = system
        if stop_sequences:
            params["stop_sequences"] = stop_sequences

        start_time = time.perf_counter()
        app_logger.info(
            "Claude stream started | model={model} | message_count={count}",
            model=target_model,
            count=len(messages),
        )

        try:
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            app_logger.info(
                "Claude stream finished | model={model} | latency_ms={latency}ms",
                model=target_model,
                latency=latency_ms,
            )

        except anthropic.BadRequestError as e:
            app_logger.error("Claude Stream BadRequestError: {error}", error=str(e))
            raw = str(getattr(e, "message", str(e)))
            if "credit balance" in raw.lower() or "billing" in raw.lower():
                raise ServiceUnavailableException(
                    message="The AI service is temporarily unavailable. Please try again later."
                ) from e
            raise ValidationException(message="The request could not be processed. Please try again.") from e
        except anthropic.AuthenticationError as e:
            app_logger.error("Claude Stream AuthenticationError: {error}", error=str(e))
            raise AuthenticationException() from e
        except anthropic.RateLimitError as e:
            app_logger.warning("Claude Stream RateLimitError: {error}", error=str(e))
            raise RateLimitException() from e
        except anthropic.APIConnectionError as e:
            app_logger.error("Claude Stream ConnectionError: {error}", error=str(e))
            raise ServiceUnavailableException() from e
        except anthropic.APIError as e:
            app_logger.error("Claude Stream APIError: {error}", error=str(e))
            raise ModelProviderException(message="The AI provider returned an error. Please try again.") from e

    async def close(self) -> None:
        """Gracefully closes underlying client HTTP connection pools."""
        await self.client.close()