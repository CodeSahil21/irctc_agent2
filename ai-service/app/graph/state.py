# graph/state.py
from typing import Annotated,Optional,TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages  # 👈 Import directly from langgraph


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    intent: Optional[str]
    needs_tool: Optional[bool]