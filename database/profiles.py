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
    delete_profiles_by_names(cursor, [profile_name])

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
        encrypt_database_field(
            "profiles",
            "profile_name",
            profile_name.lower()
        ),
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
    profile_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return profile_id


def update_profile(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()
    profile_ids = get_profile_ids_by_names(cursor, [profile_name])

    if not profile_ids:
        conn.close()
        return

    cursor.execute("""
        UPDATE profiles
        SET
            gender = ?,
            physical_traits = ?,
            personality_traits = ?,
            notes = ?
        WHERE id = ?
    """, (
        gender,
        encrypt_database_field("profiles", "physical_traits", physical_traits),
        encrypt_database_field(
            "profiles",
            "personality_traits",
            personality_traits
        ),
        encrypt_database_field("profiles", "notes", notes),
        profile_ids[0]
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
    profile_ids = get_profile_ids_by_names(cursor, [old_profile_name])

    profile_rows_changed = 0

    if profile_ids:
        cursor.execute("""
            UPDATE profiles
            SET profile_name = ?
            WHERE id = ?
        """, (
            encrypt_database_field(
                "profiles",
                "profile_name",
                new_profile_name
            ),
            profile_ids[0]
        ))
        profile_rows_changed = cursor.rowcount

    character_ids = get_character_ids_by_profile_name(
        cursor,
        old_profile_name
    )
    character_rows_changed = 0

    for character_id in character_ids:
        cursor.execute("""
            UPDATE characters
            SET profile_name = ?
            WHERE id = ?
        """, (
            encrypt_database_field(
                "characters",
                "profile_name",
                new_profile_name
            ),
            character_id
        ))
        character_rows_changed += cursor.rowcount

    if profile_rows_changed or character_rows_changed:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def clone_profile(profile_name):
    conn = get_connection()
    cursor = conn.cursor()
    row = get_profile_by_name(cursor, profile_name)

    if not row:
        conn.close()
        return None

    gender, physical_traits, personality_traits, notes = row

    base_name = f"{profile_name.lower()}_copy"
    new_name = base_name
    counter = 1

    while True:
        if not profile_name_exists(cursor, new_name):
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
        encrypt_database_field("profiles", "profile_name", new_name),
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

    deleted_count = delete_profiles_by_names(cursor, [profile_name])

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


def delete_profiles(profile_names):
    if not profile_names:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    deleted_count = delete_profiles_by_names(cursor, profile_names)

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


def get_profiles_for_export(profile_names, decrypt_values=True):
    if not profile_names:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    profile_ids = get_profile_ids_by_names(cursor, profile_names)

    if not profile_ids:
        conn.close()
        return []

    placeholders = ", ".join("?" for _profile_id in profile_ids)

    cursor.execute(f"""
        SELECT
            id,
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM profiles
        WHERE id IN ({placeholders})
        ORDER BY profile_name
    """, tuple(profile_ids))

    columns = [column[0] for column in cursor.description]
    fetched_rows = cursor.fetchall()

    if decrypt_values:
        fetched_rows = decrypt_database_rows(
            "profiles",
            fetched_rows,
            columns
        )

    rows = [
        dict(zip(columns, row))
        for row in fetched_rows
    ]

    conn.close()

    return rows


def get_profile_by_name(cursor, profile_name):
    cursor.execute("""
        SELECT
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM profiles
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "profiles",
        cursor.fetchall(),
        columns
    )

    normalized_name = profile_name.lower()

    for row in rows:
        if row[0] == normalized_name:
            return row[1:]

    return None


def get_profile_ids_by_names(cursor, profile_names):
    normalized_names = {
        profile_name.lower()
        for profile_name in profile_names
    }

    cursor.execute("""
        SELECT
            id,
            profile_name
        FROM profiles
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "profiles",
        cursor.fetchall(),
        columns
    )

    return [
        row[0]
        for row in rows
        if row[1] in normalized_names
    ]


def profile_name_exists(cursor, profile_name):
    return bool(get_profile_ids_by_names(cursor, [profile_name]))


def delete_profiles_by_names(cursor, profile_names):
    profile_ids = get_profile_ids_by_names(cursor, profile_names)

    if not profile_ids:
        return 0

    placeholders = ", ".join("?" for _profile_id in profile_ids)

    cursor.execute(f"""
        DELETE FROM profiles
        WHERE id IN ({placeholders})
    """, tuple(profile_ids))

    return cursor.rowcount


def get_character_ids_by_profile_name(cursor, profile_name):
    cursor.execute("""
        SELECT
            id,
            profile_name
        FROM characters
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "characters",
        cursor.fetchall(),
        columns
    )

    normalized_name = profile_name.lower()

    return [
        row[0]
        for row in rows
        if row[1] == normalized_name
    ]
