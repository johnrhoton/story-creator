import json
import logging

import streamlit as st

from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from database import (
    delete_story_beats,
    get_story_beats,
    get_story_chapters,
    replace_story_beats,
)
from llm_client import generate_text
from prompts import build_story_beats_prompt
from services.story_memory_service import (
    safe_delete_memory,
    safe_list_memory_items,
    safe_upsert_memory,
)


logger = logging.getLogger(__name__)


ALLOWED_BEAT_TYPES = {
    "scene",
    "transition",
    "relationship_progression",
    "emotional_shift",
    "revelation",
    "unresolved_thread",
    "time_jump",
    "world_or_setting_detail",
    "character_state_change",
}


def extract_story_beats(
    story_id: int,
    chapter_number: int,
    chapter_text: str
) -> list[dict]:
    if not chapter_text or not str(chapter_text).strip():
        return []

    prompt = build_story_beats_prompt(chapter_number, chapter_text)
    response_text = generate_text(
        st.session_state.get("llm_provider", DEFAULT_LLM_PROVIDER),
        st.session_state.get("llm_model", DEFAULT_LLM_MODEL),
        prompt
    )

    beats = parse_story_beats_response(
        response_text or "",
        fallback_chapter_number=chapter_number
    )

    return [
        {
            **beat,
            "chapter_number": chapter_number,
        }
        for beat in beats
    ]


def parse_story_beats_response(
    response_text: str,
    fallback_chapter_number=None
) -> list[dict]:
    if not response_text or not response_text.strip():
        return []

    response_text = normalize_json_response_text(response_text)

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        beats = payload.get("beats")
    elif isinstance(payload, list):
        beats = payload
    else:
        beats = None

    if not isinstance(beats, list):
        return []

    validated = []

    for index, beat in enumerate(beats, start=1):
        normalized = validate_story_beat(
            beat,
            fallback_sequence_number=index,
            fallback_chapter_number=fallback_chapter_number
        )
        if normalized:
            validated.append(normalized)

    return validated


def validate_story_beat(
    beat: dict,
    fallback_sequence_number=None,
    fallback_chapter_number=None
) -> dict | None:
    if not isinstance(beat, dict):
        return None

    beat_type = normalize_text(beat.get("beat_type"))
    if beat_type not in ALLOWED_BEAT_TYPES:
        return None

    sequence_number = normalize_positive_int(
        beat.get("sequence_number", fallback_sequence_number)
    )
    if sequence_number is None:
        return None

    chapter_number = normalize_positive_or_zero_int(
        beat.get("chapter_number", fallback_chapter_number)
    )

    return {
        "beat_type": beat_type,
        "title": normalize_text(beat.get("title")),
        "chapter_number": chapter_number,
        "sequence_number": sequence_number,
        "characters": normalize_string_list(beat.get("characters")),
        "location": normalize_nullable_text(beat.get("location")),
        "time_span": normalize_nullable_text(beat.get("time_span")),
        "summary": normalize_text(beat.get("summary")),
        "continuity_effect": normalize_text(
            beat.get("continuity_effect")
        ),
        "unresolved_threads": normalize_string_list(
            beat.get("unresolved_threads")
        ),
        "search_keywords": normalize_string_list(
            beat.get("search_keywords")
        ),
    }


def safe_extract_save_and_index_story_beats(
    story_id: int,
    chapter_number: int,
    chapter_text: str
) -> list[dict]:
    try:
        beats = extract_story_beats(story_id, chapter_number, chapter_text)
        save_and_index_story_beats(story_id, chapter_number, beats)
        return beats
    except Exception:
        logger.exception(
            "Could not extract story beats for story_id=%s chapter_number=%s",
            story_id,
            chapter_number,
        )
        return []


def safe_extract_missing_story_beats_for_story(story_id: int) -> dict:
    counts = {
        "chapters_checked": 0,
        "chapters_extracted": 0,
        "beats_extracted": 0,
    }

    try:
        chapters = get_story_chapters(story_id)
    except Exception:
        logger.exception("Could not load chapters for story beat extraction.")
        return counts

    for chapter in chapters:
        (
            _chapter_id,
            chapter_story_id,
            chapter_number,
            _chapter_description,
            chapter_body,
            _chapter_summary,
        ) = chapter

        if not chapter_body or not str(chapter_body).strip():
            continue

        counts["chapters_checked"] += 1

        try:
            existing_beats = get_story_beats(
                story_id=chapter_story_id,
                chapter_number=chapter_number
            )
        except Exception:
            logger.exception("Could not load existing story beats.")
            existing_beats = []

        if existing_beats:
            continue

        beats = safe_extract_save_and_index_story_beats(
            chapter_story_id,
            chapter_number,
            chapter_body
        )

        if beats:
            counts["chapters_extracted"] += 1
            counts["beats_extracted"] += len(beats)

    return counts


def save_and_index_story_beats(
    story_id: int,
    chapter_number: int,
    beats: list[dict]
) -> None:
    delete_story_beat_memory_for_chapter(story_id, chapter_number)
    replace_story_beats(story_id, chapter_number, beats)

    for beat in beats or []:
        index_story_beat(story_id, chapter_number, beat)


def index_story_beat(
    story_id: int,
    chapter_number: int,
    beat: dict
) -> None:
    sequence_number = beat.get("sequence_number")

    if not sequence_number:
        return

    safe_upsert_memory(
        build_story_beat_memory_id(story_id, chapter_number, sequence_number),
        build_story_beat_index_text(beat),
        build_story_beat_metadata(story_id, chapter_number, beat),
    )


def build_story_beat_memory_id(story_id, chapter_number, sequence_number):
    return f"story_{story_id}_chapter_{chapter_number}_beat_{sequence_number}"


def build_story_beat_index_text(beat: dict) -> str:
    return "\n".join([
        f"Title: {beat.get('title') or ''}",
        f"Beat type: {beat.get('beat_type') or ''}",
        f"Summary: {beat.get('summary') or ''}",
        f"Continuity effect: {beat.get('continuity_effect') or ''}",
        f"Characters: {', '.join(beat.get('characters') or [])}",
        (
            "Unresolved threads: "
            f"{', '.join(beat.get('unresolved_threads') or [])}"
        ),
        f"Keywords: {', '.join(beat.get('search_keywords') or [])}",
    ])


def build_story_beat_metadata(story_id, chapter_number, beat):
    return {
        "type": "story_beat",
        "beat_type": beat.get("beat_type") or "",
        "story_id": story_id,
        "chapter_number": chapter_number,
        "sequence_number": beat.get("sequence_number"),
        "title": beat.get("title") or "",
        "characters": ",".join(beat.get("characters") or []),
    }


def delete_story_beat_memory_for_chapter(story_id, chapter_number) -> None:
    found_items = False

    for item in safe_list_memory_items(where={"story_id": story_id}):
        metadata = item.get("metadata", {})
        if (
            metadata.get("type") == "story_beat"
            and metadata.get("chapter_number") == chapter_number
            and item.get("id")
        ):
            found_items = True
            safe_delete_memory(item["id"])

    if found_items:
        return

    for sequence_number in range(1, 51):
        safe_delete_memory(
            build_story_beat_memory_id(
                story_id,
                chapter_number,
                sequence_number
            )
        )


def delete_story_beats_for_chapter(story_id, chapter_number) -> None:
    delete_story_beats(story_id, chapter_number)
    delete_story_beat_memory_for_chapter(story_id, chapter_number)


def delete_story_beats_for_story(story_id) -> None:
    delete_story_beats(story_id)

    for item in safe_list_memory_items(where={"story_id": story_id}):
        metadata = item.get("metadata", {})
        if metadata.get("type") == "story_beat" and item.get("id"):
            safe_delete_memory(item["id"])


def normalize_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_nullable_text(value):
    text = normalize_text(value)
    return text if text else None


def normalize_string_list(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    if isinstance(value, str):
        if not value.strip():
            return []

        return [value.strip()]

    return []


def normalize_positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number < 1:
        return None

    return number


def normalize_positive_or_zero_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number < 0:
        return None

    return number


def normalize_json_response_text(response_text: str) -> str:
    text = response_text.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()

        if len(lines) >= 3:
            first_line = lines[0].strip().lower()
            if first_line in {"```", "```json"}:
                return "\n".join(lines[1:-1]).strip()

    return text
