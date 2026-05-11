import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DB_NAME


def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
    """, (table_name,))

    return cursor.fetchone() is not None


def get_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [column[1] for column in cursor.fetchall()]


def backup_database(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(
        f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    )

    shutil.copy2(db_path, backup_path)

    return backup_path


def migrate_profiles(cursor):
    if not table_exists(cursor, "profiles"):
        return

    columns = get_columns(cursor, "profiles")

    if "physical_traits" not in columns:
        cursor.execute("""
            ALTER TABLE profiles
            ADD COLUMN physical_traits TEXT
        """)

    if "personality_traits" not in columns:
        cursor.execute("""
            ALTER TABLE profiles
            ADD COLUMN personality_traits TEXT
        """)

    columns = get_columns(cursor, "profiles")

    if "traits" in columns:
        cursor.execute("""
            UPDATE profiles
            SET personality_traits = COALESCE(personality_traits, traits, '')
            WHERE personality_traits IS NULL
               OR personality_traits = ''
        """)

    cursor.execute("""
        UPDATE profiles
        SET physical_traits = COALESCE(physical_traits, '')
        WHERE physical_traits IS NULL
    """)


def migrate_characters_table(cursor):
    old_characters_exists = table_exists(cursor, "characters")
    old_generations_exists = table_exists(cursor, "character_generations")

    if old_characters_exists:
        migrate_existing_characters(cursor)
    elif old_generations_exists:
        migrate_character_generations_to_characters(cursor)
    else:
        create_new_characters_table(cursor)


def migrate_existing_characters(cursor):
    columns = get_columns(cursor, "characters")

    if "physical_traits" not in columns:
        cursor.execute("""
            ALTER TABLE characters
            ADD COLUMN physical_traits TEXT
        """)

    if "personality_traits" not in columns:
        cursor.execute("""
            ALTER TABLE characters
            ADD COLUMN personality_traits TEXT
        """)

    columns = get_columns(cursor, "characters")

    if "traits" in columns:
        cursor.execute("""
            UPDATE characters
            SET personality_traits = COALESCE(personality_traits, traits, '')
            WHERE personality_traits IS NULL
               OR personality_traits = ''
        """)

    cursor.execute("""
        UPDATE characters
        SET physical_traits = COALESCE(physical_traits, '')
        WHERE physical_traits IS NULL
    """)


def migrate_character_generations_to_characters(cursor):
    columns = get_columns(cursor, "character_generations")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            profile_name TEXT,
            name TEXT,
            age TEXT,
            gender TEXT,
            physical_traits TEXT,
            personality_traits TEXT,
            notes TEXT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL
        )
    """)

    source_profile_name = "profile_name" if "profile_name" in columns else "NULL"
    source_traits = "traits" if "traits" in columns else "''"
    source_notes = "notes" if "notes" in columns else "''"

    cursor.execute(f"""
        INSERT INTO characters
        (
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
            response
        )
        SELECT
            id,
            created_at,
            {source_profile_name},
            name,
            age,
            gender,
            '',
            {source_traits},
            {source_notes},
            prompt,
            response
        FROM character_generations
    """)


def create_new_characters_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            profile_name TEXT,
            name TEXT,
            age TEXT,
            gender TEXT,
            physical_traits TEXT,
            personality_traits TEXT,
            notes TEXT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL
        )
    """)


def migrate():
    db_path = Path(DB_NAME)

    if not db_path.exists():
        print(f"Database not found: {DB_NAME}")
        return

    backup_path = backup_database(db_path)
    print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    migrate_profiles(cursor)
    migrate_characters_table(cursor)

    conn.commit()
    conn.close()

    print("Migration complete.")
    print("physical_traits set to empty where missing.")
    print("old traits copied to personality_traits where applicable.")


if __name__ == "__main__":
    migrate()