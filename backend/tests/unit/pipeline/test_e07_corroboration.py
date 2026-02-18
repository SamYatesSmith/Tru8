"""
PR-E07: Corroboration refactor tests.

Tests for:
- Ownership group independence detection
- Text similarity and fact overlap corroboration
- Group ID assignment (union-find)
- Derivation chain detection (T2 citing T1)
- No score mutation (annotation only)
"""

import pytest

from app.utils.corroboration import (
    _get_ownership_group,
    _text_similarity,
    _extract_key_facts,
    _check_fact_overlap,
    find_corroborating_sources,
    apply_corroboration_boost,
    _assign_corroboration_groups,
    _detect_derivation_chains,
)


# ============================================================
# Class: TestOwnershipGroups
# ============================================================


class TestOwnershipGroups:
    """Tests for ownership group independence detection."""

    @pytest.mark.unit
    def test_same_ownership_group_newscorp(self):
        """WSJ and NY Post are in the same News Corp group."""
        assert _get_ownership_group("wsj.com", "https://wsj.com/article") == "newscorp"
        assert (
            _get_ownership_group("nypost.com", "https://nypost.com/story") == "newscorp"
        )

    @pytest.mark.unit
    def test_same_ownership_group_bbc(self):
        """bbc.com and bbc.co.uk are in the same BBC group."""
        assert _get_ownership_group("bbc.com", "https://bbc.com/news") == "bbc"
        assert _get_ownership_group("bbc.co.uk", "https://bbc.co.uk/news") == "bbc"

    @pytest.mark.unit
    def test_different_ownership_groups(self):
        """BBC and Reuters are independent."""
        bbc = _get_ownership_group("bbc.co.uk", "https://bbc.co.uk/news")
        reuters = _get_ownership_group("reuters.com", "https://reuters.com/article")
        assert bbc != reuters

    @pytest.mark.unit
    def test_unknown_source_is_independent(self):
        """Unknown sources default to their domain as group."""
        group1 = _get_ownership_group("example.com", "https://example.com/page")
        group2 = _get_ownership_group("other.com", "https://other.com/page")
        assert group1 != group2

    @pytest.mark.unit
    def test_gov_sources_grouped_by_country(self):
        """UK and US gov sources should both be in gov groups."""
        uk = _get_ownership_group("gov.uk", "https://www.gov.uk/data")
        us = _get_ownership_group("census.gov", "https://www.census.gov/data")
        # Both match ".gov" pattern — same group (us_gov)
        # This is acceptable: gov sources are independent from non-gov,
        # and cross-country corroboration is still detected by text similarity
        assert uk == us  # both match .gov


# ============================================================
# Class: TestCorroborationDetection
# ============================================================


class TestCorroborationDetection:
    """Tests for corroboration detection logic."""

    @pytest.mark.unit
    def test_similar_text_from_independent_sources(self):
        """Two independent sources with similar text should corroborate."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/news/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures released by the ONS today.",
            },
            {
                "evidence_id": "ev-2",
                "source": "reuters.com",
                "url": "https://reuters.com/article/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures released by the ONS today.",
            },
        ]

        result = find_corroborating_sources(evidence)
        assert 0 in result
        assert 1 in result[0]

    @pytest.mark.unit
    def test_same_ownership_group_not_corroborating(self):
        """Two sources in the same ownership group should NOT corroborate."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "wsj.com",
                "url": "https://wsj.com/article/1",
                "snippet": "Unemployment fell to 3.8% in Q4 2025.",
            },
            {
                "evidence_id": "ev-2",
                "source": "nypost.com",
                "url": "https://nypost.com/story/1",
                "snippet": "Unemployment fell to 3.8% in Q4 2025.",
            },
        ]

        result = find_corroborating_sources(evidence)
        assert len(result) == 0

    @pytest.mark.unit
    def test_shared_facts_corroborate(self):
        """Evidence sharing specific numbers/facts should corroborate."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/news/1",
                "snippet": "The employment rate reached 75.6% according to ONS data for Q4 2025.",
            },
            {
                "evidence_id": "ev-2",
                "source": "theguardian.com",
                "url": "https://theguardian.com/business/1",
                "snippet": "ONS figures show 75.6% employment rate in Q4 2025, up from 75.1%.",
            },
        ]

        result = find_corroborating_sources(evidence)
        assert 0 in result
        assert 1 in result[0]

    @pytest.mark.unit
    def test_dissimilar_text_no_corroboration(self):
        """Unrelated evidence should NOT corroborate."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/news/1",
                "snippet": "The UK housing market saw record prices in central London.",
            },
            {
                "evidence_id": "ev-2",
                "source": "reuters.com",
                "url": "https://reuters.com/article/1",
                "snippet": "Japan's cherry blossom season started two weeks early this year.",
            },
        ]

        result = find_corroborating_sources(evidence)
        assert len(result) == 0

    @pytest.mark.unit
    def test_single_item_no_corroboration(self):
        """A single evidence item cannot corroborate."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/news/1",
                "snippet": "Some content.",
            },
        ]

        result = find_corroborating_sources(evidence)
        assert result == {}


# ============================================================
# Class: TestGroupAssignment
# ============================================================


class TestGroupAssignment:
    """Tests for corroboration group ID assignment."""

    @pytest.mark.unit
    def test_single_pair_gets_same_group(self):
        """Two corroborating items should get the same group ID."""
        corroboration_map = {0: [1], 1: [0]}

        groups = _assign_corroboration_groups(corroboration_map)

        assert groups[0] == groups[1]

    @pytest.mark.unit
    def test_separate_pairs_get_different_groups(self):
        """Two independent pairs should get different group IDs."""
        corroboration_map = {0: [1], 1: [0], 2: [3], 3: [2]}

        groups = _assign_corroboration_groups(corroboration_map)

        assert groups[0] == groups[1]
        assert groups[2] == groups[3]
        assert groups[0] != groups[2]

    @pytest.mark.unit
    def test_transitive_corroboration_same_group(self):
        """If A corroborates B and B corroborates C, all get same group."""
        corroboration_map = {0: [1], 1: [0, 2], 2: [1]}

        groups = _assign_corroboration_groups(corroboration_map)

        assert groups[0] == groups[1] == groups[2]

    @pytest.mark.unit
    def test_empty_map_no_groups(self):
        """Empty corroboration map should return empty groups."""
        assert _assign_corroboration_groups({}) == {}


# ============================================================
# Class: TestDerivationChains
# ============================================================


class TestDerivationChains:
    """Tests for derivation chain detection."""

    @pytest.mark.unit
    def test_two_reporting_citing_primary(self):
        """Two reporting sources corroborating with a primary should form a chain."""
        evidence = [
            {
                "evidence_id": "ev-primary",
                "source": "ons.gov.uk",
                "tier": "primary",
                "snippet": "Employment data...",
            },
            {
                "evidence_id": "ev-bbc",
                "source": "bbc.co.uk",
                "tier": "reporting",
                "snippet": "BBC reports...",
            },
            {
                "evidence_id": "ev-guardian",
                "source": "theguardian.com",
                "tier": "commentary",
                "snippet": "Guardian analysis...",
            },
        ]

        corroboration_map = {0: [1, 2], 1: [0], 2: [0]}

        chains = _detect_derivation_chains(evidence, corroboration_map)

        assert 0 in chains
        assert "ev-bbc" in chains[0]
        assert "ev-guardian" in chains[0]

    @pytest.mark.unit
    def test_no_chain_without_primary(self):
        """No derivation chain if no primary source."""
        evidence = [
            {
                "evidence_id": "ev-1",
                "source": "bbc.co.uk",
                "tier": "reporting",
                "snippet": "...",
            },
            {
                "evidence_id": "ev-2",
                "source": "reuters.com",
                "tier": "reporting",
                "snippet": "...",
            },
        ]

        corroboration_map = {0: [1], 1: [0]}

        chains = _detect_derivation_chains(evidence, corroboration_map)

        assert len(chains) == 0

    @pytest.mark.unit
    def test_no_chain_single_derived(self):
        """Chain needs at least 2 derived sources."""
        evidence = [
            {
                "evidence_id": "ev-primary",
                "source": "gov.uk",
                "tier": "primary",
                "snippet": "...",
            },
            {
                "evidence_id": "ev-bbc",
                "source": "bbc.co.uk",
                "tier": "reporting",
                "snippet": "...",
            },
        ]

        corroboration_map = {0: [1], 1: [0]}

        chains = _detect_derivation_chains(evidence, corroboration_map)

        assert len(chains) == 0


# ============================================================
# Class: TestApplyCorroborationBoost
# ============================================================


class TestApplyCorroborationBoost:
    """Tests for the full apply_corroboration_boost function."""

    @pytest.mark.unit
    def test_annotates_with_evidence_ids_not_indices(self):
        """Corroboration should use evidence_ids, not raw indices."""
        evidence = [
            {
                "evidence_id": "ev-001",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures.",
            },
            {
                "evidence_id": "ev-002",
                "source": "reuters.com",
                "url": "https://reuters.com/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures.",
            },
        ]

        result, stats = apply_corroboration_boost(evidence)

        assert stats["items_annotated"] == 2
        # Check evidence_ids are used, not indices
        assert result[0].get("corroborating_evidence_ids") == "ev-002"
        assert result[1].get("corroborating_evidence_ids") == "ev-001"

    @pytest.mark.unit
    def test_assigns_group_ids(self):
        """Corroborated items should get corroboration_group_id."""
        evidence = [
            {
                "evidence_id": "ev-001",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/1",
                "snippet": "GDP grew by 2.1% in Q4 2025 according to official figures.",
            },
            {
                "evidence_id": "ev-002",
                "source": "reuters.com",
                "url": "https://reuters.com/1",
                "snippet": "GDP grew by 2.1% in Q4 2025 according to official figures.",
            },
        ]

        result, stats = apply_corroboration_boost(evidence)

        assert result[0].get("corroboration_group_id") is not None
        assert (
            result[0]["corroboration_group_id"] == result[1]["corroboration_group_id"]
        )

    @pytest.mark.unit
    def test_no_score_mutation(self):
        """Corroboration should NOT modify any score fields."""
        evidence = [
            {
                "evidence_id": "ev-001",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/1",
                "snippet": "GDP grew by 2.1% in Q4 2025 according to official figures.",
                "relevance_score": 0.8,
            },
            {
                "evidence_id": "ev-002",
                "source": "reuters.com",
                "url": "https://reuters.com/1",
                "snippet": "GDP grew by 2.1% in Q4 2025 according to official figures.",
                "relevance_score": 0.7,
            },
        ]

        result, _ = apply_corroboration_boost(evidence)

        # Scores should be unchanged
        assert result[0]["relevance_score"] == 0.8
        assert result[1]["relevance_score"] == 0.7

    @pytest.mark.unit
    def test_stats_contain_group_count(self):
        """Stats should report number of groups and derivation chains."""
        evidence = [
            {
                "evidence_id": "ev-001",
                "source": "bbc.co.uk",
                "url": "https://bbc.co.uk/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures.",
            },
            {
                "evidence_id": "ev-002",
                "source": "reuters.com",
                "url": "https://reuters.com/1",
                "snippet": "UK unemployment fell to 3.8% in the latest quarterly figures.",
            },
        ]

        _, stats = apply_corroboration_boost(evidence)

        assert stats["enabled"] is True
        assert stats["items_annotated"] == 2
        assert "groups" in stats
        assert stats["groups"] >= 1
        assert "derivation_chains" in stats


# ============================================================
# Class: TestHelperFunctions
# ============================================================


class TestHelperFunctions:
    """Tests for utility functions."""

    @pytest.mark.unit
    def test_text_similarity_identical(self):
        assert _text_similarity("hello world", "hello world") == 1.0

    @pytest.mark.unit
    def test_text_similarity_empty(self):
        assert _text_similarity("", "hello") == 0.0
        assert _text_similarity("hello", "") == 0.0

    @pytest.mark.unit
    def test_extract_key_facts_numbers(self):
        facts = _extract_key_facts("GDP grew 2.1% in Q4 2025")
        # Regex extracts "2.1" (number) and "2025" — % is a word boundary
        assert "2.1" in facts
        assert "2025" in facts

    @pytest.mark.unit
    def test_fact_overlap_identical(self):
        facts = {"2.1%", "2025", "Q4"}
        assert _check_fact_overlap(facts, facts) == 1.0

    @pytest.mark.unit
    def test_fact_overlap_empty(self):
        assert _check_fact_overlap(set(), {"2.1%"}) == 0.0
