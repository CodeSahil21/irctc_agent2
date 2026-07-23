# graph/ranking.py
"""
Pure-Python deterministic train ranking.

Called directly from tool_executor_node whenever search_trains or
recommend_trains returns results.  No LLM, no intent gating, no graph node —
just a sort.

Modes
-----
cheapest   — sort by total fare ascending       (default)
fastest    — sort by journey duration ascending
best_avail — sort by available seats descending, then fare ascending

The mode is detected from the user's most recent message.  If no keyword
matches, the default is cheapest.

Field parsing handles the varied shapes the IRCTC MCP server can return:
  - search_trains    → trains have durationMins / duration; fare is absent
  - recommend_trains → trains have nested fare ({amount|total}) and
                       availability ({count|available})
Trains missing the field required by the chosen mode keep their original
relative order (stable sort via a large sentinel), so the function never
reorders on garbage data.
"""
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Keyword sets for mode detection
# ---------------------------------------------------------------------------
_CHEAPEST_KW = {"cheap", "cheapest", "budget", "affordable", "low fare", "economical"}
_FASTEST_KW  = {"fast", "fastest", "quick", "quickest", "shortest", "less time", "direct"}
_AVAIL_KW    = {"available", "availability", "seats", "confirm", "confirmed"}

_MAX_DUR  = 10 ** 9
_MAX_FARE = float(10 ** 9)


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------

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


def _parse_duration(train: Dict[str, Any]) -> Optional[int]:
    """Return journey duration in minutes, or None if not parseable."""
    mins = _to_int(train.get("durationMins"))
    if mins is not None:
        return mins
    dur = str(train.get("duration") or "")
    try:
        if "h" in dur.lower():
            h, m = dur.lower().replace("m", "").split("h")
            return int(h) * 60 + int(m or 0)
        if ":" in dur:
            h, m = dur.split(":")
            return int(h) * 60 + int(m)
    except (ValueError, IndexError):
        pass
    return None


def _parse_fare(train: Dict[str, Any]) -> Optional[float]:
    """Return a numeric fare amount, handling flat and nested fare objects."""
    fare = train.get("fare")
    if isinstance(fare, dict):
        for key in ("amount", "total"):
            v = _to_float(fare.get(key))
            if v is not None:
                return v
        bd = fare.get("breakdown")
        if isinstance(bd, dict):
            v = _to_float(bd.get("total"))
            if v is not None:
                return v
    else:
        v = _to_float(fare)
        if v is not None:
            return v
    for key in ("totalFare", "amount", "baseFare", "price"):
        v = _to_float(train.get(key))
        if v is not None:
            return v
    return None


def _parse_seats(train: Dict[str, Any]) -> Optional[int]:
    """Return available seat count, handling nested availability objects."""
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_mode(user_text: str) -> str:
    """
    Infer ranking mode from raw user message text.
    Returns one of: "fastest" | "best_avail" | "cheapest"
    """
    t = (user_text or "").lower()
    if any(k in t for k in _FASTEST_KW):
        return "fastest"
    if any(k in t for k in _AVAIL_KW):
        return "best_avail"
    if any(k in t for k in _CHEAPEST_KW):
        return "cheapest"
    return "cheapest"


def rank_trains(trains: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """
    Return a sorted copy of *trains* according to *mode*.
    Trains that lack the sort field bubble to the end (None sentinel).
    """
    if mode == "fastest":
        return sorted(
            trains,
            key=lambda t: (_parse_duration(t) is None, _parse_duration(t) or _MAX_DUR),
        )
    if mode == "best_avail":
        return sorted(
            trains,
            key=lambda t: (
                _parse_seats(t) is None,
                -(_parse_seats(t) or 0),
                _parse_fare(t) or _MAX_FARE,
            ),
        )
    # default: cheapest
    return sorted(
        trains,
        key=lambda t: (_parse_fare(t) is None, _parse_fare(t) or _MAX_FARE),
    )
