import json

import streamlit as st

from database import (
    add_story_chapter,
    clone_story,
    create_story_from_template,
    delete_story,
    delete_story_chapter,
    get_character_summaries_by_names,
    get_characters_by_gender,
    get_story,
    get_stories,
    get_story_chapters,
    get_story_templates,
    update_story,
    update_story_chapter,
)
from llm_client import generate_text
from prompts import (
    build_story_chapter_prompt,
    build_story_chapter_zero_prompt,
    build_story_chapter_summary_prompt,
)


def list_templates():
    return get_story_templates()


def list_stories():
    return get_stories()


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


def call_selected_llm(prompt):
    return generate_text(
        st.session_state.get("llm_provider", "Gemini"),
        st.session_state.get("llm_model", "gemini-2.5-flash"),
        prompt
    )


def generate_story_chapters(story_id):
    story = get_story(story_id)

    if not story:
        return

    (
        _story_id,
        _created_at,
        _story_name,
        _template_id,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ) = story

    chapters = get_story_chapters(story_id)
    outline = build_story_outline(chapters)
    characters = build_character_list(
        male_characters,
        female_characters
    )
    previous_summaries = []

    for chapter in chapters:
        (
            chapter_id,
            _chapter_story_id,
            chapter_number,
            chapter_description,
            _chapter_body,
            _chapter_summary
        ) = chapter

        if chapter_number == 0:
            chapter_prompt = build_story_chapter_zero_prompt(
                overview,
                setting_background,
                tone_style,
                outline,
                characters,
                chapter_description
            )
        else:
            chapter_prompt = build_story_chapter_prompt(
                overview,
                setting_background,
                tone_style,
                outline,
                previous_summaries,
                chapter_number,
                chapter_description
            )

        chapter_body = call_selected_llm(chapter_prompt)

        if not chapter_body:
            continue

        summary_prompt = build_story_chapter_summary_prompt(
            chapter_body
        )

        chapter_summary = call_selected_llm(summary_prompt) or ""

        update_story_chapter(
            chapter_id,
            chapter_number,
            chapter_description,
            chapter_body,
            chapter_summary
        )

        previous_summaries.append(
            f"Chapter {chapter_number}: {chapter_summary}"
        )


def build_story_outline(chapters):
    return "\n".join(
        f"Chapter {chapter[2]}: {chapter[3] or ''}"
        for chapter in chapters
    )


def build_character_list(
    male_characters_json,
    female_characters_json
):
    male_characters = safe_json_loads(male_characters_json)
    female_characters = safe_json_loads(female_characters_json)
    character_summaries = get_character_summaries_by_names(
        male_characters + female_characters
    )

    character_lines = []

    for index, name in enumerate(male_characters, start=1):
        character_lines.append(
            build_character_context_line(
                f"M{index}",
                name,
                character_summaries
            )
        )

    for index, name in enumerate(female_characters, start=1):
        character_lines.append(
            build_character_context_line(
                f"F{index}",
                name,
                character_summaries
            )
        )

    if not character_lines:
        return "No characters selected."

    return "\n".join(character_lines)


def build_character_context_line(
    placeholder,
    name,
    character_summaries
):
    summary = character_summaries.get(
        name.strip().lower(),
        ""
    )

    if summary:
        return f"{placeholder}: {name} — {summary}"

    return f"{placeholder}: {name} — No summary available."


def safe_json_loads(value):
    if not value:
        return []

    try:
        return json.loads(value)
    except Exception:
        return []


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
