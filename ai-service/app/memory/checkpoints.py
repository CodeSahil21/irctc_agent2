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


async def get_checkpointer(
    mongo_url: str,
    mongo_db: str,
    client: AsyncIOMotorClient = None,
) -> AsyncMongoDBSaver:
    """
    Creates and returns an AsyncMongoDBSaver checkpointer.
    Pass the existing Motor client from lifespan to share the connection pool.
    If no client is provided, a new one is created (test/standalone use).
    """
    if client is None:
        client = AsyncIOMotorClient(mongo_url)
    checkpointer = AsyncMongoDBSaver(client, db_name=mongo_db)
    await checkpointer.asetup()
    return checkpointer
