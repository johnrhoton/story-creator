import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from config import DB_NAME
from database.authorized_users import (
    add_authorized_user,
    bind_authorized_user_google_sub,
    delete_authorized_user,
    get_authorized_user_by_identity,
    get_authorized_users,
    update_authorized_user,
)
from database.characters import get_characters, save_character
from database.db_encryption import (
    DATABASE_ENCRYPTION_EXPORT_KEY,
    DATABASE_ENCRYPTED_VALUE_PREFIX,
    enable_database_encryption,
    get_database_encryption_status,
    set_active_database_password,
)
from database.import_export import (
    export_database_to_dict,
    export_database_to_json,
    export_database_to_yaml,
    import_database_from_dict,
    import_database_from_json,
    import_database_from_yaml,
    serialize_export_to_json,
    serialize_export_to_yaml,
)
from database.llm_models import (
    add_llm_model,
    get_llm_models_by_provider,
    set_default_llm_model,
)
from database.migrations import run_migrations
from database.profiles import add_profile, get_profiles
from database.schema import create_tables
from database.stories import add_story, get_stories
from database.object_history import get_object_history, log_object_history
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
            set_active_database_password("")
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
    def test_authorized_users_seed_default_administrator(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            users = get_authorized_users()

            self.assertEqual(len(users), 1)
            self.assertEqual(users[0][1], "rhoton@gmail.com")
            self.assertEqual(users[0][2], "Administrator")

    def test_authorized_users_support_crud_and_identity_binding(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            user_id = add_authorized_user(" User@Example.com ", "User")

            user = get_authorized_user_by_identity(email="user@example.com")
            self.assertEqual(user[0], user_id)
            self.assertEqual(user[1], "user@example.com")
            self.assertEqual(user[2], "User")
            self.assertFalse(user[3])

            self.assertTrue(
                bind_authorized_user_google_sub(user_id, "google-sub-1")
            )
            user = get_authorized_user_by_identity(
                google_sub="google-sub-1"
            )
            self.assertEqual(user[0], user_id)
            self.assertEqual(user[3], "google-sub-1")

            self.assertTrue(
                update_authorized_user(
                    user_id,
                    "updated@example.com",
                    "Administrator"
                )
            )
            user = get_authorized_user_by_identity(
                google_sub="google-sub-1"
            )
            self.assertEqual(user[1], "updated@example.com")
            self.assertEqual(user[2], "Administrator")

            self.assertTrue(delete_authorized_user(user_id))
            self.assertIsNone(
                get_authorized_user_by_identity(
                    google_sub="google-sub-1"
                )
            )

    def test_object_history_round_trips_contents(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            log_object_history(
                "Stories",
                7,
                "Harbor",
                "Update",
                {
                    "story_name": "Harbor",
                    "overview": "Fog and bells",
                }
            )

            rows = get_object_history()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][2], "Stories")
            self.assertEqual(rows[0][3], "7")
            self.assertEqual(rows[0][4], "Harbor")
            self.assertEqual(rows[0][5], "Update")
            self.assertIn('"story_name": "Harbor"', rows[0][6])

    def test_get_stories_orders_newest_first(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            older_id = add_story(
                "Older",
                None,
                "overview",
                "setting",
                "tone",
                [],
                []
            )
            newer_id = add_story(
                "Newer",
                None,
                "overview",
                "setting",
                "tone",
                [],
                []
            )

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE stories SET created_at = ? WHERE id = ?",
                ("2026-05-14T10:00:00", older_id)
            )
            cursor.execute(
                "UPDATE stories SET created_at = ? WHERE id = ?",
                ("2026-05-15T10:00:00", newer_id)
            )
            conn.commit()
            conn.close()

            self.assertEqual(
                [story[2] for story in get_stories()],
                ["Newer", "Older"]
            )

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

    def test_export_json_uses_export_dictionary(self):
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
                "note",
                "prompt",
                "response",
                "summary"
            )

            export_data = export_database_to_dict()
            export_json = export_database_to_json()

            self.assertIn("exported_at", export_data)
            self.assertEqual(
                export_data["characters"][0]["name"],
                "Alice"
            )
            self.assertEqual(
                json.loads(serialize_export_to_json(export_data)),
                export_data
            )
            self.assertEqual(
                json.loads(export_json)["characters"][0]["name"],
                "Alice"
            )

    def test_export_yaml_uses_export_dictionary(self):
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
                "note",
                "prompt",
                "response",
                "summary"
            )

            export_data = export_database_to_dict()
            export_yaml = export_database_to_yaml()

            self.assertEqual(
                serialize_export_to_yaml(export_data),
                export_yaml
            )
            self.assertIn("characters:", export_yaml)
            self.assertIn("name: Alice", export_yaml)

    def test_import_database_from_dict_matches_json_import(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            import_payload = {
                "profiles": [
                    {
                        "profile_name": "Hero",
                        "gender": "female",
                        "physical_traits": "quick",
                        "personality_traits": "kind",
                        "notes": "note"
                    }
                ]
            }

            result = import_database_from_dict(import_payload)

            self.assertEqual(result["profiles"], 1)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    profile_name,
                    physical_traits,
                    personality_traits
                FROM profiles
            """)
            rows = cursor.fetchall()
            conn.close()

            self.assertEqual(
                rows,
                [("hero", "quick", "kind")]
            )

    def test_import_database_from_yaml(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            import_payload = """
profiles:
  - profile_name: Hero
    gender: female
    physical_traits: quick
    personality_traits: kind
    notes: note
"""

            result = import_database_from_yaml(
                StringIO(import_payload)
            )

            self.assertEqual(result["profiles"], 1)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    profile_name,
                    physical_traits,
                    personality_traits
                FROM profiles
            """)
            rows = cursor.fetchall()
            conn.close()

            self.assertEqual(
                rows,
                [("hero", "quick", "kind")]
            )

    def test_raw_json_export_import_round_trip(self):
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
                "note",
                "prompt",
                "response",
                "summary"
            )

            encrypted_json = export_database_to_json(
                encrypt_values=True,
                password="password"
            )

            self.assertIn("characters", encrypted_json)
            self.assertIn('"Alice"', encrypted_json)
            self.assertNotIn("encrypted:v2:", encrypted_json)

        with isolated_database_directory():
            run_migrations()
            create_tables()

            result = import_database_from_json(
                StringIO(encrypted_json),
                password="password"
            )

            self.assertEqual(result["characters"], 1)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    name,
                    age,
                    summary
                FROM characters
            """)
            rows = cursor.fetchall()
            conn.close()

            self.assertEqual(
                rows,
                [("Alice", "18", "summary")]
            )

    def test_raw_yaml_export_import_round_trip(self):
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
                "note",
                "prompt",
                "response",
                "summary"
            )

            encrypted_yaml = export_database_to_yaml(
                encrypt_values=True,
                password="password"
            )

            self.assertIn("characters:", encrypted_yaml)
            self.assertIn("Alice", encrypted_yaml)
            self.assertNotIn("encrypted:v2:", encrypted_yaml)

        with isolated_database_directory():
            run_migrations()
            create_tables()

            result = import_database_from_yaml(
                StringIO(encrypted_yaml),
                password="password"
            )

            self.assertEqual(result["characters"], 1)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    name,
                    age,
                    summary
                FROM characters
            """)
            rows = cursor.fetchall()
            conn.close()

            self.assertEqual(
                rows,
                [("Alice", "18", "summary")]
            )

    def test_raw_export_does_not_require_password(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            export_json = export_database_to_json(
                encrypt_values=True,
                password=""
            )

            self.assertIn("characters", export_json)

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

    def test_sync_local_export_includes_database_encryption_metadata(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()
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

            export_data = sync_service.get_local_export()

            self.assertIn(DATABASE_ENCRYPTION_EXPORT_KEY, export_data)
            self.assertIn(
                "salt",
                export_data[DATABASE_ENCRYPTION_EXPORT_KEY]
            )
            self.assertTrue(
                export_data["characters"][0]["profile_name"].startswith(
                    DATABASE_ENCRYPTED_VALUE_PREFIX
                )
            )

    def test_sync_pull_applies_database_encryption_metadata(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()
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
            add_profile(
                "hero",
                "female",
                "quick",
                "curious",
                "note"
            )
            add_profile(
                "mentor",
                "male",
                "older",
                "patient",
                "guides"
            )
            enable_database_encryption("password")
            mongo_data = sync_service.get_local_export()
            mongo_hash = sync_service.get_content_hash(mongo_data)

        with isolated_database_directory():
            run_migrations()
            create_tables()

            original_get_mongo_backup = sync_service.get_mongo_backup
            sync_service.get_mongo_backup = lambda: {
                "_id": sync_service.SYNC_DOCUMENT_ID,
                "last_synced_at": "2026-05-14T12:00:00+00:00",
                "data_modified_at": "2026-05-14T12:00:00+00:00",
                "content_hash": mongo_hash,
                "data": mongo_data
            }

            try:
                sync_service.pull_mongo_to_local()
            finally:
                sync_service.get_mongo_backup = original_get_mongo_backup

            self.assertEqual(
                get_database_encryption_status(),
                {
                    "enabled": True,
                    "unlocked": False,
                }
            )

            set_active_database_password("password")

            self.assertEqual(
                get_characters()[0][3],
                "Alice"
            )
            self.assertEqual(
                get_characters()[0][6],
                "quick"
            )
            self.assertEqual(
                [profile[0] for profile in get_profiles()],
                ["hero", "mentor"]
            )


if __name__ == "__main__":
    unittest.main()
