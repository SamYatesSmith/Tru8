"""Date parsing utilities for handling various date formats."""

from datetime import datetime
from typing import Optional, Any
import re
import logging

logger = logging.getLogger(__name__)


def parse_date(date_value: Any) -> Optional[datetime]:
    """
    Parse dates from various formats into datetime objects.

    This utility consolidates date parsing logic to ensure consistency
    across the codebase and reduce code duplication.

    Handles:
    - datetime objects (passthrough)
    - ISO format strings ("2025-01-28", "2025-01-28T10:30:00Z")
    - Common date formats ("28-01-2025", "January 28, 2025", etc.)
    - Year-only strings ("2025" → Jan 1, 2025)

    Args:
        date_value: Can be datetime object, string, or None

    Returns:
        datetime object or None if unparseable

    Examples:
        >>> parse_date("2025-01-28")
        datetime.datetime(2025, 1, 28, 0, 0)
        >>> parse_date(datetime(2025, 1, 28))
        datetime.datetime(2025, 1, 28, 0, 0)
        >>> parse_date("invalid")
        None
    """
    if date_value is None:
        return None

    # Already a datetime
    if isinstance(date_value, datetime):
        return date_value

    # String date
    if isinstance(date_value, str):
        # Try ISO format (most common from APIs)
        try:
            # Handle both "2025-01-28" and "2025-01-28T10:30:00Z"
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d",           # 2025-01-28
            "%Y/%m/%d",           # 2025/01/28
            "%d-%m-%Y",           # 28-01-2025
            "%B %d, %Y",          # January 28, 2025
            "%b %d, %Y",          # Jan 28, 2025
            "%Y-%m-%dT%H:%M:%S",  # 2025-01-28T10:30:00
            "%d/%m/%Y",           # 28/01/2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt)
            except:
                continue

        # Extract year and assume Jan 1 (fallback for "2025" or "Published in 2025")
        match = re.search(r"20\d{2}", date_value)
        if match:
            year = int(match.group(0))
            return datetime(year, 1, 1)

    # Can't parse
    logger.warning(f"Could not parse date: {date_value} (type: {type(date_value)})")
    return None
