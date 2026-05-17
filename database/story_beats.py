import json
from datetime import datetime

from database.connection import get_connection
from database.db_encryption import (
    decrypt_database_rows,
    encrypt_database_field,
)
from database.metadata import mark_local_data_modified


def replace_story_beats(story_id, chapter_number, beats):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM story_beats
        WHERE story_id = ?
          AND chapter_number = ?
    """, (
        story_id,
        chapter_number,
    ))

    now = datetime.now().isoformat(timespec="seconds")

    for beat in beats or []:
        cursor.execute("""
            INSERT INTO story_beats
            (
                story_id,
                chapter_number,
                sequence_number,
                beat_type,
                title,
                characters,
                location,
                time_span,
                summary,
                continuity_effect,
                unresolved_threads,
                search_keywords,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story_id,
            chapter_number,
            beat.get("sequence_number"),
            beat.get("beat_type"),
            encrypt_story_beat_field("title", beat.get("title")),
            serialize_and_encrypt("characters", beat.get("characters")),
            encrypt_story_beat_field("location", beat.get("location")),
            encrypt_story_beat_field("time_span", beat.get("time_span")),
            encrypt_story_beat_field("summary", beat.get("summary")),
            encrypt_story_beat_field(
                "continuity_effect",
                beat.get("continuity_effect")
            ),
            serialize_and_encrypt(
                "unresolved_threads",
                beat.get("unresolved_threads")
            ),
            serialize_and_encrypt(
                "search_keywords",
                beat.get("search_keywords")
            ),
            now,
            now,
        ))

    mark_local_data_modified(cursor)
    conn.commit()
    conn.close()


def get_story_beats(story_id=None, chapter_number=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            id,
            story_id,
            chapter_number,
            sequence_number,
            beat_type,
            title,
            characters,
            location,
            time_span,
            summary,
            continuity_effect,
            unresolved_threads,
            search_keywords,
            created_at,
            updated_at
        FROM story_beats
    """
    clauses = []
    values = []

    if story_id is not None:
        clauses.append("story_id = ?")
        values.append(story_id)

    if chapter_number is not None:
        clauses.append("chapter_number = ?")
        values.append(chapter_number)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY story_id, chapter_number, sequence_number"

    cursor.execute(query, tuple(values))

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows("story_beats", cursor.fetchall(), columns)
    conn.close()

    return [
        deserialize_story_beat(dict(zip(columns, row)))
        for row in rows
    ]


def delete_story_beats(story_id, chapter_number=None):
    conn = get_connection()
    cursor = conn.cursor()

    if chapter_number is None:
        cursor.execute("""
            DELETE FROM story_beats
            WHERE story_id = ?
        """, (
            story_id,
        ))
    else:
        cursor.execute("""
            DELETE FROM story_beats
            WHERE story_id = ?
              AND chapter_number = ?
        """, (
            story_id,
            chapter_number,
        ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def encrypt_story_beat_field(field_name, value):
    return encrypt_database_field("story_beats", field_name, value)


def serialize_and_encrypt(field_name, value):
    serialized = json.dumps(value or [], ensure_ascii=False)
    return encrypt_story_beat_field(field_name, serialized)


def deserialize_story_beat(row):
    for field_name in ("characters", "unresolved_threads", "search_keywords"):
        value = row.get(field_name)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = []
            row[field_name] = parsed if isinstance(parsed, list) else []
        elif value is None:
            row[field_name] = []

    return row
