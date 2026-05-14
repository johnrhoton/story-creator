import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from config import DB_NAME
from database.characters import get_characters, save_character
from database.profiles import add_profile, get_profiles
from database.db_encryption import (
    DATABASE_ENCRYPTION_EXPORT_KEY,
    DATABASE_ENCRYPTED_VALUE_PREFIX,
    enable_database_encryption,
    get_database_encryption_status,
    set_active_database_password,
)
from database.import_export import (
    export_database_to_json,
    import_database_from_dict,
    import_database_from_json,
)
from database.migrations import run_migrations
from database.schema import create_tables


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


class DatabaseEncryptionTests(unittest.TestCase):
    def test_enable_database_encryption_encrypts_existing_character_fields(self):
        with isolated_database_directory():
            save_character(
                "hero",
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

            enable_database_encryption("password")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    name,
                    profile_name,
                    physical_traits,
                    summary
                FROM characters
            """)
            raw_row = cursor.fetchone()
            conn.close()

            self.assertEqual(raw_row[0], "Alice")
            self.assertTrue(
                raw_row[1].startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
            )
            self.assertTrue(
                raw_row[2].startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
            )
            self.assertTrue(
                raw_row[3].startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
            )

            character = get_characters()[0]

            self.assertEqual(character[3], "Alice")
            self.assertEqual(character[6], "quick")
            self.assertEqual(character[10], "summary")

    def test_profile_names_are_encrypted_and_readable_when_unlocked(self):
        with isolated_database_directory():
            add_profile(
                "Hero",
                "female",
                "quick",
                "kind",
                "note"
            )

            enable_database_encryption("password")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    profile_name,
                    physical_traits,
                    personality_traits,
                    notes
                FROM profiles
            """)
            raw_row = cursor.fetchone()
            conn.close()

            for value in raw_row:
                self.assertTrue(
                    value.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
                )

            self.assertEqual(
                get_profiles(),
                [("hero", "female", "quick", "kind", "note")]
            )

    def test_wrong_database_password_does_not_unlock_database(self):
        with isolated_database_directory():
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
            enable_database_encryption("password")
            set_active_database_password("")

            set_active_database_password("wrong")

            self.assertEqual(
                get_database_encryption_status(),
                {
                    "enabled": True,
                    "unlocked": False,
                }
            )

    def test_plain_export_decrypts_encrypted_database_fields_when_unlocked(self):
        with isolated_database_directory():
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

            enable_database_encryption("password")

            export_json = export_database_to_json()

            self.assertIn('"physical_traits": "quick"', export_json)
            self.assertNotIn(DATABASE_ENCRYPTED_VALUE_PREFIX, export_json)

    def test_encrypted_export_preserves_database_encrypted_values(self):
        with isolated_database_directory():
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

            enable_database_encryption("password")

            export_json = export_database_to_json(encrypt_values=True)

            self.assertIn(DATABASE_ENCRYPTION_EXPORT_KEY, export_json)
            self.assertIn('"verifier"', export_json)
            self.assertIn(DATABASE_ENCRYPTED_VALUE_PREFIX, export_json)
            self.assertIn('"name": "Alice"', export_json)
            self.assertNotIn('"physical_traits": "quick"', export_json)
            self.assertNotIn('"summary": "summary"', export_json)

    def test_database_encrypted_export_import_round_trips_after_unlock(self):
        with isolated_database_directory():
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
            enable_database_encryption("password")

            export_json = export_database_to_json(encrypt_values=True)

        with isolated_database_directory():
            import_database_from_json(StringIO(export_json))
            set_active_database_password("password")

            character = get_characters()[0]

            self.assertEqual(character[3], "Alice")
            self.assertEqual(character[6], "quick")
            self.assertEqual(character[10], "summary")

    def test_clear_import_without_database_password_stores_plain_text(self):
        with isolated_database_directory():
            import_database_from_dict({
                "characters": [
                    {
                        "name": "Alice",
                        "age": "18",
                        "gender": "female",
                        "summary": "summary",
                    }
                ]
            })

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT summary FROM characters")
            raw_summary = cursor.fetchone()[0]
            conn.close()

            self.assertEqual(raw_summary, "summary")

    def test_clear_import_with_database_password_stores_encrypted_text(self):
        with isolated_database_directory():
            import_database_from_dict(
                {
                    "characters": [
                        {
                            "name": "Alice",
                            "age": "18",
                            "gender": "female",
                            "summary": "summary",
                        }
                    ]
                },
                database_password="password"
            )

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT summary FROM characters")
            raw_summary = cursor.fetchone()[0]
            conn.close()

            self.assertTrue(
                raw_summary.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
            )

            character = get_characters()[0]

            self.assertEqual(character[10], "summary")


if __name__ == "__main__":
    unittest.main()
