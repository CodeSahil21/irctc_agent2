from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def create_mongo_client(mongo_url: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(mongo_url)


def get_db(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    return client[db_name]
