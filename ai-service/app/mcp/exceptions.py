

class MCPError(Exception):
    """Base for all MCP errors."""
    def __init__(self, message: str, retryable: bool = False):
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class MCPConnectionError(MCPError):
    def __init__(self, message: str = "Could not connect to MCP server"):
        super().__init__(message, retryable=True)


class MCPTimeoutError(MCPError):
    def __init__(self, message: str = "MCP request timed out"):
        super().__init__(message, retryable=True)


class MCPSessionError(MCPError):
    def __init__(self, message: str = "MCP session is invalid or expired"):
        super().__init__(message, retryable=True)


class MCPToolNotFoundError(MCPError):
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found on MCP server", retryable=False)


class MCPInvalidResponseError(MCPError):
    def __init__(self, message: str = "MCP server returned an invalid response"):
        super().__init__(message, retryable=False)


class MCPAuthError(MCPError):
    def __init__(self, message: str = "MCP authentication failed — missing or invalid user headers"):
        super().__init__(message, retryable=False)


class MCPSchemaError(MCPError):
    def __init__(self, message: str = "Tool arguments do not match the expected schema"):
        super().__init__(message, retryable=False)
