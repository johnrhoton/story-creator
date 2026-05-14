import json
from datetime import datetime

from config import GENDER_OPTIONS
from database.connection import get_connection
from database.metadata import mark_local_data_modified


EXPORT_TABLES = [
    ("characters", "characters"),
    ("profiles", "profiles"),
    ("story_templates", "story_templates"),
    ("story_template_chapters", "story_template_chapters"),
    ("stories", "stories"),
    ("story_chapters", "story_chapters"),
    ("llm_calls", "llm_calls"),
    ("failed_llm_calls", "failed_llm_calls"),
    ("llm_models", "llm_models"),
]


IMPORT_COUNT_KEYS = [
    "profiles",
    "characters",
    "story_templates",
    "story_template_chapters",
    "stories",
    "story_chapters",
    "llm_calls",
    "failed_llm_calls",
    "llm_models",
]


def export_database_to_dict():
    conn = get_connection()
    conn.row_factory = None
    cursor = conn.cursor()

    export_data = {
        "exported_at": datetime.now().isoformat(timespec="seconds")
    }

    for export_key, table_name in EXPORT_TABLES:
        export_data[export_key] = fetch_table_rows(cursor, table_name)

    conn.close()

    return export_data


def serialize_export_to_json(export_data):
    return json.dumps(
        export_data,
        indent=2,
        ensure_ascii=False
    )


def export_database_to_json():
    return serialize_export_to_json(
        export_database_to_dict()
    )


def fetch_table_rows(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id")

    columns = [
        column[0]
        for column in cursor.description
    ]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def import_database_from_json(uploaded_file, replace_existing=False):
    data = deserialize_import_json(uploaded_file)

    return import_database_from_dict(
        data,
        replace_existing=replace_existing
    )


def deserialize_import_json(uploaded_file):
    return json.load(uploaded_file)


def import_database_from_dict(data, replace_existing=False):
    sections = get_import_sections(data)

    conn = get_connection()
    cursor = conn.cursor()

    if replace_existing:
        clear_exported_tables(cursor)

    counts = empty_import_counts()

    # -------------------------
    # LLM Models
    # -------------------------

    for llm_model in sections["llm_models"]:
        provider = llm_model.get("provider", "")
        model = llm_model.get("model", "")

        if not provider or not model:
            continue

        is_default = 1 if llm_model.get("is_default") else 0

        if is_default:
            cursor.execute("""
                UPDATE llm_models
                SET is_default = 0
                WHERE provider = ?
            """, (
                provider,
            ))

        cursor.execute("""
            INSERT OR REPLACE INTO llm_models
            (
                provider,
                model,
                best_use,
                is_default
            )
            VALUES (?, ?, ?, ?)
        """, (
            provider,
            model,
            llm_model.get("best_use", ""),
            is_default
        ))

        counts["llm_models"] += 1

    # -------------------------
    # Profiles
    # -------------------------

    for profile in sections["profiles"]:
        profile_name = (
            profile.get("profile_name") or ""
        ).lower().strip()

        if not profile_name:
            continue

        gender = profile.get("gender") or "female"

        if gender not in GENDER_OPTIONS:
            gender = "female"

        physical_traits = profile.get(
            "physical_traits",
            profile.get("traits", "")
        )

        personality_traits = profile.get(
            "personality_traits",
            ""
        )

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
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            profile.get("notes", "")
        ))

        counts["profiles"] += 1

    # -------------------------
    # Characters
    # -------------------------

    for character in sections["characters"]:
        gender = character.get("gender") or "female"

        if gender not in GENDER_OPTIONS:
            gender = "female"

        profile_name = character.get("profile_name")

        if profile_name:
            profile_name = profile_name.lower()

        physical_traits = character.get(
            "physical_traits",
            character.get("traits", "")
        )

        personality_traits = character.get(
            "personality_traits",
            ""
        )

        cursor.execute("""
            DELETE FROM characters
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
        """, (
            character.get("name", ""),
        ))

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
            character.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            profile_name,
            character.get("name", ""),
            character.get("age", ""),
            gender,
            physical_traits,
            personality_traits,
            character.get("notes", ""),
            character.get("prompt", ""),
            character.get("response", ""),
            character.get("summary", "")
        ))

        counts["characters"] += 1

    # -------------------------
    # Story Templates
    # -------------------------

    template_id_map = {}

    for template in sections["story_templates"]:
        old_id = template.get("id")
        template_name = template.get("template_name", "")

        delete_existing_template_by_name(cursor, template_name)

        cursor.execute("""
            INSERT INTO story_templates
            (
                created_at,
                template_name,
                overview,
                setting_background,
                tone_style
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            template.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            template_name,
            template.get("overview", ""),
            template.get("setting_background", ""),
            template.get("tone_style", "")
        ))

        new_id = cursor.lastrowid

        if old_id is not None:
            template_id_map[old_id] = new_id

        counts["story_templates"] += 1

    # -------------------------
    # Template Chapters
    # -------------------------

    for chapter in sections["story_template_chapters"]:
        old_template_id = chapter.get("template_id")

        new_template_id = template_id_map.get(
            old_template_id,
            old_template_id
        )

        cursor.execute("""
            INSERT INTO story_template_chapters
            (
                template_id,
                chapter_number,
                chapter_description
            )
            VALUES (?, ?, ?)
        """, (
            new_template_id,
            chapter.get("chapter_number", 1),
            chapter.get("chapter_description", "")
        ))

        counts["story_template_chapters"] += 1

    # -------------------------
    # Stories
    # -------------------------

    story_id_map = {}

    for story in sections["stories"]:
        old_id = story.get("id")
        old_template_id = story.get("template_id")
        story_name = story.get("story_name", "")

        new_template_id = template_id_map.get(
            old_template_id,
            old_template_id
        )

        delete_existing_story_by_name(cursor, story_name)

        cursor.execute("""
            INSERT INTO stories
            (
                created_at,
                story_name,
                template_id,
                overview,
                setting_background,
                tone_style,
                male_characters,
                female_characters
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            story_name,
            new_template_id,
            story.get("overview", ""),
            story.get("setting_background", ""),
            story.get("tone_style", ""),
            story.get("male_characters", "[]"),
            story.get("female_characters", "[]")
        ))

        new_id = cursor.lastrowid

        if old_id is not None:
            story_id_map[old_id] = new_id

        counts["stories"] += 1

    # -------------------------
    # Story Chapters
    # -------------------------

    for chapter in sections["story_chapters"]:
        old_story_id = chapter.get("story_id")

        new_story_id = story_id_map.get(
            old_story_id,
            old_story_id
        )

        cursor.execute("""
            INSERT INTO story_chapters
            (
                story_id,
                chapter_number,
                chapter_description,
                chapter_body,
                chapter_summary
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            new_story_id,
            chapter.get("chapter_number", 1),
            chapter.get("chapter_description", ""),
            chapter.get("chapter_body", ""),
            chapter.get("chapter_summary", "")
        ))

        counts["story_chapters"] += 1

    # -------------------------
    # LLM Calls
    # -------------------------

    for llm_call in sections["llm_calls"]:
        cursor.execute("""
            INSERT INTO llm_calls
            (
                created_at,
                provider,
                model,
                prompt,
                response
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            llm_call.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),
            llm_call.get("provider", ""),
            llm_call.get("model", ""),
            llm_call.get("prompt", ""),
            llm_call.get("response", "")
        ))

        counts["llm_calls"] += 1

    # -------------------------
    # Failed LLM Calls
    # -------------------------

    for failed_call in sections["failed_llm_calls"]:
        cursor.execute("""
            INSERT INTO failed_llm_calls
            (
                created_at,
                provider,
                model,
                prompt,
                response,
                error_type,
                error_codes,
                error_message,
                error_details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            failed_call.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),
            failed_call.get("provider", ""),
            failed_call.get("model", ""),
            failed_call.get("prompt", ""),
            failed_call.get("response", ""),
            failed_call.get("error_type", ""),
            failed_call.get("error_codes", ""),
            failed_call.get("error_message", ""),
            failed_call.get("error_details", "")
        ))

        counts["failed_llm_calls"] += 1

    if total_import_count(counts) or replace_existing:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return counts


def get_import_sections(data):
    return {
        "characters": data.get(
            "characters",
            data.get("character_generations", [])
        ),
        "profiles": data.get("profiles", []),
        "story_templates": data.get("story_templates", []),
        "story_template_chapters": data.get("story_template_chapters", []),
        "stories": data.get("stories", []),
        "story_chapters": data.get("story_chapters", []),
        "llm_calls": data.get("llm_calls", []),
        "failed_llm_calls": data.get("failed_llm_calls", []),
        "llm_models": data.get("llm_models", []),
    }


def empty_import_counts():
    return {
        key: 0
        for key in IMPORT_COUNT_KEYS
    }


def total_import_count(counts):
    return sum(counts.values())


def clear_exported_tables(cursor):
    cursor.execute("DELETE FROM llm_models")
    cursor.execute("DELETE FROM failed_llm_calls")
    cursor.execute("DELETE FROM llm_calls")
    cursor.execute("DELETE FROM story_chapters")
    cursor.execute("DELETE FROM stories")
    cursor.execute("DELETE FROM story_template_chapters")
    cursor.execute("DELETE FROM story_templates")
    cursor.execute("DELETE FROM characters")
    cursor.execute("DELETE FROM profiles")


def delete_existing_template_by_name(cursor, template_name):
    if not template_name:
        return

    cursor.execute("""
        SELECT id
        FROM story_templates
        WHERE template_name = ?
    """, (
        template_name,
    ))

    row = cursor.fetchone()

    if not row:
        return

    template_id = row[0]

    cursor.execute("""
        DELETE FROM story_template_chapters
        WHERE template_id = ?
    """, (
        template_id,
    ))

    cursor.execute("""
        DELETE FROM story_templates
        WHERE id = ?
    """, (
        template_id,
    ))


def delete_existing_story_by_name(cursor, story_name):
    if not story_name:
        return

    cursor.execute("""
        SELECT id
        FROM stories
        WHERE story_name = ?
    """, (
        story_name,
    ))

    row = cursor.fetchone()

    if not row:
        return

    story_id = row[0]

    cursor.execute("""
        DELETE FROM story_chapters
        WHERE story_id = ?
    """, (
        story_id,
    ))

    cursor.execute("""
        DELETE FROM stories
        WHERE id = ?
    """, (
        story_id,
    ))
