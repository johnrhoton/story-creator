import unittest

from services.auth_service import get_login_provider


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


if __name__ == "__main__":
    unittest.main()
