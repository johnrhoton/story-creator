import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from config import DB_NAME
from database.migrations import run_migrations
from database.schema import create_tables
from database.stories import (
    create_story_from_template,
    get_story,
    get_story_chapters,
)
from database.templates import (
    add_story_template,
    add_story_template_chapter,
    get_story_templates,
)
from services.template_service import parse_character_roles


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


class StoryTemplateSlotTests(unittest.TestCase):
    def test_template_roles_are_stored_and_parsed(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            template_id = add_story_template(
                "Quest",
                "Meet M1 and F1.",
                "At the docks with M1 and F1.",
                "Epic.",
                male_character_roles='["Captain", "Navigator"]',
                female_character_roles='["First Mate"]',
            )
            add_story_template_chapter(
                template_id,
                1,
                "M1 leads the crew while F1 checks the sails."
            )

            templates = get_story_templates()
            self.assertEqual(len(templates), 1)

            template = templates[0]
            self.assertEqual(template[2], "Quest")
            self.assertEqual(
                parse_character_roles(template[6]),
                ["Captain", "Navigator"]
            )
            self.assertEqual(
                parse_character_roles(template[7]),
                ["First Mate"]
            )

    def test_story_creation_replaces_placeholder_slots(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            template_id = add_story_template(
                "Quest",
                "M1 and F1 set sail together.",
                "The ship leaves port with M1 and F1.",
                "Adventure.",
                male_character_roles='["Captain"]',
                female_character_roles='["First Mate"]',
            )
            add_story_template_chapter(
                template_id,
                1,
                "M1 gives orders and F1 records the journey."
            )

            story_id = create_story_from_template(
                template_id,
                "Seafaring Story",
                ["Alden"],
                ["Mira"]
            )

            story = get_story(story_id)
            self.assertIsNotNone(story)
            self.assertIn("Alden", story[4])
            self.assertIn("Mira", story[4])

            chapters = get_story_chapters(story_id)
            self.assertEqual(len(chapters), 2)
            first_story_chapter = next(
                chapter for chapter in chapters if chapter[2] == 1
            )
            self.assertIn("Alden", first_story_chapter[3])
            self.assertIn("Mira", first_story_chapter[3])


if __name__ == "__main__":
    unittest.main()
