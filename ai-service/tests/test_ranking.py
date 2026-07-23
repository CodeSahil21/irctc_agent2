# tests/test_ranking.py
"""
Tests for app.graph.ranking — pure ranking functions.
These replace the old ranking_node tests; logic is identical, import paths updated.
"""
from app.graph.ranking import (
    _parse_duration,
    _parse_fare,
    _parse_seats,
    detect_mode,
    rank_trains,
)


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_duration_prefers_minutes():
    assert _parse_duration({"durationMins": 930}) == 930


def test_parse_duration_string_fallback():
    assert _parse_duration({"duration": "15h30m"}) == 930
    assert _parse_duration({"duration": "15:30"}) == 930


def test_parse_duration_missing():
    assert _parse_duration({}) is None


def test_parse_fare_nested_amount():
    assert _parse_fare({"fare": {"amount": 1250}}) == 1250.0


def test_parse_fare_nested_total_and_breakdown():
    assert _parse_fare({"fare": {"total": 990}}) == 990.0
    assert _parse_fare({"fare": {"breakdown": {"total": 500}}}) == 500.0


def test_parse_fare_flat_and_stringy():
    assert _parse_fare({"totalFare": "₹1,499"}) == 1499.0


def test_parse_fare_missing_returns_none():
    assert _parse_fare({"trainNumber": "12951"}) is None


def test_parse_seats_nested_count():
    assert _parse_seats({"availability": {"count": 42}}) == 42


def test_parse_seats_nested_boolean():
    assert _parse_seats({"availability": {"available": True}}) == 1
    assert _parse_seats({"availability": {"available": False}}) == 0


def test_parse_seats_missing_returns_none():
    assert _parse_seats({"trainNumber": "12951"}) is None


# ---------------------------------------------------------------------------
# detect_mode
# ---------------------------------------------------------------------------

def test_detect_mode_cheapest():
    assert detect_mode("show me the cheapest train") == "cheapest"
    assert detect_mode("budget option") == "cheapest"


def test_detect_mode_fastest():
    assert detect_mode("what is the fastest train?") == "fastest"
    assert detect_mode("quickest route") == "fastest"


def test_detect_mode_best_avail():
    assert detect_mode("which trains have seats available?") == "best_avail"
    assert detect_mode("confirmed availability") == "best_avail"


def test_detect_mode_default_cheapest():
    assert detect_mode("trains from Delhi to Mumbai") == "cheapest"
    assert detect_mode("") == "cheapest"


# ---------------------------------------------------------------------------
# rank_trains
# ---------------------------------------------------------------------------

def test_rank_trains_cheapest_orders_by_nested_fare():
    trains = [
        {"trainNumber": "A", "fare": {"amount": 900}},
        {"trainNumber": "B", "fare": {"amount": 400}},
        {"trainNumber": "C", "fare": {"amount": 650}},
    ]
    out = rank_trains(trains, "cheapest")
    assert [t["trainNumber"] for t in out] == ["B", "C", "A"]


def test_rank_trains_fastest_orders_by_duration():
    trains = [
        {"trainNumber": "A", "durationMins": 600},
        {"trainNumber": "B", "durationMins": 300},
    ]
    out = rank_trains(trains, "fastest")
    assert [t["trainNumber"] for t in out] == ["B", "A"]


def test_rank_trains_best_avail_orders_by_seats_desc():
    trains = [
        {"trainNumber": "A", "availability": {"count": 2}},
        {"trainNumber": "B", "availability": {"count": 50}},
    ]
    out = rank_trains(trains, "best_avail")
    assert [t["trainNumber"] for t in out] == ["B", "A"]


def test_rank_trains_missing_field_keeps_stable_order():
    trains = [{"trainNumber": "A"}, {"trainNumber": "B"}, {"trainNumber": "C"}]
    out = rank_trains(trains, "cheapest")
    assert [t["trainNumber"] for t in out] == ["A", "B", "C"]


def test_rank_trains_empty():
    assert rank_trains([], "cheapest") == []
