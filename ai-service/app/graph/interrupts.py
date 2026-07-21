# graph/interrupts.py
# Single source of truth for which tools require human approval lives in
# tool_preconditions.py. This module derives the set from there so the two
# never drift out of sync.
from app.graph.tool_preconditions import TOOL_PRECONDITIONS

HUMAN_APPROVAL_NODES: set = {
    name for name, p in TOOL_PRECONDITIONS.items() if p.requires_confirmation
}
