from app.graph.arg_patcher import patch_tool_args


def _search_state():
    return {"search_results": [{"trainNumber": "12951", "trainName": "Rajdhani Exp"}]}


def test_check_availability_resolves_train_from_search():
    args = patch_tool_args(
        "check_availability",
        {},
        _search_state(),
        {"travel_class": "3A", "date": "2026-08-01"},
    )
    assert args["trainNumber"] == "12951"
    assert args["travelClass"] == "3A"
    assert args["quota"] == "GN"
    assert args["journeyDate"] == "2026-08-01"


def test_get_fare_resolves_route_and_train():
    args = patch_tool_args(
        "get_fare",
        {},
        _search_state(),
        {"from_station": "NDLS", "to_station": "BCT", "travel_class": "2A"},
    )
    assert args["trainNumber"] == "12951"
    assert args["fromStation"] == "NDLS"
    assert args["toStation"] == "BCT"
    assert args["quota"] == "GN"


def test_explicit_planner_value_is_preserved():
    # planner already put a specific train — patcher must not overwrite it
    args = patch_tool_args(
        "check_availability",
        {"trainNumber": "22222"},
        _search_state(),
        {"travel_class": "SL", "date": "2026-08-01"},
    )
    assert args["trainNumber"] == "22222"


def test_book_ticket_without_passengers_omits_key():
    args = patch_tool_args(
        "book_ticket",
        {},
        _search_state(),
        {"from_station": "NDLS", "to_station": "BCT", "date": "2026-08-01", "travel_class": "3A"},
    )
    # Never fabricate a passenger — the key must be absent so the registry rejects it.
    assert "passengers" not in args


def test_book_ticket_resolves_saved_passengers_and_fare():
    state = {**_search_state(), "saved_passengers": [{"name": "Asha", "age": 30, "gender": "FEMALE"}], "fare": {"amount": 1450}}
    args = patch_tool_args(
        "book_ticket",
        {},
        state,
        {"from_station": "NDLS", "to_station": "BCT", "date": "2026-08-01", "travel_class": "3A"},
    )
    assert args["passengers"] == [{"name": "Asha", "age": 30, "gender": "FEMALE"}]
    assert args["fare"] == 1450
    assert args["trainName"] == "Rajdhani Exp"


def test_book_ticket_selected_passengers_take_priority():
    state = {
        **_search_state(),
        "saved_passengers": [{"name": "Asha", "age": 30, "gender": "FEMALE"}],
    }
    travel = {
        "from_station": "NDLS", "to_station": "BCT", "date": "2026-08-01", "travel_class": "3A",
        "selected_passengers": [{"name": "Ravi", "age": 40, "gender": "MALE"}],
    }
    args = patch_tool_args("book_ticket", {}, state, travel)
    assert args["passengers"] == [{"name": "Ravi", "age": 40, "gender": "MALE"}]


def test_get_platform_uses_station_code():
    args = patch_tool_args("get_platform", {}, _search_state(), {"from_station": "NDLS"})
    assert args["trainNumber"] == "12951"
    assert args["stationCode"] == "NDLS"


def test_pnr_tools_resolve_from_travel():
    args = patch_tool_args("cancel_ticket", {}, {}, {"pnr": "1234567890"})
    assert args["pnr"] == "1234567890"


def test_update_reminder_resolves_single_candidate():
    state = {"reminders": [{"id": "rem-1"}]}
    args = patch_tool_args("update_reminder", {}, state, {})
    assert args["reminderId"] == "rem-1"


def test_update_reminder_ambiguous_leaves_blank():
    state = {"reminders": [{"id": "rem-1"}, {"id": "rem-2"}]}
    args = patch_tool_args("update_reminder", {}, state, {})
    assert "reminderId" not in args
