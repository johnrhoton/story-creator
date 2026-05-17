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
    get_story,
    get_story_chapters,
    get_story_chapter,
    get_story_templates,
    log_object_history,
    update_story,
    update_story_chapter,
)
from services.rag_indexing_service import (
    delete_chapter_summary_memory,
    delete_story_memory,
    index_chapter_summary,
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
    female_characters,
    additional_instructions="",
    language="",
    language_level="",
    progress_callback=None
):
    story_id = create_story_from_template(
        template_id,
        story_name,
        male_characters,
        female_characters,
        additional_instructions=additional_instructions,
        language=language,
        language_level=language_level
    )

    if story_id:
        story = get_story(story_id)
        if story:
            log_story_history_from_row(story, "Create")
        generate_story_chapters(story_id, progress_callback=progress_callback)

    return story_id


def edit_story(
    story_id,
    story_name,
    overview,
    setting_background,
    tone_style,
    male_characters,
    female_characters,
    additional_instructions="",
    language="",
    language_level=""
):
    update_story(
        story_id,
        story_name,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters,
        additional_instructions=additional_instructions,
        language=language,
        language_level=language_level
    )
    story = get_story(story_id)
    if story:
        log_story_history_from_row(story, "Update")


def clone_existing_story(story_id):
    new_story_id = clone_story(story_id)
    story = get_story(new_story_id) if new_story_id else None
    if story:
        log_story_history_from_row(story, "Clone")

    return new_story_id


def delete_existing_story(story_id):
    story = get_story(story_id)
    chapters = get_story_chapters(story_id)
    delete_story(story_id)
    delete_story_memory(story_id)

    for chapter in chapters:
        delete_chapter_summary_memory(chapter[1], chapter[2])

    if story:
        log_story_history_from_row(story, "Delete")


def delete_existing_stories(story_ids):
    stories_by_id = {
        story_id: get_story(story_id)
        for story_id in story_ids
    }
    chapters_by_story_id = {
        story_id: get_story_chapters(story_id)
        for story_id in story_ids
    }
    deleted_count = delete_stories(story_ids)

    for story_id in story_ids:
        delete_story_memory(story_id)

    for chapters in chapters_by_story_id.values():
        for chapter in chapters:
            delete_chapter_summary_memory(chapter[1], chapter[2])

    for story in stories_by_id.values():
        if story:
            log_story_history_from_row(story, "Delete")

    return deleted_count


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
    chapter_id = add_story_chapter(
        story_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )
    if chapter_summary:
        index_chapter_summary(
            story_id,
            chapter_number,
            chapter_summary,
            title=chapter_description
        )

    return chapter_id


def create_and_generate_story_chapter(
    story_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary,
    progress_callback=None
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
        chapter_id,
        progress_callback=progress_callback
    )

    return chapter_id, result


def edit_story_chapter(
    chapter_id,
    chapter_number,
    chapter_description,
    chapter_body,
    chapter_summary
):
    old_chapter = get_story_chapter(chapter_id)

    update_story_chapter(
        chapter_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )
    if old_chapter and old_chapter[2] != chapter_number:
        delete_chapter_summary_memory(old_chapter[1], old_chapter[2])

    updated_chapter = get_story_chapter(chapter_id)

    if updated_chapter:
        index_chapter_summary(
            updated_chapter[1],
            updated_chapter[2],
            updated_chapter[5],
            title=updated_chapter[3]
        )


def delete_existing_story_chapter(chapter_id):
    chapter = get_story_chapter(chapter_id)
    delete_story_chapter(chapter_id)

    if chapter:
        delete_chapter_summary_memory(chapter[1], chapter[2])


def log_story_history_from_row(story, operation):
    (
        story_id,
        _created_at,
        story_name,
        template_id,
        overview,
        setting_background,
        tone_style,
        additional_instructions,
        language,
        language_level,
        male_characters,
        female_characters
    ) = story

    log_object_history(
        "Stories",
        story_id,
        story_name or "Untitled story",
        operation,
        {
            "story_name": story_name,
            "template_id": template_id,
            "overview": overview,
            "setting_background": setting_background,
            "tone_style": tone_style,
            "additional_instructions": additional_instructions,
            "language": language,
            "language_level": language_level,
            "male_characters": male_characters,
            "female_characters": female_characters,
        }
    )
