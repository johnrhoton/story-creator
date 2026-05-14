import os
import unittest
from unittest.mock import patch

from llm_logging import extract_error_codes, extract_error_details
from llm_providers import (
    generate_with_openrouter,
    generate_with_provider,
    get_api_key,
)


class LlmHelperTests(unittest.TestCase):
    def test_extract_error_codes_and_details_include_response_text(self):
        class Response:
            status_code = 429
            text = "quota response body"

        class ProviderError(Exception):
            status_code = 429
            response = Response()

        error = ProviderError("429 RESOURCE_EXHAUSTED")

        error_codes = extract_error_codes(error)
        error_details = extract_error_details(error)

        self.assertIn("status_code: 429", error_codes)
        self.assertIn("response.status_code: 429", error_codes)
        self.assertIn("RESOURCE_EXHAUSTED", error_codes)
        self.assertIn("quota response body", error_details)
        self.assertIn("429 RESOURCE_EXHAUSTED", error_details)

    def test_get_api_key_raises_clear_error_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "TEST_API_KEY not found"
            ):
                get_api_key("TEST_API_KEY")

    def test_generate_with_provider_rejects_unknown_provider(self):
        with self.assertRaisesRegex(ValueError, "Unsupported LLM provider"):
            generate_with_provider(
                "Unknown",
                "model",
                "prompt"
            )

    def test_generate_with_openrouter_uses_expected_request_shape(self):
        class FakeResponse:
            status_code = 200
            text = "{\"ok\": true}"

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "mocked response"
                            }
                        }
                    ]
                }

        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeResponse()

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch("llm_providers.requests.post", fake_post):
                response = generate_with_openrouter(
                    "openrouter/auto",
                    "hello"
                )

        self.assertEqual(response, "mocked response")
        self.assertEqual(
            calls[0][0][0],
            "https://openrouter.ai/api/v1/chat/completions"
        )
        self.assertEqual(
            calls[0][1]["headers"]["Authorization"],
            "Bearer test-key"
        )
        self.assertEqual(
            calls[0][1]["json"]["model"],
            "openrouter/auto"
        )
        self.assertEqual(
            calls[0][1]["json"]["messages"][0]["content"],
            "hello"
        )


if __name__ == "__main__":
    unittest.main()
