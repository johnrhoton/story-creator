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
    tone_style
):
    return add_story_template(
        template_name,
        overview,
        setting_background,
        tone_style
    )


def edit_template(
    template_id,
    template_name,
    overview,
    setting_background,
    tone_style
):
    update_story_template(
        template_id,
        template_name,
        overview,
        setting_background,
        tone_style
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
