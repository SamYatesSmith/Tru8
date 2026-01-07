# Tru8 API - Production Dockerfile
# Multi-stage build for smaller final image

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

# Copy requirements first for better caching
COPY requirements.txt .

# Build wheels for all dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ==============================================================================
# Stage 2: Production - Minimal runtime image
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r tru8 && useradd -r -g tru8 tru8

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY --chown=tru8:tru8 . .

# Remove unnecessary files from final image
RUN rm -rf tests/ docs/ *.md .pytest_cache/ __pycache__/ .coverage htmlcov/

# Set ownership
RUN chown -R tru8:tru8 /app

# Switch to non-root user
USER tru8

# Environment defaults (override in deployment)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check - verify API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run with uvicorn
# Using exec form to ensure proper signal handling
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
