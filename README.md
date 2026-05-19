# Story Builder

Story Builder is a Streamlit-based fiction creation app. It supports reusable
profiles, generated characters, story templates, generated stories, LLM call
history, JSON import/export, and optional MongoDB backup sync.

This is a hobby and learning project, so the code favors clear layers and
incremental evolution over production framework complexity.

## Run The App

```bash
streamlit run app.py
```

Streamlit is configured to run headless for this project, so open the printed
local URL manually if your terminal does not open a browser.

## Project Shape

- `app.py`: Streamlit entry point and tab wiring
- `views/`: Streamlit UI screens and shared UI helpers
- `services/`: application workflow logic
- `database/`: SQLite schema, migrations, import/export, and persistence
- `prompts.py`: prompt builders for characters and stories
- `llm_client.py`, `llm_providers.py`, `llm_logging.py`, `llm_throttle.py`: LLM integration
- `scripts/`: manual command-line utilities
- `tests/`: regression tests

## Database

The local SQLite database is:

```text
story_builder.db
```

The app runs migrations at startup. You can also run them manually:

```bash
./venv/bin/python scripts/migrate.py
```

## LLM Models

The app supports Gemini, Groq, and OpenRouter. Starter model records can be
seeded with:

```bash
./venv/bin/python scripts/seed_llm_models.py
```

The Models tab lets you add, remove, export, import, and choose default models
for each provider.

## Streamlit Secrets

Local configuration lives in `.streamlit/secrets.toml`, matching the nested
tables used in Streamlit Community Cloud secrets:

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

[auth]
redirect_uri="http://localhost:8501/oauth2callback"
cookie_secret="..."

[auth.google]
client_id="..."
client_secret="..."
server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
```

Mongo database names are optional. If omitted, the app uses `story_builder`.
Existing legacy MongoDB backups using the `story_creator_main` document ID are
still checked as a fallback.
Google OAuth stays under `[auth.google]` because that is the section Streamlit's
built-in login reads.
Full prompt/response storage in LLM call history is disabled by default; set
`llm.enable_content_logging=true` only when you intentionally want that local
debug detail.

## Import, Export, And Sync

The Export / Import tab can download or import JSON snapshots. Exports use the
`story_builder_export_YYYYMMDD_HHMMSS.json` filename pattern.

MongoDB sync compares local SQLite content with one MongoDB backup document and
warns before overwriting diverged changes.

## Tests

Run the regression suite with:

```bash
./venv/bin/python -m unittest discover -s tests
```

## Manual Scripts

See [scripts/README.md](scripts/README.md) for command-line maintenance tools.
