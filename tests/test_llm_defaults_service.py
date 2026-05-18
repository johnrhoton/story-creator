import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.llm_defaults_service import (
    DEFAULT_LLM_MODEL_ENV,
    DEFAULT_LLM_PROVIDER_ENV,
    get_saved_llm_defaults,
    save_llm_defaults,
)


class LLMDefaultsServiceTests(unittest.TestCase):
    def test_save_llm_defaults_writes_dotenv_and_process_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"

            with patch.dict(os.environ, {}, clear=True):
                saved = save_llm_defaults(
                    "Gemini",
                    "gemini-2.5-flash",
                    env_path
                )

                self.assertTrue(saved)
                self.assertEqual(os.environ[DEFAULT_LLM_PROVIDER_ENV], "Gemini")
                self.assertEqual(
                    os.environ[DEFAULT_LLM_MODEL_ENV],
                    "gemini-2.5-flash"
                )
                self.assertEqual(
                    get_saved_llm_defaults(env_path),
                    ("Gemini", "gemini-2.5-flash")
                )

    def test_save_llm_defaults_preserves_existing_dotenv_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GROQ_API_KEY=secret\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                save_llm_defaults("Groq", "llama-3.3-70b-versatile", env_path)

            contents = env_path.read_text(encoding="utf-8")

            self.assertIn("GROQ_API_KEY=secret", contents)
            self.assertIn("DEFAULT_LLM_PROVIDER='Groq'", contents)
            self.assertIn(
                "DEFAULT_LLM_MODEL='llama-3.3-70b-versatile'",
                contents
            )

    def test_save_llm_defaults_rejects_blank_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"

            self.assertFalse(save_llm_defaults("Groq", "", env_path))
            self.assertFalse(env_path.exists())


if __name__ == "__main__":
    unittest.main()
