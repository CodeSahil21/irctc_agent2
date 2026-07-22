# graph/nodes/ranking_node.py
"""
Phase 12 — Candidate Ranking

Pure Python deterministic ranking. Never asks Claude to sort.

Ranking modes (derived from intent/goal):
  cheapest   — sort by total fare ascending
  fastest    — sort by duration ascending
  best_avail — sort by available seats descending, then fare ascending

Applied when search_results are present. Writes ranked_results to state.

Field parsing is aligned with the IRCTC MCP server response shapes:
  - search_trains       → trains have `durationMins` / `duration`, no fare/seats
  - recommend_trains    → trains have nested `fare` ({amount|total}) and
                          `availability` ({count|available})
Trains missing the field required by a mode keep their original relative order
(stable sort with a sentinel), so ranking never reorders on garbage data.
"""
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState
from app.telemetry.logging import app_logger

# Keywords in user_goal that map to a ranking mode
_CHEAPEST_KEYWORDS = {"cheap", "cheapest", "budget", "affordable", "low fare", "economical"}
_FASTEST_KEYWORDS = {"fast", "fastest", "quick", "quickest", "shortest", "less time", "direct"}
_AVAIL_KEYWORDS = {"available", "availability", "seats", "confirm", "confirmed"}

_MAX_DURATION = 10**9
_MAX_FARE = float(10**9)


def _to_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _parse_duration_str(duration_str: Optional[str]) -> Optional[int]:
    """Convert 'HH:MM' or 'XhYm' to total minutes. Returns None on failure."""
    if not duration_str:
        return None
    try:
        s = str(duration_str).lower()
        if "h" in s:
            parts = s.replace("m", "").split("h")
            return int(parts[0]) * 60 + int(parts[1] or 0)
        if ":" in s:
            h, m = s.split(":")
            return int(h) * 60 + int(m)
    except (ValueError, IndexError) as exc:
        app_logger.debug("Failed to parse train duration: {error}", error=str(exc))
    return None


def _parse_duration(train: Dict[str, Any]) -> Optional[int]:
    """Prefer the numeric `durationMins`, fall back to parsing `duration`."""
    mins = _to_int(train.get("durationMins"))
    if mins is not None:
        return mins
    return _parse_duration_str(train.get("duration"))


def _parse_fare(train: Dict[str, Any]) -> Optional[float]:
    """Extract a numeric fare, handling both flat and nested `fare` objects."""
    fare = train.get("fare")
    if isinstance(fare, dict):
        for key in ("amount", "total"):
            value = _to_float(fare.get(key))
            if value is not None:
                return value
        breakdown = fare.get("breakdown")
        if isinstance(breakdown, dict):
            value = _to_float(breakdown.get("total"))
            if value is not None:
                return value
    else:
        value = _to_float(fare)
        if value is not None:
            return value
    for key in ("totalFare", "amount", "baseFare", "price"):
        value = _to_float(train.get(key))
        if value is not None:
            return value
    return None


def _parse_seats(train: Dict[str, Any]) -> Optional[int]:
    """Extract available seat count, handling nested `availability` objects."""
    avail = train.get("availability")
    if isinstance(avail, dict):
        count = _to_int(avail.get("count"))
        if count is not None:
            return count
        available = avail.get("available")
        if isinstance(available, bool):
            return 1 if available else 0
    for key in ("availableSeats", "available_seats", "seats"):
        count = _to_int(train.get(key))
        if count is not None:
            return count
    return None


def _detect_mode(user_goal: str) -> str:
    goal = (user_goal or "").lower()
    if any(k in goal for k in _FASTEST_KEYWORDS):
        return "fastest"
    if any(k in goal for k in _AVAIL_KEYWORDS):
        return "best_avail"
    if any(k in goal for k in _CHEAPEST_KEYWORDS):
        return "cheapest"
    # Default: cheapest
    return "cheapest"


def ranking_node(state: TravelState) -> Dict[str, Any]:
    search_results: List[Dict[str, Any]] = state.get("search_results") or []

    if not search_results:
        return {"ranked_results": []}

    user_goal = state.get("user_goal") or ""
    mode = _detect_mode(user_goal)

    if mode == "fastest":
        ranked = sorted(
            search_results,
            key=lambda t: (_parse_duration(t) is None, _parse_duration(t) or _MAX_DURATION),
        )
    elif mode == "best_avail":
        ranked = sorted(
            search_results,
            key=lambda t: (
                _parse_seats(t) is None,
                -(_parse_seats(t) or 0),
                _parse_fare(t) or _MAX_FARE,
            ),
        )
    else:  # cheapest
        ranked = sorted(
            search_results,
            key=lambda t: (_parse_fare(t) is None, _parse_fare(t) or _MAX_FARE),
        )

    app_logger.info(
        "Ranked {n} trains | mode={mode} | top={top}",
        n=len(ranked),
        mode=mode,
        top=ranked[0].get("trainNumber") if ranked else "none",
    )

    return {"ranked_results": ranked}
