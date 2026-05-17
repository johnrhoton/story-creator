import json

import streamlit as st

from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from database import (
    get_character_summaries_by_names,
    get_story,
    get_story_chapters,
    update_story_chapter,
)
from llm_client import generate_text
from prompts import (
    build_story_chapter_prompt,
    build_story_chapter_summary_prompt,
    build_story_chapter_zero_prompt,
)
from services.rag_indexing_service import index_chapter_summary
from services.rag_service import (
    format_rag_context,
    safe_search_memory,
    build_story_generation_memory,
)


def generate_story_chapters(story_id, progress_callback=None):
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
        additional_instructions,
        language,
        language_level,
        male_characters,
        female_characters
    ) = story

    chapters = get_story_chapters(story_id)
    total_chapters = len(chapters)
    outline = build_story_outline(chapters)
    characters = build_character_list(
        male_characters,
        female_characters
    )
    previous_summaries = []

    for chapter_index, chapter in enumerate(chapters, start=1):
        (
            chapter_id,
            _chapter_story_id,
            chapter_number,
            chapter_description,
            _chapter_body,
            _chapter_summary
        ) = chapter
        if progress_callback:
            progress_callback(chapter_index, total_chapters)

        if chapter_number == 0:
            user_request = "\n".join([
                f"Overview: {overview or ''}",
                f"Setting/background: {setting_background or ''}",
                f"Tone/style: {tone_style or ''}",
                f"Additional instructions: {additional_instructions or ''}",
                f"Language: {language or ''}",
                f"Language level: {language_level or ''}",
                f"Outline: {outline or ''}",
                f"User request: {chapter_description or ''}",
            ])

            rag_context = build_story_generation_memory(
                story_id=story_id,
                user_request=user_request,
                n_results=6,
            )
            chapter_prompt = build_story_chapter_zero_prompt(
                overview,
                setting_background,
                tone_style,
                additional_instructions,
                language,
                language_level,
                outline,
                characters,
                chapter_description,
                rag_context
            )
        else:
            user_request = "\n".join([
                f"Overview: {overview or ''}",
                f"Setting/background: {setting_background or ''}",
                f"Tone/style: {tone_style or ''}",
                f"Additional instructions: {additional_instructions or ''}",
                f"Language: {language or ''}",
                f"Language level: {language_level or ''}",
                f"Outline: {outline or ''}",
                f"User request: {chapter_description or ''}",
            ])

            rag_context = build_story_generation_memory(
                story_id=story_id,
                user_request=user_request,
                n_results=6,
            )
            chapter_prompt = build_story_chapter_prompt(
                overview,
                setting_background,
                tone_style,
                additional_instructions,
                language,
                language_level,
                outline,
                previous_summaries,
                chapter_number,
                chapter_description,
                rag_context
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
        index_chapter_summary(
            _chapter_story_id,
            chapter_number,
            chapter_summary,
            title=chapter_description
        )

        previous_summaries.append(
            f"Chapter {chapter_number}: {chapter_summary}"
        )


def generate_story_chapter_body_and_summary(story_id, chapter_id, progress_callback=None):
    story = get_story(story_id)

    if not story:
        return None

    (
        _story_id,
        _created_at,
        _story_name,
        _template_id,
        overview,
        setting_background,
        tone_style,
        additional_instructions,
        language,
        language_level,
        male_characters,
        female_characters
    ) = story

    chapters = sorted(
        get_story_chapters(story_id),
        key=lambda chapter: chapter[2]
    )
    total_chapters = len(chapters)
    target_chapter = next(
        (
            chapter
            for chapter in chapters
            if chapter[0] == chapter_id
        ),
        None
    )

    if not target_chapter:
        return None

    (
        _chapter_id,
        _chapter_story_id,
        chapter_number,
        chapter_description,
        _chapter_body,
        _chapter_summary
    ) = target_chapter

    if progress_callback:
        target_index = chapters.index(target_chapter) + 1
        progress_callback(target_index, total_chapters)

    outline = build_story_outline(chapters)

    if chapter_number == 0:
        characters = build_character_list(
            male_characters,
            female_characters
        )
        user_request = "\n".join([
            f"Overview: {overview or ''}",
            f"Setting/background: {setting_background or ''}",
            f"Tone/style: {tone_style or ''}",
            f"Additional instructions: {additional_instructions or ''}",
            f"Language: {language or ''}",
            f"Language level: {language_level or ''}",
            f"Outline: {outline or ''}",
            f"User request: {chapter_description or ''}",
        ])

        rag_context = build_story_generation_memory(
            story_id=story_id,
            user_request=user_request,
            n_results=6,
        )
        chapter_prompt = build_story_chapter_zero_prompt(
            overview,
            setting_background,
            tone_style,
            additional_instructions,
            language,
            language_level,
            outline,
            characters,
            chapter_description,
            rag_context
        )
    else:
        user_request = "\n".join([
            f"Overview: {overview or ''}",
            f"Setting/background: {setting_background or ''}",
            f"Tone/style: {tone_style or ''}",
            f"Additional instructions: {additional_instructions or ''}",
            f"Language: {language or ''}",
            f"Language level: {language_level or ''}",
            f"Outline: {outline or ''}",
            f"User request: {chapter_description or ''}",
        ])

        rag_context = build_story_generation_memory(
            story_id=story_id,
            user_request=user_request,
            n_results=6,
        )
        chapter_prompt = build_story_chapter_prompt(
            overview,
            setting_background,
            tone_style,
            additional_instructions,
            language,
            language_level,
            outline,
            build_previous_chapter_summaries(chapters, chapter_number),
            chapter_number,
            chapter_description,
            rag_context
        )

    chapter_body = call_selected_llm(chapter_prompt)

    if not chapter_body:
        return None

    summary_prompt = build_story_chapter_summary_prompt(chapter_body)
    chapter_summary = call_selected_llm(summary_prompt) or ""

    update_story_chapter(
        chapter_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    )
    index_chapter_summary(
        _chapter_story_id,
        chapter_number,
        chapter_summary,
        title=chapter_description
    )

    return {
        "chapter_body": chapter_body,
        "chapter_summary": chapter_summary,
    }


def call_selected_llm(prompt):
    return generate_text(
        st.session_state.get("llm_provider", DEFAULT_LLM_PROVIDER),
        st.session_state.get("llm_model", DEFAULT_LLM_MODEL),
        prompt
    )


def build_rag_context_for_chapter(
    overview,
    setting_background,
    tone_style,
    outline,
    chapter_description
):
    user_request = "\n".join([
        f"Overview: {overview or ''}",
        f"Setting/background: {setting_background or ''}",
        f"Tone/style: {tone_style or ''}",
        f"Outline: {outline or ''}",
        f"User request: {chapter_description or ''}",
    ])

    matches = safe_search_memory(user_request, n_results=5)

    return format_rag_context(matches)


def build_story_outline(chapters):
    return "\n".join(
        f"Chapter {chapter[2]}: {chapter[3] or ''}"
        for chapter in chapters
    )


def build_previous_chapter_summaries(chapters, current_chapter_number):
    return [
        f"Chapter {chapter[2]}: {chapter[5]}"
        for chapter in chapters
        if chapter[2] < current_chapter_number and chapter[5]
    ]


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
