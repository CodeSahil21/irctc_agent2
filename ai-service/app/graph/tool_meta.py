# graph/tool_meta.py
"""
The only place in the codebase where specific tool names are hardcoded.

WHY THIS FILE EXISTS
--------------------
The agent loop (agent_node) is fully dynamic — it reads the live MCP tool
schema every turn and lets the model decide what to call.  The one thing the
model cannot be trusted to determine on its own is whether an action is
*irreversible*, because getting that wrong has real-world consequences (money,
tickets, reminders deleted).  This file is the single authoritative list of
tools that require human confirmation before they run.

ADDING A NEW DESTRUCTIVE TOOL
------------------------------
Add one entry to DESTRUCTIVE_TOOLS.  The value is a callable that receives the
proposed tool arguments and returns True when confirmation is required.
Everything else — routing, prompt generation — is automatic.

Adding a purely read-only MCP tool needs zero changes anywhere.
"""
from typing import Any, Callable, Dict


# ---------------------------------------------------------------------------
# Helper predicates (kept out of the main dict for readability)
# ---------------------------------------------------------------------------

def _update_booking_destructive(args: Dict[str, Any]) -> bool:
    """Only destructive when changing status or boarding point — not a read."""
    return bool(args.get("status") or args.get("newBoardingStation"))


def _manage_reminder_destructive(args: Dict[str, Any]) -> bool:
    return args.get("action") == "delete"


# ---------------------------------------------------------------------------
# DESTRUCTIVE_TOOLS
# key   → MCP tool name (exact match)
# value → callable(args) → bool  (True = confirmation required for these args)
# ---------------------------------------------------------------------------

DESTRUCTIVE_TOOLS: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "book_ticket":         lambda args: True,
    "cancel_ticket":       lambda args: True,
    "update_booking":      _update_booking_destructive,
    "manage_reminder":     _manage_reminder_destructive,
    "add_saved_passenger": lambda args: True,
    "delete_saved_passenger": lambda args: True,
}


def is_destructive(tool_name: str, args: Dict[str, Any]) -> bool:
    """Return True if this tool call requires human confirmation."""
    check = DESTRUCTIVE_TOOLS.get(tool_name)
    return bool(check and check(args or {}))


# ---------------------------------------------------------------------------
# Confirmation prompt builders
# ---------------------------------------------------------------------------

def build_confirmation_prompt(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Return a conversational yes/no confirmation message for a destructive call.
    Phrased as a human travel agent would ask — not a form.
    """
    if tool_name == "book_ticket":
        train = f"{args.get('trainNumber', '?')} {args.get('trainName', '')}".strip()
        route = f"{args.get('source', '?')} → {args.get('destination', '?')}"
        date = args.get("journeyDate", "?")
        cls = args.get("travelClass", "?")
        quota = args.get("quota", "GN")
        fare = args.get("fare")
        fare_str = f"₹{fare}" if fare is not None else "fare TBD"
        pax = args.get("passengers") or []
        names = ", ".join(p.get("name", "?") for p in pax) if pax else ""
        pax_str = f" for {names}" if names else ""
        return (
            f"Just to confirm — I'll book **{train}** on **{date}** "
            f"({route}), **{cls}** class, {quota} quota, "
            f"{fare_str}{pax_str}. Shall I go ahead? (yes / no)"
        )

    if tool_name == "cancel_ticket":
        pnr = args.get("pnr", "?")
        return (
            f"Are you sure you want to cancel booking **{pnr}**? "
            f"This cannot be undone. (yes / no)"
        )

    if tool_name == "update_booking":
        parts: list[str] = []
        if args.get("status"):
            parts.append(f"status → **{args['status']}**")
        if args.get("newBoardingStation"):
            parts.append(f"boarding point → **{args['newBoardingStation']}**")
        changes = ", ".join(parts) if parts else "no changes"
        return (
            f"I'll update booking **{args.get('pnr', '?')}**: {changes}. "
            f"Proceed? (yes / no)"
        )

    if tool_name == "manage_reminder" and args.get("action") == "delete":
        return (
            f"I'll delete reminder **{args.get('reminderId', '?')}**. "
            f"Are you sure? (yes / no)"
        )

    if tool_name == "add_saved_passenger":
        name   = args.get("name", "?")
        age    = args.get("age", "?")
        gender = args.get("gender", "?")
        return (
            f"I'll save **{name}** (age {age}, {gender}) to your passenger list. "
            f"Shall I go ahead? (yes / no)"
        )

    if tool_name == "delete_saved_passenger":
        return (
            f"I'll remove passenger **{args.get('passengerId', args.get('name', '?'))}** "
            f"from your saved list. This cannot be undone. (yes / no)"
        )

    # Generic fallback for any future destructive tool added to the map
    return f"I'm about to run **{tool_name}**. Shall I proceed? (yes / no)"
