from datetime import datetime, timezone

from database.connection import get_connection


LOCAL_DATA_MODIFIED_AT = "local_data_modified_at"
LAST_SYNCED_AT = "last_synced_at"
LAST_SYNCED_CONTENT_HASH = "last_synced_content_hash"


def get_utc_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")


def set_metadata_value(cursor, key, value):
    cursor.execute("""
        INSERT OR REPLACE INTO sync_metadata
        (
            key,
            value
        )
        VALUES (?, ?)
    """, (
        key,
        value
    ))


def get_metadata_value(key):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value
        FROM sync_metadata
        WHERE key = ?
    """, (
        key,
    ))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row[0]


def get_sync_metadata():
    return {
        LOCAL_DATA_MODIFIED_AT: get_metadata_value(LOCAL_DATA_MODIFIED_AT),
        LAST_SYNCED_AT: get_metadata_value(LAST_SYNCED_AT),
        LAST_SYNCED_CONTENT_HASH: get_metadata_value(
            LAST_SYNCED_CONTENT_HASH
        )
    }


def mark_local_data_modified(cursor, timestamp=None):
    set_metadata_value(
        cursor,
        LOCAL_DATA_MODIFIED_AT,
        timestamp or get_utc_timestamp()
    )


def set_sync_metadata(
    last_synced_at,
    content_hash,
    data_modified_at=None
):
    conn = get_connection()
    cursor = conn.cursor()

    set_metadata_value(
        cursor,
        LAST_SYNCED_AT,
        last_synced_at
    )

    set_metadata_value(
        cursor,
        LAST_SYNCED_CONTENT_HASH,
        content_hash
    )

    if data_modified_at:
        set_metadata_value(
            cursor,
            LOCAL_DATA_MODIFIED_AT,
            data_modified_at
        )

    conn.commit()
    conn.close()
