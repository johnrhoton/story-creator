# services/sync_service.py

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

from database import (
    export_database_to_json,
    import_database_from_json,
)


SYNC_DOCUMENT_ID = "story_creator_main"
SYNC_COLLECTION = "database_backups"


def get_utc_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")


def parse_timestamp(value):
    if not value:
        return None

    value = value.replace(
        "Z",
        "+00:00"
    )

    parsed = datetime.fromisoformat(value)

    # If timestamp is naive/local, convert it
    # to aware local time first.
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()

    return parsed.astimezone(timezone.utc)


def get_mongo_collection():
    load_dotenv()

    uri = os.getenv("MONGODB_URI")

    database_name = os.getenv(
        "MONGODB_DATABASE",
        "story_creator"
    )

    if not uri:
        raise RuntimeError(
            "MONGODB_URI not found in .env"
        )

    client = MongoClient(uri)

    db = client[database_name]

    return db[SYNC_COLLECTION]


def get_local_export():
    export_json = export_database_to_json()

    data = json.loads(export_json)

    return data


def get_mongo_backup():
    collection = get_mongo_collection()

    return collection.find_one(
        {"_id": SYNC_DOCUMENT_ID}
    )


def get_sync_status():
    local_data = get_local_export()

    mongo_doc = get_mongo_backup()

    local_timestamp = local_data.get(
        "exported_at"
    )

    mongo_timestamp = None

    if mongo_doc:
        mongo_timestamp = mongo_doc.get(
            "last_synced_at"
        )

    local_dt = parse_timestamp(
        local_timestamp
    )

    mongo_dt = parse_timestamp(
        mongo_timestamp
    )

    if not mongo_doc:
        direction = "push"

        message = (
            "No MongoDB backup found. "
            "Local data will be uploaded."
        )

    elif local_dt > mongo_dt:
        direction = "push"

        message = (
            "Local SQLite data appears newer. "
            "Sync will push to MongoDB."
        )

    elif mongo_dt > local_dt:
        direction = "pull"

        message = (
            "MongoDB data appears newer. "
            "Sync will pull into SQLite."
        )

    else:
        direction = "none"

        message = (
            "Local and MongoDB timestamps match. "
            "No sync needed."
        )

    return {
        "direction": direction,
        "message": message,
        "local_timestamp": local_timestamp,
        "mongo_timestamp": mongo_timestamp
    }


def push_local_to_mongo():
    collection = get_mongo_collection()

    local_data = get_local_export()

    sync_timestamp = get_utc_timestamp()

    local_data["exported_at"] = sync_timestamp

    collection.replace_one(
        {"_id": SYNC_DOCUMENT_ID},
        {
            "_id": SYNC_DOCUMENT_ID,
            "last_synced_at": sync_timestamp,
            "data": local_data
        },
        upsert=True
    )

    return sync_timestamp


def pull_mongo_to_local():
    mongo_doc = get_mongo_backup()

    if not mongo_doc:
        raise RuntimeError(
            "No MongoDB backup found to pull."
        )

    data = mongo_doc.get("data")

    if not data:
        raise RuntimeError(
            "MongoDB backup does not contain data."
        )

    json_payload = json.dumps(
        data,
        ensure_ascii=False
    )

    class UploadedFileLike:
        def read(self):
            return json_payload.encode("utf-8")

    result = import_database_from_json(
        UploadedFileLike()
    )

    return result


def sync_now():
    status = get_sync_status()

    direction = status["direction"]

    if direction == "push":
        timestamp = push_local_to_mongo()

        return {
            "direction": "push",
            "message": (
                "Uploaded local SQLite data "
                f"to MongoDB at {timestamp}."
            ),
            "details": None
        }

    if direction == "pull":
        result = pull_mongo_to_local()

        return {
            "direction": "pull",
            "message": (
                "Pulled MongoDB data into "
                "local SQLite."
            ),
            "details": result
        }

    return {
        "direction": "none",
        "message": "No sync needed.",
        "details": None
    }