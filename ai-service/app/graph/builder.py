from .state import GraphState


def build_graph() -> dict[str, str]:
    return {"status": "graph-not-built-yet", "state": GraphState.__name__}