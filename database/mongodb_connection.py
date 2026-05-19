from pymongo import MongoClient, ReturnDocument

from config import get_app_mongo_database, get_app_mongo_uri


_client = None


def get_mongo_uri():
    uri = get_app_mongo_uri()

    if not uri:
        raise RuntimeError(
            "MongoDB provider is active but APP_MONGO_URI is not configured."
        )

    return uri


def get_mongo_database_name():
    return get_app_mongo_database()


def get_mongo_client():
    global _client

    if _client is None:
        _client = MongoClient(get_mongo_uri())

    return _client


def get_mongo_database():
    return get_mongo_client()[get_mongo_database_name()]


def get_collection(name):
    return get_mongo_database()[name]


def get_next_id(collection_name):
    counter = get_collection("counters").find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return int(counter["value"])
