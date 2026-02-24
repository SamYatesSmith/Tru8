# Tru8 API - Production Dockerfile (CPU-only PyTorch)
# Optimized for Railway deployment

# ==============================================================================
# Stage 1: Builder - Install dependencies and build wheels
# ==============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL: Install CPU-only PyTorch FIRST
# This prevents sentence-transformers from pulling the 2.5GB CUDA version
RUN pip install --no-cache-dir \
    torch==2.5.1+cpu \
    torchvision==0.20.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ==============================================================================
# Stage 2: Production - Minimal runtime image
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r tru8 && useradd -r -g tru8 tru8

# Install runtime dependencies + temporary build deps for pycairo
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    build-essential \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch in final image (NOT from wheels)
RUN pip install --no-cache-dir \
    torch==2.5.1+cpu \
    torchvision==0.20.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Remove build dependencies to reduce image size
RUN apt-get update && apt-get remove -y \
    build-essential \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY --chown=tru8:tru8 . .

# Remove unnecessary files from final image
RUN rm -rf tests/ docs/ *.md .pytest_cache/ __pycache__/ .coverage htmlcov/

# Ensure scripts directory exists and copy startup scripts
RUN mkdir -p scripts
COPY --chown=tru8:tru8 scripts/download_models.py scripts/
COPY --chown=tru8:tru8 entrypoint.sh .

# Fix Windows line endings (CRLF -> LF) and make executable
RUN sed -i 's/\r$//' entrypoint.sh scripts/download_models.py && chmod +x entrypoint.sh

# Set ownership
RUN chown -R tru8:tru8 /app

# Switch to non-root user
USER tru8

# Environment defaults (override in deployment)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    PORT=8000 \
    HF_HOME=/models/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/models/sentence-transformers \
    TRANSFORMERS_CACHE=/models/transformers

# Expose port
EXPOSE 8000

# Health check - increased start period for model download
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run with entrypoint for model download
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
