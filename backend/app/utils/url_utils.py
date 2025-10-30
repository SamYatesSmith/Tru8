"""URL utility functions for domain extraction and normalization."""

from urllib.parse import urlparse
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_domain(url: str, fallback: str = "") -> str:
    """
    Extract clean domain from URL with consistent normalization.

    This utility consolidates domain extraction logic used across the codebase
    to ensure consistency and reduce code duplication.

    Args:
        url: Full URL string (e.g., "https://www.bbc.co.uk/news/article")
        fallback: Value to return on error or invalid URL (default: empty string)

    Returns:
        Clean domain in lowercase without www prefix (e.g., "bbc.co.uk")

    Examples:
        >>> extract_domain("https://www.bbc.co.uk/news/article")
        "bbc.co.uk"
        >>> extract_domain("http://example.com/path")
        "example.com"
        >>> extract_domain("invalid-url", fallback="unknown")
        "unknown"
    """
    if not url:
        return fallback

    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove www. prefix for consistency
        if domain.startswith('www.'):
            domain = domain[4:]

        # Validate domain is not empty or protocol-only
        if domain and domain not in ['', 'http:', 'https:']:
            return domain.lower()

        return fallback

    except Exception as e:
        logger.warning(f"Failed to extract domain from URL '{url}': {e}")
        return fallback
