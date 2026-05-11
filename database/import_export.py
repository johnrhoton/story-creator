import json
from datetime import datetime

from config import GENDER_OPTIONS
from database.connection import get_connection


def export_database_to_json():
    conn = get_connection()
    conn.row_factory = None
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM characters ORDER BY id")
    character_columns = [column[0] for column in cursor.description]
    characters = [
        dict(zip(character_columns, row))
        for row in cursor.fetchall()
    ]

    cursor.execute("SELECT * FROM profiles ORDER BY id")
    profile_columns = [column[0] for column in cursor.description]
    profiles = [
        dict(zip(profile_columns, row))
        for row in cursor.fetchall()
    ]

    cursor.execute("SELECT * FROM story_templates ORDER BY id")
    template_columns = [column[0] for column in cursor.description]
    story_templates = [
        dict(zip(template_columns, row))
        for row in cursor.fetchall()
    ]

    cursor.execute("SELECT * FROM story_template_chapters ORDER BY id")
    chapter_columns = [column[0] for column in cursor.description]
    story_template_chapters = [
        dict(zip(chapter_columns, row))
        for row in cursor.fetchall()
    ]

    conn.close()

    export_data = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "characters": characters,
        "profiles": profiles,
        "story_templates": story_templates,
        "story_template_chapters": story_template_chapters
    }

    return json.dumps(
        export_data,
        indent=2,
        ensure_ascii=False
    )


def import_database_from_json(uploaded_file):
    data = json.load(uploaded_file)

    characters = data.get(
        "characters",
        data.get("character_generations", [])
    )

    profiles = data.get("profiles", [])

    story_templates = data.get(
        "story_templates",
        []
    )

    story_template_chapters = data.get(
        "story_template_chapters",
        []
    )

    conn = get_connection()
    cursor = conn.cursor()

    imported_profiles = 0
    imported_characters = 0
    imported_templates = 0
    imported_template_chapters = 0

    # -------------------------
    # Profiles
    # -------------------------

    for profile in profiles:
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
                name,
                age,
                gender,
                physical_traits,
                personality_traits,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_name,
            profile.get("name", ""),
            profile.get("age", ""),
            gender,
            physical_traits,
            personality_traits,
            profile.get("notes", "")
        ))

        imported_profiles += 1

    # -------------------------
    # Characters
    # -------------------------

    for character in characters:
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

        imported_characters += 1

    # -------------------------
    # Story Templates
    # -------------------------

    template_id_map = {}

    for template in story_templates:
        old_id = template.get("id")

        cursor.execute("""
            INSERT OR REPLACE INTO story_templates
            (
                created_at,
                template_name,
                overview,
                setting_background,
                tone_style,
                male_characters,
                female_characters
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            template.get("template_name", ""),
            template.get("overview", ""),
            template.get("setting_background", ""),
            template.get("tone_style", ""),
            template.get("male_characters", "[]"),
            template.get("female_characters", "[]")
        ))

        new_id = cursor.lastrowid

        if old_id is not None:
            template_id_map[old_id] = new_id

        imported_templates += 1

    # -------------------------
    # Template Chapters
    # -------------------------

    for chapter in story_template_chapters:
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
                chapter_description,
                chapter_body,
                chapter_summary
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            new_template_id,
            chapter.get("chapter_number", 1),
            chapter.get("chapter_description", ""),
            chapter.get("chapter_body", ""),
            chapter.get("chapter_summary", "")
        ))

        imported_template_chapters += 1

    conn.commit()
    conn.close()

    return {
        "profiles": imported_profiles,
        "characters": imported_characters,
        "story_templates": imported_templates,
        "story_template_chapters": imported_template_chapters
    }