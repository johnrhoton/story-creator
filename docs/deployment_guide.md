# Deployment Guide

## Local Development

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Setup Steps
1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd story-builder
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**:
   ```bash
   python scripts/migrate.py
   python scripts/seed_llm_models.py
   ```

5. **Run Application**:
   ```bash
   streamlit run app.py
   ```

### Configuration
- Set root-level values in `.streamlit/secrets.toml`. Use the same keys in
  Streamlit Community Cloud's Secrets UI:
  ```toml
  GEMINI_API_KEY="your_gemini_key"
  GROQ_API_KEY="your_groq_key"
  OPENROUTER_API_KEY="your_openrouter_key"
  APP_MONGO_URI="your_primary_mongodb_uri"  # Optional
  BACKUP_MONGO_URI="your_backup_mongodb_uri"  # Optional
  ```

## Production Deployment

### Basic Streamlit Deployment

1. **Streamlit Cloud**:
   - Push code to GitHub
   - Connect to Streamlit Cloud
   - Set secrets for API keys
   - Deploy automatically

2. **Local Server**:
   ```bash
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   ```

3. **Docker Deployment**:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   RUN python scripts/migrate.py
   
   CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
   ```

### Advanced Deployment (Future)

#### Kubernetes Deployment

The project is designed to eventually support Kubernetes deployment for scalability:

- **Containerization**: Docker image with Python app
- **Database**: Persistent volume for SQLite or migration to PostgreSQL
- **LLM Integration**: External API calls (no local models)
- **Scaling**: Horizontal pod scaling for multiple users
- **Configuration**: ConfigMaps and Secrets for API keys

#### Raspberry Pi Deployment

Planned for local, offline-capable deployment:

- **Hardware Requirements**: Raspberry Pi 4+ with adequate RAM
- **Local LLM**: Integration with local models (Ollama, LM Studio)
- **Storage**: Local SQLite database
- **Networking**: Optional web access via local network
- **Power Management**: Low-power operation considerations

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | No* |
| `GROQ_API_KEY` | Groq API key | No* |
| `OPENROUTER_API_KEY` | OpenRouter API key | No* |
| `DEFAULT_LLM_PROVIDER` | Default provider selected in the sidebar | No |
| `DEFAULT_LLM_MODEL` | Default model selected in the sidebar | No |
| `DB_PROVIDER` | Active persistence provider: `sqlite` or `mongodb` | No |
| `APP_MONGO_URI` | Primary MongoDB Atlas URI for `DB_PROVIDER=mongodb` | Required for MongoDB |
| `APP_MONGO_DATABASE` | Primary MongoDB database name; defaults to `story_builder` | No |
| `BACKUP_MONGO_URI` | MongoDB URI for push/pull backup snapshots | Required for MongoDB sync |
| `BACKUP_MONGO_DATABASE` | MongoDB backup database name; defaults to `story_builder` | No |
| `MONGO_URI` / `MONGO_DATABASE` | Legacy fallback names for app and backup MongoDB settings | No |
| `MONGODB_URI` / `MONGODB_DATABASE` | Legacy fallback names, mainly from older backup sync setup | No |
| `VECTOR_PROVIDER` | Story Memory vector provider: `none`, `chroma`, or `mongodb_vector` | No |
| `VECTOR_COLLECTION_NAME` | Vector collection name; defaults to `story_memory` | No |
| `VECTOR_INDEX_NAME` | MongoDB Atlas Vector Search index name | Required for `mongodb_vector` |
| `DATABASE_PASSWORD` | Database encryption password | No |

*At least one LLM API key required for story/character generation

### Database Management

- **Provider**: `sqlite` by default locally; set `DB_PROVIDER=mongodb` for MongoDB Atlas
- **Streamlit Cloud**: Configure `DB_PROVIDER="mongodb"` and `APP_MONGO_URI` in secrets
- **Migrations**: SQLite migrations run automatically; MongoDB startup creates indexes and seed records
- **Backup**: Use Export/Import feature for data backup
- **Encryption**: Optional field-level encryption
- **MongoDB Sync**: Optional cloud backup synchronization using `BACKUP_MONGO_URI`; this may point at a separate cluster/database from the primary app database
- **Vector Provider**: `chroma` by default locally; use `mongodb_vector` on Streamlit Cloud or `none` to disable RAG
- **Chroma Story Memory Index**: Stored under `data/chroma_db`; rebuildable from the active database provider via the Story Memory tab
- **MongoDB Atlas Vector Search**: Stores text, metadata, and embeddings in the configured vector collection; create the Atlas vector index named by `VECTOR_INDEX_NAME`
- **LLM Defaults**: Sidebar model changes update local `.streamlit/secrets.toml`; set the same root-level keys in Streamlit Community Cloud secrets

### Monitoring and Maintenance

- **Logs**: Check Streamlit logs for errors
- **LLM History**: Monitor API usage in History tab
- **Object History**: Inspect CRUD history in the History tab
- **Story Memory Index**: Inspect or rebuild the configured vector index from the Story Memory tab after imports or deployments
- **Database Health**: Regular export/import testing
- **Updates**: Pull latest code and run migrations

### Security Considerations

- Store API keys securely (environment variables, not code)
- Use database encryption for sensitive data
- Regular backup of user data
- Monitor LLM API usage and costs
- Validate imports to prevent data corruption
