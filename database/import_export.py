import json
from datetime import datetime

import yaml

from config import GENDER_OPTIONS
from database.connection import get_connection
from database.db_encryption import (
    DATABASE_ENCRYPTION_EXPORT_KEY,
    apply_database_encryption_export_metadata,
    decrypt_database_row,
    encrypt_database_row,
    get_database_encryption_export_metadata,
    initialize_database_encryption,
    is_database_encrypted_value,
    is_database_encryption_enabled,
    set_active_database_password,
)
from database.export_crypto import (
    decrypt_export_values,
)
from database.metadata import mark_local_data_modified


EXPORT_TABLES = [
    ("characters", "characters"),
    ("profiles", "profiles"),
    ("story_templates", "story_templates"),
    ("story_template_chapters", "story_template_chapters"),
    ("stories", "stories"),
    ("story_chapters", "story_chapters"),
    ("story_beats", "story_beats"),
    ("llm_calls", "llm_calls"),
    ("failed_llm_calls", "failed_llm_calls"),
    ("llm_models", "llm_models"),
    ("object_history", "object_history"),
    ("app_events", "app_events"),
]


IMPORT_COUNT_KEYS = [
    "profiles",
    "characters",
    "story_templates",
    "story_template_chapters",
    "stories",
    "story_chapters",
    "story_beats",
    "llm_calls",
    "failed_llm_calls",
    "llm_models",
    "object_history",
    "app_events",
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


def serialize_export_to_yaml(export_data):
    return yaml.safe_dump(
        export_data,
        allow_unicode=True,
        sort_keys=False
    )


def prepare_export_data(encrypt_values=False, password=""):
    export_data = export_database_to_dict()

    if encrypt_values:
        return add_database_encryption_export_metadata(export_data)

    export_data = decrypt_database_export_data(export_data)

    if password:
        export_data = decrypt_export_values(export_data, password)

    return export_data


def add_database_encryption_export_metadata(export_data):
    metadata = get_database_encryption_export_metadata()

    if not metadata:
        return export_data

    export_data = dict(export_data)
    export_data[DATABASE_ENCRYPTION_EXPORT_KEY] = metadata

    return export_data


def decrypt_database_export_data(export_data):
    decrypted_data = dict(export_data)

    for export_key, table_name in EXPORT_TABLES:
        decrypted_data[export_key] = [
            decrypt_database_row(table_name, row)
            for row in export_data.get(export_key, [])
        ]

    return decrypted_data


def export_database_to_json(encrypt_values=False, password=""):
    return serialize_export_to_json(
        prepare_export_data(
            encrypt_values=encrypt_values,
            password=password
        )
    )


def export_database_to_yaml(encrypt_values=False, password=""):
    return serialize_export_to_yaml(
        prepare_export_data(
            encrypt_values=encrypt_values,
            password=password
        )
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


def import_database_from_json(
    uploaded_file,
    replace_existing=False,
    password="",
    database_password=""
):
    data = deserialize_import_json(uploaded_file)

    if password:
        data = decrypt_export_values(data, password)

    return import_database_from_dict(
        data,
        replace_existing=replace_existing,
        database_password=database_password
    )


def import_database_from_yaml(
    uploaded_file,
    replace_existing=False,
    password="",
    database_password=""
):
    data = deserialize_import_yaml(uploaded_file)

    if password:
        data = decrypt_export_values(data, password)

    return import_database_from_dict(
        data,
        replace_existing=replace_existing,
        database_password=database_password
    )


def deserialize_import_json(uploaded_file):
    return json.loads(read_uploaded_text(uploaded_file))


def deserialize_import_yaml(uploaded_file):
    return yaml.safe_load(read_uploaded_text(uploaded_file)) or {}


def read_uploaded_text(uploaded_file):
    content = uploaded_file.read()

    if isinstance(content, bytes):
        return content.decode("utf-8")

    return content


def import_database_from_dict(
    data,
    replace_existing=False,
    database_password=""
):
    sections = get_import_sections(data)

    if database_password and DATABASE_ENCRYPTION_EXPORT_KEY not in data:
        initialize_database_encryption(database_password)

    conn = get_connection()
    cursor = conn.cursor()

    if replace_existing:
        clear_exported_tables(cursor)

    apply_database_encryption_export_metadata(
        data.get(DATABASE_ENCRYPTION_EXPORT_KEY),
        cursor
    )

    if database_password and DATABASE_ENCRYPTION_EXPORT_KEY in data:
        set_active_database_password(database_password)

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
        )

        if not is_database_encrypted_value(profile_name):
            profile_name = profile_name.lower().strip()

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
        profile_row = encrypt_database_row(
            "profiles",
            {
                "profile_name": profile_name,
                "physical_traits": physical_traits,
                "personality_traits": personality_traits,
                "notes": profile.get("notes", ""),
            }
        )

        if (
            not replace_existing
            and not is_database_encrypted_value(profile_name)
        ):
            delete_existing_profile_by_name(cursor, profile_name)

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
            profile_row["profile_name"],
            gender,
            profile_row["physical_traits"],
            profile_row["personality_traits"],
            profile_row["notes"]
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

        if profile_name and not is_database_encrypted_value(profile_name):
            profile_name = profile_name.lower()

        physical_traits = character.get(
            "physical_traits",
            character.get("traits", "")
        )

        personality_traits = character.get(
            "personality_traits",
            ""
        )
        character_row = encrypt_database_row(
            "characters",
            {
                "profile_name": profile_name,
                "physical_traits": physical_traits,
                "personality_traits": personality_traits,
                "notes": character.get("notes", ""),
                "prompt": character.get("prompt", ""),
                "response": character.get("response", ""),
                "summary": character.get("summary", ""),
            }
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

            character_row["profile_name"],
            character.get("name", ""),
            character.get("age", ""),
            gender,
            character_row["physical_traits"],
            character_row["personality_traits"],
            character_row["notes"],
            character_row["prompt"],
            character_row["response"],
            character_row["summary"]
        ))

        counts["characters"] += 1

    # -------------------------
    # Story Templates
    # -------------------------

    template_id_map = {}

    for template in sections["story_templates"]:
        old_id = template.get("id")
        template_name = template.get("template_name", "")
        template_row = encrypt_database_row(
            "story_templates",
            {
                "overview": template.get("overview", ""),
                "setting_background": template.get(
                    "setting_background",
                    ""
                ),
                "tone_style": template.get("tone_style", ""),
                "male_character_roles": template.get(
                    "male_character_roles",
                    "[]"
                ),
                "female_character_roles": template.get(
                    "female_character_roles",
                    "[]"
                ),
            }
        )

        if not replace_existing:
            delete_existing_template_by_name(cursor, template_name)

        cursor.execute("""
            INSERT INTO story_templates
            (
                created_at,
                template_name,
                overview,
                setting_background,
                tone_style,
                male_character_roles,
                female_character_roles
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            template.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            template_name,
            template_row["overview"],
            template_row["setting_background"],
            template_row["tone_style"],
            template_row["male_character_roles"],
            template_row["female_character_roles"]
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
        chapter_row = encrypt_database_row(
            "story_template_chapters",
            {
                "chapter_description": chapter.get(
                    "chapter_description",
                    ""
                ),
            }
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
            chapter_row["chapter_description"]
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
        story_row = encrypt_database_row(
            "stories",
            {
                "overview": story.get("overview", ""),
                "setting_background": story.get("setting_background", ""),
                "tone_style": story.get("tone_style", ""),
                "additional_instructions": story.get(
                    "additional_instructions",
                    ""
                ),
                "language": story.get("language", ""),
                "language_level": story.get("language_level", ""),
                "male_characters": story.get("male_characters", "[]"),
                "female_characters": story.get("female_characters", "[]"),
            }
        )

        new_template_id = template_id_map.get(
            old_template_id,
            old_template_id
        )

        if not replace_existing:
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
                additional_instructions,
                language,
                language_level,
                male_characters,
                female_characters
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),

            story_name,
            new_template_id,
            story_row["overview"],
            story_row["setting_background"],
            story_row["tone_style"],
            story_row["additional_instructions"],
            story_row["language"],
            story_row["language_level"],
            story_row["male_characters"],
            story_row["female_characters"]
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
        chapter_row = encrypt_database_row(
            "story_chapters",
            {
                "chapter_description": chapter.get(
                    "chapter_description",
                    ""
                ),
                "chapter_body": chapter.get("chapter_body", ""),
                "chapter_summary": chapter.get("chapter_summary", ""),
            }
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
            chapter_row["chapter_description"],
            chapter_row["chapter_body"],
            chapter_row["chapter_summary"]
        ))

        counts["story_chapters"] += 1

    # -------------------------
    # Story Beats
    # -------------------------

    for beat in sections["story_beats"]:
        old_story_id = beat.get("story_id")
        new_story_id = story_id_map.get(
            old_story_id,
            old_story_id
        )
        beat_row = encrypt_database_row(
            "story_beats",
            {
                "title": beat.get("title", ""),
                "characters": serialize_import_list(
                    beat.get("characters", [])
                ),
                "location": beat.get("location", ""),
                "time_span": beat.get("time_span", ""),
                "summary": beat.get("summary", ""),
                "continuity_effect": beat.get("continuity_effect", ""),
                "unresolved_threads": serialize_import_list(
                    beat.get("unresolved_threads", [])
                ),
                "search_keywords": serialize_import_list(
                    beat.get("search_keywords", [])
                ),
            }
        )

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
            new_story_id,
            beat.get("chapter_number", 1),
            beat.get("sequence_number", 1),
            beat.get("beat_type", "scene"),
            beat_row["title"],
            beat_row["characters"],
            beat_row["location"],
            beat_row["time_span"],
            beat_row["summary"],
            beat_row["continuity_effect"],
            beat_row["unresolved_threads"],
            beat_row["search_keywords"],
            beat.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),
            beat.get("updated_at")
            or datetime.now().isoformat(timespec="seconds"),
        ))

        counts["story_beats"] += 1

    # -------------------------
    # LLM Calls
    # -------------------------

    for llm_call in sections["llm_calls"]:
        llm_call_row = encrypt_database_row(
            "llm_calls",
            {
                "prompt": llm_call.get("prompt", ""),
                "response": llm_call.get("response", ""),
            }
        )

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
            llm_call_row["prompt"],
            llm_call_row["response"]
        ))

        counts["llm_calls"] += 1

    # -------------------------
    # Failed LLM Calls
    # -------------------------

    for failed_call in sections["failed_llm_calls"]:
        failed_call_row = encrypt_database_row(
            "failed_llm_calls",
            {
                "prompt": failed_call.get("prompt", ""),
                "response": failed_call.get("response", ""),
                "error_message": failed_call.get("error_message", ""),
                "error_details": failed_call.get("error_details", ""),
            }
        )

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
            failed_call_row["prompt"],
            failed_call_row["response"],
            failed_call.get("error_type", ""),
            failed_call.get("error_codes", ""),
            failed_call_row["error_message"],
            failed_call_row["error_details"]
        ))

        counts["failed_llm_calls"] += 1

    # -------------------------
    # Object History
    # -------------------------

    for history_entry in sections["object_history"]:
        history_row = encrypt_database_row(
            "object_history",
            {
                "contents": history_entry.get("contents", ""),
            }
        )

        cursor.execute("""
            INSERT INTO object_history
            (
                created_at,
                object_type,
                object_id,
                object_name,
                operation,
                contents
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            history_entry.get("created_at")
            or datetime.now().isoformat(timespec="seconds"),
            history_entry.get("object_type", ""),
            history_entry.get("object_id", ""),
            history_entry.get("object_name", ""),
            history_entry.get("operation", ""),
            history_row["contents"]
        ))

        counts["object_history"] += 1

    # -------------------------
    # App Events
    # -------------------------

    for event in sections["app_events"]:
        cursor.execute("""
            INSERT INTO app_events
            (
                event_type,
                timestamp,
                status,
                duration_ms,
                story_id,
                chapter_id,
                template_id,
                character_id,
                provider,
                model,
                token_estimate,
                error_type,
                error_message,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("event_type", ""),
            event.get("timestamp")
            or datetime.now().isoformat(timespec="seconds"),
            event.get("status", ""),
            event.get("duration_ms"),
            event.get("story_id"),
            event.get("chapter_id"),
            event.get("template_id"),
            event.get("character_id"),
            event.get("provider", ""),
            event.get("model", ""),
            event.get("token_estimate"),
            event.get("error_type", ""),
            event.get("error_message", ""),
            event.get("metadata_json", ""),
        ))

        counts["app_events"] += 1

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
        "story_beats": data.get("story_beats", []),
        "llm_calls": data.get("llm_calls", []),
        "failed_llm_calls": data.get("failed_llm_calls", []),
        "llm_models": data.get("llm_models", []),
        "object_history": data.get("object_history", []),
        "app_events": data.get("app_events", []),
    }


def serialize_import_list(value):
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)

    return "[]"


def empty_import_counts():
    return {
        key: 0
        for key in IMPORT_COUNT_KEYS
    }


def total_import_count(counts):
    return sum(counts.values())


def clear_exported_tables(cursor):
    cursor.execute("DELETE FROM app_events")
    cursor.execute("DELETE FROM object_history")
    cursor.execute("DELETE FROM llm_models")
    cursor.execute("DELETE FROM failed_llm_calls")
    cursor.execute("DELETE FROM llm_calls")
    cursor.execute("DELETE FROM story_beats")
    cursor.execute("DELETE FROM story_chapters")
    cursor.execute("DELETE FROM stories")
    cursor.execute("DELETE FROM story_template_chapters")
    cursor.execute("DELETE FROM story_templates")
    cursor.execute("DELETE FROM characters")
    cursor.execute("DELETE FROM profiles")


def delete_existing_profile_by_name(cursor, profile_name):
    if not profile_name:
        return

    cursor.execute("""
        SELECT
            id,
            profile_name
        FROM profiles
    """)

    columns = [column[0] for column in cursor.description]
    rows = [
        decrypt_database_row(
            "profiles",
            dict(zip(columns, row))
        )
        for row in cursor.fetchall()
    ]

    profile_ids = [
        row["id"]
        for row in rows
        if row["profile_name"] == profile_name
    ]

    if not profile_ids:
        return

    placeholders = ", ".join("?" for _profile_id in profile_ids)

    cursor.execute(f"""
        DELETE FROM profiles
        WHERE id IN ({placeholders})
    """, tuple(profile_ids))


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
        DELETE FROM story_beats
        WHERE story_id = ?
    """, (
        story_id,
    ))

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
