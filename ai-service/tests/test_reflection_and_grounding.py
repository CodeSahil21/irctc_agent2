# tests/test_reflection_and_grounding.py
"""
Tests for reflection_node and the PNR grounding helper in agent_node.
"""
from app.graph.nodes.reflection_node import reflection_node
from app.graph.nodes.agent_node import _ground_reply


class _NeverCalledLLM:
    """Asserts that the reflection pre-gate never reaches the model."""

    async def chat_raw(self, *args, **kwargs):
        raise AssertionError("LLM must not be called when tools already failed")


# ---------------------------------------------------------------------------
# reflection_node — fast-path (pre-gate) tests
# ---------------------------------------------------------------------------

async def test_reflection_pregate_fails_on_errors():
    out = await reflection_node(
        {
            "errors": ["book_ticket: INVALID_PARAMETERS"],
            "tool_history": [],
            "messages": [],
        },
        llm_service=_NeverCalledLLM(),
    )
    assert out["reflection_passed"] is False
    assert out["reflection_required"] is False
    assert "INVALID_PARAMETERS" in out["reflection_feedback"]


async def test_reflection_pregate_fails_on_failed_tool_status():
    out = await reflection_node(
        {
            "errors": [],
            "tool_history": [{"tool": "get_fare", "status": "failed"}],
            "messages": [],
        },
        llm_service=_NeverCalledLLM(),
    )
    assert out["reflection_passed"] is False


async def test_reflection_increments_retries():
    out = await reflection_node(
        {
            "errors": ["some_tool: timeout"],
            "tool_history": [],
            "messages": [],
            "reflection_retries": 0,
        },
        llm_service=_NeverCalledLLM(),
    )
    assert out["reflection_retries"] == 1


# ---------------------------------------------------------------------------
# PNR grounding (_ground_reply from agent_node)
# ---------------------------------------------------------------------------

def test_ground_reply_redacts_ungrounded_pnr():
    reply = "Your ticket is booked. PNR: 9999999999"
    out = _ground_reply(reply, {"booking": {}, "persistent_results": {}, "tool_history": []})
    assert "9999999999" not in out
    assert "[PNR unavailable]" in out


def test_ground_reply_keeps_grounded_pnr():
    # PNR present in booking field (top-level compat field)
    state = {
        "booking": {"pnr": "1234567890"},
        "persistent_results": {},
        "tool_history": [],
    }
    reply = "Booked! Your PNR is 1234567890."
    out = _ground_reply(reply, state)
    assert "1234567890" in out
    assert "[PNR unavailable]" not in out


def test_ground_reply_keeps_pnr_from_tool_history():
    # PNR surfaced in a ToolMessage result rather than booking field
    state = {
        "booking": None,
        "persistent_results": {},
        "tool_history": [{"result": {"pnr": "5556667778"}, "status": "success"}],
    }
    reply = "Booking confirmed. PNR: 5556667778"
    out = _ground_reply(reply, state)
    assert "5556667778" in out


def test_ground_reply_multiple_pnrs_mixed():
    state = {
        "booking": {"pnr": "1111111111"},
        "persistent_results": {},
        "tool_history": [],
    }
    # 1111111111 is grounded; 9999999999 is not
    reply = "PNR 1111111111 is confirmed. Also saw 9999999999."
    out = _ground_reply(reply, state)
    assert "1111111111" in out
    assert "9999999999" not in out
