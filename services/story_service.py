from database import (
    add_story_chapter,
    clone_story,
    create_story_from_template,
    delete_story,
    delete_story_chapter,
    get_stories,
    get_story_chapters,
    get_story_templates,
    update_story,
    update_story_chapter,
)


def list_templates():
    return get_story_templates()


def list_stories():
    return get_stories()


def create_from_template(template_id, story_name):
    return create_story_from_template(template_id, story_name)


def edit_story(
    story_id,
    story_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters
):
    update_story(
        story_id,
        story_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    )


def clone_existing_story(story_id):
    return clone_story(story_id)


def delete_existing_story(story_id):
    delete_story(story_id)


def list_story_chapters(story_id):
    return get_story_chapters(story_id)


def create_story_chapter(
    story_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    return add_story_chapter(
        story_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )


def edit_story_chapter(
    chapter_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    update_story_chapter(
        chapter_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )


def delete_existing_story_chapter(chapter_id):
    delete_story_chapter(chapter_id)