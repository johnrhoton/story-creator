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
- Set environment variables in `.env` file:
  ```
  GOOGLE_API_KEY=your_gemini_key
  GROQ_API_KEY=your_groq_key
  OPENROUTER_API_KEY=your_openrouter_key
  MONGODB_URI=your_mongodb_uri  # Optional
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
| `GOOGLE_API_KEY` | Google Gemini API key | No* |
| `GROQ_API_KEY` | Groq API key | No* |
| `OPENROUTER_API_KEY` | OpenRouter API key | No* |
| `DEFAULT_LLM_PROVIDER` | Default provider selected in the sidebar | No |
| `DEFAULT_LLM_MODEL` | Default model selected in the sidebar | No |
| `MONGODB_URI` | MongoDB connection URI | No |
| `DATABASE_PASSWORD` | Database encryption password | No |

*At least one LLM API key required for story/character generation

### Database Management

- **Migrations**: Run automatically on startup
- **Backup**: Use Export/Import feature for data backup
- **Encryption**: Optional field-level encryption
- **MongoDB Sync**: Optional cloud backup synchronization
- **Chroma Story Memory Index**: Stored under `data/chroma_db`; rebuildable from SQLite via the Story Memory tab
- **LLM Defaults**: Sidebar model changes update `.env`; keep deployment `.env` files local and uncommitted

### Monitoring and Maintenance

- **Logs**: Check Streamlit logs for errors
- **LLM History**: Monitor API usage in History tab
- **Object History**: Inspect CRUD history in the History tab
- **Story Memory Index**: Inspect or rebuild Chroma from the Story Memory tab after imports or deployments
- **Database Health**: Regular export/import testing
- **Updates**: Pull latest code and run migrations

### Security Considerations

- Store API keys securely (environment variables, not code)
- Use database encryption for sensitive data
- Regular backup of user data
- Monitor LLM API usage and costs
- Validate imports to prevent data corruption
