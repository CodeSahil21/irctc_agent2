# memory/preference_memory.py
"""
Layer 3 — User Preference Memory

Write-through cache: reads/writes hit the in-process dict first for
sync access inside graph nodes, and persist to MongoDB asynchronously.

Sync helpers (get_preferences, merge_preferences_into_travel, preferences_summary)
are called from intent_node — they use the in-process cache.

Async helpers (load_preferences_from_db, persist_preferences) are called
from lifespan / conversation manager to hydrate and flush the cache.
"""
from typing import Dict, Optional

from app.graph.state import UserPreferences

# In-process write-through cache: user_email → UserPreferences
_cache: Dict[str, UserPreferences] = {}


# ── Sync (used inside graph nodes) ───────────────────────────────────────────

def get_preferences(user_email: str) -> UserPreferences:
    return dict(_cache.get(user_email, {}))


def set_preferences(user_email: str, prefs: UserPreferences) -> None:
    existing = dict(_cache.get(user_email, {}))
    existing.update({k: v for k, v in prefs.items() if v is not None})
    _cache[user_email] = UserPreferences(**existing)


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


# ── Async (used by conversation manager / lifespan) ──────────────────────────

async def load_preferences_from_db(db, user_email: str) -> UserPreferences:
    """Load preferences from MongoDB into the in-process cache."""
    from app.db.repositories.preference_repo import get_preferences as db_get
    doc = await db_get(db, user_email)
    if doc:
        prefs = UserPreferences(
            preferred_class=doc.get("preferred_class"),
            preferred_quota=doc.get("preferred_quota"),
            berth_preference=doc.get("berth_preference"),
            senior_citizen=doc.get("senior_citizen"),
        )
        _cache[user_email] = prefs
        return prefs
    return {}


async def persist_preferences(db, user_email: str) -> None:
    """Flush the in-process cache entry for this user to MongoDB."""
    from app.db.repositories.preference_repo import upsert_preferences
    from app.db.models import UserPreferenceDoc
    prefs = _cache.get(user_email, {})
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
