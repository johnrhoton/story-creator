import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import yaml

from config import DB_NAME
from database.characters import (
    delete_characters,
    get_characters_for_export,
    save_character,
)
from database.db_encryption import (
    DATABASE_ENCRYPTED_VALUE_PREFIX,
    enable_database_encryption,
    set_active_database_password,
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
from views.bulk_actions import build_bulk_export_file_name, build_export_data
from views.export_import_view import build_full_export_file_name


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
            set_active_database_password("")
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
        export_yaml = build_export_data({
            "characters": [
                {
                    "name": "Alice"
                }
            ]
        })

        export_data = yaml.safe_load(export_yaml)

        self.assertIn("exported_at", export_data)
        self.assertEqual(
            export_data["characters"],
            [
                {
                    "name": "Alice"
                }
            ]
        )

    def test_build_export_data_does_not_reencrypt_yaml_payload(self):
        with isolated_database_directory():
            export_yaml = build_export_data(
                {
                    "characters": [
                        {
                            "name": "Alice"
                        }
                    ]
                },
                include_database_encryption_metadata=True
            )

        export_data = yaml.safe_load(export_yaml)

        self.assertEqual(
            export_data["characters"],
            [
                {
                    "name": "Alice"
                }
            ]
        )

    def test_build_bulk_export_file_name_uses_item_and_encrypted_suffix(self):
        file_name = build_bulk_export_file_name(
            "exported_characters",
            "20260514_175346",
            True
        )

        self.assertEqual(
            file_name,
            "story_builder_export__characters_20260514_175346_encrypted.yaml"
        )

    def test_build_bulk_export_file_name_omits_encrypted_suffix(self):
        file_name = build_bulk_export_file_name(
            "exported_profiles",
            "20260514_175346",
            False
        )

        self.assertEqual(
            file_name,
            "story_builder_export__profiles_20260514_175346.yaml"
        )

    def test_build_full_export_file_name_uses_full_and_encrypted_suffix(self):
        file_name = build_full_export_file_name(
            "20260514_175346",
            True,
            "yaml"
        )

        self.assertEqual(
            file_name,
            "story_builder_export_full_20260514_175346_encrypted.yaml"
        )

    def test_build_full_export_file_name_omits_encrypted_suffix(self):
        file_name = build_full_export_file_name(
            "20260514_175346",
            False,
            "json"
        )

        self.assertEqual(
            file_name,
            "story_builder_export_full_20260514_175346.json"
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

    def test_character_raw_export_keeps_ids_clear_and_db_fields_encrypted(self):
        with isolated_database_directory():
            save_character(
                "hero",
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
            enable_database_encryption("password")

            exported = get_characters_for_export([1], decrypt_values=False)

            self.assertEqual(exported[0]["id"], 1)
            self.assertEqual(exported[0]["name"], "Alice")
            self.assertTrue(
                exported[0]["physical_traits"].startswith(
                    DATABASE_ENCRYPTED_VALUE_PREFIX
                )
            )
            self.assertTrue(
                exported[0]["profile_name"].startswith(
                    DATABASE_ENCRYPTED_VALUE_PREFIX
                )
            )

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
