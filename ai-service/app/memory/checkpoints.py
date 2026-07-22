from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver


def get_checkpointer(
    mongo_url: str,
    mongo_db: str,
) -> MongoDBSaver:
    """
    Creates and returns a MongoDBSaver checkpointer.
    Uses a dedicated sync pymongo client (MongoDBSaver requires pymongo, not Motor).

    The graph runs via ainvoke/astream_events, which call MongoDBSaver's async
    methods (aput/aget_tuple/alist). Those offload the blocking pymongo calls to a
    thread executor, so checkpointing does not block the event loop.
    """
    client = MongoClient(mongo_url)
    try:
        return MongoDBSaver(client, db_name=mongo_db)
    except Exception:
        client.close()
        raise
