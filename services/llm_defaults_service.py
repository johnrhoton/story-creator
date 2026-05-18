import os
from pathlib import Path

from dotenv import dotenv_values, set_key


DEFAULT_LLM_PROVIDER_ENV = "DEFAULT_LLM_PROVIDER"
DEFAULT_LLM_MODEL_ENV = "DEFAULT_LLM_MODEL"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def get_saved_llm_defaults(env_path=ENV_PATH):
    values = {}

    if env_path.exists():
        values = dotenv_values(env_path)

    provider = (
        os.getenv(DEFAULT_LLM_PROVIDER_ENV)
        or values.get(DEFAULT_LLM_PROVIDER_ENV)
        or ""
    )
    model = (
        os.getenv(DEFAULT_LLM_MODEL_ENV)
        or values.get(DEFAULT_LLM_MODEL_ENV)
        or ""
    )

    return provider, model


def save_llm_defaults(provider, model, env_path=ENV_PATH):
    provider = (provider or "").strip()
    model = (model or "").strip()

    if not provider or not model:
        return False

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.touch(exist_ok=True)

    set_key(str(env_path), DEFAULT_LLM_PROVIDER_ENV, provider)
    set_key(str(env_path), DEFAULT_LLM_MODEL_ENV, model)

    os.environ[DEFAULT_LLM_PROVIDER_ENV] = provider
    os.environ[DEFAULT_LLM_MODEL_ENV] = model

    return True
