"""Tests for URL utility functions."""

import pytest

from app.utils.url_utils import extract_domain


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_basic_url(self):
        """Extracts clean domain from a standard URL."""
        assert extract_domain("https://www.bbc.co.uk/news") == "bbc.co.uk"

    def test_strips_www(self):
        """www prefix is removed from domain."""
        assert extract_domain("https://www.example.com") == "example.com"

    def test_preserves_subdomain(self):
        """Non-www subdomains are preserved."""
        result = extract_domain("https://api.example.com/v1/data")
        assert result == "api.example.com"

    def test_empty_string(self):
        """Empty URL returns the default fallback (empty string)."""
        assert extract_domain("") == ""

    def test_invalid_url(self):
        """URL without scheme returns fallback since netloc is empty."""
        result = extract_domain("not a url")
        assert result == ""

    def test_custom_fallback(self):
        """Custom fallback value is returned for empty/invalid URLs."""
        assert extract_domain("", "unknown") == "unknown"
