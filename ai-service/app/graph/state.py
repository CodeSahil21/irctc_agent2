from typing import TypedDict


class GraphState(TypedDict, total=False):
    user_id: str
    message: str
    plan: list[str]
    result: str