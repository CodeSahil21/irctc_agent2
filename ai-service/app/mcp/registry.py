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

    Tool schemas come from the MCP server at startup — nothing is hardcoded here.
    """

    def __init__(self, client: MCPClient, discovery: MCPDiscovery) -> None:
        self._client = client
        self._discovery = discovery

    async def _ensure_discovery(self) -> None:
        """Refresh the tool cache if startup discovery missed tools."""
        if self._discovery.has_tools():
            return
        app_logger.warning("Tool cache empty — refreshing MCP discovery")
        await self._discovery.refresh()

    def _clean_and_validate_args(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        1. Strips extra hallucinated arguments not in properties.
        2. Checks for missing required arguments.
        Returns: (cleaned_args, error_message)
        """
        schema_info = self._discovery.get_tool_schema(tool_name)
        if not schema_info:
            return arguments, None

        input_schema = schema_info.get("input_schema", {})
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        if properties:
            cleaned_args = {k: v for k, v in arguments.items() if k in properties}
        else:
            cleaned_args = dict(arguments)

        missing = [field for field in required_fields if field not in cleaned_args]
        if missing:
            return cleaned_args, f"Missing required parameter(s) for '{tool_name}': {', '.join(missing)}"

        return cleaned_args, None

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
        Returns a JSON string in the same envelope format as before.
        """
        await self._ensure_discovery()

        if not self._discovery.is_known(tool_name):
            await self._discovery.refresh()

        if not self._discovery.is_known(tool_name):
            app_logger.warning("Unknown tool requested | tool={tool}", tool=tool_name)
            return json.dumps({
                "status": "error",
                "error_type": "UNKNOWN_TOOL",
                "message": f"Tool '{tool_name}' is not registered on the MCP server.",
            })

        cleaned_args, error_msg = self._clean_and_validate_args(tool_name, arguments)
        if error_msg:
            app_logger.warning("Tool parameter error | tool={tool} | error={err}", tool=tool_name, err=error_msg)
            return json.dumps({
                "status": "error",
                "error_type": "INVALID_PARAMETERS",
                "message": error_msg,
            })

        result: ToolResult = await self._client.call_tool(
            tool_name=tool_name,
            arguments=cleaned_args,
            user_email=user_email,
            user_name=user_name,
        )

        return json.dumps(result.to_dict())

    def get_tool_schemas(self) -> list:
        """
        Return tool schemas in OpenAI function-calling format.
        Used by tool_planner_node to pass the live tool list to the LLM.
        """
        return self._discovery.get_tools()

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Return the schema dictionary for a specific tool (flattened, with input_schema key)."""
        return self._discovery.get_tool_schema(tool_name)

    def is_known(self, tool_name: str) -> bool:
        return self._discovery.is_known(tool_name)
