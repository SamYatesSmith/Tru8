# Tru8 API - Production Dockerfile (CPU-only PyTorch)
# Single-stage build to reduce peak memory usage on Railway

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build + runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpq-dev \
    curl \
    build-essential \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch FIRST (prevents sentence-transformers pulling 2.5GB CUDA)
RUN pip install --no-cache-dir \
    torch==2.5.1+cpu \
    torchvision==0.20.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build-only dependencies to shrink image
RUN apt-get update && apt-get remove -y \
    build-essential \
    libcairo2-dev \
    libpq-dev \
    pkg-config \
    python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code (entrypoint.sh and scripts/ included)
COPY . .

# Remove unnecessary files and fix Windows line endings
RUN rm -rf tests/ docs/ *.md .pytest_cache/ __pycache__/ .coverage htmlcov/ \
    && sed -i 's/\r$//' entrypoint.sh scripts/download_models.py \
    && chmod +x entrypoint.sh

# Create model cache directory and non-root user
RUN mkdir -p /app/models && \
    groupadd -r tru8 && useradd -r -g tru8 tru8 && \
    chown -R tru8:tru8 /app
USER tru8

# Environment defaults (override in deployment)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    PORT=8000 \
    HF_HOME=/app/models/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/models/sentence-transformers \
    TRANSFORMERS_CACHE=/app/models/transformers

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
