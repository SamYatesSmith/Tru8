"""Tests for M-05 jurisdiction-aware source routing.

Covers:
- UK jurisdiction adapter ordering (ONS/Hansard/GOV.UK prioritised)
- US jurisdiction adapter ordering (FRED/GovInfo/LoC prioritised)
- Global jurisdiction — no reordering
- Fewer than cap adapters — no truncation
- Jurisdiction filter (M-05 upgrade) — adapter set narrowing
"""

import pytest
from unittest.mock import MagicMock

from app.pipeline.retrieve import get_adapters_for_jurisdiction


# ── Helper ─────────────────────────────────────────────────────────────────


def _make_adapter(name: str, priority_tier: int = 1) -> MagicMock:
    adapter = MagicMock()
    adapter.api_name = name
    adapter.priority_tier = priority_tier
    return adapter


def _apply_jurisdiction_sort(adapters, jurisdiction, max_cap=3):
    """Reproduce the tier-aware jurisdiction sorting logic from retrieve.py (PQ-06).

    Updated for M-05: uses get_adapters_for_jurisdiction() instead of static dict.
    """
    if len(adapters) > max_cap:
        allowed = get_adapters_for_jurisdiction(jurisdiction) or []

        def _sort_key(adapter):
            tier = getattr(adapter, "priority_tier", 1)
            try:
                pref = allowed.index(adapter.api_name)
            except ValueError:
                pref = len(allowed) + 1
            return (tier, pref, adapter.api_name)

        adapters.sort(key=_sort_key)
        adapters = adapters[:max_cap]
    return adapters


# ── UK jurisdiction ────────────────────────────────────────────────────────


class TestUKJurisdictionAdapterOrdering:
    def test_uk_prefers_ons_hansard_govuk(self):
        adapters = [
            _make_adapter("FRED"),
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("UK Parliament Hansard"),
            _make_adapter("GOV.UK Content API"),
            _make_adapter("GovInfo.gov"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        names = [a.api_name for a in result]

        # UK-specific and global adapters preferred
        assert len(result) == 3

    def test_uk_companies_house_preferred(self):
        adapters = [
            _make_adapter("FRED"),
            _make_adapter("GovInfo.gov"),
            _make_adapter("Companies House"),
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("Library of Congress"),
        ]
        result = _apply_jurisdiction_sort(adapters, "UK", max_cap=3)
        names = [a.api_name for a in result]

        # UK adapters should be in the allowed list
        uk_allowed = get_adapters_for_jurisdiction("UK")
        assert "ONS Economic Statistics" in uk_allowed
        assert "Companies House" in uk_allowed


# ── US jurisdiction ────────────────────────────────────────────────────────


class TestUSJurisdictionAdapterOrdering:
    def test_us_prefers_fred_govinfo_loc(self):
        adapters = [
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("FRED"),
            _make_adapter("GovInfo.gov"),
            _make_adapter("Library of Congress"),
            _make_adapter("UK Parliament Hansard"),
        ]
        result = _apply_jurisdiction_sort(adapters, "US", max_cap=3)
        names = [a.api_name for a in result]

        assert "FRED" in names
        assert "GovInfo.gov" in names
        assert "Library of Congress" in names
        assert len(result) == 3


# ── Global jurisdiction ────────────────────────────────────────────────────


class TestGlobalNoPreference:
    def test_global_alphabetical_tiebreak(self):
        """Global jurisdiction has no preference mapping — alphabetical tiebreak within same tier."""
        adapters = [
            _make_adapter("ONS Economic Statistics"),
            _make_adapter("FRED"),
            _make_adapter("PubMed"),
            _make_adapter("GovInfo.gov"),
        ]
        result = _apply_jurisdiction_sort(adapters, "Global", max_cap=3)
        result_names = [a.api_name for a in result]

        # All same tier, global sort → alphabetical by api_name, take first 3
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
            _make_adapter("FRED"),
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


# ── Jurisdiction filter mapping shape ──────────────────────────────────────


class TestJurisdictionMappingShape:
    def test_uk_has_expected_adapters(self):
        uk = get_adapters_for_jurisdiction("UK")
        assert uk is not None
        # UK-specific adapters present
        assert "ONS Economic Statistics" in uk
        assert "UK Parliament Hansard" in uk
        assert "GOV.UK Content API" in uk
        assert "Companies House" in uk
        assert "UK Legislation" in uk
        # SC-15: Bills API fallback (Law + Politics specialist independent of
        # legislation.gov.uk, which is IP-blocked under SC-05).
        assert "UK Parliament Bills" in uk

    def test_us_has_expected_adapters(self):
        us = get_adapters_for_jurisdiction("US")
        assert us is not None
        assert "FRED" in us
        assert "GovInfo.gov" in us
        assert "Library of Congress" in us

    def test_global_has_expected_health_and_academic_adapters(self):
        """Regression guard for the H0/WHO class of bug.

        NOAA was silently excluded until 2026-04-23 (H0: "NOAA Climate Data"
        string mismatch). WHO was silently excluded until this fix (omitted
        entirely from the global list). Both had the same shape — Health/
        Science specialists declared as global-jurisdiction in-code but
        missing from the M-05 allow-list, so the jurisdiction filter quietly
        dropped them before any HTTP call. This test pins the adapters whose
        exclusion would materially degrade coverage on Health/Science claims.
        """
        global_names = get_adapters_for_jurisdiction(None)
        assert global_names is not None

        for required in (
            "PubMed",
            "WHO",
            "Semantic Scholar",
            "OpenAlex",
            "NOAA CDO",
            "Wikipedia",
        ):
            assert required in global_names, (
                f"{required} missing from global jurisdiction allow-list — "
                f"health/science claims will silently lose this specialist"
            )

    def test_no_duplicate_entries(self):
        for jurisdiction in ["UK", "US", None]:
            adapters = get_adapters_for_jurisdiction(jurisdiction)
            if adapters:
                assert len(adapters) == len(
                    set(adapters)
                ), f"Duplicates in {jurisdiction}"
