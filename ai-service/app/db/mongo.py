"""
Motor async MongoDB client.
Initialized once in lifespan.py and stored on app.state.
get_db() is used by repositories to get the database handle.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def create_mongo_client(mongo_url: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(mongo_url)


def get_db(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    return client[db_name]
