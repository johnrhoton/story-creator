import json
from datetime import datetime

from database.connection import get_connection
from database.db_encryption import (
    decrypt_database_rows,
    encrypt_database_field,
)
from database.metadata import mark_local_data_modified


def log_object_history(
    object_type,
    object_id,
    object_name,
    operation,
    contents
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO object_history
        (
            created_at,
            object_type,
            object_id,
            object_name,
            operation,
            contents
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        object_type,
        str(object_id) if object_id is not None else "",
        object_name or "",
        operation,
        encrypt_database_field(
            "object_history",
            "contents",
            json.dumps(contents or {}, ensure_ascii=False)
        )
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_object_history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            object_type,
            object_id,
            object_name,
            operation,
            contents
        FROM object_history
        ORDER BY datetime(created_at) DESC, id DESC
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "object_history",
        cursor.fetchall(),
        columns
    )
    conn.close()

    return rows
