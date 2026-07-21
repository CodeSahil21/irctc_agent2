# memory/checkpoints.py
"""
Phase 8 — LangGraph MongoDB Checkpointing

Uses langgraph-checkpoint-mongodb (AsyncMongoDBSaver) for durable,
cross-restart state persistence.

Enables:
  - Multi-turn state persistence across HTTP requests (same thread_id)
  - Interrupt + resume flows (human approval, slot filling mid-flight)
  - State restoration after server restarts
"""
from motor.motor_asyncio import AsyncIOMotorClient
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver


async def get_checkpointer(mongo_url: str, mongo_db: str) -> AsyncMongoDBSaver:
    """
    Creates and returns an AsyncMongoDBSaver checkpointer.
    Called once at startup in lifespan.py and stored on app.state.
    The caller is responsible for calling .aclose() on shutdown.
    """
    client = AsyncIOMotorClient(mongo_url)
    checkpointer = AsyncMongoDBSaver(client, db_name=mongo_db)
    await checkpointer.asetup()
    return checkpointer
