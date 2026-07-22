"""
Layer 3 — User Preference Memory

Preferences (preferred class/quota/berth/senior) are loaded from MongoDB when a
conversation opens and flow through the graph via `state["user_preferences"]`.

There is deliberately NO process-global cache: a module-level dict would be shared
across every concurrent request/user and every uvicorn worker, causing stale or
cross-request reads. Loading per conversation-open and passing through graph state
keeps each request isolated.
"""
from typing import Dict

from app.graph.state import UserPreferences


def merge_preferences_into_travel(travel: Dict, prefs: UserPreferences) -> Dict:
    updated = dict(travel)
    if not updated.get("travel_class") and prefs.get("preferred_class"):
        updated["travel_class"] = prefs["preferred_class"]
    if not updated.get("quota") and prefs.get("preferred_quota"):
        updated["quota"] = prefs["preferred_quota"]
    return updated


def preferences_summary(prefs: UserPreferences) -> str:
    if not prefs:
        return ""
    parts = []
    if prefs.get("preferred_class"):
        parts.append(f"Preferred class: {prefs['preferred_class']}")
    if prefs.get("preferred_quota"):
        parts.append(f"Preferred quota: {prefs['preferred_quota']}")
    if prefs.get("berth_preference"):
        parts.append(f"Berth preference: {prefs['berth_preference']}")
    if prefs.get("senior_citizen"):
        parts.append("Senior citizen: yes")
    return ", ".join(parts)


async def load_preferences_from_db(db, user_email: str) -> UserPreferences:
    """Load a user's preferences from MongoDB. Returns {} when none exist."""
    from app.db.repositories.preference_repo import get_preferences as db_get
    doc = await db_get(db, user_email)
    if doc:
        return UserPreferences(
            preferred_class=doc.get("preferred_class"),
            preferred_quota=doc.get("preferred_quota"),
            berth_preference=doc.get("berth_preference"),
            senior_citizen=doc.get("senior_citizen"),
        )
    return {}


async def persist_preferences(db, user_email: str, prefs: UserPreferences) -> None:
    """Persist explicit preferences for a user to MongoDB."""
    if not prefs:
        return
    from app.db.models import UserPreferenceDoc
    from app.db.repositories.preference_repo import upsert_preferences
    await upsert_preferences(
        db,
        UserPreferenceDoc(
            user_email=user_email,
            preferred_class=prefs.get("preferred_class"),
            preferred_quota=prefs.get("preferred_quota"),
            berth_preference=prefs.get("berth_preference"),
            senior_citizen=prefs.get("senior_citizen"),
        ),
    )
