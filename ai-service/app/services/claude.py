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
        client: AsyncAnthropic,  # ✅ Accept pre-initialized client instance from app state
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
            params["system"] = system
        if stop_sequences:
            params["stop_sequences"] = stop_sequences
        if tools:
            params["tools"] = tools

        start_time = time.perf_counter()
        
        # Privacy-Safe Logging: Log request start with metadata only
        app_logger.info(
            f"Claude request started | model={target_model} | message_count={len(messages)}"
        )

        try:
            response = await self.client.messages.create(**params)

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            input_tokens = getattr(response.usage, "input_tokens", 0) if hasattr(response, "usage") else 0
            output_tokens = getattr(response.usage, "output_tokens", 0) if hasattr(response, "usage") else 0

            # Telemetry Log: Latency + Token Usage
            app_logger.info(
                f"Claude request finished | model={target_model} | latency_ms={latency_ms}ms "
                f"| input_tokens={input_tokens} | output_tokens={output_tokens} | stop_reason={getattr(response, 'stop_reason', None)}"
            )
            return response

        except anthropic.BadRequestError as e:
            app_logger.error(f"Claude BadRequestError: {str(e)}")
            raise ValidationException(message=str(e.message)) from e
        except anthropic.AuthenticationError as e:
            app_logger.error(f"Claude AuthenticationError: {str(e)}")
            raise AuthenticationException() from e
        except anthropic.RateLimitError as e:
            app_logger.warning(f"Claude RateLimitError: {str(e)}")
            raise RateLimitException() from e
        except anthropic.APIConnectionError as e:
            app_logger.error(f"Claude APIConnectionError: {str(e)}")
            raise ServiceUnavailableException() from e
        except anthropic.APIError as e:
            app_logger.error(f"Claude Provider APIError: {str(e)}")
            raise ModelProviderException(message=str(e.message)) from e
        except Exception as e:
            app_logger.error(f"Unexpected error in ClaudeService: {str(e)}", exc_info=True)
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
            f"Claude stream started | model={target_model} | message_count={len(messages)}"
        )

        try:
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            app_logger.info(
                f"Claude stream finished | model={target_model} | latency_ms={latency_ms}ms"
            )

        except anthropic.BadRequestError as e:
            app_logger.error(f"Claude Stream BadRequestError: {str(e)}")
            raise ValidationException(message=str(e.message)) from e
        except anthropic.AuthenticationError as e:
            app_logger.error(f"Claude Stream AuthenticationError: {str(e)}")
            raise AuthenticationException() from e
        except anthropic.RateLimitError as e:
            app_logger.warning(f"Claude Stream RateLimitError: {str(e)}")
            raise RateLimitException() from e
        except anthropic.APIConnectionError as e:
            app_logger.error(f"Claude Stream ConnectionError: {str(e)}")
            raise ServiceUnavailableException() from e
        except anthropic.APIError as e:
            app_logger.error(f"Claude Stream APIError: {str(e)}")
            raise ModelProviderException(message=str(e.message)) from e

    async def close(self) -> None:
        """Gracefully closes underlying client HTTP connection pools."""
        await self.client.close()