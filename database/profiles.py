from database.connection import get_connection
from database.db_encryption import (
    decrypt_database_rows,
    encrypt_database_field,
)
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
        encrypt_database_field("profiles", "physical_traits", physical_traits),
        encrypt_database_field(
            "profiles",
            "personality_traits",
            personality_traits
        ),
        encrypt_database_field("profiles", "notes", notes)
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
        encrypt_database_field("profiles", "physical_traits", physical_traits),
        encrypt_database_field(
            "profiles",
            "personality_traits",
            personality_traits
        ),
        encrypt_database_field("profiles", "notes", notes),
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
        encrypt_database_field("profiles", "physical_traits", physical_traits),
        encrypt_database_field(
            "profiles",
            "personality_traits",
            personality_traits
        ),
        encrypt_database_field("profiles", "notes", notes)
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


def delete_profiles(profile_names):
    if not profile_names:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    normalized_names = [
        profile_name.lower()
        for profile_name in profile_names
    ]

    placeholders = ", ".join("?" for _profile_name in normalized_names)

    cursor.execute(f"""
        DELETE FROM profiles
        WHERE profile_name IN ({placeholders})
    """, tuple(normalized_names))

    deleted_count = cursor.rowcount

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


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

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "profiles",
        cursor.fetchall(),
        columns
    )
    conn.close()

    return rows


def get_profiles_for_export(profile_names):
    if not profile_names:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    normalized_names = [
        profile_name.lower()
        for profile_name in profile_names
    ]

    placeholders = ", ".join("?" for _profile_name in normalized_names)

    cursor.execute(f"""
        SELECT
            id,
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM profiles
        WHERE profile_name IN ({placeholders})
        ORDER BY profile_name
    """, tuple(normalized_names))

    columns = [column[0] for column in cursor.description]
    rows = [
        dict(zip(columns, row))
        for row in decrypt_database_rows(
            "profiles",
            cursor.fetchall(),
            columns
        )
    ]

    conn.close()

    return rows
