from app.graph.tool_preconditions import TOOL_PRECONDITIONS

HUMAN_APPROVAL_NODES: set = {
    name for name, p in TOOL_PRECONDITIONS.items() if p.requires_confirmation
}
