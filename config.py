import os


ALLOWED_DB_PROVIDERS = {"sqlite", "mongodb"}

DB_NAME = "story_builder.db"

DATABASE_ENCRYPTION_KDF_ITERATIONS = 100000

EXPORT_FILENAME_PREFIX = "story_builder_export"

MONGODB_DEFAULT_DATABASE = "story_builder"
MONGODB_SYNC_COLLECTION = "database_backups"
MONGODB_SYNC_DOCUMENT_ID = "story_builder_main"
MONGODB_LEGACY_SYNC_DOCUMENT_ID = "story_creator_main"

GENDER_OPTIONS = ["female", "male"]

DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "Groq")
DEFAULT_LLM_MODEL = os.getenv(
    "DEFAULT_LLM_MODEL",
    "llama-3.3-70b-versatile"
)


def get_config_value(name, default=None):
    value = os.getenv(name)

    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        pass

    return default


def get_db_provider():
    provider = str(get_config_value("DB_PROVIDER", "sqlite")).strip().lower()

    if provider not in ALLOWED_DB_PROVIDERS:
        raise ValueError(
            "DB_PROVIDER must be one of: "
            f"{', '.join(sorted(ALLOWED_DB_PROVIDERS))}"
        )

    return provider


DB_PROVIDER = get_db_provider()
