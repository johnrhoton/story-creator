import json
import logging

from database import (
    add_story_template,
    add_story_template_chapter,
    clone_story_template,
    delete_story_template,
    delete_story_template_chapter,
    delete_story_templates,
    get_story_template,
    get_story_template_chapters,
    get_story_templates_for_export,
    get_story_templates,
    log_object_history,
    update_story_template,
    update_story_template_chapter,
)


logger = logging.getLogger(__name__)


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
        logger.exception("Could not parse template character roles JSON.")

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
    template_id = add_story_template(
        template_name,
        overview,
        setting_background,
        tone_style,
        male_character_roles=json.dumps(male_character_roles, ensure_ascii=False)
        if male_character_roles is not None else None,
        female_character_roles=json.dumps(female_character_roles, ensure_ascii=False)
        if female_character_roles is not None else None,
    )
    log_object_history(
        "Templates",
        template_id,
        template_name,
        "Create",
        build_template_history_contents(
            template_name,
            overview,
            setting_background,
            tone_style,
            male_character_roles,
            female_character_roles
        )
    )

    return template_id


def edit_template(
    template_id,
    template_name,
    overview,
    setting_background,
    tone_style,
    male_character_roles=None,
    female_character_roles=None,
):
    male_roles_json = (
        json.dumps(male_character_roles, ensure_ascii=False)
        if male_character_roles is not None else None
    )
    female_roles_json = (
        json.dumps(female_character_roles, ensure_ascii=False)
        if female_character_roles is not None else None
    )
    update_story_template(
        template_id,
        template_name,
        overview,
        setting_background,
        tone_style,
        male_character_roles=male_roles_json,
        female_character_roles=female_roles_json,
    )
    log_object_history(
        "Templates",
        template_id,
        template_name,
        "Update",
        build_template_history_contents(
            template_name,
            overview,
            setting_background,
            tone_style,
            male_character_roles,
            female_character_roles
        )
    )


def clone_template(template_id):
    new_template_id = clone_story_template(template_id)
    if new_template_id:
        template = get_story_template(new_template_id)
        if template:
            log_template_history_from_row(template, "Clone")

    return new_template_id


def delete_template(template_id):
    template = get_story_template(template_id)
    delete_story_template(template_id)
    if template:
        log_template_history_from_row(template, "Delete")


def delete_templates(template_ids):
    templates = [
        get_story_template(template_id)
        for template_id in template_ids
    ]
    deleted_count = delete_story_templates(template_ids)

    for template in templates:
        if template:
            log_template_history_from_row(template, "Delete")

    return deleted_count


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


def build_template_history_contents(
    template_name,
    overview,
    setting_background,
    tone_style,
    male_character_roles,
    female_character_roles
):
    return {
        "template_name": template_name,
        "overview": overview,
        "setting_background": setting_background,
        "tone_style": tone_style,
        "male_character_roles": male_character_roles,
        "female_character_roles": female_character_roles,
    }


def log_template_history_from_row(template, operation):
    (
        template_id,
        _created_at,
        template_name,
        overview,
        setting_background,
        tone_style,
        male_character_roles,
        female_character_roles
    ) = template

    log_object_history(
        "Templates",
        template_id,
        template_name or "Untitled template",
        operation,
        {
            "template_name": template_name,
            "overview": overview,
            "setting_background": setting_background,
            "tone_style": tone_style,
            "male_character_roles": male_character_roles,
            "female_character_roles": female_character_roles,
        }
    )
