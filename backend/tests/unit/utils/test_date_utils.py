"""Tests for date parsing utilities."""

import pytest
from datetime import datetime, timezone

from app.utils.date_utils import parse_date


class TestParseDate:
    """Tests for parse_date function."""

    def test_iso_date(self):
        """ISO date string is parsed correctly."""
        result = parse_date("2025-01-28")
        assert result == datetime(2025, 1, 28)

    def test_iso_datetime(self):
        """ISO datetime with Z suffix is parsed correctly with timezone stripped."""
        result = parse_date("2025-01-28T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 28
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo is None

    def test_common_format_dmy(self):
        """Day-month-year with dashes is parsed correctly."""
        result = parse_date("28-01-2025")
        assert result is not None
        assert result.day == 28
        assert result.month == 1
        assert result.year == 2025

    def test_long_month(self):
        """Full month name format is parsed correctly."""
        result = parse_date("January 28, 2025")
        assert result == datetime(2025, 1, 28)

    def test_short_month(self):
        """Abbreviated month name format is parsed correctly."""
        result = parse_date("Jan 28, 2025")
        assert result == datetime(2025, 1, 28)

    def test_slash_dmy(self):
        """Day/month/year with slashes is parsed correctly."""
        result = parse_date("28/01/2025")
        assert result is not None
        assert result.day == 28
        assert result.month == 1
        assert result.year == 2025

    def test_slash_ymd(self):
        """Year/month/day with slashes is parsed correctly."""
        result = parse_date("2025/01/28")
        assert result is not None
        assert result.day == 28
        assert result.month == 1
        assert result.year == 2025

    def test_year_only(self):
        """Year-only string defaults to January 1."""
        result = parse_date("2025")
        assert result == datetime(2025, 1, 1)

    def test_none_returns_none(self):
        """None input returns None."""
        assert parse_date(None) is None

    def test_garbage_returns_none(self):
        """Unparseable string returns None."""
        assert parse_date("not a date") is None

    def test_datetime_passthrough(self):
        """datetime object is returned as-is; timezone stripped if present."""
        naive = datetime(2025, 1, 28, 12, 0, 0)
        assert parse_date(naive) is naive

        aware = datetime(2025, 1, 28, 12, 0, 0, tzinfo=timezone.utc)
        result = parse_date(aware)
        assert result is not None
        assert result.tzinfo is None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 28
