"""M-05: Tests for jurisdiction-aware source routing.

Covers:
- Jurisdiction adapter mapping
- Global fallback
- Unknown jurisdiction handling
- Config parsing
"""

import pytest
from unittest.mock import patch


class TestGetAdaptersForJurisdiction:
    def test_uk_includes_uk_and_global(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction("UK")
        assert result is not None
        # Should include UK-specific adapters
        assert "GOV.UK Content API" in result
        assert "UK Parliament Hansard" in result
        assert "ONS Economic Statistics" in result
        assert "Companies House" in result
        assert "UK Legislation" in result
        # Should include global adapters
        assert "Semantic Scholar" in result
        assert "Wikipedia" in result

    def test_us_includes_us_and_global(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction("US")
        assert result is not None
        assert "FRED" in result
        assert "GovInfo.gov" in result
        assert "Library of Congress" in result
        # Global included
        assert "Wikipedia" in result

    def test_us_excludes_uk(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction("US")
        assert result is not None
        assert "GOV.UK Content API" not in result
        assert "UK Parliament Hansard" not in result

    def test_uk_excludes_us(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction("UK")
        assert result is not None
        assert "FRED" not in result
        assert "GovInfo.gov" not in result

    def test_none_jurisdiction_returns_global_only(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction(None)
        assert result is not None
        # Global adapters included
        assert "Wikipedia" in result
        assert "Semantic Scholar" in result
        # Jurisdiction-specific excluded
        assert "GOV.UK Content API" not in result
        assert "FRED" not in result

    def test_unknown_jurisdiction_returns_global(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        result = get_adapters_for_jurisdiction("AU")
        assert result is not None
        # Should still have global adapters
        assert "Wikipedia" in result
        # No AU-specific adapters exist
        assert "GOV.UK Content API" not in result

    def test_case_insensitive(self):
        from app.pipeline.retrieve import get_adapters_for_jurisdiction

        uk_upper = get_adapters_for_jurisdiction("UK")
        uk_lower = get_adapters_for_jurisdiction("uk")
        assert uk_upper == uk_lower


class TestLoadJurisdictionAdapters:
    def test_loads_from_config(self):
        from app.pipeline.retrieve import _load_jurisdiction_adapters

        result = _load_jurisdiction_adapters()
        assert isinstance(result, dict)
        assert "uk" in result or "UK" in result
        assert "global" in result

    def test_handles_empty_config(self):
        from app.pipeline.retrieve import _load_jurisdiction_adapters

        with patch("app.pipeline.retrieve.settings") as mock:
            mock.JURISDICTION_ADAPTERS = "{}"
            result = _load_jurisdiction_adapters()
        assert result == {}

    def test_handles_invalid_json(self):
        from app.pipeline.retrieve import _load_jurisdiction_adapters

        with patch("app.pipeline.retrieve.settings") as mock:
            mock.JURISDICTION_ADAPTERS = "not json"
            result = _load_jurisdiction_adapters()
        assert result == {}
