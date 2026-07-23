# graph/builder.py
from functools import partial

from langgraph.graph import END, START, StateGraph

from app.graph.edges import (
    route_after_agent,
    route_after_human_approval,
    route_after_reflection,
    route_after_tool_executor,
)
from app.graph.nodes.agent_node import agent_node
from app.graph.nodes.human_approval_node import human_approval_node
from app.graph.nodes.reflection_node import reflection_node
from app.graph.nodes.tool_executor_node import tool_executor_node
from app.graph.state import TravelState


def create_agent_graph(llm_service, mcp_registry=None, checkpointer=None):
    """
    Compile and return the IRCTC agent graph.

    Flow:
        START → agent_node  ⇄  tool_executor_node
                    ↓ (destructive call proposed)
             human_approval_node → tool_executor_node
                    ↓ (no tool calls = final answer)
             reflection_node (optional, capped at 1 retry) → END

    The model reads the live MCP tool schema every turn — no hardcoded tool
    names in routing or planning logic.
    """
    builder = StateGraph(TravelState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    builder.add_node(
        "agent_node",
        partial(agent_node, llm_service=llm_service, mcp_registry=mcp_registry),
    )
    builder.add_node(
        "tool_executor_node",
        partial(tool_executor_node, mcp_registry=mcp_registry),
    )
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node(
        "reflection_node",
        partial(reflection_node, llm_service=llm_service),
    )

    # ── Edges ──────────────────────────────────────────────────────────────
    builder.add_edge(START, "agent_node")

    builder.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {
            "tool_executor_node":   "tool_executor_node",
            "human_approval_node":  "human_approval_node",
            "reflection_node":      "reflection_node",
            "END":                  END,
        },
    )

    builder.add_conditional_edges(
        "human_approval_node",
        route_after_human_approval,
        {
            "tool_executor_node": "tool_executor_node",
            "agent_node":         "agent_node",
        },
    )

    builder.add_conditional_edges(
        "tool_executor_node",
        route_after_tool_executor,
        {
            "agent_node": "agent_node",
        },
    )

    builder.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {
            "agent_node": "agent_node",
            "END":        END,
        },
    )

    return builder.compile(checkpointer=checkpointer)


def get_graph_ascii(agent_graph) -> str:
    return agent_graph.get_graph().draw_ascii()
