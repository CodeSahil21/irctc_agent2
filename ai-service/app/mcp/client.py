# app/mcp/client.py
import asyncio
import time
from typing import Any, Dict, List, Optional

from app.mcp.exceptions import (
    MCPConnectionError,
    MCPError,
    MCPInvalidResponseError,
    MCPSessionError,
    MCPToolNotFoundError,
)
from app.mcp.normalizer import ToolResult, normalize_mcp_response
from app.mcp.session import MCPSession
from app.mcp.transport import MCPTransport
from app.telemetry.logging import app_logger

# Max retries for transient failures
_MAX_RETRIES = 3
_RETRY_BACKOFF = [0.5, 1.0, 2.0]  # seconds
_MCP_PROTOCOL_VERSION = "2024-11-05"  # Standardized protocol version


class MCPClient:
    """
    High-level MCP client.

    Responsibilities:
    - Maintain one MCPSession per user (keyed by user_email)
    - Execute tool calls via JSON-RPC over MCPTransport
    - Retry transient failures with backoff
    - Reset sessions on session errors
    - Track per-session metrics
    """

    def __init__(self, transport: MCPTransport) -> None:
        self._transport = transport
        self._sessions: Dict[str, MCPSession] = {}
        self._request_counter: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._transport.connect()
        app_logger.info("MCPClient connected")

    async def disconnect(self) -> None:
        for session in self._sessions.values():
            if session.session_id:
                await self._transport.delete_session(session.session_id)
        self._sessions.clear()
        await self._transport.disconnect()
        app_logger.info("MCPClient disconnected")

    # ── Session Management ────────────────────────────────────────────

    def _get_or_create_session(self, user_email: str, user_name: Optional[str]) -> MCPSession:
        if user_email not in self._sessions:
            self._sessions[user_email] = MCPSession(
                user_email=user_email,
                user_name=user_name,
            )
        return self._sessions[user_email]

    def _reset_session(self, user_email: str) -> None:
        if user_email in self._sessions:
            old = self._sessions[user_email]
            self._sessions[user_email] = MCPSession(
                user_email=old.user_email,
                user_name=old.user_name,
            )
            app_logger.warning("MCPClient session reset | user={user}", user=user_email)

    def get_session_health(self) -> List[Dict[str, Any]]:
        return [s.health_summary() for s in self._sessions.values()]

    # ── Tool Discovery ────────────────────────────────────────────────

    async def list_tools(self, user_email: str, user_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Call tools/list on the MCP server and return the raw tool schema list.
        Used once at startup by MCPDiscovery.
        """
        await self._ensure_initialized(user_email, user_name)
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}}
        body, _ = await self._raw_send(payload, user_email, user_name)

        result = body.get("result", {})
        tools = result.get("tools", [])
        app_logger.info("MCPClient listed {count} tools", count=len(tools))
        return tools

    # ── Tool Execution ────────────────────────────────────────────────

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_email: str,
        user_name: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool on the MCP server with automatic retry on transient errors.
        Always returns a ToolResult — never raises.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        last_error: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES):
            await self._ensure_initialized(user_email, user_name)
            start = time.perf_counter()
            try:
                body, _ = await self._raw_send(payload, user_email, user_name)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)

                result = normalize_mcp_response(body, tool_name, latency_ms)

                session = self._get_or_create_session(user_email, user_name)
                if result.success:
                    session.record_success()
                    app_logger.info(
                        "Tool call succeeded | tool={tool} | latency={ms}ms",
                        tool=tool_name, ms=latency_ms,
                    )
                else:
                    session.record_failure()
                    app_logger.warning(
                        "Tool call returned error | tool={tool} | error={err}",
                        tool=tool_name, err=result.error_message,
                    )
                return result

            except MCPToolNotFoundError as e:
                # Non-retryable
                return ToolResult(
                    success=False,
                    error_type="TOOL_NOT_FOUND",
                    error_message=e.message,
                    tool_name=tool_name,
                )

            except (MCPSessionError, MCPConnectionError) as e:
                last_error = e
                self._reset_session(user_email)
                app_logger.warning(
                    "Session reset on attempt {attempt} | tool={tool} | error={err}",
                    attempt=attempt + 1, tool=tool_name, err=str(e),
                )

            except MCPError as e:
                last_error = e
                if not e.retryable:
                    return ToolResult(
                        success=False,
                        error_type=type(e).__name__,
                        error_message=e.message,
                        tool_name=tool_name,
                    )
                app_logger.warning(
                    "Retryable MCP error on attempt {attempt} | tool={tool} | error={err}",
                    attempt=attempt + 1, tool=tool_name, err=str(e),
                )

            except Exception as e:
                last_error = e
                app_logger.error(
                    "Unexpected error on attempt {attempt} | tool={tool} | error={err}",
                    attempt=attempt + 1, tool=tool_name, err=str(e),
                )

            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_BACKOFF[attempt])

        session = self._get_or_create_session(user_email, user_name)
        session.record_failure()
        return ToolResult(
            success=False,
            error_type="MAX_RETRIES_EXCEEDED",
            error_message=f"Tool '{tool_name}' failed after {_MAX_RETRIES} attempts: {last_error}",
            tool_name=tool_name,
        )

    # ── Internal ──────────────────────────────────────────────────────

    async def _raw_send(
        self,
        payload: Dict[str, Any],
        user_email: str,
        user_name: Optional[str],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        session = self._get_or_create_session(user_email, user_name)
        body, new_session_id = await self._transport.send(
            payload=payload,
            session_id=session.session_id,
            user_email=user_email,
            user_name=user_name,
        )
        if new_session_id:
            session.session_id = new_session_id
        return body, new_session_id

    async def _ensure_initialized(self, user_email: str, user_name: Optional[str]) -> None:
        session = self._get_or_create_session(user_email, user_name)
        if session.session_id:
            return

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": _MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "ai-service",
                    "version": "1.0.0",
                },
            },
        }
        body, _ = await self._raw_send(payload, user_email, user_name)

        if not session.session_id:
            app_logger.warning("MCP initialize response did not set mcp-session-id header | user={user}", user=user_email)

        # Notify the server initialization is complete (JSON-RPC notification - NO id field)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        try:
            await self._raw_send(initialized_notification, user_email, user_name)
        except Exception as err:
            app_logger.warning("notifications/initialized notification ignored | err={err}", err=str(err))

    def _next_id(self) -> int:
        self._request_counter += 1
        return self._request_counter