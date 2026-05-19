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

Local configuration lives in `.streamlit/secrets.toml`, matching the root-level
keys used in Streamlit Community Cloud secrets:

```text
GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
APP_MONGO_URI=
APP_MONGO_DATABASE=story_builder
BACKUP_MONGO_URI=
BACKUP_MONGO_DATABASE=story_builder
```

Mongo database names are optional. If omitted, the app uses `story_builder`.
Existing legacy MongoDB backups using the `story_creator_main` document ID are
still checked as a fallback.

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
