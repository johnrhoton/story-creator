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


def delete_memory(item_id: str) -> None:
    collection = get_collection()
    collection.delete(ids=[item_id])


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
