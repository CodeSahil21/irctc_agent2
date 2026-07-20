def adapt_mcp_request(tool_name: str, arguments: dict, user_context: dict) -> dict:
    return {"tool": tool_name, "arguments": arguments, "user": user_context}