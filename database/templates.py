from datetime import datetime

from database.connection import get_connection
from database.db_encryption import (
    decrypt_database_rows,
    decrypt_database_tuple,
    encrypt_database_field,
)
from database.metadata import mark_local_data_modified


def add_story_template(
    template_name,
    overview,
    setting_background,
    tone_style,
    male_character_roles=None,
    female_character_roles=None,
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
            male_character_roles,
            female_character_roles
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        template_name,
        encrypt_database_field("story_templates", "overview", overview),
        encrypt_database_field(
            "story_templates",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("story_templates", "tone_style", tone_style),
        encrypt_database_field(
            "story_templates",
            "male_character_roles",
            male_character_roles
        ),
        encrypt_database_field(
            "story_templates",
            "female_character_roles",
            female_character_roles
        )
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
    male_character_roles=None,
    female_character_roles=None,
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
            male_character_roles = ?,
            female_character_roles = ?
        WHERE id = ?
    """, (
        template_name,
        encrypt_database_field("story_templates", "overview", overview),
        encrypt_database_field(
            "story_templates",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("story_templates", "tone_style", tone_style),
        encrypt_database_field(
            "story_templates",
            "male_character_roles",
            male_character_roles
        ),
        encrypt_database_field(
            "story_templates",
            "female_character_roles",
            female_character_roles
        ),
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
            male_character_roles,
            female_character_roles
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
        male_character_roles,
        female_character_roles
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
            male_character_roles,
            female_character_roles
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        new_name,
        encrypt_database_field("story_templates", "overview", overview),
        encrypt_database_field(
            "story_templates",
            "setting_background",
            setting_background
        ),
        encrypt_database_field("story_templates", "tone_style", tone_style),
        encrypt_database_field(
            "story_templates",
            "male_character_roles",
            male_character_roles
        ),
        encrypt_database_field(
            "story_templates",
            "female_character_roles",
            female_character_roles
        )
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
            encrypt_database_field(
                "story_template_chapters",
                "chapter_description",
                chapter_description
            )
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


def delete_story_templates(template_ids):
    if not template_ids:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _template_id in template_ids)

    cursor.execute(f"""
        DELETE FROM story_template_chapters
        WHERE template_id IN ({placeholders})
    """, tuple(template_ids))

    cursor.execute(f"""
        DELETE FROM story_templates
        WHERE id IN ({placeholders})
    """, tuple(template_ids))

    deleted_count = cursor.rowcount

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


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
            male_character_roles,
            female_character_roles
        FROM story_templates
        ORDER BY template_name
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "story_templates",
        cursor.fetchall(),
        columns
    )
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
            male_character_roles,
            female_character_roles
        FROM story_templates
        WHERE id = ?
    """, (template_id,))

    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()

    if row:
        row = decrypt_database_tuple("story_templates", row, columns)

    conn.close()

    return row


def get_story_templates_for_export(template_ids, decrypt_values=True):
    if not template_ids:
        return {
            "story_templates": [],
            "story_template_chapters": []
        }

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _template_id in template_ids)

    cursor.execute(f"""
        SELECT
            id,
            created_at,
            template_name,
            overview,
            setting_background,
            tone_style,
            male_character_roles,
            female_character_roles
        FROM story_templates
        WHERE id IN ({placeholders})
        ORDER BY template_name
    """, tuple(template_ids))

    template_columns = [column[0] for column in cursor.description]
    template_rows = cursor.fetchall()

    if decrypt_values:
        template_rows = decrypt_database_rows(
            "story_templates",
            template_rows,
            template_columns
        )

    templates = [
        dict(zip(template_columns, row))
        for row in template_rows
    ]

    cursor.execute(f"""
        SELECT
            id,
            template_id,
            chapter_number,
            chapter_description
        FROM story_template_chapters
        WHERE template_id IN ({placeholders})
        ORDER BY template_id, chapter_number
    """, tuple(template_ids))

    chapter_columns = [column[0] for column in cursor.description]
    chapter_rows = cursor.fetchall()

    if decrypt_values:
        chapter_rows = decrypt_database_rows(
            "story_template_chapters",
            chapter_rows,
            chapter_columns
        )

    chapters = [
        dict(zip(chapter_columns, row))
        for row in chapter_rows
    ]

    conn.close()

    return {
        "story_templates": templates,
        "story_template_chapters": chapters
    }


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
        encrypt_database_field(
            "story_template_chapters",
            "chapter_description",
            chapter_description
        )
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
        encrypt_database_field(
            "story_template_chapters",
            "chapter_description",
            chapter_description
        ),
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

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "story_template_chapters",
        cursor.fetchall(),
        columns
    )
    conn.close()

    return rows
