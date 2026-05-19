# AGENTS.md

## Project Purpose

Story Builder is a hobby and learning project for building a Streamlit-based
fiction/story creation app.

The project has two goals:

1. Provide a usable app for creating characters, reusable profiles, story
   templates, generated stories, story memory, language aids, import/export,
   and optional cloud backup sync.
2. Serve as a learning platform for LLM-assisted development, LLM integration,
   storage design, MongoDB, local infrastructure, and eventual Kubernetes or
   Raspberry Pi deployment experiments.

Prefer changes that support learning, clarity, and architectural evolution over
highly optimized production complexity.

## How To Run

Main entry point:

```bash
streamlit run app.py
```

Preferred local commands:

```bash
./venv/bin/python scripts/migrate.py
./venv/bin/python scripts/seed_llm_models.py
./venv/bin/python -m unittest discover -s tests
```

Streamlit is configured for headless local use, so open the printed local URL
manually if needed.

## Architecture

The app is a Streamlit desktop-style application with clear layers:

- `app.py`: Streamlit entry point, startup migrations, database initialization,
  authentication gate, and tab routing.
- `views/`: Streamlit UI screens and shared UI helpers.
- `services/`: workflow logic, business rules, LLM orchestration, auth/admin,
  sync, Story Memory, and Language Aids.
- `database/`: persistence provider boundary, SQLite implementation, MongoDB
  implementation, migrations, import/export, encryption, history, and model
  records.
- `prompts.py` and `prompts/`: prompt template loading/rendering and editable
  prompt text.
- `llm_client.py`, `llm_providers.py`, `llm_logging.py`, `llm_throttle.py`:
  LLM dispatch, provider implementations, logging, and rate limiting.
- `scripts/`: manual maintenance utilities.
- `tests/`: regression tests.

Keep UI concerns in `views/`, application decisions in `services/`, and storage
details in `database/`. Prefer existing service and repository patterns over
adding new architectural styles.

## Configuration And Secrets

Local secrets live in `.streamlit/secrets.toml`, matching Streamlit Community
Cloud's Secrets UI. Do not depend on `.env` for new work.

Preferred Streamlit secret shape:

```toml
[database]
provider="sqlite"
uri=""
database="story_builder"

[database.backup]
uri=""
database="story_builder"

[rag]
provider="chroma"

[llm]
default_provider="Groq"
default_model="llama-3.3-70b-versatile"
enable_content_logging=false

[llm.gemini]
api_key=""

[llm.groq]
api_key=""

[llm.openrouter]
api_key=""

[auth.google]
client_id=""
client_secret=""
server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
```

Important config behavior:

- Use `config.get_config_value()` for settings that may come from environment
  variables or Streamlit secrets.
- Environment variables still take precedence, and legacy flat Streamlit keys
  are accepted as fallbacks, but nested Streamlit secrets are the preferred
  parity path for local and cloud usage.
- `llm.default_provider` and `llm.default_model` are read from the shared
  config helper and saved locally by `services/llm_defaults_service.py`.
- Full prompt/response storage in LLM history is disabled by default. Use
  `llm.enable_content_logging=true` only for intentional local debugging.
- OAuth troubleshooting can be enabled temporarily with `auth.debug=true`; it
  must not print client secrets or cookie secrets.
- `.streamlit/secrets.toml`, `.env`, database files, WAL/SHM files, exports,
  logs, and virtualenv folders are local-only and should not be committed.

## Database And Storage

SQLite is the default local provider. MongoDB Atlas is optional.

- Set `database.provider="sqlite"` or `database.provider="mongodb"`.
- For live MongoDB app persistence, use `database.uri` and
  `database.database`.
- For backup snapshot sync, use `database.backup.uri` and
  `database.backup.database`.
- Legacy fallback names are still accepted: `MONGO_URI`, `MONGO_DATABASE`,
  `MONGODB_URI`, and `MONGODB_DATABASE`.

The database layer should preserve the same logical function surface for SQLite
and MongoDB providers. SQLite migrations run automatically on app startup.
MongoDB startup creates indexes and seed records where needed.

Story Memory uses a configurable vector provider:

- `rag.provider="none"` disables vector memory.
- `rag.provider="chroma"` uses local Chroma under `data/chroma_db`.
- `rag.provider="mongodb_vector"` uses MongoDB Atlas Vector Search.

SQLite or MongoDB remains the source of truth. Vector indexes are rebuildable
from the Story Memory tab.

## LLM Integration

Supported providers are Gemini, Groq, and OpenRouter. API keys should be read
through `config.get_config_value()` rather than direct `os.getenv()` or dotenv.

Prompt text lives in `prompts/`. Some prompt files contain named sections such
as `[section]`, `[characters]`, or `[item]`; preserve those conventions when
editing prompt templates.

LLM calls and failures are logged for debugging and usage review. When adding
new LLM workflows, make sure errors are visible and useful in the app.

## User-Facing Features

Core tabs include:

- Characters
- Profiles
- Templates
- Stories
- Story Memory
- Language Aids
- Models
- History
- Export / Import
- Administration, only for administrators

Authentication uses Google OIDC plus an authorized-user whitelist. The
Administration tab manages authorized users and roles.

## Development Preferences

- Favor clear, incremental changes over clever abstractions.
- Keep edits scoped to the requested behavior.
- Preserve existing data and migration paths.
- Add or update focused tests when changing config, persistence, imports,
  prompts, LLM behavior, or user-visible workflows.
- Use existing helpers and service boundaries before introducing new ones.
- Avoid committing generated/local state such as `story_builder.db`,
  `story_builder.db-shm`, `story_builder.db-wal`, `.streamlit/secrets.toml`,
  `.env`, exports, backups, and logs.

## Testing Notes

Run the full suite before broad changes:

```bash
./venv/bin/python -m unittest discover -s tests
```

For focused changes, run the matching test modules first. Useful examples:

```bash
./venv/bin/python -m unittest tests.test_llm_helpers
./venv/bin/python -m unittest tests.test_llm_defaults_service
./venv/bin/python -m unittest tests.test_database_provider
./venv/bin/python -m unittest tests.test_vector_store
```

Some Story Memory/vector tests may attempt model cache lookups and can emit
network/DNS retry warnings in restricted environments. Treat test pass/fail as
the source of truth, but mention network-related noise when reporting results.

## Documentation Pointers

- `README.md`: quick project overview, run commands, and secrets summary.
- `docs/architecture.md`: layer-by-layer architecture details.
- `docs/database.md`: SQLite/MongoDB provider and schema notes.
- `docs/deployment_guide.md`: local, Streamlit Cloud, and future deployment
  notes.
- `docs/story_memory.md`: Story Memory flow.
- `docs/language_aids.md`: glossary and reading comprehension flow.
- `docs/services.md`: service module responsibilities.
- `docs/tests.md`: test coverage notes.
- `docs/user_guide.md`: user-facing workflows.
