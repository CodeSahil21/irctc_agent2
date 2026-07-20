from collections.abc import Callable


TOOL_REGISTRY: dict[str, Callable[..., object]] = {}


def register_tool(name: str, handler: Callable[..., object]) -> None:
    TOOL_REGISTRY[name] = handler