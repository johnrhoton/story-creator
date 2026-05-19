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
    def test_save_llm_defaults_writes_streamlit_secrets_and_process_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secrets_path = Path(temp_dir) / ".streamlit" / "secrets.toml"

            with patch.dict(os.environ, {}, clear=True):
                saved = save_llm_defaults(
                    "Gemini",
                    "gemini-2.5-flash",
                    secrets_path
                )

                self.assertTrue(saved)
                self.assertEqual(os.environ[DEFAULT_LLM_PROVIDER_ENV], "Gemini")
                self.assertEqual(
                    os.environ[DEFAULT_LLM_MODEL_ENV],
                    "gemini-2.5-flash"
                )
                self.assertEqual(
                    get_saved_llm_defaults(secrets_path),
                    ("Gemini", "gemini-2.5-flash")
                )

    def test_save_llm_defaults_preserves_existing_streamlit_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secrets_path = Path(temp_dir) / ".streamlit" / "secrets.toml"
            secrets_path.parent.mkdir(parents=True)
            secrets_path.write_text(
                'GROQ_API_KEY="secret"\n\n[auth]\n'
                'redirect_uri="http://localhost:8501/oauth2callback"\n',
                encoding="utf-8"
            )

            with patch.dict(os.environ, {}, clear=True):
                save_llm_defaults(
                    "Groq",
                    "llama-3.3-70b-versatile",
                    secrets_path
                )

            contents = secrets_path.read_text(encoding="utf-8")

            self.assertIn('GROQ_API_KEY="secret"', contents)
            self.assertIn('DEFAULT_LLM_PROVIDER="Groq"', contents)
            self.assertIn(
                'DEFAULT_LLM_MODEL="llama-3.3-70b-versatile"',
                contents
            )
            self.assertIn("[auth]", contents)

    def test_save_llm_defaults_rejects_blank_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            secrets_path = Path(temp_dir) / ".streamlit" / "secrets.toml"

            self.assertFalse(save_llm_defaults("Groq", "", secrets_path))
            self.assertFalse(secrets_path.exists())


if __name__ == "__main__":
    unittest.main()
