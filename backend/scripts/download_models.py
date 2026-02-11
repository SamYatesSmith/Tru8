#!/usr/bin/env python3
"""
Pre-download ML models to persistent volume on first startup.

This script runs as part of the container entrypoint to ensure models
are downloaded to the Fly.io volume before the app starts serving requests.
Models are cached on the volume so subsequent startups are instant.

NOTE: Only the Celery worker needs ML models. The web process (uvicorn)
only serves the API and delegates ML inference to the worker.
"""
import os
import sys

HF_HOME = os.environ.get("HF_HOME", "/models/huggingface")


def is_worker_process():
    """Check if this is the Celery worker process (needs ML models)."""
    # Check command line args for celery
    return any("celery" in arg.lower() for arg in sys.argv)


def models_cached():
    """Check if required models already exist on the volume."""
    paths = [
        f"{HF_HOME}/hub/models--sentence-transformers--all-MiniLM-L6-v2",
        f"{HF_HOME}/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2",
    ]
    return all(os.path.exists(p) for p in paths)


def download_models():
    """Download all required ML models to the persistent cache."""
    print("Downloading ML models to persistent cache...")
    print(f"Cache directory: {HF_HOME}")

    # Ensure cache directory exists
    os.makedirs(HF_HOME, exist_ok=True)

    from sentence_transformers import SentenceTransformer, CrossEncoder

    print("  [1/2] Downloading all-MiniLM-L6-v2 (embeddings)...")
    SentenceTransformer("all-MiniLM-L6-v2")
    print("        Done.")

    print("  [2/2] Downloading cross-encoder/ms-marco-MiniLM-L-6-v2 (reranking)...")
    CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    print("        Done.")

    print("All models downloaded successfully!")


if __name__ == "__main__":
    # Check if this is the web process (uvicorn) - skip model download
    # Web process only serves API, worker handles ML inference
    if not is_worker_process():
        print("Web process detected - skipping ML model download (worker handles ML).")
        sys.exit(0)

    if models_cached():
        print("Models already cached on volume, skipping download.")
        sys.exit(0)

    try:
        download_models()
    except Exception as e:
        print(f"Error downloading models: {e}")
        print("App will attempt to download models on first request.")
        # Don't fail startup - models can be downloaded lazily
        sys.exit(0)
