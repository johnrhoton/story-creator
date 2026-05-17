CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "story_memory"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client = None
_embedding_fn = None

from prompts import render_prompt_template_section


def get_collection():
    global _client, _embedding_fn

    if _client is None or _embedding_fn is None:
        import chromadb
        from chromadb.utils import embedding_functions

        _embedding_fn = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
        )
        _client = chromadb.PersistentClient(path=CHROMA_PATH)

    return _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )


def reset_collection() -> None:
    global _client

    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    get_collection()


def upsert_memory(item_id: str, text: str, metadata: dict) -> None:
    if not text or not text.strip():
        return

    collection = get_collection()
    collection.upsert(
        ids=[item_id],
        documents=[text.strip()],
        metadatas=[clean_metadata(metadata)],
    )


def safe_upsert_memory(item_id: str, text: str, metadata: dict) -> bool:
    try:
        upsert_memory(item_id, text, metadata)
    except Exception:
        return False

    return True


def search_memory(
    query: str,
    n_results: int = 5,
    where: dict | None = None
) -> list[dict]:
    if not query or not query.strip():
        return []

    collection = get_collection()
    kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    matches = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, document in enumerate(documents):
        matches.append({
            "text": document,
            "metadata": (
                metadatas[index]
                if index < len(metadatas) and metadatas[index]
                else {}
            ),
            "distance": (
                distances[index]
                if index < len(distances)
                else None
            ),
        })

    return matches


def list_memory_items(
    limit: int | None = None,
    where: dict | None = None
) -> list[dict]:
    collection = get_read_collection()
    kwargs = {
        "include": ["documents", "metadatas"],
    }

    if limit:
        kwargs["limit"] = limit

    if where:
        kwargs["where"] = where

    results = collection.get(**kwargs)
    ids = results.get("ids", [])
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    items = []

    for index, item_id in enumerate(ids):
        items.append({
            "id": item_id,
            "text": (
                documents[index]
                if index < len(documents)
                else ""
            ),
            "metadata": (
                metadatas[index]
                if index < len(metadatas) and metadatas[index]
                else {}
            ),
        })

    return items


def get_read_collection():
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def safe_list_memory_items(
    limit: int | None = None,
    where: dict | None = None
) -> list[dict]:
    try:
        return list_memory_items(limit=limit, where=where)
    except Exception:
        return []


def group_memory_items_by_type(items: list[dict]) -> dict[str, list[dict]]:
    grouped = {}

    for item in items:
        metadata = item.get("metadata", {})
        item_type = metadata.get("type") or "unknown"
        grouped.setdefault(item_type, []).append(item)

    return dict(sorted(grouped.items()))


def safe_search_memory(
    query: str,
    n_results: int = 5,
    where: dict | None = None
) -> list[dict]:
    try:
        return search_memory(query, n_results=n_results, where=where)
    except Exception:
        return []


def delete_memory(item_id: str) -> None:
    collection = get_collection()
    collection.delete(ids=[item_id])


def safe_delete_memory(item_id: str) -> bool:
    try:
        delete_memory(item_id)
    except Exception:
        return False

    return True


def format_rag_context(matches: list[dict]) -> str:
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
    """
    Build a STORY MEMORY text block for chapter generation.

    - Prefer records where metadata.story_id == story_id.
    - Fill remaining slots with global-scope character records.
    - Always filter out records that do not belong to the current story or global scope.
    - Group records so prompts can distinguish characters, continuity, beats, and
      unresolved threads.
    """
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


def clean_metadata(metadata: dict) -> dict:
    cleaned = {}

    for key, value in (metadata or {}).items():
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)

    return cleaned
