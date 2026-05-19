import logging

from prompts import render_prompt_template_section
from services.vector_store import (
    clean_metadata,
    get_chroma_collection,
    get_vector_provider_status,
    get_vector_store,
)
from services.observability_service import (
    EVENT_RAG_SEARCH_COMPLETED,
    EVENT_RAG_SEARCH_FAILED,
    EVENT_RAG_SEARCH_STARTED,
    operation_events,
)


logger = logging.getLogger(__name__)


def get_collection():
    return get_chroma_collection()


def reset_collection() -> None:
    get_vector_store().reset()


def upsert_memory(item_id: str, text: str, metadata: dict) -> None:
    get_vector_store().upsert(item_id, text, metadata)


def safe_upsert_memory(item_id: str, text: str, metadata: dict) -> bool:
    try:
        upsert_memory(item_id, text, metadata)
    except Exception:
        logger.exception("Could not upsert story memory item: %s", item_id)
        return False

    return True


def search_memory(
    query: str,
    n_results: int = 5,
    where: dict | None = None
) -> list[dict]:
    with operation_events(
        EVENT_RAG_SEARCH_STARTED,
        EVENT_RAG_SEARCH_COMPLETED,
        EVENT_RAG_SEARCH_FAILED,
        metadata={
            "n_results": n_results,
            "where": where or {},
        },
    ):
        return get_vector_store().search(
            query,
            n_results=n_results,
            where=where,
        )


def safe_search_memory(
    query: str,
    n_results: int = 5,
    where: dict | None = None
) -> list[dict]:
    try:
        return search_memory(query, n_results=n_results, where=where)
    except Exception:
        logger.exception("Story memory search failed.")
        return []


def list_memory_items(
    limit: int | None = None,
    where: dict | None = None
) -> list[dict]:
    return get_vector_store().list_items(limit=limit, where=where)


def safe_list_memory_items(
    limit: int | None = None,
    where: dict | None = None
) -> list[dict]:
    try:
        return list_memory_items(limit=limit, where=where)
    except Exception:
        logger.exception("Could not list story memory items.")
        return []


def delete_memory(item_id: str) -> None:
    get_vector_store().delete(item_id)


def safe_delete_memory(item_id: str) -> bool:
    try:
        delete_memory(item_id)
    except Exception:
        logger.exception("Could not delete story memory item: %s", item_id)
        return False

    return True


def group_memory_items_by_type(items: list[dict]) -> dict[str, list[dict]]:
    grouped = {}

    for item in items:
        metadata = item.get("metadata", {})
        item_type = metadata.get("type") or "unknown"
        grouped.setdefault(item_type, []).append(item)

    return dict(sorted(grouped.items()))


def format_memory_context(matches: list[dict]) -> str:
    blocks = []

    for match in matches:
        metadata = match.get("metadata", {})
        source_type = metadata.get("type", "memory")
        label = (
            metadata.get("name")
            or metadata.get("title")
            or metadata.get("chapter_number")
            or ""
        )
        blocks.append(f"[{source_type}: {label}]\n{match.get('text', '')}")

    return "\n\n".join(blocks)


def build_story_generation_memory(
    story_id: int | None,
    user_request: str,
    n_results: int = 6,
) -> str:
    if not user_request or not user_request.strip():
        return ""

    try:
        story_matches: list[dict] = []

        if story_id:
            story_matches = safe_search_memory(
                user_request,
                n_results=n_results,
                where={"story_id": story_id},
            )

            story_matches = [
                m for m in (story_matches or [])
                if m.get("metadata", {}).get("story_id") == story_id
            ]

        global_matches = safe_search_memory(
            user_request,
            n_results=n_results,
            where={"scope": "global"},
        )
        global_matches = [
            m for m in (global_matches or [])
            if m.get("metadata", {}).get("scope") == "global"
        ]

        matches = dedupe_memory_matches(story_matches + global_matches)

        if not story_id:
            extra_matches = safe_search_memory(
                user_request,
                n_results=n_results,
            )
            matches = dedupe_memory_matches(matches + (extra_matches or []))

        if not matches:
            return ""

        filtered = filter_story_memory_matches(matches, story_id)

        if not filtered:
            return ""

        return format_story_memory_context(filtered)

    except Exception:
        logger.exception("Could not build story generation memory.")
        return ""


def dedupe_memory_matches(matches: list[dict]) -> list[dict]:
    deduped = []
    seen = set()

    for match in matches:
        metadata = match.get("metadata", {})
        key = (
            metadata.get("type"),
            metadata.get("story_id"),
            metadata.get("chapter_number"),
            metadata.get("sequence_number"),
            metadata.get("character_id"),
            metadata.get("name"),
            match.get("text"),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(match)

    return deduped


def filter_story_memory_matches(matches: list[dict], story_id) -> list[dict]:
    filtered = []

    for match in matches:
        metadata = match.get("metadata", {})

        if story_id:
            if (
                metadata.get("story_id") == story_id
                or metadata.get("scope") == "global"
            ):
                filtered.append(match)
        else:
            filtered.append(match)

    return filtered


def format_story_memory_context(matches: list[dict]) -> str:
    groups = {
        "characters": [],
        "recent_continuity": [],
        "relevant_story_beats": [],
        "unresolved_threads": [],
    }

    for match in matches:
        metadata = match.get("metadata", {})
        item_type = metadata.get("type")

        if item_type == "character":
            groups["characters"].append(match)
        elif item_type == "story_beat":
            if metadata.get("beat_type") == "unresolved_thread":
                groups["unresolved_threads"].append(match)
            else:
                groups["relevant_story_beats"].append(match)
        elif item_type in {"chapter_summary", "story"}:
            groups["recent_continuity"].append(match)
        else:
            groups["relevant_story_beats"].append(match)

    sections = []

    for section_name, section_matches in groups.items():
        if not section_matches:
            continue

        sections.append(
            render_prompt_template_section(
                "story_memory_section.txt",
                section_name,
                items=format_story_memory_section(section_matches),
            )
        )

    return "\n\n".join(sections)


def format_story_memory_section(matches: list[dict]) -> str:
    lines = []

    for match in matches:
        metadata = match.get("metadata", {})
        label = (
            metadata.get("name")
            or metadata.get("title")
            or metadata.get("chapter_number")
            or metadata.get("character_id")
            or metadata.get("type")
            or "memory"
        )
        lines.append(
            render_prompt_template_section(
                "story_memory_section.txt",
                "item",
                label=label,
                text=match.get("text", ""),
            )
        )

    return "\n".join(lines)
