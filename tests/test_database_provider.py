import io
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from config import (
    get_app_mongo_database,
    get_app_mongo_uri,
    get_backup_mongo_database,
    get_backup_mongo_uri,
    get_db_provider,
    get_vector_provider,
)
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

    def test_get_vector_provider_defaults_to_chroma(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_vector_provider(), "chroma")

    def test_get_vector_provider_accepts_none_and_mongodb_vector(self):
        with patch.dict(os.environ, {"VECTOR_PROVIDER": "none"}, clear=True):
            self.assertEqual(get_vector_provider(), "none")

        with patch.dict(
            os.environ,
            {"VECTOR_PROVIDER": "mongodb_vector"},
            clear=True
        ):
            self.assertEqual(get_vector_provider(), "mongodb_vector")

    def test_invalid_vector_provider_fails_fast(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import config",
            ],
            env={**os.environ, "VECTOR_PROVIDER": "pinecone"},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("VECTOR_PROVIDER must be one of", result.stderr)

    def test_app_mongo_uri_supports_legacy_mongo_uri_env_name(self):
        with patch.dict(os.environ, {"MONGO_URI": "mongodb+srv://example"}, clear=True):
            self.assertEqual(get_mongo_uri(), "mongodb+srv://example")

    def test_app_mongo_database_name_defaults_to_story_builder(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "config.get_config_value",
            side_effect=lambda _name, default=None: default,
        ):
            self.assertEqual(get_mongo_database_name(), "story_builder")

    def test_app_mongo_settings_prefer_explicit_names(self):
        with patch.dict(
            os.environ,
            {
                "APP_MONGO_URI": "mongodb+srv://app",
                "APP_MONGO_DATABASE": "app_db",
                "MONGO_URI": "mongodb+srv://legacy",
                "MONGO_DATABASE": "legacy_db",
            },
            clear=True,
        ):
            self.assertEqual(get_app_mongo_uri(), "mongodb+srv://app")
            self.assertEqual(get_app_mongo_database(), "app_db")

    def test_backup_mongo_settings_prefer_explicit_names(self):
        with patch.dict(
            os.environ,
            {
                "BACKUP_MONGO_URI": "mongodb+srv://backup",
                "BACKUP_MONGO_DATABASE": "backup_db",
                "MONGO_URI": "mongodb+srv://legacy",
                "MONGO_DATABASE": "legacy_db",
            },
            clear=True,
        ):
            self.assertEqual(get_backup_mongo_uri(), "mongodb+srv://backup")
            self.assertEqual(get_backup_mongo_database(), "backup_db")

    def test_backup_mongo_settings_fall_back_to_legacy_names(self):
        with patch.dict(
            os.environ,
            {
                "MONGODB_URI": "mongodb+srv://legacy-backup",
                "MONGODB_DATABASE": "legacy_backup_db",
            },
            clear=True,
        ):
            self.assertEqual(get_backup_mongo_uri(), "mongodb+srv://legacy-backup")
            self.assertEqual(get_backup_mongo_database(), "legacy_backup_db")

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

    def test_mongodb_import_functions_accept_ui_kwargs(self):
        from database import mongodb_repositories

        uploaded_file = io.BytesIO(b"stories:\n- id: 1\n  story_name: Test\n")

        with patch.object(
            mongodb_repositories,
            "import_database_from_dict",
            return_value={"stories": 1},
        ) as mock_import:
            result = mongodb_repositories.import_database_from_yaml(
                uploaded_file,
                password="",
                database_password="",
            )

        self.assertEqual(result, {"stories": 1})
        mock_import.assert_called_once_with(
            {"stories": [{"id": 1, "story_name": "Test"}]},
            replace_existing=False,
            database_password="",
        )

    def test_mongodb_json_import_accepts_sync_pull_kwargs(self):
        from database import mongodb_repositories

        uploaded_file = io.BytesIO(b'{"stories": [{"id": 1, "story_name": "Test"}]}')

        with patch.object(
            mongodb_repositories,
            "import_database_from_dict",
            return_value={"stories": 1},
        ) as mock_import:
            result = mongodb_repositories.import_database_from_json(
                uploaded_file,
                replace_existing=True,
                database_password="secret",
            )

        self.assertEqual(result, {"stories": 1})
        mock_import.assert_called_once_with(
            {"stories": [{"id": 1, "story_name": "Test"}]},
            replace_existing=True,
            database_password="secret",
        )

    def test_mongodb_export_functions_accept_ui_kwargs(self):
        from database import mongodb_repositories

        with patch.object(
            mongodb_repositories,
            "prepare_export_data",
            return_value={"stories": []},
        ) as mock_prepare:
            output = mongodb_repositories.export_database_to_json(
                encrypt_values=False,
                password="",
            )

        self.assertIn('"stories": []', output)
        mock_prepare.assert_called_once_with(
            encrypt_values=False,
            password="",
        )


if __name__ == "__main__":
    unittest.main()
