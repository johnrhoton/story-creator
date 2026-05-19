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
        or _get_toml_value(
            secrets_path,
            ("llm", "default_provider")
        )
        or _get_toml_value(secrets_path, (DEFAULT_LLM_PROVIDER_ENV,))
        or get_config_value(DEFAULT_LLM_PROVIDER_ENV)
        or ""
    )
    model = (
        os.getenv(DEFAULT_LLM_MODEL_ENV)
        or _get_toml_value(
            secrets_path,
            ("llm", "default_model")
        )
        or _get_toml_value(secrets_path, (DEFAULT_LLM_MODEL_ENV,))
        or get_config_value(DEFAULT_LLM_MODEL_ENV)
        or ""
    )

    return provider, model


def save_llm_defaults(provider, model, secrets_path=SECRETS_PATH):
    provider = (provider or "").strip()
    model = (model or "").strip()

    if not provider or not model:
        return False

    _set_section_toml_values(
        secrets_path,
        "llm",
        {
            "default_provider": provider,
            "default_model": model,
        }
    )

    os.environ[DEFAULT_LLM_PROVIDER_ENV] = provider
    os.environ[DEFAULT_LLM_MODEL_ENV] = model

    return True


def _get_toml_value(path, key_path):
    if not path.exists():
        return None

    section = None
    key = key_path[0]
    if len(key_path) > 1:
        section = ".".join(key_path[:-1])
        key = key_path[-1]

    pattern = re.compile(rf"^{re.escape(key)}\s*=\s*(['\"])(.*?)\1\s*$")
    active_section = None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            active_section = stripped.strip("[]")
            continue

        if active_section != section:
            continue

        match = pattern.match(stripped)
        if match:
            return match.group(2)

    return None


def _set_section_toml_values(path, section, values):
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    section_header = f"[{section}]"
    section_start = next(
        (index for index, line in enumerate(lines) if line.strip() == section_header),
        None
    )

    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(section_header)
        section_start = len(lines) - 1

    section_end = next(
        (
            index
            for index in range(section_start + 1, len(lines))
            if lines[index].strip().startswith("[")
        ),
        len(lines)
    )

    section_lines = lines[section_start + 1:section_end]
    updated_keys = set()

    for index, line in enumerate(section_lines):
        stripped = line.strip()

        for key, value in values.items():
            if re.match(rf"^{re.escape(key)}\s*=", stripped):
                section_lines[index] = f'{key}="{_escape_toml_string(value)}"'
                updated_keys.add(key)

    additions = [
        f'{key}="{_escape_toml_string(value)}"'
        for key, value in values.items()
        if key not in updated_keys
    ]

    if additions:
        if section_lines and section_lines[-1].strip():
            section_lines.append("")
        section_lines.extend(additions)

    new_lines = (
        lines[:section_start + 1]
        + section_lines
        + lines[section_end:]
    )

    path.write_text(
        "\n".join(new_lines).rstrip() + "\n",
        encoding="utf-8"
    )


def _escape_toml_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')
