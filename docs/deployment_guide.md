# Deployment Guide

## Local Development

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./venv/bin/python scripts/migrate.py
./venv/bin/python scripts/seed_llm_models.py
streamlit run app.py
```

On Windows, activate the virtual environment with
`venv\Scripts\activate`.

### Local Configuration

Local configuration can live in environment variables, a local `.env` file, or
`.streamlit/secrets.toml`. The same nested TOML shape works in Streamlit
Community Cloud's Secrets UI:

```toml
[database]
provider="sqlite"
path="data/sqlite/story_builder.db"
uri=""
database="story_builder"

[database.backup]
uri=""
database="story_builder"

[rag]
provider="chroma"
chroma_path="data/chroma_db"

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
cookie_secret="replace-with-a-long-random-string"
debug=false

[auth.google]
client_id="replace-with-google-client-id"
client_secret="replace-with-google-client-secret"
server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
```

Environment variables and `.env` values take precedence over Streamlit secrets.
This keeps local Docker-style testing close to the Kubernetes path while
preserving Streamlit Community Cloud compatibility.

## Container Deployment

The Dockerfile builds a Streamlit image for CPU-only hosts:

- Base image: `python:3.12-slim`
- App entry point: `app.py`
- Streamlit port: `8501`
- Runtime startup script: `scripts/start_container.py`
- SQLite path: `/app/data/sqlite/story_builder.db`
- Chroma path: `/app/data/chroma`

The startup script creates `/app/data/sqlite` and `/app/data/chroma`, loads
`/app/.env` if present, writes a runtime-only `.streamlit/secrets.toml` from
auth environment variables when possible, and then starts Streamlit with:

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
```

Build and push:

```bash
docker build -t ghcr.io/johnrhoton/story-builder:0.1 .
docker push ghcr.io/johnrhoton/story-builder:0.1
```

Run locally with secrets mounted at runtime:

```bash
docker run --rm \
  --env-file .env \
  -p 8501:8501 \
  -v story-builder-data:/app/data \
  ghcr.io/johnrhoton/story-builder:0.1
```

Do not expect a rebuilt image to contain `.env`; `.dockerignore` excludes it.
The app only sees those values when Docker or Kubernetes supplies them at
runtime.

### CPU-Only PyTorch

Container deployments use `requirements-torch-cpu.txt` to pin CPU-only
PyTorch:

```text
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.3.0+cpu
```

`sentence-transformers` pulls PyTorch transitively, so the Dockerfile constrains
the first requirements install to `torch==2.3.0+cpu`, then installs
`requirements-torch-cpu.txt`, removes any accidental `nvidia-*` packages, and
fails the build if `pip list` still contains `nvidia-*`.

Verify an image with:

```bash
docker run --rm ghcr.io/johnrhoton/story-builder:0.1 sh -c "pip list | grep nvidia"
docker run --rm ghcr.io/johnrhoton/story-builder:0.1 python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

The first command should return no output. The second should show a `+cpu`
torch build and `False` for CUDA availability.

## K3s Homelab Deployment

The Kubernetes manifests in `k8s/` target a first homelab deployment on
CPU-only mini PCs:

- Namespace: `story-builder`
- Deployment: `story-builder`
- Replicas: `1`
- Image: `ghcr.io/johnrhoton/story-builder:0.1`
- Storage: Longhorn PVC mounted at `/app/data`
- Service: ClusterIP on port `80` targeting container port `8501`
- Ingress host: `story-builder.local`
- Secret name: `story-builder-secrets`

Apply in this order after creating real secrets from the example:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

`k8s/secrets.example.yaml` is a placeholder template only. Do not commit a real
`k8s/secrets.yaml`.

### Kubernetes Secrets

The Deployment reads individual keys from `story-builder-secrets` and also
mounts the Secret key `.env` at `/app/.env`. The duplication is intentional:
the direct environment variables are convenient for Kubernetes, while `.env`
lets the container startup script load the same values and generate
Streamlit's runtime auth file if needed.

Important auth keys:

```text
AUTH_COOKIE_SECRET
AUTH_REDIRECT_URI
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_SERVER_METADATA_URL
AUTH_DEBUG
```

Important app keys:

```text
DB_PROVIDER
STORY_DB_PATH
CHROMA_DB_PATH
VECTOR_PROVIDER
DEFAULT_LLM_PROVIDER
DEFAULT_LLM_MODEL
GROQ_API_KEY
GEMINI_API_KEY
OPENROUTER_API_KEY
ENABLE_LLM_CONTENT_LOGGING
APP_MONGO_URI
APP_MONGO_DATABASE
BACKUP_MONGO_URI
BACKUP_MONGO_DATABASE
VECTOR_INDEX_NAME
```

SQLite is the default. MongoDB remains optional; set `DB_PROVIDER=mongodb` and
the MongoDB URI/database variables only when intentionally using MongoDB.

## Streamlit Community Cloud

Streamlit Community Cloud should continue to use its Secrets UI with the TOML
shape shown above. MongoDB Atlas is usually a better persistence target there
than local SQLite:

```toml
[database]
provider="mongodb"
uri="mongodb+srv://..."
database="story_builder"
```

Story Memory can use `rag.provider="mongodb_vector"` on Atlas, or
`rag.provider="none"` if vector memory is not needed.

## Configuration Reference

| Environment variable | Streamlit secrets path | Description |
| --- | --- | --- |
| `DB_PROVIDER` | `database.provider` | `sqlite` or `mongodb`; defaults to `sqlite` |
| `STORY_DB_PATH` | `database.path` | SQLite file path; defaults to `data/sqlite/story_builder.db` |
| `APP_MONGO_URI` | `database.uri` | Primary MongoDB Atlas URI |
| `APP_MONGO_DATABASE` | `database.database` | Primary MongoDB database; defaults to `story_builder` |
| `BACKUP_MONGO_URI` | `database.backup.uri` | MongoDB URI for backup sync |
| `BACKUP_MONGO_DATABASE` | `database.backup.database` | Backup database; defaults to `story_builder` |
| `VECTOR_PROVIDER` | `rag.provider` | `none`, `chroma`, or `mongodb_vector` |
| `CHROMA_DB_PATH` | `rag.chroma_path` | Chroma persistence path; defaults to `data/chroma_db` |
| `VECTOR_COLLECTION_NAME` | `rag.collection_name` | Vector collection name; defaults to `story_memory` |
| `VECTOR_INDEX_NAME` | `rag.index_name` | Atlas Vector Search index name |
| `DEFAULT_LLM_PROVIDER` | `llm.default_provider` | Default sidebar provider |
| `DEFAULT_LLM_MODEL` | `llm.default_model` | Default sidebar model |
| `GEMINI_API_KEY` | `llm.gemini.api_key` | Gemini API key |
| `GROQ_API_KEY` | `llm.groq.api_key` | Groq API key |
| `OPENROUTER_API_KEY` | `llm.openrouter.api_key` | OpenRouter API key |
| `ENABLE_LLM_CONTENT_LOGGING` | `llm.enable_content_logging` | Store full prompts/responses in LLM history |
| `AUTH_COOKIE_SECRET` | `auth.cookie_secret` | Streamlit auth cookie secret |
| `AUTH_REDIRECT_URI` | `auth.redirect_uri` | OAuth callback URL ending in `/oauth2callback` |
| `GOOGLE_CLIENT_ID` | `auth.google.client_id` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `auth.google.client_secret` | Google OAuth client secret |
| `GOOGLE_SERVER_METADATA_URL` | `auth.google.server_metadata_url` | Google OIDC metadata URL |
| `AUTH_DEBUG` | `auth.debug` | Show safe auth troubleshooting metadata |

Legacy names `MONGO_URI`, `MONGO_DATABASE`, `MONGODB_URI`, and
`MONGODB_DATABASE` are still accepted as compatibility fallbacks.

## Monitoring And Maintenance

- Logs include normal Python logging plus lightweight observability events for
  story generation, RAG retrieval, LLM calls, and selected database saves.
- The Debug / Observability tab lists recent app events for administrators.
- The History tab shows LLM call history and object history.
- Use Export / Import for manual backups.
- Rebuild Story Memory from the Story Memory tab after imports or deployment
  changes if vector search looks stale.

## Security Notes

- Do not commit `.env`, `.env.*`, `.streamlit/secrets.toml`, or real
  Kubernetes Secret manifests.
- The Docker image excludes local `.env` and `.streamlit/secrets.toml` files.
- In Kubernetes, real secrets live in `story-builder-secrets` and are mounted or
  injected only at runtime.
- Full LLM prompt/response logging is disabled by default; enable it only for
  intentional local debugging.
