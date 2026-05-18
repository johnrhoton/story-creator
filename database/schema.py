from database.connection import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT NOT NULL UNIQUE,
            gender TEXT,
            physical_traits TEXT,
            personality_traits TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_number INTEGER NOT NULL,
            gender TEXT NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(gender, name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            template_name TEXT NOT NULL UNIQUE,
            overview TEXT,
            setting_background TEXT,
            tone_style TEXT,
            male_character_roles TEXT,
            female_character_roles TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_template_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            chapter_description TEXT,
            FOREIGN KEY (template_id)
                REFERENCES story_templates (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            story_name TEXT NOT NULL UNIQUE,
            template_id INTEGER,
            overview TEXT,
            setting_background TEXT,
            tone_style TEXT,
            additional_instructions TEXT,
            language TEXT,
            language_level TEXT,
            male_characters TEXT,
            female_characters TEXT,
            FOREIGN KEY (template_id)
                REFERENCES story_templates (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            chapter_description TEXT,
            chapter_body TEXT,
            chapter_summary TEXT,
            FOREIGN KEY (story_id)
                REFERENCES stories (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_beats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            beat_type TEXT NOT NULL,
            title TEXT,
            characters TEXT,
            location TEXT,
            time_span TEXT,
            summary TEXT,
            continuity_effect TEXT,
            unresolved_threads TEXT,
            search_keywords TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (story_id)
                REFERENCES stories (id)
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS failed_llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT,
            error_type TEXT,
            error_codes TEXT,
            error_message TEXT,
            error_details TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            best_use TEXT,
            is_default INTEGER NOT NULL DEFAULT 0,
            UNIQUE(provider, model)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS object_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT,
            object_name TEXT,
            operation TEXT NOT NULL,
            contents TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            google_sub TEXT UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    from database.authorized_users import seed_default_authorized_user

    seed_default_authorized_user(cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
