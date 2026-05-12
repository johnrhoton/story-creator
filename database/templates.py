import json
from datetime import datetime

from database.connection import get_connection
from database.metadata import mark_local_data_modified


def add_story_template(
    template_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO story_templates
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
        datetime.now().isoformat(timespec="seconds"),
        template_name,
        overview,
        setting_background,
        tone_style,
        json.dumps(male_characters, ensure_ascii=False),
        json.dumps(female_characters, ensure_ascii=False)
    ))

    template_id = cursor.lastrowid
    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return template_id


def update_story_template(
    template_id,
    template_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE story_templates
        SET
            template_name = ?,
            overview = ?,
            setting_background = ?,
            tone_style = ?,
            male_characters = ?,
            female_characters = ?
        WHERE id = ?
    """, (
        template_name,
        overview,
        setting_background,
        tone_style,
        json.dumps(male_characters, ensure_ascii=False),
        json.dumps(female_characters, ensure_ascii=False),
        template_id
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def clone_story_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            template_name,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM story_templates
        WHERE id = ?
    """, (template_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    (
        template_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ) = row

    base_name = f"{template_name}_copy"
    new_name = base_name
    counter = 1

    while True:
        cursor.execute(
            "SELECT 1 FROM story_templates WHERE template_name = ?",
            (new_name,)
        )

        if not cursor.fetchone():
            break

        counter += 1
        new_name = f"{base_name}_{counter}"

    cursor.execute("""
        INSERT INTO story_templates
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
        datetime.now().isoformat(timespec="seconds"),
        new_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ))

    new_template_id = cursor.lastrowid

    cursor.execute("""
        SELECT
            chapter_number,
            chapter_description
        FROM story_template_chapters
        WHERE template_id = ?
        ORDER BY chapter_number
    """, (template_id,))

    chapters = cursor.fetchall()

    for chapter_number, chapter_description in chapters:
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
            chapter_number,
            chapter_description
        ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return new_template_id


def delete_story_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM story_template_chapters
        WHERE template_id = ?
    """, (template_id,))

    cursor.execute("""
        DELETE FROM story_templates
        WHERE id = ?
    """, (template_id,))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_story_templates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            template_name,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM story_templates
        ORDER BY template_name
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_story_template(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            template_name,
            overview,
            setting_background,
            tone_style,
            male_characters,
            female_characters
        FROM story_templates
        WHERE id = ?
    """, (template_id,))

    row = cursor.fetchone()
    conn.close()

    return row


def add_story_template_chapter(
    template_id,
    chapter_number,
    chapter_description
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO story_template_chapters
        (
            template_id,
            chapter_number,
            chapter_description
        )
        VALUES (?, ?, ?)
    """, (
        template_id,
        chapter_number,
        chapter_description
    ))

    chapter_id = cursor.lastrowid

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return chapter_id


def update_story_template_chapter(
    chapter_id,
    chapter_number,
    chapter_description
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE story_template_chapters
        SET
            chapter_number = ?,
            chapter_description = ?
        WHERE id = ?
    """, (
        chapter_number,
        chapter_description,
        chapter_id
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def delete_story_template_chapter(chapter_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM story_template_chapters
        WHERE id = ?
    """, (chapter_id,))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_story_template_chapters(template_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            template_id,
            chapter_number,
            chapter_description
        FROM story_template_chapters
        WHERE template_id = ?
        ORDER BY chapter_number
    """, (template_id,))

    rows = cursor.fetchall()
    conn.close()

    return rows
