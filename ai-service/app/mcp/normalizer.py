# mcp/normalizer.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """
    Normalized result envelope returned by every MCP tool call.
    The rest of the application only ever sees this — never raw JSON-RPC.
    """
    success: bool
    data: Any = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    tool_name: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        if self.success:
            return {"status": "success", "data": self.data}
        return {
            "status": "error",
            "error_type": self.error_type or "UNKNOWN",
            "message": self.error_message or "Unknown error",
        }


def normalize_mcp_response(
    body: Dict[str, Any],
    tool_name: str,
    latency_ms: float,
) -> ToolResult:
    """
    Parse a raw JSON-RPC 2.0 response body into a ToolResult.

    MCP success shape:
        { "result": { "content": [ { "type": "text", "text": "<json>" } ] } }

    MCP error shape:
        { "error": { "code": -32000, "message": "..." } }
    """
    import json

    # JSON-RPC error
    if "error" in body:
        err = body["error"]
        code = err.get("code", -1)
        msg = err.get("message", "MCP server error")
        error_type = _map_jsonrpc_error_code(code)
        return ToolResult(
            success=False,
            error_type=error_type,
            error_message=msg,
            tool_name=tool_name,
            latency_ms=latency_ms,
        )

    result = body.get("result")
    if result is None:
        return ToolResult(
            success=False,
            error_type="INVALID_RESPONSE",
            error_message="MCP response missing 'result' field",
            tool_name=tool_name,
            latency_ms=latency_ms,
        )

    # Extract data from content array (Streamable HTTP MCP format)
    content: List[Dict[str, Any]] = result.get("content", [])
    parsed_data: Any = None

    for block in content:
        if block.get("type") == "text":
            raw_text = block.get("text", "")
            try:
                parsed_data = json.loads(raw_text)
            except (json.JSONDecodeError, TypeError):
                parsed_data = raw_text
            break

    if parsed_data is None:
        # Some tools return empty content (e.g. delete operations)
        parsed_data = result

    return ToolResult(
        success=True,
        data=parsed_data,
        tool_name=tool_name,
        latency_ms=latency_ms,
    )


def _map_jsonrpc_error_code(code: int) -> str:
    mapping = {
        -32700: "PARSE_ERROR",
        -32600: "INVALID_REQUEST",
        -32601: "METHOD_NOT_FOUND",
        -32602: "INVALID_PARAMS",
        -32603: "INTERNAL_ERROR",
    }
    return mapping.get(code, "MCP_ERROR")
