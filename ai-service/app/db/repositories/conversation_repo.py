from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.models import ConversationDoc, MessageDoc

_CONVERSATIONS = "conversations"
_MESSAGES = "messages"


async def upsert_conversation(db: AsyncIOMotorDatabase, doc: ConversationDoc) -> None:
    data = doc.model_dump()
    safe_set = {k: v for k, v in data.items() if k not in ("summary", "turn_count", "created_at")}
    safe_set["updated_at"] = datetime.now(timezone.utc)
    await db[_CONVERSATIONS].update_one(
        {"conversation_id": doc.conversation_id},
        {
            "$set": safe_set,
            "$setOnInsert": {"created_at": doc.created_at, "turn_count": 0, "summary": None},
        },
        upsert=True,
    )


async def increment_turn(db: AsyncIOMotorDatabase, conversation_id: str) -> None:
    await db[_CONVERSATIONS].update_one(
        {"conversation_id": conversation_id},
        {
            "$inc": {"turn_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


async def get_conversation(db: AsyncIOMotorDatabase, conversation_id: str) -> Optional[dict]:
    return await db[_CONVERSATIONS].find_one({"conversation_id": conversation_id}, {"_id": 0})


async def update_summary(db: AsyncIOMotorDatabase, conversation_id: str, summary: str) -> None:
    await db[_CONVERSATIONS].update_one(
        {"conversation_id": conversation_id},
        {"$set": {"summary": summary, "updated_at": datetime.now(timezone.utc)}},
    )


async def get_recent_conversations(
    db: AsyncIOMotorDatabase,
    user_email: str,
    limit: int = 20,
) -> List[dict]:
    cursor = (
        db[_CONVERSATIONS]
        .find({"user_email": user_email}, {"_id": 0})
        .sort("updated_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def save_message(db: AsyncIOMotorDatabase, doc: MessageDoc) -> None:
    await db[_MESSAGES].insert_one(doc.model_dump())


async def get_messages(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    limit: int = 50,
) -> List[dict]:
    cursor = (
        db[_MESSAGES]
        .find({"conversation_id": conversation_id}, {"_id": 0})
        .sort("created_at", 1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def setup_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[_CONVERSATIONS].create_index("conversation_id", unique=True)
    await db[_CONVERSATIONS].create_index("user_email")
    await db[_MESSAGES].create_index("conversation_id")
    await db[_MESSAGES].create_index([("conversation_id", 1), ("created_at", 1)])
