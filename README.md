# Story Builder

Story Builder is a Streamlit-based fiction creation app. It supports reusable
profiles, generated characters, story templates, generated stories, LLM call
history, Story Memory retrieval, language-learning aids, JSON/YAML
import/export, lightweight observability, and optional MongoDB backup sync.

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
- `database/`: SQLite/MongoDB persistence, migrations, import/export, history, and app events
- `prompts.py`: prompt builders for characters, stories, story memory, and language aids
- `llm_client.py`, `llm_providers.py`, `llm_logging.py`, `llm_throttle.py`: LLM integration
- `scripts/`: manual command-line utilities
- `tests/`: regression tests

## Database

The local SQLite database is:

```text
data/sqlite/story_builder.db
```

Set `STORY_DB_PATH` to use a different local SQLite file.

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

Local configuration can come from environment variables, a local `.env` file,
or `.streamlit/secrets.toml`. Environment variables and `.env` values take
precedence, which is the preferred container/Kubernetes path.
`.streamlit/secrets.toml` remains useful for local Streamlit and Streamlit
Community Cloud:

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

Equivalent container environment variables include:

```text
AUTH_COOKIE_SECRET
AUTH_REDIRECT_URI
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_SERVER_METADATA_URL
GROQ_API_KEY
GEMINI_API_KEY
OPENROUTER_API_KEY
STORY_DB_PATH
CHROMA_DB_PATH
```

The app loads a local `.env` file on startup if one exists. The
Docker/Kubernetes startup path can also load these from `/app/.env` at runtime
and writes a runtime-only `.streamlit/secrets.toml` so Streamlit's built-in
Google login can work without baking secrets into the image.

Mongo database names are optional. If omitted, the app uses `story_builder`.
Existing legacy MongoDB backups using the `story_creator_main` document ID are
still checked as a fallback.
Google OAuth stays under `[auth.google]` because that is the section Streamlit's
built-in login reads.
Full prompt/response storage in LLM call history is disabled by default; set
`llm.enable_content_logging=true` only when you intentionally want that local
debug detail.

## Docker And K3s

The included Dockerfile is intended for CPU-only mini PCs and K3s homelab use.
It installs normal app requirements and then pins CPU-only PyTorch through
`requirements-torch-cpu.txt`. It should not include `nvidia-*` CUDA runtime
wheels.

The Kubernetes manifests in `k8s/` deploy a single replica in the
`story-builder` namespace, mount a Longhorn PVC at `/app/data`, and expose the
app with a ClusterIP Service plus an Ingress for `story-builder.local`.

For local Docker testing, pass secrets at runtime:

```bash
docker run --rm --env-file .env -p 8501:8501 -v story-builder-data:/app/data ghcr.io/johnrhoton/story-builder:0.1
```

Use `k8s/secrets.example.yaml` as a placeholder template only. Real secrets
belong in a Kubernetes Secret named `story-builder-secrets`; the image itself
does not contain `.env` or `.streamlit/secrets.toml`.

## Import, Export, And Sync

The Export / Import tab can download or import JSON/YAML snapshots. Exports use
the `story_builder_export_YYYYMMDD_HHMMSS` filename pattern.

MongoDB sync compares local SQLite content with one MongoDB backup document and
warns before overwriting diverged changes.

## Tests

Run the regression suite with:

```bash
./venv/bin/python -m unittest discover -s tests
```

## Manual Scripts

See [scripts/README.md](scripts/README.md) for command-line maintenance tools.
