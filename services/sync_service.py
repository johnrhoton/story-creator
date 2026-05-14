# services/sync_service.py

import hashlib
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

from config import (
    MONGODB_DEFAULT_DATABASE,
    MONGODB_LEGACY_SYNC_DOCUMENT_ID,
    MONGODB_SYNC_COLLECTION,
    MONGODB_SYNC_DOCUMENT_ID,
)
from database import (
    export_database_to_json,
    get_sync_metadata,
    import_database_from_json,
    set_sync_metadata,
)


SYNC_DOCUMENT_ID = MONGODB_SYNC_DOCUMENT_ID
LEGACY_SYNC_DOCUMENT_ID = MONGODB_LEGACY_SYNC_DOCUMENT_ID
SYNC_COLLECTION = MONGODB_SYNC_COLLECTION


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
        MONGODB_DEFAULT_DATABASE
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


def get_content_hash(data):
    hash_data = normalise_for_content_hash(data)

    encoded_data = json.dumps(
        hash_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    return hashlib.sha256(encoded_data).hexdigest()


def normalise_for_content_hash(data):
    normalised = {}

    for key, value in data.items():
        if key == "exported_at":
            continue

        if key == "characters":
            normalised[key] = normalise_rows(value, ["id"])
        elif key == "profiles":
            normalised[key] = normalise_rows(value, ["id"])
        elif key == "story_templates":
            normalised[key] = normalise_rows(value, ["id"])
        elif key == "story_template_chapters":
            normalised[key] = normalise_rows(value, ["id", "template_id"])
        elif key == "stories":
            normalised[key] = normalise_rows(value, ["id", "template_id"])
        elif key == "story_chapters":
            normalised[key] = normalise_rows(value, ["id", "story_id"])
        elif key == "llm_calls":
            normalised[key] = normalise_rows(value, ["id"])
        elif key == "failed_llm_calls":
            normalised[key] = normalise_rows(value, ["id"])
        elif key == "llm_models":
            normalised[key] = normalise_rows(value, ["id"])
        else:
            normalised[key] = value

    return normalised


def normalise_rows(rows, ignored_keys):
    normalised_rows = []

    for row in rows:
        normalised_rows.append({
            key: value
            for key, value in row.items()
            if key not in ignored_keys
        })

    return sorted(
        normalised_rows,
        key=lambda row: json.dumps(
            row,
            sort_keys=True,
            ensure_ascii=False
        )
    )


def get_mongo_backup():
    collection = get_mongo_collection()

    mongo_doc = collection.find_one(
        {"_id": SYNC_DOCUMENT_ID}
    )

    if mongo_doc:
        return mongo_doc

    return collection.find_one(
        {"_id": LEGACY_SYNC_DOCUMENT_ID}
    )


def get_sync_status():
    local_data = get_local_export()
    local_hash = get_content_hash(local_data)
    metadata = get_sync_metadata()

    mongo_doc = get_mongo_backup()

    local_timestamp = metadata.get(
        "local_data_modified_at"
    )

    mongo_timestamp = None
    mongo_hash = None
    last_synced_hash = metadata.get(
        "last_synced_content_hash"
    )

    if mongo_doc:
        mongo_timestamp = mongo_doc.get(
            "data_modified_at"
        ) or mongo_doc.get(
            "last_synced_at"
        )

        mongo_data = mongo_doc.get("data")

        if mongo_data:
            mongo_hash = (
                mongo_doc.get("content_hash")
                or get_content_hash(mongo_data)
            )

    if not mongo_doc or not mongo_hash:
        direction = "push"

        message = (
            "No MongoDB backup found. "
            "Local data will be uploaded."
        )

    elif local_hash == mongo_hash:
        direction = "none"

        message = (
            "Local SQLite data and MongoDB backup have the same content. "
            "No sync needed."
        )

    elif not last_synced_hash:
        direction = "conflict"

        message = (
            "Local SQLite data and MongoDB backup are different, and this "
            "device has no previous sync baseline. Choose manually whether "
            "to push local data or pull the MongoDB backup."
        )

    else:
        local_changed = local_hash != last_synced_hash
        mongo_changed = mongo_hash != last_synced_hash

        if local_changed and mongo_changed:
            direction = "conflict"

            message = (
                "Both local SQLite data and MongoDB backup changed since "
                "the last sync. Choose manually whether to keep local data "
                "or replace it with MongoDB."
            )

        elif local_changed:
            direction = "push"

            message = (
                "Local SQLite data changed since the last sync. "
                "Sync will push to MongoDB."
            )

        elif mongo_changed:
            direction = "pull"

            message = (
                "MongoDB backup changed since the last sync. "
                "Sync will pull into SQLite."
            )

        else:
            direction = "none"

            message = (
                "Local and MongoDB content match the last sync. "
                "No sync needed."
            )

    if direction == "push":
        local_timestamp = (
            local_timestamp
            or local_data.get("exported_at")
        )

    return {
        "direction": direction,
        "message": message,
        "local_timestamp": local_timestamp,
        "mongo_timestamp": mongo_timestamp,
        "local_hash": local_hash,
        "mongo_hash": mongo_hash,
        "last_synced_hash": last_synced_hash
    }


def push_local_to_mongo():
    collection = get_mongo_collection()

    local_data = get_local_export()
    local_hash = get_content_hash(local_data)
    metadata = get_sync_metadata()

    sync_timestamp = get_utc_timestamp()

    data_modified_at = (
        metadata.get("local_data_modified_at")
        or sync_timestamp
    )

    local_data["exported_at"] = sync_timestamp

    collection.replace_one(
        {"_id": SYNC_DOCUMENT_ID},
        {
            "_id": SYNC_DOCUMENT_ID,
            "last_synced_at": sync_timestamp,
            "data_modified_at": data_modified_at,
            "content_hash": local_hash,
            "data": local_data
        },
        upsert=True
    )

    set_sync_metadata(
        sync_timestamp,
        local_hash,
        data_modified_at
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

    mongo_hash = (
        mongo_doc.get("content_hash")
        or get_content_hash(data)
    )

    data_modified_at = (
        mongo_doc.get("data_modified_at")
        or mongo_doc.get("last_synced_at")
        or get_utc_timestamp()
    )

    json_payload = json.dumps(
        data,
        ensure_ascii=False
    )

    class UploadedFileLike:
        def read(self):
            return json_payload.encode("utf-8")

    result = import_database_from_json(
        UploadedFileLike(),
        replace_existing=True
    )

    sync_timestamp = get_utc_timestamp()

    set_sync_metadata(
        sync_timestamp,
        mongo_hash,
        data_modified_at
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

    if direction == "conflict":
        return {
            "direction": "conflict",
            "message": status["message"],
            "details": {
                "local_timestamp": status["local_timestamp"],
                "mongo_timestamp": status["mongo_timestamp"],
                "local_hash": status["local_hash"],
                "mongo_hash": status["mongo_hash"]
            }
        }

    return {
        "direction": "none",
        "message": "No sync needed.",
        "details": None
    }
