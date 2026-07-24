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
        self._schema_by_name: Dict[str, Dict[str, Any]] = {}  # pre-built at discover()

    async def discover(self) -> None:
        """
        Fetch tool list from MCP server and populate the cache.
        Called once during application startup.
        """
        raw_tools = await self._client.list_tools(user_email=_PROBE_EMAIL)

        self._tools = [self._normalize_tool(t) for t in raw_tools]
        # Index by the function name inside the OpenAI wrapper
        self._by_name = {t["function"]["name"]: t for t in self._tools}
        # Pre-build flattened schema dicts so get_tool_schema() is a zero-cost
        # dict lookup instead of constructing a new object on every call.
        self._schema_by_name: Dict[str, Dict[str, Any]] = {
            name: {
                "name": name,
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {}),
            }
            for name, t in self._by_name.items()
        }

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
        Return the pre-built flattened schema dict for a tool by name.
        Zero-cost dict lookup — the object is built once at discovery time.
        """
        return self._schema_by_name.get(name)

    def is_known(self, name: str) -> bool:
        return name in self._by_name

    @property
    def tool_count(self) -> int:
        return len(self._tools)
