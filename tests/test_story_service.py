import unittest

from services.story_service import build_full_story_markdown


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


if __name__ == "__main__":
    unittest.main()
