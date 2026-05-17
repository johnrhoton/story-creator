import unittest

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


if __name__ == "__main__":
    unittest.main()
