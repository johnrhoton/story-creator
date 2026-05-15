from database import get_characters, get_profiles, get_stories, get_story_chapters
from services.rag_service import delete_memory, reset_collection, upsert_memory


def index_character(character) -> None:
    data = normalize_character(character)
    character_id = data.get("id")

    if not character_id:
        return

    profile = get_profile_data(data.get("profile_name"))
    text = build_character_memory_text(data, profile)

    upsert_memory(
        f"character_{character_id}",
        text,
        {
            "type": "character",
            "character_id": character_id,
            "name": data.get("name") or "",
            "gender": data.get("gender") or "",
            "profile_name": data.get("profile_name") or "",
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

    upsert_memory(
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
    delete_memory(f"character_{character_id}")


def delete_chapter_summary_memory(story_id, chapter_number) -> None:
    delete_memory(f"story_{story_id}_chapter_{chapter_number}")


def rebuild_rag_index_from_sqlite() -> None:
    reset_collection()

    for character in get_characters():
        index_character(character)

    for story in get_stories():
        story_id = story[0]

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
