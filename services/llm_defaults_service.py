import os
import re
from pathlib import Path

from config import get_config_value


DEFAULT_LLM_PROVIDER_ENV = "DEFAULT_LLM_PROVIDER"
DEFAULT_LLM_MODEL_ENV = "DEFAULT_LLM_MODEL"
SECRETS_PATH = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def get_saved_llm_defaults(secrets_path=SECRETS_PATH):
    provider = (
        os.getenv(DEFAULT_LLM_PROVIDER_ENV)
        or _get_root_toml_value(secrets_path, DEFAULT_LLM_PROVIDER_ENV)
        or get_config_value(DEFAULT_LLM_PROVIDER_ENV)
        or ""
    )
    model = (
        os.getenv(DEFAULT_LLM_MODEL_ENV)
        or _get_root_toml_value(secrets_path, DEFAULT_LLM_MODEL_ENV)
        or get_config_value(DEFAULT_LLM_MODEL_ENV)
        or ""
    )

    return provider, model


def save_llm_defaults(provider, model, secrets_path=SECRETS_PATH):
    provider = (provider or "").strip()
    model = (model or "").strip()

    if not provider or not model:
        return False

    _set_root_toml_values(
        secrets_path,
        {
            DEFAULT_LLM_PROVIDER_ENV: provider,
            DEFAULT_LLM_MODEL_ENV: model,
        }
    )

    os.environ[DEFAULT_LLM_PROVIDER_ENV] = provider
    os.environ[DEFAULT_LLM_MODEL_ENV] = model

    return True


def _get_root_toml_value(path, key):
    if not path.exists():
        return None

    pattern = re.compile(rf"^{re.escape(key)}\s*=\s*(['\"])(.*?)\1\s*$")

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("["):
            return None

        match = pattern.match(line.strip())
        if match:
            return match.group(2)

    return None


def _set_root_toml_values(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    section_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith("[")
        ),
        len(lines)
    )

    root_lines = lines[:section_index]
    section_lines = lines[section_index:]
    updated_keys = set()

    for index, line in enumerate(root_lines):
        stripped = line.strip()

        for key, value in values.items():
            if re.match(rf"^{re.escape(key)}\s*=", stripped):
                root_lines[index] = f'{key}="{_escape_toml_string(value)}"'
                updated_keys.add(key)

    additions = [
        f'{key}="{_escape_toml_string(value)}"'
        for key, value in values.items()
        if key not in updated_keys
    ]

    if additions:
        if root_lines and root_lines[-1].strip():
            root_lines.append("")
        root_lines.extend(additions)

    if root_lines and section_lines and root_lines[-1].strip():
        root_lines.append("")

    path.write_text(
        "\n".join(root_lines + section_lines).rstrip() + "\n",
        encoding="utf-8"
    )


def _escape_toml_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')
