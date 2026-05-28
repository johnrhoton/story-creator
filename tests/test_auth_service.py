import unittest
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from streamlit.runtime.scriptrunner import StopException

from services.auth_service import (
    auth_config_is_complete,
    build_auth_debug_summary,
    build_auth_config,
    ensure_streamlit_auth_secrets_from_env,
    get_auth_debug_enabled,
    get_login_provider,
    require_login,
)
from config import load_dotenv_file as load_config_dotenv_file
from scripts.start_container import load_dotenv_file


class AuthServiceTests(unittest.TestCase):
    def test_get_login_provider_uses_named_google_provider_when_configured(self):
        self.assertEqual(
            get_login_provider({
                "redirect_uri": "http://localhost:8501/oauth2callback",
                "cookie_secret": "secret",
                "google": {
                    "client_id": "client",
                    "client_secret": "secret",
                    "server_metadata_url": "metadata",
                },
            }),
            "google"
        )

    def test_get_login_provider_uses_default_provider_without_named_google(self):
        self.assertIsNone(
            get_login_provider({
                "redirect_uri": "http://localhost:8501/oauth2callback",
                "cookie_secret": "secret",
                "client_id": "client",
                "client_secret": "secret",
                "server_metadata_url": "metadata",
            })
        )

    def test_require_login_uses_named_google_provider_when_configured(self):
        class User:
            is_logged_in = False

        class FakeStreamlit:
            user = User()
            session_state = {}
            login_calls = []

            @staticmethod
            def title(_text):
                return None

            @staticmethod
            def info(_text):
                return None

            @staticmethod
            def button(_label):
                return True

            @classmethod
            def login(cls, provider=None):
                cls.login_calls.append(provider)

            @staticmethod
            def stop():
                raise StopException()

        with patch("services.auth_service.st", FakeStreamlit), patch.dict(
            "os.environ",
            {
                "AUTH_COOKIE_SECRET": "cookie",
                "AUTH_REDIRECT_URI": "https://example.test/oauth2callback",
                "GOOGLE_CLIENT_ID": "client",
                "GOOGLE_CLIENT_SECRET": "secret",
                "GOOGLE_SERVER_METADATA_URL": "metadata",
            },
            clear=True,
        ), tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            os.chdir(temp_dir)
            with self.assertRaises(StopException):
                try:
                    require_login()
                finally:
                    os.chdir(original_cwd)

        self.assertEqual(FakeStreamlit.login_calls, ["google"])

    def test_auth_debug_summary_redacts_sensitive_values(self):
        class User:
            is_logged_in = False

        summary = build_auth_debug_summary(
            {
                "debug": True,
                "redirect_uri": "https://example.streamlit.app/~/+/oauth2callback",
                "cookie_secret": "cookie-secret",
                "google": {
                    "client_id": "client-id",
                    "client_secret": "client-secret",
                    "server_metadata_url": "metadata-url",
                },
            },
            User(),
        )

        self.assertTrue(summary["auth_debug_enabled"])
        self.assertTrue(summary["cookie_secret_configured"])
        self.assertTrue(summary["google_provider_configured"])
        self.assertEqual(summary["login_provider"], "google")
        self.assertNotIn("client-secret", str(summary))
        self.assertNotIn("cookie-secret", str(summary))

    def test_auth_debug_can_be_enabled_from_auth_config(self):
        self.assertTrue(get_auth_debug_enabled({"debug": "true"}))
        self.assertFalse(get_auth_debug_enabled({"debug": "false"}))

    def test_build_auth_config_prefers_environment_variables(self):
        with patch.dict(
            "os.environ",
            {
                "AUTH_COOKIE_SECRET": "env-cookie",
                "AUTH_REDIRECT_URI": "https://example.test/oauth2callback",
                "GOOGLE_CLIENT_ID": "env-client",
                "GOOGLE_CLIENT_SECRET": "env-secret",
                "GOOGLE_SERVER_METADATA_URL": "env-metadata",
            },
            clear=True,
        ):
            auth_config = build_auth_config()

        self.assertTrue(auth_config_is_complete(auth_config))
        self.assertEqual(auth_config["cookie_secret"], "env-cookie")
        self.assertEqual(auth_config["redirect_uri"], "https://example.test/oauth2callback")
        self.assertEqual(auth_config["google"]["client_id"], "env-client")
        self.assertEqual(auth_config["google"]["client_secret"], "env-secret")
        self.assertEqual(auth_config["google"]["server_metadata_url"], "env-metadata")

    def test_build_auth_config_can_load_local_dotenv_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "\n".join([
                    "AUTH_COOKIE_SECRET=dotenv-cookie",
                    "AUTH_REDIRECT_URI=http://localhost:8501/oauth2callback",
                    "GOOGLE_CLIENT_ID=dotenv-client",
                    "GOOGLE_CLIENT_SECRET=dotenv-secret",
                    "GOOGLE_SERVER_METADATA_URL=dotenv-metadata",
                ]),
                encoding="utf-8",
            )

            load_config_dotenv_file(dotenv_path)
            auth_config = build_auth_config()

        self.assertTrue(auth_config_is_complete(auth_config))
        self.assertEqual(auth_config["cookie_secret"], "dotenv-cookie")
        self.assertEqual(auth_config["google"]["client_id"], "dotenv-client")

    def test_require_login_handles_missing_auth_config_without_secrets_file(self):
        class User:
            is_logged_in = False

        class FakeStreamlit:
            user = User()
            session_state = {}
            warnings = []

            @staticmethod
            def title(_text):
                return None

            @staticmethod
            def info(_text):
                return None

            @classmethod
            def warning(cls, text):
                cls.warnings.append(text)

            @staticmethod
            def button(_label):
                return False

            @staticmethod
            def stop():
                raise StopException()

        with patch("services.auth_service.st", FakeStreamlit), patch.dict(
            "os.environ",
            {},
            clear=True,
        ), patch(
            "services.auth_service.get_config",
            side_effect=lambda _name, default=None: default,
        ):
            with self.assertRaises(StopException):
                require_login()

        self.assertTrue(FakeStreamlit.warnings)

    def test_env_auth_config_creates_runtime_streamlit_secrets(self):
        auth_config = {
            "redirect_uri": "https://example.test/oauth2callback",
            "cookie_secret": "cookie",
            "google": {
                "client_id": "client",
                "client_secret": "secret",
                "server_metadata_url": "metadata",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ",
            {
                "AUTH_COOKIE_SECRET": "cookie",
                "AUTH_REDIRECT_URI": "https://example.test/oauth2callback",
                "GOOGLE_CLIENT_ID": "client",
                "GOOGLE_CLIENT_SECRET": "secret",
            },
            clear=True,
        ):
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                secrets_path = ensure_streamlit_auth_secrets_from_env(auth_config)
                contents = Path(".streamlit", "secrets.toml").read_text()
            finally:
                os.chdir(original_cwd)

        self.assertIsNotNone(secrets_path)
        self.assertIn("[auth]", contents)
        self.assertIn("[auth.google]", contents)
        self.assertIn('client_id="client"', contents)

    def test_container_startup_loads_dotenv_without_overriding_env(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ",
            {"GOOGLE_CLIENT_ID": "from-env"},
            clear=True,
        ):
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                "\n".join([
                    "AUTH_COOKIE_SECRET=from-dotenv",
                    "AUTH_REDIRECT_URI=http://story-builder.local/oauth2callback",
                    "GOOGLE_CLIENT_ID=from-dotenv",
                    'GOOGLE_CLIENT_SECRET="quoted-secret"',
                ]),
                encoding="utf-8",
            )

            load_dotenv_file(dotenv_path)

            self.assertEqual(os.environ["AUTH_COOKIE_SECRET"], "from-dotenv")
            self.assertEqual(os.environ["GOOGLE_CLIENT_ID"], "from-env")
            self.assertEqual(os.environ["GOOGLE_CLIENT_SECRET"], "quoted-secret")


if __name__ == "__main__":
    unittest.main()
