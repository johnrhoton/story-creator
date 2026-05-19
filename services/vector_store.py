from abc import ABC, abstractmethod
import logging

from config import (
    VECTOR_COLLECTION_NAME,
    VECTOR_INDEX_NAME,
    VECTOR_PROVIDER,
)


logger = logging.getLogger(__name__)


CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = VECTOR_COLLECTION_NAME
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embedding_model = None
_vector_store = None
_chroma_client = None


class VectorStore(ABC):
    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def upsert(self, item_id: str, text: str, metadata: dict) -> None:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None
    ) -> list[dict]:
        pass

    @abstractmethod
    def list_items(
        self,
        limit: int | None = None,
        where: dict | None = None
    ) -> list[dict]:
        pass

    @abstractmethod
    def delete(self, item_id: str) -> None:
        pass


class NoopVectorStore(VectorStore):
    def reset(self) -> None:
        return None

    def upsert(self, item_id: str, text: str, metadata: dict) -> None:
        return None

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None
    ) -> list[dict]:
        return []

    def list_items(
        self,
        limit: int | None = None,
        where: dict | None = None
    ) -> list[dict]:
        return []

    def delete(self, item_id: str) -> None:
        return None


class ChromaVectorStore(VectorStore):
    def reset(self) -> None:
        global _chroma_client

        client = get_chroma_client()

        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            logger.exception("Could not delete Chroma collection during reset.")

        get_chroma_collection()

    def upsert(self, item_id: str, text: str, metadata: dict) -> None:
        if not text or not text.strip():
            return

        get_chroma_collection().upsert(
            ids=[item_id],
            documents=[text.strip()],
            metadatas=[clean_metadata(metadata)],
            embeddings=[embed_text(text)],
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None
    ) -> list[dict]:
        if not query or not query.strip():
            return []

        kwargs = {
            "query_embeddings": [embed_text(query)],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        results = get_chroma_collection().query(**kwargs)
        return build_chroma_matches(results)

    def list_items(
        self,
        limit: int | None = None,
        where: dict | None = None
    ) -> list[dict]:
        kwargs = {
            "include": ["documents", "metadatas"],
        }

        if limit:
            kwargs["limit"] = limit

        if where:
            kwargs["where"] = where

        results = get_chroma_collection(read_only=True).get(**kwargs)
        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        return [
            {
                "id": item_id,
                "text": documents[index] if index < len(documents) else "",
                "metadata": (
                    metadatas[index]
                    if index < len(metadatas) and metadatas[index]
                    else {}
                ),
            }
            for index, item_id in enumerate(ids)
        ]

    def delete(self, item_id: str) -> None:
        get_chroma_collection().delete(ids=[item_id])


class MongoDBVectorStore(VectorStore):
    def reset(self) -> None:
        get_mongo_vector_collection().delete_many({})

    def upsert(self, item_id: str, text: str, metadata: dict) -> None:
        if not text or not text.strip():
            return

        get_mongo_vector_collection().replace_one(
            {"_id": item_id},
            {
                "_id": item_id,
                "text": text.strip(),
                "metadata": clean_metadata(metadata),
                "embedding": embed_text(text),
            },
            upsert=True,
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None
    ) -> list[dict]:
        if not query or not query.strip():
            return []

        vector_stage = {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": embed_text(query),
                "numCandidates": max(n_results * 20, 100),
                "limit": n_results,
            }
        }

        filter_query = build_mongo_metadata_filter(where)
        if filter_query:
            vector_stage["$vectorSearch"]["filter"] = filter_query

        pipeline = [
            vector_stage,
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        return [
            {
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}) or {},
                "distance": doc.get("score"),
            }
            for doc in get_mongo_vector_collection().aggregate(pipeline)
        ]

    def list_items(
        self,
        limit: int | None = None,
        where: dict | None = None
    ) -> list[dict]:
        cursor = get_mongo_vector_collection().find(
            build_mongo_metadata_filter(where),
            {
                "embedding": 0,
            }
        ).sort("_id", 1)

        if limit:
            cursor = cursor.limit(limit)

        return [
            {
                "id": doc.get("_id"),
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}) or {},
            }
            for doc in cursor
        ]

    def delete(self, item_id: str) -> None:
        get_mongo_vector_collection().delete_one({"_id": item_id})


def get_vector_store():
    global _vector_store

    if _vector_store is None:
        if VECTOR_PROVIDER == "none":
            _vector_store = NoopVectorStore()
        elif VECTOR_PROVIDER == "mongodb_vector":
            _vector_store = MongoDBVectorStore()
        else:
            _vector_store = ChromaVectorStore()

    return _vector_store


def get_vector_provider_status():
    labels = {
        "none": "Disabled",
        "chroma": "Chroma",
        "mongodb_vector": "MongoDB Atlas Vector Search",
    }
    return {
        "provider": VECTOR_PROVIDER,
        "label": labels[VECTOR_PROVIDER],
        "embedding_model": EMBEDDING_MODEL,
    }


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    return _embedding_model


def embed_text(text: str) -> list[float]:
    embedding = get_embedding_model().encode(
        text or "",
        normalize_embeddings=True,
    )
    return embedding.tolist()


def get_chroma_client():
    global _chroma_client

    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    return _chroma_client


def get_chroma_collection(read_only=False):
    if read_only:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_PATH)
    else:
        client = get_chroma_client()

    return client.get_or_create_collection(name=COLLECTION_NAME)


def get_mongo_vector_collection():
    from database.mongodb_connection import get_collection

    return get_collection(COLLECTION_NAME)


def build_chroma_matches(results):
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


def build_mongo_metadata_filter(where):
    return {
        f"metadata.{key}": value
        for key, value in (where or {}).items()
    }


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
