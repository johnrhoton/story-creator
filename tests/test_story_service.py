import unittest
from unittest.mock import patch

from services.story_service import (
    build_full_story_markdown,
    create_and_generate_story_chapter,
)
from services.story_generation_service import (
    LLMGenerationError,
    generate_story_chapters,
    generate_story_chapter_body_and_summary,
)


class StoryServiceTests(unittest.TestCase):
    def test_build_full_story_markdown_uses_chapter_order_from_zero(self):
        chapters = [
            (3, 1, 2, "Later", "Third body", "summary"),
            (1, 1, 0, "Opening", "Opening body", "summary"),
            (2, 1, 1, "Middle", "Middle body", "summary"),
        ]

        markdown = build_full_story_markdown(chapters)

        self.assertEqual(
            markdown,
            (
                "## Chapter 0\n\nOpening body\n\n"
                "## Chapter 1\n\nMiddle body\n\n"
                "## Chapter 2\n\nThird body"
            )
        )

    def test_build_full_story_markdown_skips_negative_chapters(self):
        chapters = [
            (1, 1, -1, "Draft note", "Ignore me", "summary"),
            (2, 1, 0, "Opening", "Keep me", "summary"),
        ]

        self.assertEqual(
            build_full_story_markdown(chapters),
            "## Chapter 0\n\nKeep me"
        )

    @patch("services.story_generation_service.update_story_chapter")
    @patch("services.story_generation_service.call_selected_llm")
    @patch("services.story_generation_service.get_story_chapters")
    @patch("services.story_generation_service.get_story")
    def test_generate_story_chapter_uses_previous_summaries(
        self,
        mock_get_story,
        mock_get_story_chapters,
        mock_call_selected_llm,
        mock_update_story_chapter
    ):
        mock_get_story.return_value = (
            1,
            "2026-05-14T12:00:00",
            "Story",
            10,
            "Overview",
            "Setting",
            "Tone",
            "",
            "",
            "",
            "[]",
            "[]",
        )
        mock_get_story_chapters.return_value = [
            (1, 1, 0, "Opening", "Old body", "Opening summary"),
            (2, 1, 1, "Next step", "Existing body", "Existing summary"),
        ]
        mock_call_selected_llm.side_effect = [
            "Generated body",
            "Generated summary",
        ]

        result = generate_story_chapter_body_and_summary(1, 2)

        first_prompt = mock_call_selected_llm.call_args_list[0].args[0]
        self.assertIn(
            "Previous chapter summaries:\nChapter 0: Opening summary",
            first_prompt
        )
        self.assertNotIn("Existing summary", first_prompt)
        mock_update_story_chapter.assert_called_once_with(
            2,
            1,
            "Next step",
            "Generated body",
            "Generated summary"
        )
        self.assertEqual(
            result,
            {
                "chapter_body": "Generated body",
                "chapter_summary": "Generated summary",
            }
        )

    @patch("services.story_generation_service.get_character_summaries_by_names")
    @patch("services.story_generation_service.update_story_chapter")
    @patch("services.story_generation_service.call_selected_llm")
    @patch("services.story_generation_service.get_story_chapters")
    @patch("services.story_generation_service.get_story")
    def test_generate_story_chapter_zero_uses_character_context(
        self,
        mock_get_story,
        mock_get_story_chapters,
        mock_call_selected_llm,
        mock_update_story_chapter,
        mock_get_character_summaries
    ):
        mock_get_story.return_value = (
            1,
            "2026-05-14T12:00:00",
            "Story",
            10,
            "Overview",
            "Setting",
            "Tone",
            "Keep scenes concise.",
            "French",
            "B1",
            '["Alice"]',
            "[]",
        )
        mock_get_story_chapters.return_value = [
            (1, 1, 0, "Opening", "", ""),
        ]
        mock_get_character_summaries.return_value = {
            "alice": "Alice continuity notes"
        }
        mock_call_selected_llm.side_effect = [
            "Generated opening",
            "Opening summary",
        ]

        generate_story_chapter_body_and_summary(1, 1)

        first_prompt = mock_call_selected_llm.call_args_list[0].args[0]
        self.assertIn("Write Chapter 0", first_prompt)
        self.assertIn("HIGH PRIORITY STORY INSTRUCTIONS:", first_prompt)
        self.assertIn("Additional instructions: Keep scenes concise.", first_prompt)
        self.assertIn("Target language: French", first_prompt)
        self.assertIn("Target language proficiency level: B1 CEFR", first_prompt)
        self.assertIn("Characters:\nM1: Alice", first_prompt)
        self.assertIn("Alice continuity notes", first_prompt)
        mock_update_story_chapter.assert_called_once_with(
            1,
            0,
            "Opening",
            "Generated opening",
            "Opening summary"
        )

    @patch("services.story_generation_service.index_chapter_summary")
    @patch("services.story_generation_service.get_character_summaries_by_names")
    @patch("services.story_generation_service.update_story_chapter")
    @patch("services.story_generation_service.call_selected_llm")
    @patch("services.story_generation_service.get_story_chapters")
    @patch("services.story_generation_service.get_story")
    def test_generate_story_chapters_progress_uses_chapter_number_over_last_chapter(
        self,
        mock_get_story,
        mock_get_story_chapters,
        mock_call_selected_llm,
        mock_update_story_chapter,
        mock_get_character_summaries,
        mock_index_chapter_summary
    ):
        mock_get_story.return_value = (
            1,
            "2026-05-14T12:00:00",
            "Story",
            10,
            "Overview",
            "Setting",
            "Tone",
            "",
            "",
            "",
            "[]",
            "[]",
        )
        mock_get_story_chapters.return_value = [
            (10, 1, 0, "Opening", "", ""),
            (11, 1, 1, "Chapter one", "", ""),
            (12, 1, 2, "Chapter two", "", ""),
            (13, 1, 3, "Chapter three", "", ""),
            (14, 1, 4, "Chapter four", "", ""),
            (15, 1, 5, "Chapter five", "", ""),
        ]
        mock_get_character_summaries.return_value = {}
        mock_call_selected_llm.side_effect = [
            value
            for chapter_number in range(6)
            for value in [
                f"Body {chapter_number}",
                f"Summary {chapter_number}",
            ]
        ]
        progress_calls = []

        generate_story_chapters(
            1,
            progress_callback=lambda current, total: progress_calls.append(
                (current, total)
            )
        )

        self.assertEqual(
            progress_calls,
            [
                (0, 5),
                (1, 5),
                (2, 5),
                (3, 5),
                (4, 5),
                (5, 5),
            ]
        )

    @patch("services.story_generation_service.index_chapter_summary")
    @patch("services.story_generation_service.get_character_summaries_by_names")
    @patch("services.story_generation_service.update_story_chapter")
    @patch("services.story_generation_service.call_selected_llm")
    @patch("services.story_generation_service.get_story_chapters")
    @patch("services.story_generation_service.get_story")
    def test_generate_story_chapters_aborts_after_failed_llm_call(
        self,
        mock_get_story,
        mock_get_story_chapters,
        mock_call_selected_llm,
        mock_update_story_chapter,
        mock_get_character_summaries,
        mock_index_chapter_summary
    ):
        mock_get_story.return_value = (
            1,
            "2026-05-14T12:00:00",
            "Story",
            10,
            "Overview",
            "Setting",
            "Tone",
            "",
            "",
            "",
            "[]",
            "[]",
        )
        mock_get_story_chapters.return_value = [
            (10, 1, 0, "Opening", "", ""),
            (11, 1, 1, "Chapter one", "", ""),
        ]
        mock_get_character_summaries.return_value = {}
        mock_call_selected_llm.return_value = None

        with self.assertRaises(LLMGenerationError):
            generate_story_chapters(1)

        mock_call_selected_llm.assert_called_once()
        mock_update_story_chapter.assert_not_called()
        mock_index_chapter_summary.assert_not_called()

    @patch("services.story_service.generate_story_chapter_body_and_summary")
    @patch("services.story_service.create_story_chapter")
    def test_create_and_generate_story_chapter_generates_new_chapter(
        self,
        mock_create_story_chapter,
        mock_generate_story_chapter
    ):
        mock_create_story_chapter.return_value = 42
        mock_generate_story_chapter.return_value = {
            "chapter_body": "Generated body",
            "chapter_summary": "Generated summary",
        }

        result = create_and_generate_story_chapter(
            1,
            3,
            "New chapter",
            "",
            ""
        )

        mock_create_story_chapter.assert_called_once_with(
            1,
            3,
            "New chapter",
            "",
            ""
        )
        mock_generate_story_chapter.assert_called_once_with(
            1,
            42,
            progress_callback=None
        )
        self.assertEqual(
            result,
            (
                42,
                {
                    "chapter_body": "Generated body",
                    "chapter_summary": "Generated summary",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
