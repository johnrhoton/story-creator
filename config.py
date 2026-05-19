import os


ALLOWED_DB_PROVIDERS = {"sqlite", "mongodb"}
ALLOWED_VECTOR_PROVIDERS = {"none", "chroma", "mongodb_vector"}

DB_NAME = "story_builder.db"

DATABASE_ENCRYPTION_KDF_ITERATIONS = 100000

EXPORT_FILENAME_PREFIX = "story_builder_export"

MONGODB_DEFAULT_DATABASE = "story_builder"
MONGODB_SYNC_COLLECTION = "database_backups"
MONGODB_SYNC_DOCUMENT_ID = "story_builder_main"
MONGODB_LEGACY_SYNC_DOCUMENT_ID = "story_creator_main"

GENDER_OPTIONS = ["female", "male"]


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


DEFAULT_LLM_PROVIDER = get_config_value("DEFAULT_LLM_PROVIDER", "Groq")
DEFAULT_LLM_MODEL = get_config_value(
    "DEFAULT_LLM_MODEL",
    "llama-3.3-70b-versatile"
)


def get_first_config_value(names, default=None):
    for name in names:
        value = get_config_value(name)
        if value not in (None, ""):
            return value

    return default


def get_app_mongo_uri():
    return get_first_config_value([
        "APP_MONGO_URI",
        "MONGO_URI",
        "MONGODB_URI",
    ])


def get_app_mongo_database():
    return get_first_config_value([
        "APP_MONGO_DATABASE",
        "MONGO_DATABASE",
        "MONGODB_DATABASE",
    ], MONGODB_DEFAULT_DATABASE)


def get_backup_mongo_uri():
    return get_first_config_value([
        "BACKUP_MONGO_URI",
        "MONGO_URI",
        "MONGODB_URI",
    ])


def get_backup_mongo_database():
    return get_first_config_value([
        "BACKUP_MONGO_DATABASE",
        "MONGO_DATABASE",
        "MONGODB_DATABASE",
    ], MONGODB_DEFAULT_DATABASE)


def get_db_provider():
    provider = str(get_config_value("DB_PROVIDER", "sqlite")).strip().lower()

    if provider not in ALLOWED_DB_PROVIDERS:
        raise ValueError(
            "DB_PROVIDER must be one of: "
            f"{', '.join(sorted(ALLOWED_DB_PROVIDERS))}"
        )

    return provider


DB_PROVIDER = get_db_provider()


def get_vector_provider():
    provider = str(
        get_config_value("VECTOR_PROVIDER", "chroma")
    ).strip().lower()

    if provider not in ALLOWED_VECTOR_PROVIDERS:
        raise ValueError(
            "VECTOR_PROVIDER must be one of: "
            f"{', '.join(sorted(ALLOWED_VECTOR_PROVIDERS))}"
        )

    return provider


VECTOR_PROVIDER = get_vector_provider()

VECTOR_COLLECTION_NAME = get_config_value(
    "VECTOR_COLLECTION_NAME",
    "story_memory"
)
VECTOR_INDEX_NAME = get_config_value(
    "VECTOR_INDEX_NAME",
    "story_memory_vector_index"
)
