from database.connection import get_connection


def run_migrations():
    conn = get_connection()
    cursor = conn.cursor()

    ensure_schema_migrations_table(cursor)

    migrations = [
        (
            "20260511063500_character_traits",
            migrate_20260511063500_character_traits
        ),
        (
            "20260512210000_sync_metadata",
            migrate_20260512210000_sync_metadata
        ),
        (
            "20260512220000_llm_calls",
            migrate_20260512220000_llm_calls
        ),
        (
            "20260513100000_remove_template_characters",
            migrate_20260513100000_remove_template_characters
        ),
    ]

    for migration_id, migration in migrations:
        if migration_applied(cursor, migration_id):
            continue

        migration(cursor)
        mark_migration_applied(cursor, migration_id)
        conn.commit()

    conn.close()


def ensure_schema_migrations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def migration_applied(cursor, migration_id):
    cursor.execute("""
        SELECT 1
        FROM schema_migrations
        WHERE migration_id = ?
    """, (
        migration_id,
    ))

    return cursor.fetchone() is not None


def mark_migration_applied(cursor, migration_id):
    cursor.execute("""
        INSERT INTO schema_migrations
        (
            migration_id
        )
        VALUES (?)
    """, (
        migration_id,
    ))


def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
    """, (
        table_name,
    ))

    return cursor.fetchone() is not None


def get_columns(cursor, table_name):
    if not table_exists(cursor, table_name):
        return []

    cursor.execute(f"PRAGMA table_info({table_name})")

    return [
        column[1]
        for column in cursor.fetchall()
    ]


def add_column_if_missing(cursor, table_name, column_name, definition):
    columns = get_columns(cursor, table_name)

    if column_name in columns:
        return

    cursor.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {definition}
    """)


# 2026-05-11 06:35
# Consolidate earlier character/profile migration work:
# - migrate old character_generations rows into characters when needed
# - split old traits into personality_traits
# - add physical_traits and summary columns where missing
def migrate_20260511063500_character_traits(cursor):
    migrate_profiles(cursor)
    migrate_characters(cursor)


def migrate_profiles(cursor):
    if not table_exists(cursor, "profiles"):
        return

    add_column_if_missing(
        cursor,
        "profiles",
        "physical_traits",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "profiles",
        "personality_traits",
        "TEXT"
    )

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


def migrate_characters(cursor):
    if not table_exists(cursor, "characters"):
        if table_exists(cursor, "character_generations"):
            migrate_character_generations_to_characters(cursor)
        return

    add_column_if_missing(
        cursor,
        "characters",
        "physical_traits",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "characters",
        "personality_traits",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "characters",
        "summary",
        "TEXT"
    )

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

    source_profile_name = (
        "profile_name"
        if "profile_name" in columns
        else "NULL"
    )

    source_traits = (
        "traits"
        if "traits" in columns
        else "''"
    )

    source_notes = (
        "notes"
        if "notes" in columns
        else "''"
    )

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
            response TEXT NOT NULL,
            summary TEXT
        )
    """)

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
            response,
            summary
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
            response,
            ''
        FROM character_generations
    """)


# 2026-05-12 21:00
# Add local sync metadata for safer MongoDB backup direction checks.
def migrate_20260512210000_sync_metadata(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


# 2026-05-12 22:00
# Add an audit log for successful LLM calls.
def migrate_20260512220000_llm_calls(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT
        )
    """)


# 2026-05-13 10:00
# Templates describe reusable structure only. Story-specific character choices
# now belong to stories, so remove male_characters/female_characters from
# story_templates.
def migrate_20260513100000_remove_template_characters(cursor):
    columns = get_columns(cursor, "story_templates")

    if "male_characters" not in columns and "female_characters" not in columns:
        return

    cursor.execute("""
        ALTER TABLE story_templates
        RENAME TO story_templates_old
    """)

    cursor.execute("""
        CREATE TABLE story_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            template_name TEXT NOT NULL UNIQUE,
            overview TEXT,
            setting_background TEXT,
            tone_style TEXT
        )
    """)

    cursor.execute("""
        INSERT INTO story_templates
        (
            id,
            created_at,
            template_name,
            overview,
            setting_background,
            tone_style
        )
        SELECT
            id,
            created_at,
            template_name,
            overview,
            setting_background,
            tone_style
        FROM story_templates_old
    """)

    cursor.execute("""
        DROP TABLE story_templates_old
    """)
