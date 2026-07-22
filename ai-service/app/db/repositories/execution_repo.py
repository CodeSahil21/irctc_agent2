from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.models import ExecutionLogDoc

_COLLECTION = "execution_logs"


async def save_execution_log(db: AsyncIOMotorDatabase, doc: ExecutionLogDoc) -> None:
    await db[_COLLECTION].insert_one(doc.model_dump())


async def setup_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[_COLLECTION].create_index("conversation_id")
    await db[_COLLECTION].create_index([("conversation_id", 1), ("turn", 1)])
