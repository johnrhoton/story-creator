FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    DB_PROVIDER=sqlite \
    STORY_DB_PATH=/app/data/sqlite/story_builder.db \
    CHROMA_DB_PATH=/app/data/chroma \
    VECTOR_PROVIDER=chroma

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-torch-cpu.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==2.3.0+cpu" \
    && pip install --no-cache-dir -r requirements-torch-cpu.txt \
    && NVIDIA_PACKAGES="$(pip list --format=freeze | sed -n 's/^\(nvidia-[^=]*\)==.*/\1/p')" \
    && if [ -n "$NVIDIA_PACKAGES" ]; then pip uninstall -y $NVIDIA_PACKAGES; fi \
    && (pip uninstall -y triton || true) \
    && if pip list --format=freeze | grep -i '^nvidia-'; then exit 1; fi

COPY . .

RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
    && mkdir -p /app/data/sqlite /app/data/chroma /app/.streamlit \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["python", "scripts/start_container.py"]
