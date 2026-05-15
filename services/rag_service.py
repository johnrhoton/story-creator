CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "story_memory"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client = None
_embedding_fn = None


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
    - Fill remaining slots with global-scope records (metadata.scope == 'global').
    - Always filter out records that do not belong to the current story or global scope.
    - Return formatted text suitable for prompt injection, or empty string.
    """
    if not user_request or not user_request.strip():
        return ""

    try:
        matches: list[dict] = []

        # First, try to retrieve records specific to the current story
        if story_id:
            story_matches = safe_search_memory(
                user_request,
                n_results=n_results,
                where={"story_id": story_id},
            )

            # Only keep strictly matching story records or global ones
            story_matches = [
                m for m in (story_matches or [])
                if (m.get("metadata", {}).get("story_id") == story_id)
                or (m.get("metadata", {}).get("scope") == "global")
            ]

            matches.extend(story_matches)

        # If we still need more results, fetch global-scoped memories
        if len(matches) < n_results:
            remaining = n_results - len(matches)
            global_matches = safe_search_memory(
                user_request,
                n_results=remaining,
                where={"scope": "global"},
            )

            # Ensure global matches have scope global
            global_matches = [
                m for m in (global_matches or [])
                if m.get("metadata", {}).get("scope") == "global"
            ]

            # Append only non-duplicate matches
            existing_texts = {m.get("text") for m in matches}
            for m in global_matches:
                if m.get("text") not in existing_texts:
                    matches.append(m)

        if not matches:
            return ""

        # Final safety filter: ensure no unrelated story memory is present
        filtered = []
        for m in matches:
            md = m.get("metadata", {})
            if story_id:
                if md.get("story_id") == story_id or md.get("scope") == "global":
                    filtered.append(m)
            else:
                # No story context: accept both global and any story-scoped memories
                filtered.append(m)

        if not filtered:
            return ""

        return format_rag_context(filtered)

    except Exception:
        return ""


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
