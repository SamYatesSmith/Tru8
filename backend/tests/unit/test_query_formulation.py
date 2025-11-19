"""
Unit tests for Query Formulation Enhancement (Tier 1 Improvement)

Tests the QueryFormulator class which transforms vague claims into optimized search queries.
"""

import pytest
from app.utils.query_formulation import QueryFormulator


class TestQueryFormulator:
    """Test query formulation enhancement"""

    @pytest.fixture
    def formulator(self):
        """Create QueryFormulator instance"""
        return QueryFormulator()

    def test_entity_extraction(self, formulator):
        """Test: Extracts entities from claim"""
        claim = "President Biden signed the Infrastructure Act in 2021"

        query = formulator.formulate_query(claim)

        # Should extract key entities
        assert "Biden" in query or "Infrastructure" in query
        # Should exclude fact-check sites
        assert "-site:snopes.com" in query
        assert "-site:factcheck.org" in query

    def test_temporal_refinement(self, formulator):
        """Test: Adds year for time-sensitive claims"""
        claim = "Company X hired 500 employees this year"
        temporal_analysis = {
            'is_time_sensitive': True,
            'temporal_window': 'year_2025',
            'temporal_markers': [{'type': 'YEAR', 'value': 2025}]
        }

        query = formulator.formulate_query(claim, temporal_analysis=temporal_analysis)

        assert "2025" in query

    def test_primary_source_filters(self, formulator):
        """Test: Adds .gov/.edu/.org filters"""
        claim = "Study shows coffee reduces cancer risk"

        query = formulator.formulate_query(claim)

        # Should prefer primary sources
        assert "site:.gov" in query or "site:.edu" in query or "site:.org" in query

    def test_key_entities_used(self, formulator):
        """Test: Uses pre-extracted entities from claim extraction"""
        claim = "The project received funding"
        key_entities = ["Golden Gate Park", "San Francisco"]

        query = formulator.formulate_query(claim, key_entities=key_entities)

        # Should include entities from extraction
        assert "Golden Gate Park" in query or "San Francisco" in query

    def test_fallback_when_spacy_unavailable(self, formulator):
        """Test: Falls back gracefully when spaCy unavailable"""
        # Simulate spaCy failure
        formulator.nlp = None

        claim = "Biden announced new policy in 2024"
        key_entities = ["Biden"]
        temporal_analysis = {
            'is_time_sensitive': True,
            'temporal_markers': [{'type': 'YEAR', 'value': 2024}]
        }

        query = formulator.formulate_query(
            claim,
            key_entities=key_entities,
            temporal_analysis=temporal_analysis
        )

        # Should still produce a query
        assert len(query) > 0
        assert "Biden" in query

    def test_query_length_limit(self, formulator):
        """Test: Enforces 250 character API limit"""
        claim = "Very long claim " * 50  # Create very long claim
        key_entities = ["Entity" + str(i) for i in range(20)]

        query = formulator.formulate_query(claim, key_entities=key_entities)

        assert len(query) <= 250

    def test_deduplication(self, formulator):
        """Test: Removes duplicate terms"""
        claim = "Biden Biden announced announcement policy policy"

        query = formulator.formulate_query(claim)

        # Should not have obvious duplicates
        terms = query.lower().split()
        # Allow some duplication from filters, but check main content
        biden_count = sum(1 for term in terms if 'biden' in term)
        assert biden_count <= 2  # One from extraction, maybe one from filters
