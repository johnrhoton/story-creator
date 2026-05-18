import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from config import get_db_provider
from database.mongodb_connection import get_mongo_database_name, get_mongo_uri


class DatabaseProviderTests(unittest.TestCase):
    def test_get_db_provider_defaults_to_sqlite(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_db_provider(), "sqlite")

    def test_get_db_provider_accepts_mongodb(self):
        with patch.dict(os.environ, {"DB_PROVIDER": "mongodb"}, clear=True):
            self.assertEqual(get_db_provider(), "mongodb")

    def test_invalid_db_provider_fails_fast(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import config",
            ],
            env={**os.environ, "DB_PROVIDER": "postgres"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DB_PROVIDER must be one of", result.stderr)

    def test_mongo_uri_supports_mongo_uri_env_name(self):
        with patch.dict(os.environ, {"MONGO_URI": "mongodb+srv://example"}, clear=True):
            self.assertEqual(get_mongo_uri(), "mongodb+srv://example")

    def test_mongo_database_name_defaults_to_story_builder(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_mongo_database_name(), "story_builder")

    def test_database_package_exports_mongo_provider_functions(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import database; "
                    "print(database.get_database_provider_status()['provider']); "
                    "print(hasattr(database, 'get_stories')); "
                    "print(hasattr(database, 'get_authorized_users'))"
                ),
            ],
            env={**os.environ, "DB_PROVIDER": "mongodb"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            ["mongodb", "True", "True"]
        )


if __name__ == "__main__":
    unittest.main()
