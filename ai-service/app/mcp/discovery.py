from typing import Any, Dict, List, Optional

from app.mcp.client import MCPClient
from app.telemetry.logging import app_logger

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

        self._tools = [self._normalize_tool(t) for t in raw_tools]
        # Index by the function name inside the OpenAI wrapper
        self._by_name = {t["function"]["name"]: t for t in self._tools}

        app_logger.info(
            "Tool discovery complete | tools={names}",
            names=list(self._by_name.keys()),
        )

    async def refresh(self) -> None:
        """Re-fetch the tool list from MCP and replace the cached registry."""
        await self.discover()

    @staticmethod
    def _normalize_tool(tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert MCP tool schema into OpenAI function-calling format:
        {"type": "function", "function": {"name", "description", "parameters"}}
        """
        raw_schema = tool.get("input_schema") or tool.get("inputSchema", {})

        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": raw_schema,
            },
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return all cached tool schemas (OpenAI function-calling format)."""
        return self._tools

    def has_tools(self) -> bool:
        return bool(self._by_name)

    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Return the schema dict for a tool by name.
        Returns a flattened dict with 'input_schema' key so slot_filler_node
        can read input_schema.properties / input_schema.required as before.
        """
        wrapped = self._by_name.get(name)
        if wrapped is None:
            return None
        fn = wrapped["function"]
        return {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {}),
        }

    def is_known(self, name: str) -> bool:
        return name in self._by_name

    @property
    def tool_count(self) -> int:
        return len(self._tools)
