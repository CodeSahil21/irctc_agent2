from app.graph.nodes.reflection_node import reflection_node
from app.graph.nodes.response_node import _ground_response


class ExplodingClaude:
    """Fails the test if the reflection pre-gate ever calls the model."""

    async def chat_raw(self, *args, **kwargs):
        raise AssertionError("Claude must not be called when tools already failed")


async def test_reflection_pregate_fails_on_errors():
    out = await reflection_node(
        {"user_goal": "book", "errors": ["book_ticket: INVALID_PARAMETERS"], "tool_history": []},
        claude_service=ExplodingClaude(),
    )
    assert out["reflection_passed"] is False
    assert out["reflection_required"] is False
    assert "INVALID_PARAMETERS" in out["reflection_feedback"]


async def test_reflection_pregate_fails_on_failed_tool_status():
    out = await reflection_node(
        {
            "user_goal": "check",
            "errors": [],
            "tool_history": [{"tool": "get_fare", "status": "failed"}],
        },
        claude_service=ExplodingClaude(),
    )
    assert out["reflection_passed"] is False


def test_ground_response_redacts_ungrounded_pnr():
    reply = "Your ticket is booked. PNR: 9999999999"
    out = _ground_response(reply, {"booking": {}, "travel": {}, "tool_results": {}})
    assert "9999999999" not in out
    assert "[PNR unavailable]" in out


def test_ground_response_keeps_grounded_pnr():
    state = {"booking": {"pnr": "1234567890"}, "travel": {}, "tool_results": {}}
    reply = "Booked! Your PNR is 1234567890."
    out = _ground_response(reply, state)
    assert "1234567890" in out
    assert "[PNR unavailable]" not in out
