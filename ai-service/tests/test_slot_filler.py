from app.graph.nodes.slot_filler_node import slot_filler_node


class FakeRegistry:
    def __init__(self, schemas):
        self._schemas = schemas

    def is_known(self, name):
        return name in self._schemas

    def get_tool_schema(self, name):
        return self._schemas.get(name)


_SCHEMAS = {
    "search_trains": {
        "input_schema": {
            "required": ["fromStation", "toStation", "journeyDate"],
            "properties": {},
        }
    },
    "check_availability": {
        "input_schema": {
            "required": ["trainNumber", "travelClass", "quota", "journeyDate"],
            "properties": {},
        }
    },
    "get_pnr": {
        "input_schema": {"required": ["pnr"], "properties": {}}
    },
    "get_saved_passengers": {
        "input_schema": {"required": [], "properties": {}}
    },
}


def _registry():
    return FakeRegistry(_SCHEMAS)


def test_search_trains_missing_fields_asks_one():
    out = slot_filler_node(
        {"intent": "search_trains", "travel": {}},
        mcp_registry=_registry(),
    )
    assert out["missing_slots"]
    assert out["pending_question"]
    # Only one question surfaced at a time
    assert isinstance(out["pending_question"], str)


def test_search_trains_all_present_no_missing():
    out = slot_filler_node(
        {"intent": "search_trains", "travel": {"from_station": "NDLS", "to_station": "BCT", "date": "2026-08-01"}},
        mcp_registry=_registry(),
    )
    assert out["missing_slots"] == []
    assert out["pending_question"] is None


def test_quota_is_not_asked_default_applied():
    # check_availability requires quota, but it has a safe default → never asked
    out = slot_filler_node(
        {
            "intent": "check_availability",
            "travel": {"train_number": "12951", "travel_class": "3A", "date": "2026-08-01"},
        },
        mcp_registry=_registry(),
    )
    assert out["missing_slots"] == []


def test_train_number_resolvable_from_route_not_asked():
    # No train yet, but from+to+date present → a search can resolve it, so don't ask
    out = slot_filler_node(
        {
            "intent": "check_availability",
            "travel": {"from_station": "NDLS", "to_station": "BCT", "date": "2026-08-01", "travel_class": "3A"},
        },
        mcp_registry=_registry(),
    )
    assert "train_number" not in out["missing_slots"]


def test_train_number_unresolvable_is_asked():
    out = slot_filler_node(
        {"intent": "check_availability", "travel": {"travel_class": "3A", "date": "2026-08-01"}},
        mcp_registry=_registry(),
    )
    assert "train_number" in out["missing_slots"]


def test_get_pnr_requires_pnr():
    missing = slot_filler_node({"intent": "get_pnr", "travel": {}}, mcp_registry=_registry())
    assert "pnr" in missing["missing_slots"]

    ok = slot_filler_node({"intent": "get_pnr", "travel": {"pnr": "1234567890"}}, mcp_registry=_registry())
    assert ok["missing_slots"] == []


def test_no_required_fields_no_question():
    out = slot_filler_node({"intent": "get_saved_passengers", "travel": {}}, mcp_registry=_registry())
    assert out["missing_slots"] == []


def test_general_question_skipped():
    out = slot_filler_node({"intent": "general_question", "travel": {}}, mcp_registry=_registry())
    assert out["missing_slots"] == []


def test_fallback_to_static_preconditions_without_registry():
    # No registry → static preconditions path (search_trains needs from/to/date)
    out = slot_filler_node({"intent": "search_trains", "travel": {}}, mcp_registry=None)
    assert set(out["missing_slots"]) == {"from_station", "to_station", "date"}
