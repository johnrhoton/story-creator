from database import (
    add_story_template,
    add_story_template_chapter,
    clone_story_template,
    delete_story_template,
    delete_story_template_chapter,
    get_characters_by_gender,
    get_story_template_chapters,
    get_story_templates,
    update_story_template,
    update_story_template_chapter,
)


def list_templates():
    return get_story_templates()


def create_template(
    template_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    return add_story_template(
        template_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    )


def edit_template(
    template_id,
    template_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    update_story_template(
        template_id,
        template_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    )


def clone_template(template_id):
    return clone_story_template(template_id)


def delete_template(template_id):
    delete_story_template(template_id)


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


def list_male_characters():
    return get_characters_by_gender("male")


def list_female_characters():
    return get_characters_by_gender("female")