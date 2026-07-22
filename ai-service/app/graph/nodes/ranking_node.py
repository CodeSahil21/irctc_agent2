# graph/nodes/ranking_node.py
"""
Phase 12 — Candidate Ranking

Pure Python deterministic ranking. Never asks Claude to sort.

Ranking modes (derived from intent/goal):
  cheapest   — sort by total fare ascending
  fastest    — sort by duration ascending
  best_avail — sort by available seats descending, then fare ascending

Applied when search_results are present. Writes ranked_results to state.
"""
from typing import Any, Dict, List, Optional

from app.graph.state import TravelState
from app.telemetry.logging import app_logger

# Keywords in user_goal that map to a ranking mode
_CHEAPEST_KEYWORDS = {"cheap", "cheapest", "budget", "affordable", "low fare", "economical"}
_FASTEST_KEYWORDS = {"fast", "fastest", "quick", "quickest", "shortest", "less time", "direct"}
_AVAIL_KEYWORDS = {"available", "availability", "seats", "confirm", "confirmed"}


def _parse_duration(duration_str: Optional[str]) -> int:
    """Convert 'HH:MM' or 'XhYm' to total minutes. Returns large int on failure."""
    if not duration_str:
        return 99999
    try:
        if "h" in duration_str:
            parts = duration_str.lower().replace("m", "").split("h")
            return int(parts[0]) * 60 + int(parts[1] or 0)
        if ":" in duration_str:
            h, m = duration_str.split(":")
            return int(h) * 60 + int(m)
    except (ValueError, IndexError) as exc:
        app_logger.debug("Failed to parse train duration: {error}", error=str(exc))
    return 99999


def _parse_fare(train: Dict[str, Any]) -> float:
    """Extract numeric fare from a train dict."""
    for key in ("fare", "totalFare", "baseFare", "price"):
        val = train.get(key)
        if val is not None:
            try:
                return float(str(val).replace(",", "").replace("₹", "").strip())
            except ValueError:
                pass
    return 999999.0


def _parse_seats(train: Dict[str, Any]) -> int:
    """Extract available seat count from a train dict."""
    for key in ("availableSeats", "available_seats", "seats", "availability"):
        val = train.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return 0


def _detect_mode(user_goal: str) -> str:
    goal = (user_goal or "").lower()
    if any(k in goal for k in _FASTEST_KEYWORDS):
        return "fastest"
    if any(k in goal for k in _AVAIL_KEYWORDS):
        return "best_avail"
    # Default: cheapest
    return "cheapest"


def ranking_node(state: TravelState) -> Dict[str, Any]:
    search_results: List[Dict[str, Any]] = state.get("search_results") or []

    if not search_results:
        return {"ranked_results": []}

    user_goal = state.get("user_goal") or ""
    mode = _detect_mode(user_goal)

    if mode == "fastest":
        ranked = sorted(search_results, key=lambda t: _parse_duration(t.get("duration")))
    elif mode == "best_avail":
        ranked = sorted(search_results, key=lambda t: (-_parse_seats(t), _parse_fare(t)))
    else:  # cheapest
        ranked = sorted(search_results, key=lambda t: _parse_fare(t))

    app_logger.info(
        "Ranked {n} trains | mode={mode} | top={top}",
        n=len(ranked),
        mode=mode,
        top=ranked[0].get("trainNumber") if ranked else "none",
    )

    return {"ranked_results": ranked}
