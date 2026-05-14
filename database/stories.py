import json
import re
from datetime import datetime

from database.connection import get_connection
from database.db_encryption import (
    decrypt_database_rows,
    decrypt_database_tuple,
    encrypt_database_field,
)
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
        encrypt_database_field("stories", "overview", overview),
        encrypt_database_field(
            "stories",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("stories", "tone_style", tone_style),
        encrypt_database_field(
            "stories",
            "male_characters",
            json.dumps(male_characters, ensure_ascii=False)
        ),
        encrypt_database_field(
            "stories",
            "female_characters",
            json.dumps(female_characters, ensure_ascii=False)
        )
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
        encrypt_database_field("stories", "overview", overview),
        encrypt_database_field(
            "stories",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("stories", "tone_style", tone_style),
        encrypt_database_field(
            "stories",
            "male_characters",
            json.dumps(male_characters, ensure_ascii=False)
        ),
        encrypt_database_field(
            "stories",
            "female_characters",
            json.dumps(female_characters, ensure_ascii=False)
        ),
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


def delete_stories(story_ids):
    if not story_ids:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _story_id in story_ids)

    cursor.execute(f"""
        DELETE FROM story_chapters
        WHERE story_id IN ({placeholders})
    """, tuple(story_ids))

    cursor.execute(f"""
        DELETE FROM stories
        WHERE id IN ({placeholders})
    """, tuple(story_ids))

    deleted_count = cursor.rowcount

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


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
        encrypt_database_field("stories", "overview", overview),
        encrypt_database_field(
            "stories",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("stories", "tone_style", tone_style),
        encrypt_database_field("stories", "male_characters", male_characters),
        encrypt_database_field(
            "stories",
            "female_characters",
            female_characters
        )
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
            encrypt_database_field(
                "story_chapters",
                "chapter_description",
                chapter_description
            ),
            encrypt_database_field(
                "story_chapters",
                "chapter_body",
                chapter_body
            ),
            encrypt_database_field(
                "story_chapters",
                "chapter_summary",
                chapter_summary
            )
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

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "stories",
        cursor.fetchall(),
        columns
    )

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

    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()

    if row:
        row = decrypt_database_tuple("stories", row, columns)

    conn.close()

    return row


def get_stories_for_export(story_ids, decrypt_values=True):
    if not story_ids:
        return {
            "stories": [],
            "story_chapters": []
        }

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _story_id in story_ids)

    cursor.execute(f"""
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
        WHERE id IN ({placeholders})
        ORDER BY story_name
    """, tuple(story_ids))

    story_columns = [column[0] for column in cursor.description]
    story_rows = cursor.fetchall()

    if decrypt_values:
        story_rows = decrypt_database_rows(
            "stories",
            story_rows,
            story_columns
        )

    stories = [
        dict(zip(story_columns, row))
        for row in story_rows
    ]

    cursor.execute(f"""
        SELECT
            id,
            story_id,
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        FROM story_chapters
        WHERE story_id IN ({placeholders})
        ORDER BY story_id, chapter_number
    """, tuple(story_ids))

    chapter_columns = [column[0] for column in cursor.description]
    chapter_rows = cursor.fetchall()

    if decrypt_values:
        chapter_rows = decrypt_database_rows(
            "story_chapters",
            chapter_rows,
            chapter_columns
        )

    chapters = [
        dict(zip(chapter_columns, row))
        for row in chapter_rows
    ]

    conn.close()

    return {
        "stories": stories,
        "story_chapters": chapters
    }


def create_story_from_template(
    template_id,
    story_name,
    male_characters,
    female_characters
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            overview,
            setting_background,
            tone_style
        FROM story_templates
        WHERE id = ?
    """, (template_id,))

    template_columns = [column[0] for column in cursor.description]
    template_row = cursor.fetchone()

    if not template_row:
        conn.close()
        return None

    template_row = decrypt_database_tuple(
        "story_templates",
        template_row,
        template_columns
    )

    (
        overview,
        setting_background,
        tone_style
    ) = template_row

    male_characters_json = json.dumps(
        male_characters,
        ensure_ascii=False
    )

    female_characters_json = json.dumps(
        female_characters,
        ensure_ascii=False
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
        encrypt_database_field("stories", "overview", resolved_overview),
        encrypt_database_field(
            "stories",
            "setting_background",
            resolved_setting_background
        ),
        encrypt_database_field("stories", "tone_style", tone_style),
        encrypt_database_field(
            "stories",
            "male_characters",
            male_characters_json
        ),
        encrypt_database_field(
            "stories",
            "female_characters",
            female_characters_json
        )
    ))

    story_id = cursor.lastrowid

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
        0,
        encrypt_database_field(
            "story_chapters",
            "chapter_description",
            "Establish the setting and introduce the characters."
        ),
        "",
        ""
    ))

    cursor.execute("""
        SELECT
            chapter_number,
            chapter_description
        FROM story_template_chapters
        WHERE template_id = ?
        ORDER BY chapter_number
    """, (template_id,))

    chapter_columns = [column[0] for column in cursor.description]
    chapters = decrypt_database_rows(
        "story_template_chapters",
        cursor.fetchall(),
        chapter_columns
    )

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
            encrypt_database_field(
                "story_chapters",
                "chapter_description",
                resolved_description
            ),
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
        encrypt_database_field(
            "story_chapters",
            "chapter_description",
            chapter_description
        ),
        encrypt_database_field("story_chapters", "chapter_body", chapter_body),
        encrypt_database_field(
            "story_chapters",
            "chapter_summary",
            chapter_summary
        )
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
        encrypt_database_field(
            "story_chapters",
            "chapter_description",
            chapter_description
        ),
        encrypt_database_field("story_chapters", "chapter_body", chapter_body),
        encrypt_database_field(
            "story_chapters",
            "chapter_summary",
            chapter_summary
        ),
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

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "story_chapters",
        cursor.fetchall(),
        columns
    )

    conn.close()

    return rows
