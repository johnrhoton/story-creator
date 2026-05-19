import unittest
from unittest.mock import patch

from streamlit.runtime.scriptrunner import StopException

from services.auth_service import get_login_provider, require_login


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
            secrets = {
                "auth": {
                    "google": {
                        "client_id": "client",
                        "client_secret": "secret",
                        "server_metadata_url": "metadata",
                    }
                }
            }
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

        with patch("services.auth_service.st", FakeStreamlit):
            with self.assertRaises(StopException):
                require_login()

        self.assertEqual(FakeStreamlit.login_calls, ["google"])


if __name__ == "__main__":
    unittest.main()
