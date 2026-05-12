import json
import re
from datetime import datetime

from database.connection import get_connection
from database.metadata import mark_local_data_modified


def replace_character_placeholders(
    text,
    male_characters,
    female_characters
):
    if not text:
        return ""

    def replace_match(match):
        gender_code = match.group(1)
        number = int(match.group(2))
        index = number - 1

        if gender_code == "M":
            if index < len(male_characters):
                return male_characters[index]

            return f"[MISSING MALE CHARACTER M{number}]"

        if gender_code == "F":
            if index < len(female_characters):
                return female_characters[index]

            return f"[MISSING FEMALE CHARACTER F{number}]"

        return match.group(0)

    return re.sub(
        r"\b([MF])(\d+)\b",
        replace_match,
        text
    )


def safe_json_loads(value):
    if not value:
        return []

    try:
        return json.loads(value)

    except Exception:
        return []


def add_story(
    story_name,
    template_id,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    conn = get_connection()
    cursor = conn.cursor()

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
        datetime.now().isoformat(timespec="seconds"),
        story_name,
        template_id,
        overview,
        setting_background,
        tone_style,
        json.dumps(male_characters, ensure_ascii=False),
        json.dumps(female_characters, ensure_ascii=False)
    ))

    story_id = cursor.lastrowid

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return story_id


def update_story(
    story_id,
    story_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE stories
        SET
            story_name = ?,
            overview = ?,
            setting_background = ?,
            tone_style = ?,
            male_characters = ?,
            female_characters = ?
        WHERE id = ?
    """, (
        story_name,
        overview,
        setting_background,
        tone_style,
        json.dumps(male_characters, ensure_ascii=False),
        json.dumps(female_characters, ensure_ascii=False),
        story_id
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def delete_story(story_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM story_chapters
        WHERE story_id = ?
    """, (story_id,))

    cursor.execute("""
        DELETE FROM stories
        WHERE id = ?
    """, (story_id,))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def clone_story(story_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            story_name,
            template_id,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM stories
        WHERE id = ?
    """, (story_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    (
        story_name,
        template_id,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ) = row

    base_name = f"{story_name}_copy"
    new_name = base_name
    counter = 1

    while True:
        cursor.execute(
            "SELECT 1 FROM stories WHERE story_name = ?",
            (new_name,)
        )

        if not cursor.fetchone():
            break

        counter += 1
        new_name = f"{base_name}_{counter}"

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
        datetime.now().isoformat(timespec="seconds"),
        new_name,
        template_id,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ))

    new_story_id = cursor.lastrowid

    cursor.execute("""
        SELECT
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        FROM story_chapters
        WHERE story_id = ?
        ORDER BY chapter_number
    """, (story_id,))

    chapters = cursor.fetchall()

    for chapter in chapters:
        (
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        ) = chapter

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
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return new_story_id


def get_stories():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            story_name,
            template_id,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM stories
        ORDER BY story_name
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_story(story_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            story_name,
            template_id,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM stories
        WHERE id = ?
    """, (story_id,))

    row = cursor.fetchone()

    conn.close()

    return row


def create_story_from_template(
    template_id,
    story_name
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM story_templates
        WHERE id = ?
    """, (template_id,))

    template_row = cursor.fetchone()

    if not template_row:
        conn.close()
        return None

    (
        overview,
        setting_background,
        tone_style,
        male_characters_json,
        female_characters_json
    ) = template_row

    male_characters = safe_json_loads(
        male_characters_json
    )

    female_characters = safe_json_loads(
        female_characters_json
    )

    resolved_overview = replace_character_placeholders(
        overview,
        male_characters,
        female_characters
    )

    resolved_setting_background = replace_character_placeholders(
        setting_background,
        male_characters,
        female_characters
    )

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
        datetime.now().isoformat(timespec="seconds"),
        story_name,
        template_id,
        resolved_overview,
        resolved_setting_background,
        tone_style,
        male_characters_json,
        female_characters_json
    ))

    story_id = cursor.lastrowid

    cursor.execute("""
        SELECT
            chapter_number,
            chapter_description
        FROM story_template_chapters
        WHERE template_id = ?
        ORDER BY chapter_number
    """, (template_id,))

    chapters = cursor.fetchall()

    for (
        chapter_number,
        chapter_description
    ) in chapters:

        resolved_description = replace_character_placeholders(
            chapter_description,
            male_characters,
            female_characters
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
            story_id,
            chapter_number,
            resolved_description,
            "",
            ""
        ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return story_id


def add_story_chapter(
    story_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    conn = get_connection()
    cursor = conn.cursor()

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
        story_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    ))

    chapter_id = cursor.lastrowid

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return chapter_id


def update_story_chapter(
    chapter_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE story_chapters
        SET
            chapter_number = ?,
            chapter_description = ?,
            chapter_body = ?,
            chapter_summary = ?
        WHERE id = ?
    """, (
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary,
        chapter_id
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def delete_story_chapter(chapter_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM story_chapters
        WHERE id = ?
    """, (chapter_id,))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_story_chapters(story_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            story_id,
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        FROM story_chapters
        WHERE story_id = ?
        ORDER BY chapter_number
    """, (story_id,))

    rows = cursor.fetchall()

    conn.close()

    return rows
