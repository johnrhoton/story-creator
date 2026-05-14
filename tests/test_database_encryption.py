import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from config import DB_NAME
from database.characters import get_characters, save_character
from database.db_encryption import (
    DATABASE_ENCRYPTED_VALUE_PREFIX,
    enable_database_encryption,
    set_active_database_password,
)
from database.import_export import export_database_to_json
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

            character = get_characters()[0]

            self.assertEqual(character[3], "Alice")
            self.assertEqual(character[6], "quick")
            self.assertEqual(character[10], "summary")

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


if __name__ == "__main__":
    unittest.main()
