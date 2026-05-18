import json
import unittest
from unittest.mock import patch

from services.story_memory_service import build_story_generation_memory
from services.story_beat_service import (
    build_story_beat_index_text,
    index_story_beat,
    parse_story_beats_response,
    safe_extract_save_and_index_story_beats,
    validate_story_beat,
)


class StoryBeatTests(unittest.TestCase):
    def test_parse_story_beats_response_accepts_valid_json(self):
        response = json.dumps({
            "beats": [
                {
                    "beat_type": "relationship_progression",
                    "title": "Mark and Susan run together",
                    "chapter_number": 4,
                    "sequence_number": 1,
                    "characters": ["Mark", "Susan"],
                    "location": None,
                    "time_span": "several weeks",
                    "summary": "Their running habit turns into a routine.",
                    "continuity_effect": "They are closer now.",
                    "unresolved_threads": [],
                    "search_keywords": ["running", "routine"],
                }
            ]
        })

        beats = parse_story_beats_response(response)

        self.assertEqual(len(beats), 1)
        self.assertEqual(beats[0]["beat_type"], "relationship_progression")
        self.assertEqual(beats[0]["characters"], ["Mark", "Susan"])

    def test_parse_story_beats_response_rejects_invalid_json(self):
        self.assertEqual(parse_story_beats_response("not json"), [])

    def test_parse_story_beats_response_accepts_fenced_json(self):
        response = """```json
{
  "beats": [
    {
      "beat_type": "transition",
      "title": "Weeks pass",
      "chapter_number": 1,
      "sequence_number": 1,
      "characters": [],
      "location": null,
      "time_span": "weeks",
      "summary": "Time passes.",
      "continuity_effect": "The situation has settled.",
      "unresolved_threads": [],
      "search_keywords": ["time"]
    }
  ]
}
```"""

        beats = parse_story_beats_response(response)

        self.assertEqual(len(beats), 1)
        self.assertEqual(beats[0]["beat_type"], "transition")

    def test_parse_story_beats_response_accepts_bare_list_and_fallbacks(self):
        response = json.dumps([
            {
                "beat_type": "revelation",
                "title": "The signal is local",
                "characters": ["Mira"],
                "summary": "Mira learns the signal came from nearby.",
                "continuity_effect": "The search narrows.",
                "unresolved_threads": [],
                "search_keywords": ["signal"],
            }
        ])

        beats = parse_story_beats_response(
            response,
            fallback_chapter_number=3
        )

        self.assertEqual(beats[0]["chapter_number"], 3)
        self.assertEqual(beats[0]["sequence_number"], 1)

    def test_validate_story_beat_normalizes_supported_fields(self):
        beat = validate_story_beat({
            "beat_type": "transition",
            "title": "Weeks pass",
            "chapter_number": 2,
            "sequence_number": "3",
            "characters": "Mira",
            "location": "",
            "time_span": "weeks",
            "summary": "Mira settles into a new pattern.",
            "continuity_effect": "Her routine has changed.",
            "unresolved_threads": ["Who sent the letter?"],
            "search_keywords": ["routine", "letter"],
        })

        self.assertIsNotNone(beat)
        self.assertEqual(beat["sequence_number"], 3)
        self.assertEqual(beat["characters"], ["Mira"])
        self.assertIsNone(beat["location"])

    def test_validate_story_beat_rejects_unknown_type(self):
        self.assertIsNone(
            validate_story_beat({
                "beat_type": "misc",
                "sequence_number": 1,
            })
        )

    def test_story_beat_index_text_contains_retrieval_fields(self):
        text = build_story_beat_index_text({
            "beat_type": "revelation",
            "title": "The signal is local",
            "summary": "Mira learns the signal came from the harbor.",
            "continuity_effect": "The search narrows to the harbor.",
            "characters": ["Mira"],
            "unresolved_threads": ["Who sent the signal?"],
            "search_keywords": ["signal", "harbor"],
        })

        self.assertIn("Title: The signal is local", text)
        self.assertIn("Beat type: revelation", text)
        self.assertIn("Characters: Mira", text)
        self.assertIn("Keywords: signal, harbor", text)

    @patch("services.story_beat_service.safe_upsert_memory")
    def test_index_story_beat_uses_expected_id_text_and_metadata(
        self,
        mock_safe_upsert_memory
    ):
        beat = {
            "beat_type": "emotional_shift",
            "title": "Mira trusts Alden",
            "sequence_number": 2,
            "characters": ["Mira", "Alden"],
            "summary": "Mira chooses to trust Alden.",
            "continuity_effect": "Their alliance is stronger.",
            "unresolved_threads": [],
            "search_keywords": ["trust", "alliance"],
        }

        index_story_beat(7, 4, beat)

        item_id, text, metadata = mock_safe_upsert_memory.call_args.args
        self.assertEqual(item_id, "story_7_chapter_4_beat_2")
        self.assertIn("Mira chooses to trust Alden.", text)
        self.assertEqual(metadata["type"], "story_beat")
        self.assertEqual(metadata["story_id"], 7)
        self.assertEqual(metadata["characters"], "Mira,Alden")

    def test_generation_memory_includes_story_beat_records(self):
        def fake_search(query, n_results=5, where=None):
            if where and where.get("story_id") == 1:
                return [
                    {
                        "text": "Summary: They reached the harbor.",
                        "metadata": {
                            "type": "chapter_summary",
                            "story_id": 1,
                            "chapter_number": 2,
                        },
                    },
                    {
                        "text": "Summary: Mira trusts Alden.",
                        "metadata": {
                            "type": "story_beat",
                            "beat_type": "relationship_progression",
                            "story_id": 1,
                            "chapter_number": 2,
                            "sequence_number": 1,
                            "title": "Trust grows",
                        },
                    },
                    {
                        "text": "Summary: Unrelated story.",
                        "metadata": {
                            "type": "story_beat",
                            "story_id": 2,
                            "chapter_number": 1,
                        },
                    },
                ]
            if where and where.get("scope") == "global":
                return [
                    {
                        "text": "Mira is a careful navigator.",
                        "metadata": {
                            "type": "character",
                            "scope": "global",
                            "name": "Mira",
                        },
                    }
                ]
            return []

        with patch("services.story_memory_service.safe_search_memory", side_effect=fake_search):
            memory = build_story_generation_memory(
                1,
                "Mira and Alden return to the harbor.",
                n_results=6
            )

        self.assertIn("CHARACTERS:", memory)
        self.assertIn("RECENT CONTINUITY:", memory)
        self.assertIn("RELEVANT STORY BEATS:", memory)
        self.assertIn("Mira trusts Alden.", memory)
        self.assertNotIn("Unrelated story", memory)

    @patch("services.story_beat_service.extract_story_beats")
    def test_failed_beat_extraction_does_not_raise(self, mock_extract):
        mock_extract.side_effect = RuntimeError("LLM unavailable")

        beats = safe_extract_save_and_index_story_beats(
            1,
            2,
            "Chapter text"
        )

        self.assertEqual(beats, [])


if __name__ == "__main__":
    unittest.main()
