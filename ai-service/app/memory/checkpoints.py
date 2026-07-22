from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver


def get_checkpointer(
    mongo_url: str,
    mongo_db: str,
) -> MongoDBSaver:
    """
    Creates and returns a MongoDBSaver checkpointer.
    Uses a dedicated sync pymongo client (MongoDBSaver requires pymongo, not Motor).
    """
    client = MongoClient(mongo_url)
    try:
        return MongoDBSaver(client, db_name=mongo_db)
    except Exception:
        client.close()
        raise
