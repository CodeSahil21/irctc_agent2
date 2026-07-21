# mcp/discovery.py
from typing import Any, Dict, List, Optional

from app.mcp.client import MCPClient
from app.telemetry.logging import app_logger

# Discovery uses a system-level probe user — no real user data is sent
_PROBE_EMAIL = "system@irctc-agent.internal"


class MCPDiscovery:
    """
    Discovers and caches tool schemas from the MCP server at startup.

    After discover() is called, the cached registry is available via
    get_tools() and get_tool_schema(name).
    """

    def __init__(self, client: MCPClient) -> None:
        self._client = client
        self._tools: List[Dict[str, Any]] = []
        self._by_name: Dict[str, Dict[str, Any]] = {}

    async def discover(self) -> None:
        """
        Fetch tool list from MCP server and populate the cache.
        Called once during application startup.
        """
        raw_tools = await self._client.list_tools(user_email=_PROBE_EMAIL)

        self._tools = raw_tools
        self._by_name = {t["name"]: t for t in raw_tools}

        app_logger.info(
            "Tool discovery complete | tools={names}",
            names=list(self._by_name.keys()),
        )

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return all cached tool schemas (Anthropic-compatible format)."""
        return self._tools

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        return self._by_name.get(name)

    def is_known(self, name: str) -> bool:
        return name in self._by_name

    @property
    def tool_count(self) -> int:
        return len(self._tools)
