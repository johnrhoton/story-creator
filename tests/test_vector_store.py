import unittest
from unittest.mock import MagicMock, patch

from services.vector_store import (
    MongoDBVectorStore,
    NoopVectorStore,
    build_mongo_metadata_filter,
)


class VectorStoreTests(unittest.TestCase):
    def test_noop_vector_store_returns_empty_results(self):
        store = NoopVectorStore()

        store.upsert("id", "text", {"type": "story"})
        self.assertEqual(store.search("query"), [])
        self.assertEqual(store.list_items(), [])
        store.delete("id")
        store.reset()

    def test_build_mongo_metadata_filter_prefixes_metadata_fields(self):
        self.assertEqual(
            build_mongo_metadata_filter({
                "story_id": 7,
                "type": "story_beat",
            }),
            {
                "metadata.story_id": 7,
                "metadata.type": "story_beat",
            }
        )

    @patch("services.vector_store.embed_text", return_value=[0.1, 0.2])
    @patch("services.vector_store.get_mongo_vector_collection")
    def test_mongodb_vector_store_upserts_embedding_with_record(
        self,
        mock_get_collection,
        _mock_embed_text
    ):
        collection = MagicMock()
        mock_get_collection.return_value = collection
        store = MongoDBVectorStore()

        store.upsert(
            "story_1",
            "Story text",
            {"type": "story", "story_id": 1}
        )

        collection.replace_one.assert_called_once_with(
            {"_id": "story_1"},
            {
                "_id": "story_1",
                "text": "Story text",
                "metadata": {"type": "story", "story_id": 1},
                "embedding": [0.1, 0.2],
            },
            upsert=True,
        )

    @patch("services.vector_store.embed_text", return_value=[0.1, 0.2])
    @patch("services.vector_store.get_mongo_vector_collection")
    def test_mongodb_vector_store_search_uses_vector_search_pipeline(
        self,
        mock_get_collection,
        _mock_embed_text
    ):
        collection = MagicMock()
        collection.aggregate.return_value = [
            {
                "text": "Memory",
                "metadata": {"type": "story"},
                "score": 0.95,
            }
        ]
        mock_get_collection.return_value = collection
        store = MongoDBVectorStore()

        matches = store.search(
            "query",
            n_results=3,
            where={"story_id": 1}
        )

        pipeline = collection.aggregate.call_args.args[0]
        self.assertEqual(
            pipeline[0]["$vectorSearch"]["queryVector"],
            [0.1, 0.2]
        )
        self.assertEqual(
            pipeline[0]["$vectorSearch"]["filter"],
            {"metadata.story_id": 1}
        )
        self.assertEqual(matches[0]["distance"], 0.95)


if __name__ == "__main__":
    unittest.main()
