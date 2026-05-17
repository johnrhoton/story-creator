import unittest
from unittest.mock import patch

from prompts import build_story_chapter_prompt
from services.rag_indexing_service import (
    build_story_memory_text,
    build_character_memory_text,
    index_chapter_summary,
    rebuild_rag_index_from_sqlite,
)
from services.rag_service import (
    clean_metadata,
    format_rag_context,
    group_memory_items_by_type,
    safe_delete_memory,
    safe_search_memory,
    safe_upsert_memory,
)


class RagHelperTests(unittest.TestCase):
    def test_clean_metadata_keeps_chroma_supported_values(self):
        metadata = clean_metadata({
            "name": "Mira",
            "chapter": 2,
            "score": 0.42,
            "active": True,
            "empty": None,
            "tags": ["navigator", "coast"],
        })

        self.assertEqual(
            metadata,
            {
                "name": "Mira",
                "chapter": 2,
                "score": 0.42,
                "active": True,
                "tags": "['navigator', 'coast']",
            }
        )

    def test_format_rag_context_uses_metadata_label(self):
        context = format_rag_context([
            {
                "text": "Mira remembers every coastline.",
                "metadata": {
                    "type": "character",
                    "name": "Mira",
                },
            },
            {
                "text": "The crew reaches the harbor.",
                "metadata": {
                    "type": "chapter_summary",
                    "chapter_number": 3,
                },
            },
        ])

        self.assertIn("[character: Mira]", context)
        self.assertIn("Mira remembers every coastline.", context)
        self.assertIn("[chapter_summary: 3]", context)

    def test_group_memory_items_by_type_segments_index_items(self):
        grouped = group_memory_items_by_type([
            {
                "id": "character_1",
                "text": "Character memory",
                "metadata": {"type": "character"},
            },
            {
                "id": "story_1_chapter_1",
                "text": "Chapter memory",
                "metadata": {"type": "chapter_summary"},
            },
            {
                "id": "story_1",
                "text": "Story memory",
                "metadata": {"type": "story"},
            },
            {
                "id": "loose",
                "text": "Loose memory",
                "metadata": {},
            },
        ])

        self.assertEqual(
            sorted(grouped.keys()),
            ["chapter_summary", "character", "story", "unknown"]
        )
        self.assertEqual(grouped["character"][0]["id"], "character_1")
        self.assertEqual(grouped["chapter_summary"][0]["id"], "story_1_chapter_1")
        self.assertEqual(grouped["story"][0]["id"], "story_1")
        self.assertEqual(grouped["unknown"][0]["id"], "loose")

    @patch("services.rag_indexing_service.index_story_beat")
    @patch("services.rag_indexing_service.index_chapter_summary")
    @patch("services.rag_indexing_service.index_story")
    @patch("services.rag_indexing_service.index_character")
    @patch("services.rag_indexing_service.get_story_beats")
    @patch("services.rag_indexing_service.get_story_chapters")
    @patch("services.rag_indexing_service.get_stories")
    @patch("services.rag_indexing_service.get_characters")
    @patch("services.rag_indexing_service.reset_collection")
    def test_rebuild_rag_index_returns_category_counts(
        self,
        mock_reset_collection,
        mock_get_characters,
        mock_get_stories,
        mock_get_story_chapters,
        mock_get_story_beats,
        mock_index_character,
        mock_index_story,
        mock_index_chapter_summary,
        mock_index_story_beat
    ):
        mock_get_characters.return_value = [
            (1, None, None, "Alice", "18", "female", "", "", "", "", ""),
            (2, None, None, "Ben", "19", "male", "", "", "", "", ""),
        ]
        mock_get_stories.return_value = [
            (10, "created", "Story", None, "", "", "", "", "", "", "", ""),
        ]
        mock_get_story_chapters.return_value = [
            (1, 10, 0, "Opening", "Body", "Summary"),
            (2, 10, 1, "Next", "Body", ""),
        ]
        mock_get_story_beats.return_value = [
            {
                "story_id": 10,
                "chapter_number": 1,
                "sequence_number": 1,
                "beat_type": "transition",
                "title": "Travel",
                "characters": [],
                "summary": "They travel.",
                "continuity_effect": "They are elsewhere.",
                "unresolved_threads": [],
                "search_keywords": ["travel"],
            }
        ]

        counts = rebuild_rag_index_from_sqlite()

        self.assertEqual(
            counts,
            {
                "stories": 1,
                "characters": 2,
                "chapter_summaries": 1,
                "story_beats": 1,
            }
        )
        mock_reset_collection.assert_called_once()
        self.assertEqual(mock_index_character.call_count, 2)
        mock_index_story.assert_called_once()
        self.assertEqual(mock_index_chapter_summary.call_count, 2)
        mock_index_story_beat.assert_called_once()

    def test_build_story_memory_text_includes_story_fields(self):
        text = build_story_memory_text({
            "story_name": "Harbor Lights",
            "overview": "A crew searches for a lost signal.",
            "setting_background": "A foggy port.",
            "tone_style": "Quiet mystery.",
            "additional_instructions": "Keep scenes short.",
            "language": "French",
            "language_level": "B1",
            "male_characters": '["Alden"]',
            "female_characters": '["Mira"]',
        })

        self.assertIn("Story name: Harbor Lights", text)
        self.assertIn("Overview: A crew searches", text)
        self.assertIn("Language level: B1", text)

    def test_prompt_includes_story_memory_and_user_request(self):
        prompt = build_story_chapter_prompt(
            "Overview",
            "Setting",
            "Tone",
            "",
            "",
            "",
            "Chapter 1: Depart",
            [],
            1,
            "Find the old harbor.",
            "[character: Mira]\nMira remembers every coastline.",
        )

        self.assertIn("STORY MEMORY:", prompt)
        self.assertIn("Mira remembers every coastline.", prompt)
        self.assertIn("USER REQUEST:\nFind the old harbor.", prompt)
        self.assertIn("Use the story memory for continuity.", prompt)

    def test_safe_rag_operations_do_not_raise_when_backend_fails(self):
        with patch(
            "services.rag_service.get_collection",
            side_effect=RuntimeError("backend unavailable")
        ):
            self.assertFalse(
                safe_upsert_memory("item", "text", {"type": "test"})
            )
            self.assertEqual(safe_search_memory("query"), [])
            self.assertFalse(safe_delete_memory("item"))

    def test_character_memory_text_includes_profile_traits(self):
        text = build_character_memory_text(
            {
                "name": "Mira",
                "age": "31",
                "gender": "female",
                "summary": "Careful navigator.",
                "response": "Mira studies currents.",
                "physical_traits": "steady gaze",
                "personality_traits": "patient",
                "notes": "keeps maps",
            },
            {
                "profile_name": "navigator",
                "physical_traits": "weathered coat",
                "personality_traits": "observant",
                "notes": "knows old routes",
            },
        )

        self.assertIn("Name: Mira", text)
        self.assertIn("Summary: Careful navigator.", text)
        self.assertIn("Attached profile: navigator", text)
        self.assertIn("Profile personality traits: observant", text)

    @patch("services.rag_indexing_service.safe_delete_memory")
    def test_blank_chapter_summary_removes_existing_memory(
        self,
        mock_safe_delete_memory
    ):
        index_chapter_summary(7, 2, "   ")

        mock_safe_delete_memory.assert_called_once_with("story_7_chapter_2")


if __name__ == "__main__":
    unittest.main()
