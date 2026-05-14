import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from config import DB_NAME
from database.characters import (
    delete_characters,
    get_characters_for_export,
    save_character,
)
from database.llm_models import (
    add_llm_model,
    delete_llm_models,
    get_llm_models,
    get_llm_models_for_export,
)
from database.migrations import run_migrations
from database.profiles import (
    add_profile,
    delete_profiles,
    get_profiles_for_export,
)
from database.schema import create_tables
from database.stories import (
    add_story,
    add_story_chapter,
    delete_stories,
    get_stories_for_export,
)
from database.templates import (
    add_story_template,
    add_story_template_chapter,
    delete_story_templates,
    get_story_templates_for_export,
)
from views.bulk_actions import build_export_data


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            run_migrations()
            create_tables()
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


def fetch_count(table_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()

    return count


class BulkHelperTests(unittest.TestCase):
    def test_build_export_data_adds_timestamp_and_payload(self):
        export_json = build_export_data({
            "characters": [
                {
                    "name": "Alice"
                }
            ]
        })

        export_data = json.loads(export_json)

        self.assertIn("exported_at", export_data)
        self.assertEqual(
            export_data["characters"],
            [
                {
                    "name": "Alice"
                }
            ]
        )

    def test_character_bulk_export_and_delete_helpers(self):
        with isolated_database_directory():
            save_character(
                None,
                "Alice",
                "18",
                "female",
                "quick",
                "curious",
                "note",
                "prompt",
                "response",
                "summary"
            )
            save_character(
                None,
                "Ben",
                "19",
                "male",
                "tall",
                "kind",
                "note",
                "prompt",
                "response",
                "summary"
            )

            exported = get_characters_for_export([1, 2])
            self.assertEqual(
                [row["name"] for row in exported],
                ["Alice", "Ben"]
            )

            self.assertEqual(delete_characters([1, 2]), 2)
            self.assertEqual(fetch_count("characters"), 0)

    def test_profile_bulk_export_and_delete_helpers(self):
        with isolated_database_directory():
            add_profile(
                "Hero",
                "female",
                "athletic",
                "brave",
                "profile note"
            )
            add_profile(
                "Mentor",
                "male",
                "older",
                "wise",
                "profile note"
            )

            exported = get_profiles_for_export(["Hero", "Mentor"])
            self.assertEqual(
                [row["profile_name"] for row in exported],
                ["hero", "mentor"]
            )

            self.assertEqual(delete_profiles(["Hero", "Mentor"]), 2)
            self.assertEqual(fetch_count("profiles"), 0)

    def test_template_bulk_export_and_delete_helpers_include_chapters(self):
        with isolated_database_directory():
            template_id = add_story_template(
                "Quest",
                "overview",
                "setting",
                "tone"
            )
            add_story_template_chapter(
                template_id,
                1,
                "The journey begins."
            )

            exported = get_story_templates_for_export([template_id])
            self.assertEqual(
                exported["story_templates"][0]["template_name"],
                "Quest"
            )
            self.assertEqual(
                exported["story_template_chapters"][0]["chapter_description"],
                "The journey begins."
            )

            self.assertEqual(delete_story_templates([template_id]), 1)
            self.assertEqual(fetch_count("story_templates"), 0)
            self.assertEqual(fetch_count("story_template_chapters"), 0)

    def test_story_bulk_export_and_delete_helpers_include_chapters(self):
        with isolated_database_directory():
            story_id = add_story(
                "Quest Draft",
                None,
                "overview",
                "setting",
                "tone",
                ["Ben"],
                ["Alice"]
            )
            add_story_chapter(
                story_id,
                0,
                "Introduce everyone.",
                "Body",
                "Summary"
            )

            exported = get_stories_for_export([story_id])
            self.assertEqual(
                exported["stories"][0]["story_name"],
                "Quest Draft"
            )
            self.assertEqual(
                exported["story_chapters"][0]["chapter_summary"],
                "Summary"
            )

            self.assertEqual(delete_stories([story_id]), 1)
            self.assertEqual(fetch_count("stories"), 0)
            self.assertEqual(fetch_count("story_chapters"), 0)

    def test_model_bulk_export_and_delete_helpers(self):
        with isolated_database_directory():
            add_llm_model(
                "Groq",
                "llama-3.3-70b-versatile",
                "General reasoning",
                True
            )
            add_llm_model(
                "OpenRouter",
                "openrouter/auto",
                "Routing",
                True
            )

            model_ids = [
                row[0]
                for row in get_llm_models()
            ]
            exported = get_llm_models_for_export(model_ids)

            self.assertEqual(
                [row["model"] for row in exported],
                ["llama-3.3-70b-versatile", "openrouter/auto"]
            )

            self.assertEqual(delete_llm_models(model_ids), 2)
            self.assertEqual(fetch_count("llm_models"), 0)


if __name__ == "__main__":
    unittest.main()
