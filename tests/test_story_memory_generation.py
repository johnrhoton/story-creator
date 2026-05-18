import unittest
from unittest.mock import patch

from services.story_memory_service import build_story_generation_memory


class StoryMemoryGenerationTests(unittest.TestCase):
    def test_build_story_generation_memory_prefers_story_id_and_includes_global(self):
        def fake_search(query, n_results=5, where=None):
            if where and where.get("story_id") == 1:
                return [
                    {
                        "text": "Chapter 1 summary for story 1.",
                        "metadata": {"type": "chapter_summary", "story_id": 1, "chapter_number": 1},
                    }
                ]
            if where and where.get("scope") == "global":
                return [
                    {
                        "text": "Mira is a careful navigator.",
                        "metadata": {"type": "character", "name": "Mira", "scope": "global"},
                    }
                ]
            return []

        with patch("services.story_memory_service.safe_search_memory", side_effect=fake_search):
            context = build_story_generation_memory(1, "Find the old harbor.", n_results=6)

        self.assertIn("Chapter 1 summary for story 1.", context)
        self.assertIn("Mira is a careful navigator.", context)

    def test_missing_chroma_does_not_break_generation(self):
        with patch("services.story_memory_service.safe_search_memory", side_effect=Exception("backend down")):
            context = build_story_generation_memory(1, "Any request", n_results=6)

        self.assertEqual(context, "")

    def test_story_id_filtering_prevents_unrelated_story_memory(self):
        def fake_search_unrelated(query, n_results=5, where=None):
            # Return unrelated story memory when asked for story_id 1
            if where and where.get("story_id") == 1:
                return [
                    {
                        "text": "Chapter summary from story 2.",
                        "metadata": {"type": "chapter_summary", "story_id": 2, "chapter_number": 1},
                    }
                ]
            # No global matches
            return []

        with patch("services.story_memory_service.safe_search_memory", side_effect=fake_search_unrelated):
            context = build_story_generation_memory(1, "Request", n_results=6)

        # Unrelated story memory should be filtered out
        self.assertEqual(context, "")


if __name__ == "__main__":
    unittest.main()
