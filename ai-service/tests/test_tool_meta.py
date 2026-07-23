# tests/test_tool_meta.py
"""
Tests for app.graph.tool_meta — replaces test_slot_filler.py and
test_arg_patcher.py with tests appropriate to the new architecture.

The slot-filler / arg-patcher concepts no longer exist; the equivalent
correctness guarantees are:
  - is_destructive() correctly classifies tools that need human confirmation.
  - build_confirmation_prompt() produces non-empty, human-readable strings.
  - Non-destructive tools (search, info lookups) are never flagged.
"""
from app.graph.tool_meta import build_confirmation_prompt, is_destructive


# ---------------------------------------------------------------------------
# is_destructive
# ---------------------------------------------------------------------------

class TestIsDestructive:
    def test_book_ticket_always_destructive(self):
        assert is_destructive("book_ticket", {}) is True
        assert is_destructive("book_ticket", {"trainNumber": "12951"}) is True

    def test_cancel_ticket_always_destructive(self):
        assert is_destructive("cancel_ticket", {}) is True
        assert is_destructive("cancel_ticket", {"pnr": "1234567890"}) is True

    def test_update_booking_destructive_on_status_change(self):
        assert is_destructive("update_booking", {"status": "CANCELLED"}) is True

    def test_update_booking_destructive_on_boarding_change(self):
        assert is_destructive("update_booking", {"newBoardingStation": "MTJ"}) is True

    def test_update_booking_not_destructive_empty_args(self):
        # No status or newBoardingStation → not a side-effecting change
        assert is_destructive("update_booking", {}) is False

    def test_manage_reminder_delete_is_destructive(self):
        assert is_destructive("manage_reminder", {"action": "delete", "reminderId": "r1"}) is True

    def test_manage_reminder_create_not_destructive(self):
        assert is_destructive("manage_reminder", {"action": "create"}) is False

    def test_manage_reminder_update_not_destructive(self):
        assert is_destructive("manage_reminder", {"action": "update"}) is False

    # Read-only / search tools must never be flagged
    def test_search_trains_not_destructive(self):
        assert is_destructive("search_trains", {"fromStation": "NDLS"}) is False

    def test_check_availability_not_destructive(self):
        assert is_destructive("check_availability", {}) is False

    def test_get_fare_not_destructive(self):
        assert is_destructive("get_fare", {}) is False

    def test_get_pnr_not_destructive(self):
        assert is_destructive("get_pnr", {"pnr": "1234567890"}) is False

    def test_get_booking_history_not_destructive(self):
        assert is_destructive("get_booking_history", {}) is False

    def test_get_saved_passengers_not_destructive(self):
        assert is_destructive("get_saved_passengers", {}) is False

    def test_unknown_tool_not_destructive(self):
        # A brand-new MCP tool with no entry in the map must default to safe
        assert is_destructive("some_future_tool", {}) is False
        assert is_destructive("", {}) is False


# ---------------------------------------------------------------------------
# build_confirmation_prompt
# ---------------------------------------------------------------------------

class TestBuildConfirmationPrompt:
    def test_book_ticket_includes_key_details(self):
        args = {
            "trainNumber": "12951",
            "trainName": "Rajdhani Express",
            "source": "NDLS",
            "destination": "BCT",
            "journeyDate": "2026-08-15",
            "travelClass": "3A",
            "quota": "GN",
            "fare": 1450,
            "passengers": [{"name": "Asha"}, {"name": "Ravi"}],
        }
        prompt = build_confirmation_prompt("book_ticket", args)
        assert "12951" in prompt
        assert "Rajdhani Express" in prompt
        assert "NDLS" in prompt
        assert "BCT" in prompt
        assert "2026-08-15" in prompt
        assert "3A" in prompt
        assert "₹1450" in prompt
        assert "Asha" in prompt
        assert "yes" in prompt.lower() or "no" in prompt.lower()

    def test_cancel_ticket_includes_pnr(self):
        prompt = build_confirmation_prompt("cancel_ticket", {"pnr": "9876543210"})
        assert "9876543210" in prompt
        assert "cancel" in prompt.lower()

    def test_update_booking_status_change(self):
        prompt = build_confirmation_prompt(
            "update_booking", {"pnr": "1111111111", "status": "CANCELLED"}
        )
        assert "1111111111" in prompt
        assert "CANCELLED" in prompt

    def test_update_booking_boarding_change(self):
        prompt = build_confirmation_prompt(
            "update_booking",
            {"pnr": "1111111111", "newBoardingStation": "MTJ"},
        )
        assert "MTJ" in prompt

    def test_manage_reminder_delete(self):
        prompt = build_confirmation_prompt(
            "manage_reminder", {"action": "delete", "reminderId": "rem-42"}
        )
        assert "rem-42" in prompt
        assert "delete" in prompt.lower()

    def test_generic_fallback_is_non_empty(self):
        prompt = build_confirmation_prompt("some_future_destructive_tool", {})
        assert len(prompt) > 10
        assert "some_future_destructive_tool" in prompt

    def test_book_ticket_no_passengers_still_valid(self):
        prompt = build_confirmation_prompt("book_ticket", {
            "trainNumber": "22222", "journeyDate": "2026-09-01",
            "travelClass": "SL", "quota": "GN",
        })
        assert "22222" in prompt
        assert len(prompt) > 10
