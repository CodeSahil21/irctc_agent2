# mcp/transport.py
import httpx
from typing import Any, Dict, Optional

from app.mcp.exceptions import (
    MCPAuthError,
    MCPConnectionError,
    MCPInvalidResponseError,
    MCPSessionError,
    MCPTimeoutError,
)
from app.telemetry.logging import app_logger


class MCPTransport:
    """
    Async HTTP transport for the MCP Streamable HTTP protocol.

    Responsibilities:
    - Send JSON-RPC 2.0 requests to POST /mcp
    - Attach x-user-email, x-user-name, mcp-session-id headers
    - Return the raw parsed JSON response
    - Map HTTP / network errors to MCP exceptions
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        )
        app_logger.info("MCPTransport connected | base_url={url}", url=self.base_url)

    async def disconnect(self) -> None:
        if not self._client:
            return
        try:
            await self._client.aclose()
            app_logger.info("MCPTransport disconnected")
        finally:
            self._client = None

    async def send(
        self,
        payload: Dict[str, Any],
        session_id: Optional[str],
        user_email: str,
        user_name: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Send a JSON-RPC payload to POST /mcp.

        Returns:
            (response_body, new_session_id_if_any)
        """
        if self._client is None:
            raise MCPConnectionError("Transport is not connected")

        headers: Dict[str, str] = {"x-user-email": user_email}
        if user_name:
            headers["x-user-name"] = user_name
        if session_id:
            headers["mcp-session-id"] = session_id

        try:
            response = await self._client.post("/mcp", json=payload, headers=headers)
        except httpx.TimeoutException as e:
            raise MCPTimeoutError() from e
        except httpx.ConnectError as e:
            raise MCPConnectionError(f"Connection refused: {e}") from e
        except httpx.NetworkError as e:
            raise MCPConnectionError(f"Network error: {e}") from e

        # Map HTTP status codes
        if response.status_code == 401:
            raise MCPAuthError()
        if response.status_code == 403:
            raise MCPSessionError("Session does not belong to this user")
        if response.status_code == 404:
            raise MCPSessionError("Session not found")
        if response.status_code >= 500:
            raise MCPInvalidResponseError(f"MCP server error: HTTP {response.status_code}")

        try:
            body = response.json()
        except (ValueError, Exception) as e:
            raise MCPInvalidResponseError(f"Non-JSON response from MCP server: {e}") from e

        returned_session_id = response.headers.get("mcp-session-id")
        return body, returned_session_id

    async def delete_session(self, session_id: str) -> None:
        """Send DELETE /mcp to close the server-side session."""
        if self._client is None:
            return
        try:
            await self._client.request("DELETE", "/mcp", headers={"mcp-session-id": session_id})
        except httpx.HTTPError as exc:
            app_logger.warning("MCP session cleanup failed | session_id={session_id} | error={error}", session_id=session_id, error=str(exc))
