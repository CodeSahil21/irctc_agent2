from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.models import UserPreferenceDoc

_COLLECTION = "user_preferences"


async def get_preferences(db: AsyncIOMotorDatabase, user_email: str) -> Optional[dict]:
    return await db[_COLLECTION].find_one({"user_email": user_email}, {"_id": 0})


async def upsert_preferences(db: AsyncIOMotorDatabase, doc: UserPreferenceDoc) -> None:
    data = doc.model_dump()
    data["updated_at"] = datetime.now(timezone.utc)
    await db[_COLLECTION].update_one(
        {"user_email": doc.user_email},
        {"$set": data},
        upsert=True,
    )


async def setup_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[_COLLECTION].create_index("user_email", unique=True)
