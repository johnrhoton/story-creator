import os


ALLOWED_DB_PROVIDERS = {"sqlite", "mongodb"}
ALLOWED_VECTOR_PROVIDERS = {"none", "chroma", "mongodb_vector"}

DEFAULT_SQLITE_DB_PATH = "data/sqlite/story_builder.db"

DATABASE_ENCRYPTION_KDF_ITERATIONS = 100000

EXPORT_FILENAME_PREFIX = "story_builder_export"

MONGODB_DEFAULT_DATABASE = "story_builder"
MONGODB_SYNC_COLLECTION = "database_backups"
MONGODB_SYNC_DOCUMENT_ID = "story_builder_main"
MONGODB_LEGACY_SYNC_DOCUMENT_ID = "story_creator_main"

GENDER_OPTIONS = ["female", "male"]

CONFIG_ALIASES = {
    "AUTH_DEBUG": [
        ("auth", "debug"),
    ],
    "APP_MONGO_DATABASE": [
        ("database", "database"),
    ],
    "APP_MONGO_URI": [
        ("database", "uri"),
    ],
    "BACKUP_MONGO_DATABASE": [
        ("database", "backup", "database"),
    ],
    "BACKUP_MONGO_URI": [
        ("database", "backup", "uri"),
    ],
    "DB_PROVIDER": [
        ("database", "provider"),
    ],
    "DEFAULT_LLM_MODEL": [
        ("llm", "default_model"),
    ],
    "DEFAULT_LLM_PROVIDER": [
        ("llm", "default_provider"),
    ],
    "ENABLE_LLM_CONTENT_LOGGING": [
        ("llm", "enable_content_logging"),
    ],
    "GEMINI_API_BASE_URL": [
        ("llm", "gemini", "api_base_url"),
    ],
    "GEMINI_API_KEY": [
        ("llm", "gemini", "api_key"),
    ],
    "GROQ_API_KEY": [
        ("llm", "groq", "api_key"),
    ],
    "HF_TOKEN": [
        ("huggingface", "token"),
    ],
    "OPENROUTER_API_KEY": [
        ("llm", "openrouter", "api_key"),
    ],
    "STORY_DB_PATH": [
        ("database", "path"),
    ],
    "VECTOR_COLLECTION_NAME": [
        ("rag", "collection_name"),
    ],
    "VECTOR_INDEX_NAME": [
        ("rag", "index_name"),
    ],
    "VECTOR_PROVIDER": [
        ("rag", "provider"),
    ],
}


def get_config_value(name, default=None):
    value = os.getenv(name)

    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        for path in CONFIG_ALIASES.get(name, []):
            value = get_nested_secret(st.secrets, path)
            if value not in (None, ""):
                return value

        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        pass

    return default


def get_nested_secret(secrets, path):
    value = secrets

    for key in path:
        if not hasattr(value, "get"):
            return None

        value = value.get(key)

        if value is None:
            return None

    return value


def get_config_bool(name, default=False):
    value = get_config_value(name)

    if value in (None, ""):
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_sqlite_db_path():
    return get_config_value("STORY_DB_PATH", DEFAULT_SQLITE_DB_PATH)


# Backwards-compatible alias for older scripts and tests. New database access
# should use get_sqlite_db_path() through database.connection.
DB_NAME = get_sqlite_db_path()


DEFAULT_LLM_PROVIDER = get_config_value("DEFAULT_LLM_PROVIDER", "Groq")
DEFAULT_LLM_MODEL = get_config_value(
    "DEFAULT_LLM_MODEL",
    "llama-3.3-70b-versatile"
)


def get_first_config_value(names, default=None):
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value

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
