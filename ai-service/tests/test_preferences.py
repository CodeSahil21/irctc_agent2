from app.memory.preference_memory import (
    merge_preferences_into_travel,
    preferences_summary,
)


def test_merge_fills_only_empty_slots():
    travel = {"from_station": "NDLS"}
    prefs = {"preferred_class": "3A", "preferred_quota": "TQ"}
    out = merge_preferences_into_travel(travel, prefs)
    assert out["travel_class"] == "3A"
    assert out["quota"] == "TQ"
    # original untouched
    assert travel == {"from_station": "NDLS"}


def test_merge_does_not_override_explicit_values():
    travel = {"travel_class": "1A", "quota": "GN"}
    prefs = {"preferred_class": "3A", "preferred_quota": "TQ"}
    out = merge_preferences_into_travel(travel, prefs)
    assert out["travel_class"] == "1A"
    assert out["quota"] == "GN"


def test_preferences_summary_empty():
    assert preferences_summary({}) == ""


def test_preferences_summary_formats_fields():
    s = preferences_summary({"preferred_class": "3A", "senior_citizen": True})
    assert "3A" in s
    assert "Senior citizen" in s
