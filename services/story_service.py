from database import (
    add_story_chapter,
    clone_story,
    create_story_from_template,
    delete_story,
    delete_story_chapter,
    delete_stories,
    get_characters_by_gender,
    get_stories,
    get_stories_for_export,
    get_story_chapters,
    get_story_templates,
    update_story,
    update_story_chapter,
)
from services.story_generation_service import (
    generate_story_chapter_body_and_summary,
    generate_story_chapters,
)


def list_templates():
    return get_story_templates()


def list_stories():
    return get_stories()


def list_stories_for_export(story_ids, decrypt_values=True):
    return get_stories_for_export(story_ids, decrypt_values=decrypt_values)


def list_male_characters():
    return get_characters_by_gender("male")


def list_female_characters():
    return get_characters_by_gender("female")


def create_from_template(
    template_id,
    story_name,
    male_characters,
    female_characters
):
    story_id = create_story_from_template(
        template_id,
        story_name,
        male_characters,
        female_characters
    )

    if story_id:
        generate_story_chapters(story_id)

    return story_id


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


def delete_existing_stories(story_ids):
    return delete_stories(story_ids)


def list_story_chapters(story_id):
    return get_story_chapters(story_id)


def build_full_story_markdown(chapters):
    sections = []

    sorted_chapters = sorted(
        chapters,
        key=lambda chapter: chapter[2]
    )

    for chapter in sorted_chapters:
        chapter_number = chapter[2]
        chapter_body = (chapter[4] or "").strip()

        if chapter_number < 0:
            continue

        if chapter_body:
            sections.append(
                f"## Chapter {chapter_number}\n\n{chapter_body}"
            )
        else:
            sections.append(f"## Chapter {chapter_number}")

    return "\n\n".join(sections).strip()


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


def create_and_generate_story_chapter(
    story_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    chapter_id = create_story_chapter(
        story_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )

    result = generate_story_chapter_body_and_summary(
        story_id,
        chapter_id
    )

    return chapter_id, result


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
