import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import (
    get_config_value,
    get_app_mongo_database,
    get_app_mongo_uri,
    get_backup_mongo_database,
    get_backup_mongo_uri,
    get_db_provider,
    get_chroma_db_path,
    get_sqlite_db_path,
    get_vector_provider,
)
from database.mongodb_connection import get_mongo_database_name, get_mongo_uri
from database.connection import get_connection


class DatabaseProviderTests(unittest.TestCase):
    def test_get_db_provider_defaults_to_sqlite(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_db_provider(), "sqlite")

    def test_get_db_provider_accepts_mongodb(self):
        with patch.dict(os.environ, {"DB_PROVIDER": "mongodb"}, clear=True):
            self.assertEqual(get_db_provider(), "mongodb")

    def test_sqlite_db_path_defaults_to_data_directory(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "config.get_config_value",
            side_effect=lambda _name, default=None: default,
        ):
            self.assertEqual(
                get_sqlite_db_path(),
                "data/sqlite/story_builder.db",
            )

    def test_sqlite_db_path_can_be_configured_with_env(self):
        with patch.dict(
            os.environ,
            {"STORY_DB_PATH": "/tmp/custom_story_builder.db"},
            clear=True,
        ):
            self.assertEqual(
                get_sqlite_db_path(),
                "/tmp/custom_story_builder.db",
            )

    def test_sqlite_connection_uses_configured_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nested" / "custom.db"

            with patch.dict(
                os.environ,
                {"STORY_DB_PATH": str(db_path)},
                clear=True,
            ):
                conn = get_connection()
                conn.close()

            self.assertTrue(db_path.exists())

    def test_chroma_db_path_can_be_configured_with_env(self):
        with patch.dict(
            os.environ,
            {"CHROMA_DB_PATH": "/tmp/custom_chroma"},
            clear=True,
        ):
            self.assertEqual(get_chroma_db_path(), "/tmp/custom_chroma")

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

    def test_nested_streamlit_secrets_are_supported(self):
        fake_secrets = {
            "database": {
                "provider": "mongodb",
                "uri": "mongodb+srv://app-nested",
                "database": "app_nested_db",
                "backup": {
                    "uri": "mongodb+srv://backup-nested",
                    "database": "backup_nested_db",
                },
            },
            "rag": {
                "provider": "mongodb_vector",
            },
            "llm": {
                "openrouter": {
                    "api_key": "openrouter-secret",
                },
            },
        }

        class FakeStreamlit:
            secrets = fake_secrets

        with patch.dict(os.environ, {}, clear=True), patch.dict(
            sys.modules,
            {"streamlit": FakeStreamlit}
        ):
            self.assertEqual(get_config_value("DB_PROVIDER"), "mongodb")
            self.assertEqual(get_app_mongo_uri(), "mongodb+srv://app-nested")
            self.assertEqual(get_app_mongo_database(), "app_nested_db")
            self.assertEqual(get_backup_mongo_uri(), "mongodb+srv://backup-nested")
            self.assertEqual(get_backup_mongo_database(), "backup_nested_db")
            self.assertEqual(get_config_value("VECTOR_PROVIDER"), "mongodb_vector")
            self.assertEqual(
                get_config_value("OPENROUTER_API_KEY"),
                "openrouter-secret"
            )

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
