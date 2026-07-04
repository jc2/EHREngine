def mcp_dump(result):
    """Serialize MCP Pydantic tool results for dict-style test assertions."""
    if hasattr(result, "model_dump"):
        return result.model_dump(exclude_none=True)
    return result
