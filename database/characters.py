from datetime import datetime

from database.connection import get_connection
from database.metadata import mark_local_data_modified


def save_character(
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    prompt,
    response,
    summary
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO characters
        (
            created_at,
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            prompt,
            response,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        profile_name.lower() if profile_name else None,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        prompt,
        response,
        summary
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def update_character(
    record_id,
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    response,
    summary
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE characters
        SET
            profile_name = ?,
            name = ?,
            age = ?,
            gender = ?,
            physical_traits = ?,
            personality_traits = ?,
            notes = ?,
            response = ?,
            summary = ?
        WHERE id = ?
    """, (
        profile_name.lower() if profile_name else None,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary,
        record_id
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def clone_character(record_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            prompt,
            response,
            summary
        FROM characters
        WHERE id = ?
    """, (record_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    (
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        prompt,
        response,
        summary
    ) = row

    cursor.execute("""
        INSERT INTO characters
        (
            created_at,
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            prompt,
            response,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        prompt,
        response,
        summary
    ))

    new_id = cursor.lastrowid

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return new_id


def delete_character(record_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM characters
        WHERE id = ?
    """, (record_id,))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def delete_characters(record_ids):
    if not record_ids:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _record_id in record_ids)

    cursor.execute(f"""
        DELETE FROM characters
        WHERE id IN ({placeholders})
    """, tuple(record_ids))

    deleted_count = cursor.rowcount

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


def get_characters():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            response,
            summary
        FROM characters
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_characters_for_export(record_ids):
    if not record_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _record_id in record_ids)

    cursor.execute(f"""
        SELECT
            id,
            created_at,
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            prompt,
            response,
            summary
        FROM characters
        WHERE id IN ({placeholders})
        ORDER BY id
    """, tuple(record_ids))

    columns = [column[0] for column in cursor.description]
    rows = [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

    conn.close()

    return rows


def get_characters_by_gender(gender):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            age,
            gender,
            summary
        FROM characters
        WHERE gender = ?
        ORDER BY name
    """, (gender,))

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_character_summaries_by_names(names):
    if not names:
        return {}

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _name in names)

    cursor.execute(f"""
        SELECT
            name,
            summary
        FROM characters
        WHERE LOWER(TRIM(name)) IN ({placeholders})
    """, tuple(
        name.strip().lower()
        for name in names
    ))

    summaries = {
        row[0].strip().lower(): row[1] or ""
        for row in cursor.fetchall()
        if row[0]
    }

    conn.close()

    return summaries
