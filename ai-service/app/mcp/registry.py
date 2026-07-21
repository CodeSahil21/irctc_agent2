# mcp/registry.py
import json
from typing import Any, Dict, Optional

from app.mcp.client import MCPClient
from app.mcp.discovery import MCPDiscovery
from app.mcp.normalizer import ToolResult
from app.telemetry.logging import app_logger
from langsmith import traceable


class MCPToolRegistry:
    """
    Dynamic tool registry backed by MCP discovery.

    Replaces the hardcoded TOOL_REGISTRY + execute_tool() in tools/registry.py.
    Tool schemas come from the MCP server at startup — nothing is hardcoded here.
    """

    def __init__(self, client: MCPClient, discovery: MCPDiscovery) -> None:
        self._client = client
        self._discovery = discovery

    @traceable(name="mcp_execute_tool", run_type="tool")
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_email: str,
        user_name: Optional[str] = None,
    ) -> str:
        """
        Execute a tool by name via MCP.
        Returns a JSON string in the same envelope format as the old execute_tool()
        so tool_executor_node needs minimal changes.
        """
        if not self._discovery.is_known(tool_name):
            app_logger.warning("Unknown tool requested | tool={tool}", tool=tool_name)
            return json.dumps({
                "status": "error",
                "error_type": "UNKNOWN_TOOL",
                "message": f"Tool '{tool_name}' is not registered on the MCP server.",
            })

        result: ToolResult = await self._client.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            user_email=user_email,
            user_name=user_name,
        )

        return json.dumps(result.to_dict())

    def get_schemas_for_claude(self) -> list:
        """
        Return tool schemas in Anthropic tool-use format.
        Used by tool_planner_node to give Claude the live tool list.
        """
        return self._discovery.get_tools()

    def is_known(self, tool_name: str) -> bool:
        return self._discovery.is_known(tool_name)
