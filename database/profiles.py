from database.connection import get_connection
from database.metadata import mark_local_data_modified


def add_profile(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO profiles
        (
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        profile_name.lower(),
        gender,
        physical_traits,
        personality_traits,
        notes
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def update_profile(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE profiles
        SET
            gender = ?,
            physical_traits = ?,
            personality_traits = ?,
            notes = ?
        WHERE profile_name = ?
    """, (
        gender,
        physical_traits,
        personality_traits,
        notes,
        profile_name.lower()
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def rename_profile(old_profile_name, new_profile_name):
    conn = get_connection()
    cursor = conn.cursor()

    old_profile_name = old_profile_name.lower()
    new_profile_name = new_profile_name.lower()

    cursor.execute("""
        UPDATE profiles
        SET profile_name = ?
        WHERE profile_name = ?
    """, (
        new_profile_name,
        old_profile_name
    ))
    profile_rows_changed = cursor.rowcount

    cursor.execute("""
        UPDATE characters
        SET profile_name = ?
        WHERE profile_name = ?
    """, (
        new_profile_name,
        old_profile_name
    ))
    character_rows_changed = cursor.rowcount

    if profile_rows_changed or character_rows_changed:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def clone_profile(profile_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM profiles
        WHERE profile_name = ?
    """, (profile_name.lower(),))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    gender, physical_traits, personality_traits, notes = row

    base_name = f"{profile_name.lower()}_copy"
    new_name = base_name
    counter = 1

    while True:
        cursor.execute(
            "SELECT 1 FROM profiles WHERE profile_name = ?",
            (new_name,)
        )

        if not cursor.fetchone():
            break

        counter += 1
        new_name = f"{base_name}_{counter}"

    cursor.execute("""
        INSERT INTO profiles
        (
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        new_name,
        gender,
        physical_traits,
        personality_traits,
        notes
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return new_name


def delete_profile(profile_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM profiles
        WHERE profile_name = ?
    """, (profile_name.lower(),))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_profiles():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM profiles
        ORDER BY gender, profile_name
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows
