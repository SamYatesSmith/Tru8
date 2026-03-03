"""Tests for M-05 jurisdiction-aware source routing.

Covers:
- UK jurisdiction adapter ordering (ONS/Hansard/GOV.UK prioritised)
- US jurisdiction adapter ordering (FRED/GovInfo/LoC prioritised)
- Global jurisdiction — no reordering
- Fewer than cap adapters — no truncation
"""

import pytest
from unittest.mock import MagicMock

from app.pipeline.retrieve import JURISDICTION_ADAPTER_PREFERENCES


# ── Helper ─────────────────────────────────────────────────────────────────


def _make_adapter(name: str) -> MagicMock:
    adapter = MagicMock()
    adapter.api_name = name
    return adapter


def _apply_jurisdiction_sort(adapters, jurisdiction, max_cap=3):
    """Reproduce the jurisdiction sorting logic from retrieve.py."""
    if len(adapters) > max_cap:
        preferences = JURISDICTION_ADAPTER_PREFERENCES.get(jurisdiction, [])
        if preferences:

            def _priority(adapter):
                try:
                    return preferences.index(adapter.api_name)
                except ValueError:
                    return len(preferences) + 1

            adapters.sort(key=_priority)
        adapters = adapters[:max_cap]
    return adapters


# ── UK jurisdiction ────────────────────────────────────────────────────────


class TestUKJurisdictionAdapterOrdering:
    def test_uk_prefers_ons_hansard_govuk(self):
        adapters = [
            _make_adapter("FRED Economic Data"),
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("Hansard Parliamentary Records"),
            _make_adapter("GOV.UK Publications"),
            _make_adapter("GovInfo Publications"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        names = [a.api_name for a in result]

        assert "ONS Economic Statistics" in names
        assert "Hansard Parliamentary Records" in names
        assert "GOV.UK Publications" in names
        assert len(result) == 3

    def test_uk_companies_house_preferred(self):
        adapters = [
            _make_adapter("FRED Economic Data"),
            _make_adapter("GovInfo Publications"),
            _make_adapter("Companies House"),
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("Library of Congress"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        names = [a.api_name for a in result]

        # ONS should be first (index 0 in preferences), Companies House at index 3
        assert names[0] == "ONS Economic Statistics"
        assert "Companies House" in names


# ── US jurisdiction ────────────────────────────────────────────────────────


class TestUSJurisdictionAdapterOrdering:
    def test_us_prefers_fred_govinfo_loc(self):
        adapters = [
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("FRED Economic Data"),
            _make_adapter("GovInfo Publications"),
            _make_adapter("Library of Congress"),
            _make_adapter("Hansard Parliamentary Records"),
        ]
        result = _apply_jurisdiction_sort(adapters, "US", max_cap=3)
        names = [a.api_name for a in result]

        assert "FRED Economic Data" in names
        assert "GovInfo Publications" in names
        assert "Library of Congress" in names
        assert len(result) == 3


# ── Global jurisdiction ────────────────────────────────────────────────────


class TestGlobalNoPreference:
    def test_global_no_reordering(self):
        """Global jurisdiction has no preference mapping — first-3-wins."""
        adapters = [
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("FRED Economic Data"),
            _make_adapter("PubMed"),
            _make_adapter("GovInfo Publications"),
        ]
        original_names = [a.api_name for a in adapters[:3]]
        result = _apply_jurisdiction_sort(adapters, "Global", max_cap=3)
        result_names = [a.api_name for a in result]

        # Without preferences, truncation takes the first 3
        assert result_names == original_names
        assert len(result) == 3

    def test_unknown_jurisdiction_no_reordering(self):
        adapters = [
            _make_adapter("A"),
            _make_adapter("B"),
            _make_adapter("C"),
            _make_adapter("D"),
        ]
        result = _apply_jurisdiction_sort(adapters, "AU", max_cap=3)
        assert [a.api_name for a in result] == ["A", "B", "C"]


# ── Fewer than cap ─────────────────────────────────────────────────────────


class TestFewerThanCapNoTruncation:
    def test_two_adapters_unaffected(self):
        adapters = [
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("FRED Economic Data"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        assert len(result) == 2

    def test_three_adapters_unaffected(self):
        adapters = [
            _make_adapter("A"),
            _make_adapter("B"),
            _make_adapter("C"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        assert len(result) == 3

    def test_empty_adapters(self):
        result = _apply_jurisdiction_sort([], "UK", max_cap=3)
        assert result == []


# ── Preference mapping shape ───────────────────────────────────────────────


class TestPreferenceMappingShape:
    def test_uk_has_four_entries(self):
        assert len(JURISDICTION_ADAPTER_PREFERENCES["UK"]) == 4

    def test_us_has_three_entries(self):
        assert len(JURISDICTION_ADAPTER_PREFERENCES["US"]) == 3

    def test_no_duplicate_entries(self):
        for jurisdiction, prefs in JURISDICTION_ADAPTER_PREFERENCES.items():
            assert len(prefs) == len(set(prefs)), f"Duplicates in {jurisdiction}"
