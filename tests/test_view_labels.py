import unittest

from views.history_view import (
    build_llm_history_label,
    build_object_history_label,
)
from views.profiles_view import build_profile_expander_label
from views.rag_debug_view import order_memory_groups
from views.stories_view import (
    build_story_expander_title,
    count_story_words,
    count_words,
)


class ViewLabelTests(unittest.TestCase):
    def test_story_expander_title_includes_template_and_word_count(self):
        chapters = [
            (1, 10, 0, "Opening", "one two three", "summary"),
            (2, 10, 1, "First chapter", "four five", "summary"),
        ]

        self.assertEqual(
            build_story_expander_title(
                "My story",
                7,
                {7: "My template"},
                chapters
            ),
            "My story - My template (5 words)"
        )

    def test_story_word_count_uses_chapter_bodies(self):
        chapters = [
            (1, 10, 0, "Opening", "one two", "summary has many words"),
            (2, 10, 1, "First chapter", "", "summary"),
        ]

        self.assertEqual(count_story_words(chapters), 2)
        self.assertEqual(count_words(None), 0)

    def test_profile_expander_label_includes_first_five_traits(self):
        self.assertEqual(
            build_profile_expander_label(
                "hero",
                "tall, scarred, quick\nsharp-eyed",
                "brave; patient; curious"
            ),
            "hero - tall, scarred, quick, sharp-eyed, brave"
        )

    def test_profile_expander_label_uses_name_when_no_traits(self):
        self.assertEqual(
            build_profile_expander_label("hero", "", ""),
            "hero"
        )

    def test_rag_memory_groups_use_preferred_order(self):
        grouped = {
            "character": ["character"],
            "unknown": ["unknown"],
            "story": ["story"],
            "chapter_summary": ["chapter"],
        }

        self.assertEqual(
            list(order_memory_groups(grouped).keys()),
            ["story", "chapter_summary", "character", "unknown"]
        )

    def test_object_history_label_includes_required_fields(self):
        self.assertEqual(
            build_object_history_label({
                "object_type": "Stories",
                "object_id": 7,
                "name": "Harbor",
                "timestamp": "2026-05-17T10:30:00",
                "operation": "Update",
            }),
            "Stories — #7 — Harbor — 2026-05-17 10:30:00 — Update"
        )

    def test_llm_history_label_includes_status(self):
        self.assertEqual(
            build_llm_history_label({
                "id": 3,
                "provider": "Groq",
                "model": "llama",
                "timestamp": "2026-05-17T10:30:00",
                "status": "Failure",
            }),
            "#3 — Groq — llama — 2026-05-17 10:30:00 — Failure"
        )


if __name__ == "__main__":
    unittest.main()
