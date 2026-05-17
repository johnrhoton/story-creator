from database import get_characters, get_profiles, get_stories, get_story_chapters
from services.rag_service import (
    reset_collection,
    safe_delete_memory,
    safe_upsert_memory,
)


def index_character(character) -> None:
    data = normalize_character(character)
    character_id = data.get("id")

    if not character_id:
        return

    profile = get_profile_data(data.get("profile_name"))
    text = build_character_memory_text(data, profile)

    safe_upsert_memory(
        f"character_{character_id}",
        text,
        {
            "type": "character",
            "character_id": character_id,
            "name": data.get("name") or "",
            "gender": data.get("gender") or "",
            "profile_name": data.get("profile_name") or "",
            # If the character is attached to a specific story include story_id,
            # otherwise mark it as global scope so it can be optionally reused.
            "story_id": data.get("story_id") if data.get("story_id") else None,
            "scope": "global" if not data.get("story_id") else "story",
        },
    )


def index_story(story) -> None:
    data = normalize_story(story)
    story_id = data.get("id")

    if not story_id:
        return

    safe_upsert_memory(
        f"story_{story_id}",
        build_story_memory_text(data),
        {
            "type": "story",
            "story_id": story_id,
            "name": data.get("story_name") or "",
            "scope": "story",
        },
    )


def index_chapter_summary(
    story_id,
    chapter_number,
    summary,
    title=None
) -> None:
    if not summary or not str(summary).strip():
        delete_chapter_summary_memory(story_id, chapter_number)
        return

    text_parts = [
        f"Story ID: {story_id}",
        f"Chapter number: {chapter_number}",
    ]

    if title:
        text_parts.append(f"Title: {title}")

    text_parts.append(f"Summary: {summary}")

    safe_upsert_memory(
        f"story_{story_id}_chapter_{chapter_number}",
        "\n".join(text_parts),
        {
            "type": "chapter_summary",
            "story_id": story_id,
            "chapter_number": chapter_number,
            "title": title or "",
        },
    )


def delete_character_memory(character_id) -> None:
    safe_delete_memory(f"character_{character_id}")


def delete_chapter_summary_memory(story_id, chapter_number) -> None:
    safe_delete_memory(f"story_{story_id}_chapter_{chapter_number}")


def delete_story_memory(story_id) -> None:
    safe_delete_memory(f"story_{story_id}")


def rebuild_rag_index_from_sqlite() -> dict:
    reset_collection()

    counts = {
        "stories": 0,
        "characters": 0,
        "chapter_summaries": 0,
    }

    for character in get_characters():
        index_character(character)
        counts["characters"] += 1

    for story in get_stories():
        story_id = story[0]
        index_story(story)
        counts["stories"] += 1

        for chapter in get_story_chapters(story_id):
            (
                _chapter_id,
                chapter_story_id,
                chapter_number,
                chapter_description,
                _chapter_body,
                chapter_summary,
            ) = chapter

            index_chapter_summary(
                chapter_story_id,
                chapter_number,
                chapter_summary,
                title=chapter_description,
            )

            if chapter_summary and str(chapter_summary).strip():
                counts["chapter_summaries"] += 1

    return counts


def normalize_character(character) -> dict:
    if isinstance(character, dict):
        return character

    (
        character_id,
        _created_at,
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary,
    ) = character

    return {
        "id": character_id,
        "profile_name": profile_name,
        "name": name,
        "age": age,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
        "response": response,
        "summary": summary,
    }


def normalize_story(story) -> dict:
    if isinstance(story, dict):
        return story

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
        female_characters,
    ) = story

    return {
        "id": story_id,
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


def get_profile_data(profile_name):
    if not profile_name:
        return None

    normalized_name = profile_name.strip().lower()

    for profile in get_profiles():
        (
            profile_row_name,
            gender,
            physical_traits,
            personality_traits,
            notes,
        ) = profile

        if profile_row_name == normalized_name:
            return {
                "profile_name": profile_row_name,
                "gender": gender,
                "physical_traits": physical_traits,
                "personality_traits": personality_traits,
                "notes": notes,
            }

    return None


def build_character_memory_text(data, profile) -> str:
    parts = [
        f"Name: {data.get('name') or ''}",
        f"Age: {data.get('age') or ''}",
        f"Gender: {data.get('gender') or ''}",
        f"Summary: {data.get('summary') or ''}",
        f"Description: {data.get('response') or ''}",
        f"Physical traits: {data.get('physical_traits') or ''}",
        f"Personality traits: {data.get('personality_traits') or ''}",
        f"Notes: {data.get('notes') or ''}",
    ]

    if profile:
        parts.extend([
            f"Attached profile: {profile.get('profile_name') or ''}",
            f"Profile physical traits: {profile.get('physical_traits') or ''}",
            (
                "Profile personality traits: "
                f"{profile.get('personality_traits') or ''}"
            ),
            f"Profile notes: {profile.get('notes') or ''}",
        ])

    return "\n".join(parts)


def build_story_memory_text(data) -> str:
    parts = [
        f"Story name: {data.get('story_name') or ''}",
        f"Template ID: {data.get('template_id') or ''}",
        f"Overview: {data.get('overview') or ''}",
        f"Setting/background: {data.get('setting_background') or ''}",
        f"Tone/style: {data.get('tone_style') or ''}",
        (
            "Additional instructions: "
            f"{data.get('additional_instructions') or ''}"
        ),
        f"Language: {data.get('language') or ''}",
        f"Language level: {data.get('language_level') or ''}",
        f"Male characters: {data.get('male_characters') or ''}",
        f"Female characters: {data.get('female_characters') or ''}",
    ]

    return "\n".join(parts)
