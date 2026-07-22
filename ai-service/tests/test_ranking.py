from app.graph.nodes.ranking_node import (
    _parse_duration,
    _parse_fare,
    _parse_seats,
    ranking_node,
)


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


def test_ranking_cheapest_orders_by_nested_fare():
    trains = [
        {"trainNumber": "A", "fare": {"amount": 900}},
        {"trainNumber": "B", "fare": {"amount": 400}},
        {"trainNumber": "C", "fare": {"amount": 650}},
    ]
    out = ranking_node({"search_results": trains, "user_goal": "cheapest train"})["ranked_results"]
    assert [t["trainNumber"] for t in out] == ["B", "C", "A"]


def test_ranking_fastest_orders_by_duration():
    trains = [
        {"trainNumber": "A", "durationMins": 600},
        {"trainNumber": "B", "durationMins": 300},
    ]
    out = ranking_node({"search_results": trains, "user_goal": "fastest option"})["ranked_results"]
    assert [t["trainNumber"] for t in out] == ["B", "A"]


def test_ranking_best_avail_orders_by_seats_desc():
    trains = [
        {"trainNumber": "A", "availability": {"count": 2}},
        {"trainNumber": "B", "availability": {"count": 50}},
    ]
    out = ranking_node({"search_results": trains, "user_goal": "which has seats available"})["ranked_results"]
    assert [t["trainNumber"] for t in out] == ["B", "A"]


def test_ranking_missing_field_keeps_stable_order():
    # No fare anywhere → cheapest mode must not reorder on garbage
    trains = [{"trainNumber": "A"}, {"trainNumber": "B"}, {"trainNumber": "C"}]
    out = ranking_node({"search_results": trains, "user_goal": "cheapest"})["ranked_results"]
    assert [t["trainNumber"] for t in out] == ["A", "B", "C"]


def test_ranking_empty():
    assert ranking_node({"search_results": []})["ranked_results"] == []
