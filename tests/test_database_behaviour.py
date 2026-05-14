import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from config import DB_NAME
from database.characters import save_character
from database.import_export import import_database_from_json
from database.llm_models import (
    add_llm_model,
    get_llm_models_by_provider,
    set_default_llm_model,
)
from database.migrations import run_migrations
from database.schema import create_tables
from services import sync_service
from services.sync_service import get_content_hash
from scripts.seed_llm_models import seed_llm_models


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


def get_columns(table_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [
        row[1]
        for row in cursor.fetchall()
    ]
    conn.close()

    return columns


class DatabaseBehaviourTests(unittest.TestCase):
    def test_migrations_rename_database_and_update_schema(self):
        with isolated_database_directory():
            old_db_path = Path("character_generations_v3.db")
            conn = sqlite3.connect(old_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL UNIQUE,
                    name TEXT,
                    age TEXT,
                    gender TEXT,
                    traits TEXT,
                    notes TEXT
                )
            """)
            cursor.execute("""
                INSERT INTO profiles
                (
                    profile_name,
                    name,
                    age,
                    gender,
                    traits,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "hero",
                "Old Default Name",
                "42",
                "female",
                "brave",
                "note"
            ))
            conn.commit()
            conn.close()

            run_migrations()
            create_tables()

            self.assertFalse(old_db_path.exists())
            self.assertTrue(Path(DB_NAME).exists())

            profile_columns = get_columns("profiles")
            self.assertNotIn("name", profile_columns)
            self.assertNotIn("age", profile_columns)
            self.assertIn("personality_traits", profile_columns)

            model_columns = get_columns("llm_models")
            self.assertIn("is_default", model_columns)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    profile_name,
                    gender,
                    personality_traits,
                    notes
                FROM profiles
            """)
            self.assertEqual(
                cursor.fetchone(),
                ("hero", "female", "brave", "note")
            )
            conn.close()

    def test_character_import_overwrites_existing_name(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            save_character(
                None,
                "Alice",
                "18",
                "female",
                "quick",
                "kind",
                "first note",
                "first prompt",
                "first response",
                "first summary"
            )

            import_payload = {
                "characters": [
                    {
                        "created_at": "2026-05-14T10:00:00",
                        "name": "Alice",
                        "age": "19",
                        "gender": "female",
                        "physical_traits": "updated physical",
                        "personality_traits": "updated personality",
                        "notes": "updated note",
                        "prompt": "updated prompt",
                        "response": "updated response",
                        "summary": "updated summary"
                    }
                ]
            }

            result = import_database_from_json(
                StringIO(json.dumps(import_payload))
            )

            self.assertEqual(result["characters"], 1)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    name,
                    age,
                    response,
                    summary
                FROM characters
                WHERE name = ?
            """, (
                "Alice",
            ))
            rows = cursor.fetchall()
            conn.close()

            self.assertEqual(
                rows,
                [("Alice", "19", "updated response", "updated summary")]
            )

    def test_seeded_models_have_one_default_per_provider(self):
        with isolated_database_directory():
            seed_llm_models()

            expected_defaults = {
                "Gemini": "gemini-2.5-flash",
                "Groq": "llama-3.3-70b-versatile",
                "OpenRouter": "openrouter/auto",
            }

            for provider, expected_model in expected_defaults.items():
                provider_models = get_llm_models_by_provider(provider)
                defaults = [
                    row for row in provider_models
                    if row[4]
                ]

                self.assertEqual(len(defaults), 1)
                self.assertEqual(defaults[0][2], expected_model)

            groq_models = get_llm_models_by_provider("Groq")
            replacement = [
                row for row in groq_models
                if row[2] == "qwen3-32b"
            ][0]

            self.assertTrue(set_default_llm_model(replacement[0]))

            defaults = [
                row for row in get_llm_models_by_provider("Groq")
                if row[4]
            ]

            self.assertEqual(len(defaults), 1)
            self.assertEqual(defaults[0][2], "qwen3-32b")

    def test_model_import_preserves_default_flag(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            import_payload = {
                "llm_models": [
                    {
                        "provider": "Groq",
                        "model": "custom-one",
                        "best_use": "first",
                        "is_default": 1
                    },
                    {
                        "provider": "Groq",
                        "model": "custom-two",
                        "best_use": "second",
                        "is_default": 0
                    }
                ]
            }

            result = import_database_from_json(
                StringIO(json.dumps(import_payload))
            )

            self.assertEqual(result["llm_models"], 2)

            defaults = [
                row for row in get_llm_models_by_provider("Groq")
                if row[4]
            ]

            self.assertEqual(len(defaults), 1)
            self.assertEqual(defaults[0][2], "custom-one")

            add_llm_model(
                "Groq",
                "custom-two",
                "second",
                True
            )

            defaults = [
                row for row in get_llm_models_by_provider("Groq")
                if row[4]
            ]

            self.assertEqual(len(defaults), 1)
            self.assertEqual(defaults[0][2], "custom-two")

    def test_sync_content_hash_ignores_ids_and_export_time(self):
        first_export = {
            "exported_at": "2026-05-14T10:00:00",
            "characters": [
                {
                    "id": 1,
                    "name": "Alice",
                    "age": "18"
                }
            ],
            "llm_models": [
                {
                    "id": 1,
                    "provider": "Groq",
                    "model": "custom",
                    "best_use": "test",
                    "is_default": 1
                }
            ],
            "story_chapters": [
                {
                    "id": 1,
                    "story_id": 10,
                    "chapter_number": 0,
                    "chapter_body": "body"
                }
            ]
        }

        second_export = {
            "exported_at": "2026-05-14T11:00:00",
            "characters": [
                {
                    "id": 99,
                    "name": "Alice",
                    "age": "18"
                }
            ],
            "llm_models": [
                {
                    "id": 42,
                    "provider": "Groq",
                    "model": "custom",
                    "best_use": "test",
                    "is_default": 1
                }
            ],
            "story_chapters": [
                {
                    "id": 8,
                    "story_id": 77,
                    "chapter_number": 0,
                    "chapter_body": "body"
                }
            ]
        }

        self.assertEqual(
            get_content_hash(first_export),
            get_content_hash(second_export)
        )

    def test_sync_uses_story_builder_document_id_with_legacy_fallback(self):
        class FakeCollection:
            def __init__(self):
                self.queries = []

            def find_one(self, query):
                self.queries.append(query)

                if query == {"_id": sync_service.LEGACY_SYNC_DOCUMENT_ID}:
                    return {
                        "_id": sync_service.LEGACY_SYNC_DOCUMENT_ID,
                        "data": {
                            "characters": []
                        }
                    }

                return None

        original_get_mongo_collection = sync_service.get_mongo_collection
        fake_collection = FakeCollection()
        sync_service.get_mongo_collection = lambda: fake_collection

        try:
            mongo_doc = sync_service.get_mongo_backup()
        finally:
            sync_service.get_mongo_collection = original_get_mongo_collection

        self.assertEqual(
            mongo_doc["_id"],
            sync_service.LEGACY_SYNC_DOCUMENT_ID
        )
        self.assertEqual(
            fake_collection.queries,
            [
                {"_id": sync_service.SYNC_DOCUMENT_ID},
                {"_id": sync_service.LEGACY_SYNC_DOCUMENT_ID}
            ]
        )


if __name__ == "__main__":
    unittest.main()
