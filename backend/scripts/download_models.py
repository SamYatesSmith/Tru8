#!/usr/bin/env python3
"""
Pre-download ML models on first startup.

Models are cached so subsequent startups are instant (~200MB total).
Pipeline runs models inline — always download if not cached.
"""
import os
import sys

HF_HOME = os.environ.get("HF_HOME", "/models/huggingface")


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
