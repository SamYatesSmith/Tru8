# Pipeline package
#
# Note: Classes are NOT imported here to prevent heavy ML libraries
# from loading at startup. Each module should be imported directly when needed.
#
# Usage:
#   from app.pipeline.extract import ClaimExtractor
#   etc.

__all__ = [
    "ingest",
    "extract",
    "retrieve",
    "claim_map_analyzer",
    "claim_selector",
]
