import json

from database import (
    add_story_template,
    add_story_template_chapter,
    clone_story_template,
    delete_story_template,
    delete_story_template_chapter,
    delete_story_templates,
    get_story_template_chapters,
    get_story_templates_for_export,
    get_story_templates,
    update_story_template,
    update_story_template_chapter,
)


def parse_character_roles(roles_value):
    if not roles_value:
        return []

    if isinstance(roles_value, list):
        return [str(role) for role in roles_value if role is not None]

    try:
        parsed = json.loads(roles_value)
        if isinstance(parsed, list):
            return [str(role) for role in parsed if role is not None]
    except Exception:
        pass

    return [line.strip() for line in str(roles_value).splitlines() if line.strip()]


def format_character_roles(roles_list):
    if not roles_list:
        return ""

    return "\n".join(str(role) for role in roles_list)


def list_templates():
    return get_story_templates()


def list_templates_for_export(template_ids, decrypt_values=True):
    return get_story_templates_for_export(
        template_ids,
        decrypt_values=decrypt_values
    )


def create_template(
    template_name,
    overview,
    setting_background,
    tone_style,
    male_character_roles=None,
    female_character_roles=None,
):
    return add_story_template(
        template_name,
        overview,
        setting_background,
        tone_style,
        male_character_roles=json.dumps(male_character_roles, ensure_ascii=False)
        if male_character_roles is not None else None,
        female_character_roles=json.dumps(female_character_roles, ensure_ascii=False)
        if female_character_roles is not None else None,
    )


def edit_template(
    template_id,
    template_name,
    overview,
    setting_background,
    tone_style,
    male_character_roles=None,
    female_character_roles=None,
):
    update_story_template(
        template_id,
        template_name,
        overview,
        setting_background,
        tone_style,
        male_character_roles=json.dumps(male_character_roles, ensure_ascii=False)
        if male_character_roles is not None else None,
        female_character_roles=json.dumps(female_character_roles, ensure_ascii=False)
        if female_character_roles is not None else None,
    )


def clone_template(template_id):
    return clone_story_template(template_id)


def delete_template(template_id):
    delete_story_template(template_id)


def delete_templates(template_ids):
    return delete_story_templates(template_ids)


def list_template_chapters(template_id):
    return get_story_template_chapters(template_id)


def create_template_chapter(
    template_id,
    chapter_number,
    chapter_description
):
    return add_story_template_chapter(
        template_id,
        chapter_number,
        chapter_description
    )


def edit_template_chapter(
    chapter_id,
    chapter_number,
    chapter_description
):
    update_story_template_chapter(
        chapter_id,
        chapter_number,
        chapter_description
    )


def delete_template_chapter(chapter_id):
    delete_story_template_chapter(chapter_id)
