# graph/builder.py
from functools import partial
from langgraph.graph import StateGraph, START, END

from app.services.claude import ClaudeService
from app.graph.state import AgentState
from app.graph.nodes import planner_node, response_node
from app.graph.edges import route_after_planner


# Placeholder node until Phase 5 MCP integration
async def tool_placeholder(state: AgentState) -> dict:
    return {}


def create_agent_graph(claude_service: ClaudeService):
    """
    Factory function to build and compile the LangGraph application 
    with injected ClaudeService dependencies.
    """
    # 1. Initialize State Graph
    builder = StateGraph(AgentState)

    # 2. Pre-bind ClaudeService into node signatures
    bound_planner = partial(planner_node, claude_service=claude_service)
    bound_response = partial(response_node, claude_service=claude_service)

    # 3. Register Nodes
    builder.add_node("planner_node", bound_planner)
    builder.add_node("response_node", bound_response)
    builder.add_node("tool_placeholder", tool_placeholder)

    # 4. Add Graph Edges
    builder.add_edge(START, "planner_node")

    # Conditional edge branching based on needs_tool flag
    builder.add_conditional_edges(
        "planner_node",
        route_after_planner,
        {
            "tool_placeholder": "tool_placeholder",
            "response_node": "response_node",
        },
    )

    builder.add_edge("tool_placeholder", "response_node")
    builder.add_edge("response_node", END)

    # 5. Compile Application
    return builder.compile()


def get_graph_ascii(agent_graph):
    """Generates an ASCII visualization of the graph flow."""
    return agent_graph.get_graph().draw_ascii()