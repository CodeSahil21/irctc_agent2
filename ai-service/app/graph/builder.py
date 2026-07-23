from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.graph.edges import (
    route_after_human_approval,
    route_after_intent,
    route_after_ranking,
    route_after_reflection,
    route_after_slot_filler,
    route_after_tool_executor,
    route_after_tool_planner,
)
from app.graph.nodes import (
    human_approval_node,
    intent_node,
    ranking_node,
    reflection_node,
    response_node,
    slot_filler_node,
    tool_executor_node,
    tool_planner_node,
)
from app.graph.state import TravelState
from app.mcp.registry import MCPToolRegistry
from app.services.openai_service import OpenAIService


def create_agent_graph(
    llm_service: OpenAIService,
    mcp_registry: MCPToolRegistry = None,
    checkpointer: MemorySaver = None,
):
    """
    Build and compile the full IRCTC agent graph.

    Flow:
        START
          → intent_node
          → slot_filler_node
          → tool_planner_node
          → human_approval_node  (destructive actions only)
          → tool_executor_node   (loops; runs parallel groups automatically)
          → ranking_node         (search intents only — pure Python sort)
          → reflection_node      (data-heavy intents — LLM quality check)
          → response_node
          → END

    Reflection failure routes back to tool_planner_node with feedback (max 1 retry).
    """
    builder = StateGraph(TravelState)

    # ── Nodes ─────────────────────────────────────────────────────────
    builder.add_node("intent_node", partial(intent_node, llm_service=llm_service))
    builder.add_node("slot_filler_node", partial(slot_filler_node, mcp_registry=mcp_registry))
    builder.add_node("tool_planner_node", partial(tool_planner_node, llm_service=llm_service, mcp_registry=mcp_registry))
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("tool_executor_node", partial(tool_executor_node, mcp_registry=mcp_registry))
    builder.add_node("ranking_node", ranking_node)
    builder.add_node("reflection_node", partial(reflection_node, llm_service=llm_service))
    builder.add_node("response_node", partial(response_node, llm_service=llm_service))

    # ── Edges ─────────────────────────────────────────────────────────
    builder.add_edge(START, "intent_node")

    builder.add_conditional_edges(
        "intent_node",
        route_after_intent,
        {
            "response_node": "response_node",
            "slot_filler_node": "slot_filler_node",
            "tool_executor_node": "tool_executor_node",
        },
    )

    builder.add_conditional_edges(
        "slot_filler_node",
        route_after_slot_filler,
        {"response_node": "response_node", "tool_planner_node": "tool_planner_node"},
    )

    builder.add_conditional_edges(
        "tool_planner_node",
        route_after_tool_planner,
        {
            "response_node": "response_node",
            "human_approval_node": "human_approval_node",
            "tool_executor_node": "tool_executor_node",
        },
    )

    builder.add_conditional_edges(
        "human_approval_node",
        route_after_human_approval,
        {"tool_executor_node": "tool_executor_node", "response_node": "response_node"},
    )

    builder.add_conditional_edges(
        "tool_executor_node",
        route_after_tool_executor,
        {
            "tool_executor_node": "tool_executor_node",
            "ranking_node": "ranking_node",
            "reflection_node": "reflection_node",
            "response_node": "response_node",
        },
    )

    builder.add_conditional_edges(
        "ranking_node",
        route_after_ranking,
        {"reflection_node": "reflection_node", "response_node": "response_node"},
    )

    builder.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {"response_node": "response_node", "tool_planner_node": "tool_planner_node"},
    )

    builder.add_edge("response_node", END)

    return builder.compile(checkpointer=checkpointer)


def get_graph_ascii(agent_graph) -> str:
    return agent_graph.get_graph().draw_ascii()
