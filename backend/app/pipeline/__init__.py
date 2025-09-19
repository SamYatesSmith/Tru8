# Pipeline package
# 
# Note: Classes are NOT imported here to prevent heavy ML libraries (transformers, torch)
# from loading at startup. Each module should be imported directly when needed.
#
# Usage:
#   from app.pipeline.verify import get_claim_verifier
#   from app.pipeline.extract import ClaimExtractor
#   etc.

__all__ = [
    "ingest",
    "extract", 
    "retrieve",
    "verify",
    "judge"
]