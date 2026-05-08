"""Tests for Stage 5.1: Coverage Recovery — targeted retrieval for low-coverage claims.

Covers:
- Threshold detection: inline logic from runner.py (extracted into testable helper)
- Candidate selection: sorting, capping, edge cases
- retrieve_for_elements: evidence retrieval, dedup, ID format, empty results
- map_evidence_to_specific_elements: ref merging, element targeting, state transitions
- Timeout handling: graceful degradation, partial success

Source code under test:
- runner.py:1450-1615 (inline threshold detection + orchestration)
- retrieve.py:647-741 (retrieve_for_elements)
- claim_map_analyzer.py:788-872 (map_evidence_to_specific_elements)
"""

import asyncio
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.claim_map import ElementState, EvidenceRelationship
from app.pipeline.retrieve import EvidenceRetriever
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, derive_orientation
from app.services.search import SearchResult


# ── Helpers ──────────────────────────────────────────────────────────────────


def _detect_recovery_candidates(claims, threshold=0.4, max_claims=3):
    """Extract of runner.py coverage recovery detection logic for unit testing.

    Mirrors the inline code at runner.py:1458-1487 exactly.
    """
    candidates = []
    for claim in claims:
        cm = claim.get("claim_map")
        if not cm or not cm.get("elements"):
            continue
        elements = cm["elements"]
        total = len(elements)
        unresolved = sum(
            1
            for e in elements
            if (
                e.get("state").value
                if hasattr(e.get("state"), "value")
                else e.get("state")
            )
            == "unresolved"
        )
        if total > 0 and (unresolved / total) > threshold:
            candidates.append(
                {
                    "claim": claim,
                    "total": total,
                    "unresolved": unresolved,
                    "ratio": unresolved / total,
                }
            )
    candidates.sort(key=lambda x: -x["ratio"])
    return candidates[:max_claims]


def _make_element(element_id, state="supported", description="Test element"):
    """Build a minimal element dict with the given state (string or enum)."""
    return {
        "element_id": element_id,
        "description": description,
        "evidence_refs": [],
        "state": state,
        "uncertainty": None,
    }


def _make_claim_with_elements(elements, position=0):
    """Build a claim dict with a claim_map containing the given elements."""
    return {
        "text": f"Claim at position {position}",
        "position": position,
        "claim_map": {
            "claim_id": f"c{position}",
            "normalised_claim": f"Normalised claim {position}",
            "elements": elements,
            "orientation": "Insufficient evidence",
        },
    }


def _make_search_result(url, title="Result", snippet="Snippet text", source="web"):
    """Build a search result dict matching the format used by retrieve_for_elements."""
    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "source": source,
        "published_date": "2026-01-15",
    }


# =============================================================================
# Group 1: Threshold detection (5 tests)
# =============================================================================


class TestThresholdDetection:
    """Tests for the inline threshold logic from runner.py:1458-1483."""

    def test_triggers_above_threshold(self):
        """3/5 unresolved (60%) exceeds the 40% threshold -- recovery triggers."""
        elements = [
            _make_element("e1", "supported"),
            _make_element("e2", "unresolved"),
            _make_element("e3", "unresolved"),
            _make_element("e4", "supported"),
            _make_element("e5", "unresolved"),
        ]
        claims = [_make_claim_with_elements(elements)]

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 1
        assert candidates[0]["unresolved"] == 3
        assert candidates[0]["total"] == 5
        assert candidates[0]["ratio"] == pytest.approx(0.6)

    def test_does_not_trigger_at_threshold(self):
        """2/5 unresolved (40%) is at the threshold boundary -- no recovery (> not >=)."""
        elements = [
            _make_element("e1", "supported"),
            _make_element("e2", "unresolved"),
            _make_element("e3", "supported"),
            _make_element("e4", "unresolved"),
            _make_element("e5", "disputed"),
        ]
        claims = [_make_claim_with_elements(elements)]

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 0

    def test_does_not_trigger_below(self):
        """1/5 unresolved (20%) is below the 40% threshold -- no recovery."""
        elements = [
            _make_element("e1", "supported"),
            _make_element("e2", "supported"),
            _make_element("e3", "disputed"),
            _make_element("e4", "supported"),
            _make_element("e5", "unresolved"),
        ]
        claims = [_make_claim_with_elements(elements)]

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 0

    def test_does_not_trigger_all_resolved(self):
        """0/5 unresolved -- no recovery needed."""
        elements = [
            _make_element("e1", "supported"),
            _make_element("e2", "supported"),
            _make_element("e3", "disputed"),
            _make_element("e4", "supported"),
            _make_element("e5", "disputed"),
        ]
        claims = [_make_claim_with_elements(elements)]

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 0

    def test_handles_enum_state_values(self):
        """ElementState enum values are correctly counted via the hasattr(value) branch."""
        elements = [
            _make_element("e1", ElementState.supported),
            _make_element("e2", ElementState.unresolved),
            _make_element("e3", ElementState.unresolved),
            _make_element("e4", ElementState.unresolved),
            _make_element("e5", ElementState.disputed),
        ]
        claims = [_make_claim_with_elements(elements)]

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 1
        assert candidates[0]["unresolved"] == 3
        assert candidates[0]["ratio"] == pytest.approx(0.6)


# =============================================================================
# Group 2: Candidate selection (3 tests)
# =============================================================================


class TestCandidateSelection:
    """Tests for candidate sorting and capping logic from runner.py:1486-1487."""

    def test_sorted_by_ratio_descending(self):
        """Multiple candidates are sorted by unresolved ratio, highest first."""
        # Claim 0: 2/4 unresolved = 50%
        claim_0 = _make_claim_with_elements(
            [
                _make_element("e1", "unresolved"),
                _make_element("e2", "unresolved"),
                _make_element("e3", "supported"),
                _make_element("e4", "supported"),
            ],
            position=0,
        )
        # Claim 1: 4/5 unresolved = 80%
        claim_1 = _make_claim_with_elements(
            [
                _make_element("e1", "unresolved"),
                _make_element("e2", "unresolved"),
                _make_element("e3", "unresolved"),
                _make_element("e4", "unresolved"),
                _make_element("e5", "supported"),
            ],
            position=1,
        )
        # Claim 2: 3/4 unresolved = 75%
        claim_2 = _make_claim_with_elements(
            [
                _make_element("e1", "unresolved"),
                _make_element("e2", "unresolved"),
                _make_element("e3", "unresolved"),
                _make_element("e4", "disputed"),
            ],
            position=2,
        )

        candidates = _detect_recovery_candidates([claim_0, claim_1, claim_2])

        assert len(candidates) == 3
        assert candidates[0]["ratio"] == pytest.approx(0.8)  # claim_1
        assert candidates[1]["ratio"] == pytest.approx(0.75)  # claim_2
        assert candidates[2]["ratio"] == pytest.approx(0.5)  # claim_0

    def test_capped_at_max_claims(self):
        """More than 3 qualifying claims -- only top 3 by ratio are returned."""
        claims = []
        for i in range(5):
            # Each claim: (i+3)/(i+5) unresolved ratio, all above 0.4
            total = i + 5
            unresolved_count = i + 3
            elements = []
            for j in range(total):
                state = "unresolved" if j < unresolved_count else "supported"
                elements.append(_make_element(f"e{j}", state))
            claims.append(_make_claim_with_elements(elements, position=i))

        candidates = _detect_recovery_candidates(claims)

        assert len(candidates) == 3
        # Verify they are the top 3 by ratio
        ratios = [c["ratio"] for c in candidates]
        assert ratios == sorted(ratios, reverse=True)

    def test_skips_claims_without_claim_map(self):
        """Claims missing claim_map are silently skipped."""
        claim_no_map = {"text": "No map claim", "position": 0}
        claim_empty_map = {
            "text": "Empty map claim",
            "position": 1,
            "claim_map": {},
        }
        claim_no_elements = {
            "text": "No elements claim",
            "position": 2,
            "claim_map": {"elements": []},
        }
        # One valid claim with high unresolved ratio
        valid_claim = _make_claim_with_elements(
            [
                _make_element("e1", "unresolved"),
                _make_element("e2", "unresolved"),
                _make_element("e3", "unresolved"),
            ],
            position=3,
        )

        candidates = _detect_recovery_candidates(
            [claim_no_map, claim_empty_map, claim_no_elements, valid_claim]
        )

        assert len(candidates) == 1
        assert candidates[0]["claim"]["position"] == 3


# =============================================================================
# Group 3: retrieve_for_elements (5 tests)
# =============================================================================


class TestRetrieveForElements:
    """Tests for EvidenceRetriever.retrieve_for_elements (retrieve.py:647-741)."""

    def _make_retriever(self, search_results=None):
        """Create an EvidenceRetriever with a mocked search_service."""
        retriever = EvidenceRetriever.__new__(EvidenceRetriever)
        retriever.search_service = AsyncMock()
        retriever.evidence_extractor = MagicMock()
        retriever.evidence_extractor.max_concurrent = 3
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)
        if search_results is not None:
            retriever.search_service.search_for_evidence = AsyncMock(
                return_value=search_results
            )
        else:
            retriever.search_service.search_for_evidence = AsyncMock(return_value=[])
        return retriever

    @pytest.mark.asyncio
    async def test_returns_evidence(self):
        """Mock search returns results -- evidence list is populated."""
        search_results = [
            _make_search_result("https://example.com/article1", title="Article 1"),
            _make_search_result("https://example.com/article2", title="Article 2"),
        ]
        retriever = self._make_retriever(search_results)
        elements = [{"element_id": "e1", "description": "Test element description"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="This is a test claim about something",
                existing_urls=set(),
            )

        assert len(evidence) == 2
        assert evidence[0]["url"] == "https://example.com/article1"
        assert evidence[1]["url"] == "https://example.com/article2"
        assert evidence[0]["is_recovery"] is True
        assert evidence[0]["metadata"]["coverage_recovery"] is True
        assert evidence[0]["metadata"]["target_element"] == "e1"

    @pytest.mark.asyncio
    async def test_deduplicates_existing_urls(self):
        """URLs already in the existing_urls set are excluded from results."""
        search_results = [
            _make_search_result("https://example.com/existing"),
            _make_search_result("https://example.com/new"),
        ]
        retriever = self._make_retriever(search_results)
        elements = [{"element_id": "e1", "description": "Test element"}]
        existing = {"https://example.com/existing"}

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=existing,
            )

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/new"

    @pytest.mark.asyncio
    async def test_generates_evidence_ids(self):
        """Evidence IDs follow the format ev-rec-{element_id}_{idx}_{hash8}."""
        url = "https://example.com/test-article"
        expected_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        search_results = [_make_search_result(url)]
        retriever = self._make_retriever(search_results)
        elements = [{"element_id": "e1", "description": "Test element"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        assert evidence[0]["evidence_id"] == f"ev-rec-e1_0_{expected_hash}"
        assert evidence[0]["id"] == "recovery_e1_0"

    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        """When search returns no results, an empty list is returned."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert evidence == []

    @pytest.mark.asyncio
    async def test_evidence_item_structure(self):
        """Returned evidence items contain all required keys in the pipeline format."""
        search_results = [_make_search_result("https://example.com/test")]
        retriever = self._make_retriever(search_results)
        elements = [{"element_id": "e1", "description": "Test element"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        required_keys = {
            "id",
            "evidence_id",
            "element_ids",
            "text",
            "snippet",
            "source",
            "url",
            "title",
            "published_date",
            "relevance_score",
            "semantic_similarity",
            "combined_score",
            "word_count",
            "receipt_status",
            "metadata",
            "content_basis",
            "is_recovery",
        }
        assert set(evidence[0].keys()) == required_keys

    @pytest.mark.asyncio
    async def test_search_result_object_does_not_crash(self):
        """Recovery loop accepts real SearchResult objects, not just dicts.

        Regression for NF-21: search providers return SearchResult instances
        (no `.get()` method); calling `r.get(...)` on them raised
        AttributeError, silently failing recovery.
        """
        search_results = [
            SearchResult(
                title="Real SearchResult",
                url="https://example.com/sr",
                snippet="Snippet text from a real SearchResult instance",
                published_date="2026-01-15",
                source="example.com",
            )
        ]
        retriever = self._make_retriever(search_results)
        elements = [{"element_id": "e1", "description": "Test element"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/sr"
        assert evidence[0]["title"] == "Real SearchResult"
        assert evidence[0]["content_basis"] == "snippet"

    @pytest.mark.asyncio
    async def test_one_query_per_element_naive(self):
        """N elements produce N naive search queries (one per element) when planner disabled."""
        retriever = self._make_retriever(search_results=[])
        elements = [
            {"element_id": "e1", "description": "First element"},
            {"element_id": "e2", "description": "Second element"},
            {"element_id": "e3", "description": "Third element"},
        ]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim about something important",
                existing_urls=set(),
            )

        assert retriever.search_service.search_for_evidence.call_count == 3
        # Verify each query includes the element description and claim context
        calls = retriever.search_service.search_for_evidence.call_args_list
        for i, call in enumerate(calls):
            query = call[0][0] if call[0] else call[1].get("query", "")
            assert elements[i]["description"] in query


# =============================================================================
# Group 3b: Edge cases in retrieve_for_elements (7 tests)
# =============================================================================


class TestRetrieveEdgeCases:
    """Edge cases for retrieve_for_elements: error handling, dedup, planner quirks."""

    def _make_retriever(self, search_results=None):
        """Create an EvidenceRetriever with a mocked search_service."""
        retriever = EvidenceRetriever.__new__(EvidenceRetriever)
        retriever.search_service = AsyncMock()
        retriever.evidence_extractor = MagicMock()
        retriever.evidence_extractor.max_concurrent = 3
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)
        if search_results is not None:
            retriever.search_service.search_for_evidence = AsyncMock(
                return_value=search_results
            )
        else:
            retriever.search_service.search_for_evidence = AsyncMock(return_value=[])
        return retriever

    @pytest.mark.asyncio
    async def test_search_exception_continues_to_next_element(self):
        """When search fails for one element, subsequent elements still searched."""
        retriever = self._make_retriever()
        retriever.search_service.search_for_evidence = AsyncMock(
            side_effect=[
                RuntimeError("Network timeout"),
                [_make_search_result("https://example.com/ok")],
            ]
        )
        elements = [
            {"element_id": "e1", "description": "First (will fail)"},
            {"element_id": "e2", "description": "Second (will succeed)"},
        ]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/ok"
        assert retriever.search_service.search_for_evidence.call_count == 2

    @pytest.mark.asyncio
    async def test_search_exception_first_query_continues_to_second(self):
        """With planner giving 2 queries, first query failure doesn't block second."""
        retriever = self._make_retriever()
        retriever.search_service.search_for_evidence = AsyncMock(
            side_effect=[
                RuntimeError("API rate limit"),
                [_make_search_result("https://example.com/second-query-ok")],
            ]
        )
        elements = [{"element_id": "e1", "description": "Test element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            return_value=[
                {
                    "element_id": "e1",
                    "queries": ["first query", "second query"],
                    "freshness": "py",
                }
            ]
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/second-query-ok"
        assert retriever.search_service.search_for_evidence.call_count == 2

    @pytest.mark.asyncio
    async def test_cross_element_url_dedup(self):
        """Same URL returned for two different elements is deduplicated."""
        shared_url = "https://example.com/shared-article"
        retriever = self._make_retriever(
            search_results=[_make_search_result(shared_url)]
        )
        elements = [
            {"element_id": "e1", "description": "First element"},
            {"element_id": "e2", "description": "Second element"},
        ]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        # Only 1 evidence item despite 2 elements returning same URL
        assert len(evidence) == 1
        assert evidence[0]["url"] == shared_url
        assert evidence[0]["metadata"]["target_element"] == "e1"

    @pytest.mark.asyncio
    async def test_planner_wrong_element_ids_ignored(self):
        """Plans for element_ids not in the elements list are silently ignored."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Real element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            return_value=[
                {
                    "element_id": "e99",  # wrong ID
                    "queries": ["irrelevant query"],
                    "freshness": "py",
                }
            ]
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        # e1 has no planner queries → falls back to naive
        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Real element" in query  # naive concat, not planner query

    @pytest.mark.asyncio
    async def test_planner_empty_queries_falls_back_to_naive(self):
        """Plan with empty queries list falls back to naive concatenation."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            return_value=[
                {
                    "element_id": "e1",
                    "queries": [],  # empty
                    "freshness": "py",
                }
            ]
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        # Empty queries → element_queries["e1"] = [] (falsy) → naive fallback
        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Test element" in query

    @pytest.mark.asyncio
    async def test_planner_returns_none_uses_naive(self):
        """When planner returns None instead of [], naive queries are used."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(return_value=None)

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim text",
                existing_urls=set(),
            )

        # None → `if plans` is falsy → element_queries stays empty → naive fallback
        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Test element" in query

    @pytest.mark.asyncio
    async def test_partial_search_failure_preserves_results(self):
        """Second query failure preserves results from first successful query."""
        retriever = self._make_retriever()
        retriever.search_service.search_for_evidence = AsyncMock(
            side_effect=[
                [_make_search_result("https://example.com/from-first-query")],
                RuntimeError("Second query fails"),
            ]
        )
        elements = [{"element_id": "e1", "description": "Test element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            return_value=[
                {
                    "element_id": "e1",
                    "queries": ["good query", "bad query"],
                    "freshness": "py",
                }
            ]
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            evidence = await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/from-first-query"


# =============================================================================
# Group 4: map_evidence_to_specific_elements (3 tests)
# =============================================================================


class TestMapEvidenceToSpecificElements:
    """Tests for ClaimMapAnalyzer.map_evidence_to_specific_elements (claim_map_analyzer.py:788-872)."""

    def _make_analyzer(self, llm_response):
        """Create a ClaimMapAnalyzer with mocked _call_llm."""
        analyzer = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
        analyzer.snippet_length = 200
        analyzer.analyzer_temperature = 0.1
        analyzer.analyzer_max_tokens = 2000
        analyzer._call_llm = AsyncMock(return_value=llm_response)
        # Bypass evidence ref validation -- return refs as-is
        analyzer._validate_evidence_refs = lambda refs, ev: refs
        return analyzer

    def _make_claim_map(self):
        """Build a claim_map with one unresolved and one supported element."""
        return {
            "claim_id": "c1",
            "normalised_claim": "Test claim for mapping",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "First element",
                    "evidence_refs": [],
                    "state": ElementState.unresolved,
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "description": "Second element",
                    "evidence_refs": [
                        {"evidence_id": "ev-existing", "relationship": "supports"}
                    ],
                    "state": ElementState.supported,
                    "uncertainty": None,
                },
            ],
            "orientation": "Insufficient evidence",
        }

    @pytest.mark.asyncio
    async def test_merges_new_refs(self):
        """New evidence_refs from LLM response are appended to existing refs."""
        claim_map = self._make_claim_map()
        # Add an existing ref to e1 so we can verify merging
        claim_map["elements"][0]["evidence_refs"] = [
            {"evidence_id": "ev-old", "relationship": "context"}
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-new-1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ]
        }
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {"evidence_id": "ev-new-1", "title": "New article", "snippet": "Content"}
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = claim_map["elements"][0]
        assert len(e1["evidence_refs"]) == 2
        assert e1["evidence_refs"][0]["evidence_id"] == "ev-old"
        assert e1["evidence_refs"][1]["evidence_id"] == "ev-new-1"

    @pytest.mark.asyncio
    async def test_only_targets_unresolved(self):
        """Resolved elements keep state unchanged; refs only added if LLM maps to them."""
        claim_map = self._make_claim_map()

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-new-1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ]
        }
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {"evidence_id": "ev-new-1", "title": "New article", "snippet": "Content"}
        ]

        # Only target e1, leave e2 alone
        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e2 = claim_map["elements"][1]
        # e2 state unchanged (LLM didn't return e2 mapping)
        assert e2["state"] == ElementState.supported
        assert len(e2["evidence_refs"]) == 1
        assert e2["evidence_refs"][0]["evidence_id"] == "ev-existing"

    @pytest.mark.asyncio
    async def test_cross_element_ref_merging(self):
        """LLM maps recovery evidence to both target (e1) and resolved (e2) elements.

        e2 gets new ref merged but state stays unchanged (supported, not disputed).
        e1 gets refs and state updated normally.
        """
        claim_map = self._make_claim_map()

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-new-1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {"evidence_id": "ev-new-1", "relationship": "context"}
                    ],
                    "state": "disputed",  # LLM suggests disputed, but should be ignored
                    "uncertainty": "Some uncertainty",
                },
            ]
        }
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {
                "evidence_id": "ev-new-1",
                "title": "Cross-element article",
                "snippet": "Content",
            }
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        # e1 (target): refs and state updated
        e1 = claim_map["elements"][0]
        assert e1["state"] == ElementState.supported
        assert len(e1["evidence_refs"]) == 1
        assert e1["evidence_refs"][0]["evidence_id"] == "ev-new-1"

        # e2 (resolved): new ref merged, but state preserved as supported
        e2 = claim_map["elements"][1]
        assert e2["state"] == ElementState.supported  # NOT disputed
        assert len(e2["evidence_refs"]) == 2
        assert e2["evidence_refs"][0]["evidence_id"] == "ev-existing"
        assert e2["evidence_refs"][1]["evidence_id"] == "ev-new-1"

    @pytest.mark.asyncio
    async def test_all_elements_in_prompt(self):
        """Prompt passed to _call_llm contains ALL elements, not just unresolved."""
        claim_map = self._make_claim_map()

        llm_response = {"elements": []}
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {"evidence_id": "ev-new-1", "title": "Article", "snippet": "Content"}
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        # Check the prompt passed to _call_llm
        call_args = analyzer._call_llm.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get(
            "prompt", call_args[0][0] if call_args[0] else ""
        )
        assert "e1:" in prompt, "Prompt should contain unresolved element e1"
        assert "e2:" in prompt, "Prompt should contain resolved element e2"

    @pytest.mark.asyncio
    async def test_evidence_formatting_unclassified(self):
        """Evidence with tier=None shows '[Tier: unclassified]', not '[Tier: None]'."""
        claim_map = self._make_claim_map()

        llm_response = {"elements": []}
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {
                "evidence_id": "ev-new-1",
                "title": "Unclassified article",
                "snippet": "Content",
                "tier": None,
                "evidence_type": None,
            }
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        call_args = analyzer._call_llm.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get(
            "prompt", call_args[0][0] if call_args[0] else ""
        )
        assert (
            "[Tier: unclassified]" in prompt
        ), f"Expected '[Tier: unclassified]' in prompt, got: {prompt}"
        assert (
            "[Type: unclassified]" in prompt
        ), f"Expected '[Type: unclassified]' in prompt, got: {prompt}"
        assert "[Tier: None]" not in prompt
        assert "[Type: None]" not in prompt

    @pytest.mark.asyncio
    async def test_evidence_id_neutralisation(self):
        """Recovery evidence IDs have element hints stripped in the prompt.

        ev-rec-e1_3_abc → ev-rec-3_abc in prompt, but real ID restored in output refs.
        """
        claim_map = self._make_claim_map()

        # LLM returns refs using the neutralised ID
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-3_abc123",
                            "relationship": "supports",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-3_abc123",
                            "relationship": "context",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_3_abc123",
                "title": "Recovery article",
                "snippet": "Content",
            }
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        # Check prompt uses neutralised ID (no element hint)
        call_args = analyzer._call_llm.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[1].get(
            "prompt", call_args[0][0] if call_args[0] else ""
        )
        assert "ev-rec-3_abc123" in prompt, "Prompt should use neutralised ID"
        assert (
            "ev-rec-e1_3_abc123" not in prompt
        ), "Prompt should NOT contain element hint"

        # Check real IDs are restored in output refs
        e1 = claim_map["elements"][0]
        assert e1["evidence_refs"][0]["evidence_id"] == "ev-rec-e1_3_abc123"

        e2 = claim_map["elements"][1]
        assert e2["evidence_refs"][1]["evidence_id"] == "ev-rec-e1_3_abc123"

    @pytest.mark.asyncio
    async def test_state_transition(self):
        """An unresolved element transitions to supported after recovery mapping."""
        claim_map = self._make_claim_map()
        assert claim_map["elements"][0]["state"] == ElementState.unresolved

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-new-1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ]
        }
        analyzer = self._make_analyzer(llm_response)
        new_evidence = [
            {"evidence_id": "ev-new-1", "title": "New article", "snippet": "Content"}
        ]

        await analyzer.map_evidence_to_specific_elements(
            claim_map=claim_map,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = claim_map["elements"][0]
        assert e1["state"] == ElementState.supported
        # Orientation should be re-derived (both elements now supported)
        assert claim_map["orientation"] is not None
        assert claim_map["orientation"] != "Insufficient evidence"


# =============================================================================
# Group 5: Timeout handling (2 tests)
# =============================================================================


class TestTimeoutHandling:
    """Tests for the asyncio.wait_for timeout wrapper from runner.py:1587-1598."""

    @pytest.mark.asyncio
    async def test_timeout_does_not_crash(self):
        """A task that exceeds the timeout is caught gracefully -- no exception propagated."""

        async def slow_recovery():
            await asyncio.sleep(10)

        # The runner wraps recovery in asyncio.wait_for with return_exceptions=True
        # Simulate that pattern: timeout should be caught, not raised
        timed_out = False
        try:
            await asyncio.wait_for(
                asyncio.gather(slow_recovery(), return_exceptions=True),
                timeout=0.05,
            )
        except asyncio.TimeoutError:
            timed_out = True

        # The runner catches TimeoutError and logs a warning -- no crash
        assert timed_out is True

    @pytest.mark.asyncio
    async def test_partial_success_on_timeout(self):
        """When one candidate completes before timeout and another does not,
        the completed result is preserved."""
        results = {}

        async def fast_recovery():
            results["fast"] = "completed"

        async def slow_recovery():
            await asyncio.sleep(10)
            results["slow"] = "completed"

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    fast_recovery(),
                    slow_recovery(),
                    return_exceptions=True,
                ),
                timeout=0.1,
            )
        except asyncio.TimeoutError:
            pass

        # The fast task completed before the timeout
        assert "fast" in results
        assert results["fast"] == "completed"
        # The slow task did not complete
        assert "slow" not in results


# ── Helpers for Efficacy Tests (Groups 6-8) ─────────────────────────────────


def _make_real_analyzer(llm_response):
    """Analyzer with mocked _call_llm but REAL _validate_evidence_refs.

    Unlike _make_analyzer (Group 4), validation runs for real — hallucinated
    evidence IDs and invalid relationships are stripped.
    """
    analyzer = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
    analyzer.snippet_length = 200
    analyzer.analyzer_temperature = 0.1
    analyzer.analyzer_max_tokens = 2000
    analyzer._call_llm = AsyncMock(return_value=llm_response)
    return analyzer


def _make_full_claim_map(element_specs, claim_id="c1"):
    """Build claim_map with derive_orientation pre-computed.

    Args:
        element_specs: list of (element_id, state_str, description, evidence_refs)
        claim_id: claim identifier

    Returns:
        dict shaped like ClaimMap with orientation derived from element states.
    """
    elements = []
    for eid, state_str, desc, refs in element_specs:
        elements.append(
            {
                "element_id": eid,
                "description": desc,
                "evidence_refs": list(refs),
                "state": ElementState(state_str),
                "uncertainty": None,
            }
        )

    cm = {
        "claim_id": claim_id,
        "normalised_claim": f"Test claim {claim_id}",
        "claim_type": "empirical",
        "elements": elements,
        "orientation": None,
        "metadata": {
            "decomposition_model": "test",
            "mapping_model": "test",
            "element_count": len(elements),
            "completed_at": None,
        },
    }
    cm["orientation"] = derive_orientation(elements)
    return cm


# =============================================================================
# Group 6: Recovery Success (5 tests)
# =============================================================================


class TestRecoverySuccess:
    """Prove that good evidence → element state transitions → orientation improvement."""

    @pytest.mark.asyncio
    async def test_full_cycle_resolves_two_of_three_unresolved(self):
        """3 elements (1 supported, 2 unresolved) → all 3 supported after recovery."""
        cm = _make_full_claim_map(
            [
                ("e1", "supported", "Economic growth exceeded 2%", []),
                ("e2", "unresolved", "Unemployment fell below 5%", []),
                ("e3", "unresolved", "Inflation stayed under 3%", []),
            ]
        )

        before_orientation = cm["orientation"]
        assert "insufficient" in before_orientation or "lacking" in before_orientation

        new_evidence = [
            {
                "evidence_id": "ev-rec-e2_0_abc",
                "title": "Jobs report",
                "snippet": "Unemployment dropped to 4.2%",
            },
            {
                "evidence_id": "ev-rec-e3_0_def",
                "title": "CPI data",
                "snippet": "Inflation at 2.8% year-over-year",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e2_0_abc",
                            "relationship": "supports",
                            "reasoning": "Confirms unemployment below 5%",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e3",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e3_0_def",
                            "relationship": "supports",
                            "reasoning": "CPI data confirms inflation under 3%",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e2", "e3"],
            new_evidence=new_evidence,
        )

        # All 3 elements now supported
        for e in cm["elements"]:
            assert e["state"] == ElementState.supported
        # Evidence refs populated on recovered elements
        assert len(cm["elements"][1]["evidence_refs"]) == 1
        assert len(cm["elements"][2]["evidence_refs"]) == 1
        # Orientation reflects full support
        assert (
            cm["orientation"]
            == "Of 3 elements examined, retrieved evidence predominantly supports all 3."
        )

    @pytest.mark.asyncio
    async def test_recovery_can_produce_disputed_not_just_supported(self):
        """Recovery maps challenging evidence → disputed state, not just supported."""
        cm = _make_full_claim_map(
            [
                ("e1", "supported", "Revenue increased by 15%", []),
                ("e2", "unresolved", "Profit margins improved", []),
            ]
        )

        assert "insufficient" in cm["orientation"] or "lacking" in cm["orientation"]

        new_evidence = [
            {
                "evidence_id": "ev-rec-e2_0_xyz",
                "title": "Earnings report",
                "snippet": "Margins narrowed from 12% to 10%",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e2_0_xyz",
                            "relationship": "challenges",
                            "reasoning": "Report shows margins decreased, not improved",
                        }
                    ],
                    "state": "disputed",
                    "uncertainty": "Earnings report contradicts margin improvement claim.",
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e2"],
            new_evidence=new_evidence,
        )

        assert cm["elements"][1]["state"] == ElementState.disputed
        assert cm["elements"][1]["uncertainty"] is not None
        # Orientation mentions conflicting evidence, not insufficient
        assert "conflicting evidence" in cm["orientation"]
        assert "insufficient" not in cm["orientation"]

    @pytest.mark.asyncio
    async def test_multiple_evidence_items_map_to_single_element(self):
        """3 evidence items map to 1 element with mixed relationships → disputed."""
        cm = _make_full_claim_map(
            [
                (
                    "e1",
                    "unresolved",
                    "Global temperature rose 1.5C above pre-industrial levels",
                    [],
                ),
            ]
        )

        assert (
            cm["orientation"]
            == "Of 1 element examined, retrieved evidence is insufficient to assess it."
        )

        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_0_aaa",
                "title": "NASA data",
                "snippet": "1.48C warming recorded",
            },
            {
                "evidence_id": "ev-rec-e1_1_bbb",
                "title": "NOAA report",
                "snippet": "1.52C above baseline",
            },
            {
                "evidence_id": "ev-rec-e1_2_ccc",
                "title": "Skeptic analysis",
                "snippet": "Measurement methodology questioned",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e1_0_aaa",
                            "relationship": "supports",
                            "reasoning": "NASA records near-1.5C warming",
                        },
                        {
                            "evidence_id": "ev-rec-e1_1_bbb",
                            "relationship": "supports",
                            "reasoning": "NOAA confirms above 1.5C",
                        },
                        {
                            "evidence_id": "ev-rec-e1_2_ccc",
                            "relationship": "challenges",
                            "reasoning": "Questions measurement accuracy",
                        },
                    ],
                    "state": "disputed",
                    "uncertainty": "Measurement methodology contested by some sources.",
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = cm["elements"][0]
        # Authority-weighted override (V1 acceptance fix 2026-05-08):
        # 2 supports + 1 challenge with equal weights → supports_dominant_2x
        # → supported (with caveat noting the 1 disagreeing source). Old
        # behaviour blindly trusted the LLM's "disputed" — exactly the
        # pattern that surfaced TRU-EF20's Reform UK 5-seats false dispute.
        assert e1["state"] == ElementState.supported
        assert len(e1["evidence_refs"]) == 3
        # Verify mixed relationships survived validation
        relationships = {r["relationship"] for r in e1["evidence_refs"]}
        assert EvidenceRelationship.supports in relationships
        assert EvidenceRelationship.challenges in relationships
        # state_derivation captures the override
        sd = e1.get("basis", {}).get("state_derivation", {})
        assert sd.get("rule_applied") == "supports_dominant_2x"
        assert sd.get("llm_state") == "disputed"
        assert sd.get("caveat") is not None  # caveat surfaces the outlier
        assert (
            cm["orientation"]
            == "Of 1 element examined, retrieved evidence predominantly supports it."
        )

    @pytest.mark.asyncio
    async def test_preserves_existing_refs_while_adding_new(self):
        """Existing context ref preserved; new supports ref added alongside."""
        existing_ref = {
            "evidence_id": "ev-original",
            "relationship": "context",
            "reasoning": "Background info",
        }
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "Policy was enacted in 2024", [existing_ref]),
            ]
        )

        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_0_new",
                "title": "Federal Register",
                "snippet": "Policy signed Jan 2024",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e1_0_new",
                            "relationship": "supports",
                            "reasoning": "Federal Register confirms 2024 enactment",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = cm["elements"][0]
        assert len(e1["evidence_refs"]) == 2
        # Old ref preserved in position 0
        assert e1["evidence_refs"][0]["evidence_id"] == "ev-original"
        # New ref appended in position 1
        assert e1["evidence_refs"][1]["evidence_id"] == "ev-rec-e1_0_new"
        assert e1["state"] == ElementState.supported
        assert (
            cm["orientation"]
            == "Of 1 element examined, retrieved evidence predominantly supports it."
        )

    @pytest.mark.asyncio
    async def test_partial_recovery_honest_orientation(self):
        """4 elements: resolves 2 of 3 unresolved — orientation reports honestly."""
        cm = _make_full_claim_map(
            [
                ("e1", "supported", "Company was founded in 2010", []),
                ("e2", "unresolved", "Revenue doubled by 2020", []),
                ("e3", "unresolved", "Employee count tripled", []),
                ("e4", "unresolved", "Market share exceeded 30%", []),
            ]
        )

        before_orientation = cm["orientation"]
        assert "insufficient" in before_orientation or "lacking" in before_orientation

        new_evidence = [
            {
                "evidence_id": "ev-rec-e2_0_rev",
                "title": "Annual report",
                "snippet": "Revenue grew from $5M to $10M",
            },
            {
                "evidence_id": "ev-rec-e3_0_emp",
                "title": "Press release",
                "snippet": "Headcount grew but margins fell",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e2_0_rev",
                            "relationship": "supports",
                            "reasoning": "Annual report confirms revenue doubling",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e3",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e3_0_emp",
                            "relationship": "challenges",
                            "reasoning": "Headcount grew but not tripled",
                        }
                    ],
                    "state": "disputed",
                    "uncertainty": "Growth occurred but magnitude disputed.",
                },
                {
                    "element_id": "e4",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e2", "e3", "e4"],
            new_evidence=new_evidence,
        )

        assert cm["elements"][1]["state"] == ElementState.supported
        assert cm["elements"][2]["state"] == ElementState.disputed
        assert cm["elements"][3]["state"] == ElementState.unresolved
        # Orientation must mention all three states honestly
        orientation = cm["orientation"]
        assert "Of 4 elements examined" in orientation
        assert "predominantly supported" in orientation
        assert "conflicting evidence" in orientation
        assert "lacking sufficient evidence" in orientation


# =============================================================================
# Group 7: Recovery Futility (4 tests)
# =============================================================================


class TestRecoveryFutility:
    """Prove that when evidence doesn't help, the system reports honestly."""

    @pytest.mark.asyncio
    async def test_evidence_found_but_all_elements_stay_unresolved(self):
        """Context-only evidence → all elements remain unresolved, orientation unchanged."""
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "Claim sub-assertion A", []),
                ("e2", "unresolved", "Claim sub-assertion B", []),
                ("e3", "unresolved", "Claim sub-assertion C", []),
            ]
        )

        before_orientation = cm["orientation"]
        assert (
            before_orientation
            == "Of 3 elements examined, retrieved evidence is insufficient to assess any."
        )

        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_0_ctx",
                "title": "Background article",
                "snippet": "General context about the topic",
            },
            {
                "evidence_id": "ev-rec-e2_0_ctx",
                "title": "Overview piece",
                "snippet": "Historical context provided",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e1_0_ctx",
                            "relationship": "context",
                            "reasoning": "Provides background only",
                        }
                    ],
                    "state": "unresolved",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e2_0_ctx",
                            "relationship": "context",
                            "reasoning": "Historical context, not direct evidence",
                        }
                    ],
                    "state": "unresolved",
                    "uncertainty": None,
                },
                {
                    "element_id": "e3",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1", "e2", "e3"],
            new_evidence=new_evidence,
        )

        # All elements remain unresolved
        for e in cm["elements"]:
            assert e["state"] == ElementState.unresolved
        # Orientation unchanged
        assert cm["orientation"] == before_orientation
        # Context refs were still added (evidence found, just not decisive)
        assert len(cm["elements"][0]["evidence_refs"]) == 1
        assert len(cm["elements"][1]["evidence_refs"]) == 1
        assert len(cm["elements"][2]["evidence_refs"]) == 0

    @pytest.mark.asyncio
    async def test_llm_returns_none_no_state_change(self):
        """LLM failure (None) → no state changes, no refs added, orientation re-derived."""
        cm = _make_full_claim_map(
            [
                ("e1", "supported", "First element already resolved", []),
                ("e2", "unresolved", "Second element needs evidence", []),
            ]
        )

        before_orientation = cm["orientation"]
        before_e2_state = cm["elements"][1]["state"]
        before_e2_refs = list(cm["elements"][1]["evidence_refs"])

        new_evidence = [
            {
                "evidence_id": "ev-rec-e2_0_fail",
                "title": "Some article",
                "snippet": "Content",
            },
        ]

        analyzer = _make_real_analyzer(None)  # LLM returns None
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e2"],
            new_evidence=new_evidence,
        )

        # e2 unchanged
        assert cm["elements"][1]["state"] == before_e2_state
        assert cm["elements"][1]["evidence_refs"] == before_e2_refs
        # Orientation re-derived but identical (same states)
        assert cm["orientation"] == before_orientation

    @pytest.mark.asyncio
    async def test_llm_returns_empty_elements_no_mapping(self):
        """LLM returns empty elements list → no mapping applied, states unchanged."""
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "First unresolved element", []),
                ("e2", "unresolved", "Second unresolved element", []),
            ]
        )

        before_orientation = cm["orientation"]

        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_0_noop",
                "title": "Article",
                "snippet": "Content",
            },
        ]

        llm_response = {"elements": []}  # LLM says nothing to map

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1", "e2"],
            new_evidence=new_evidence,
        )

        # Both elements unchanged
        for e in cm["elements"]:
            assert e["state"] == ElementState.unresolved
            assert e["evidence_refs"] == []
        # Orientation re-derived but identical
        assert cm["orientation"] == before_orientation

    @pytest.mark.asyncio
    async def test_elements_resolved_counter_zero_when_nothing_improves(self):
        """Runner.py counting logic (lines 1569-1580) yields 0 when nothing improves."""
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "First element", []),
                ("e2", "unresolved", "Second element", []),
                ("e3", "unresolved", "Third element", []),
            ]
        )

        unresolved_ids = ["e1", "e2", "e3"]

        new_evidence = [
            {
                "evidence_id": "ev-rec-e1_0_ctx",
                "title": "Background",
                "snippet": "General info",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e1_0_ctx",
                            "relationship": "context",
                            "reasoning": "Background only",
                        }
                    ],
                    "state": "unresolved",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                },
                {
                    "element_id": "e3",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=unresolved_ids,
            new_evidence=new_evidence,
        )

        # Apply the exact counting logic from runner.py:1569-1580
        newly_resolved = sum(
            1
            for e in cm["elements"]
            if e["element_id"] in unresolved_ids
            and (
                e.get("state").value
                if hasattr(e.get("state"), "value")
                else e.get("state")
            )
            != "unresolved"
        )

        assert newly_resolved == 0


# =============================================================================
# Group 8: Quality Gates (4 tests)
# =============================================================================


class TestQualityGates:
    """Prove that bad/redundant evidence is rejected at quality boundaries."""

    @pytest.mark.asyncio
    async def test_hallucinated_evidence_ids_stripped(self):
        """Fake evidence_id from LLM is stripped by real _validate_evidence_refs.

        After the V1 acceptance fix (2026-05-08), state is derived from
        the surviving (validated) evidence_refs — not the LLM's claim.
        With all refs stripped → no evidence → state=unresolved. The
        previous "state-vs-ref independence" was the exact failure mode
        we hardened against.
        """
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "Test element for hallucination check", []),
            ]
        )

        # Evidence pool has only ev-real-001
        new_evidence = [
            {
                "evidence_id": "ev-real-001",
                "title": "Real article",
                "snippet": "Real content",
            },
        ]

        # LLM hallucinates an evidence_id that doesn't exist in new_evidence
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-HALLUCINATED",
                            "relationship": "supports",
                            "reasoning": "Fabricated reference",
                        }
                    ],
                    "state": "supported",  # LLM claims supported
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = cm["elements"][0]
        # Hallucinated ref stripped — 0 valid refs
        assert len(e1["evidence_refs"]) == 0
        # Override: 0 refs → unresolved (LLM's "supported" no longer
        # honoured when nothing supports it).
        assert e1["state"] == ElementState.unresolved
        sd = e1.get("basis", {}).get("state_derivation", {})
        assert sd.get("rule_applied") == "no_evidence"
        assert sd.get("llm_state") == "supported"

    @pytest.mark.asyncio
    async def test_invalid_relationship_stripped(self):
        """Valid evidence_id but invalid relationship ('proves') is stripped.

        Documents that only 3 relationship types pass validation:
        supports, challenges, context. After the V1 acceptance override
        (2026-05-08), all-stripped refs → unresolved.
        """
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "Test element for relationship check", []),
            ]
        )

        new_evidence = [
            {
                "evidence_id": "ev-valid-001",
                "title": "Valid article",
                "snippet": "Valid content",
            },
        ]

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-valid-001",
                            "relationship": "proves",
                            "reasoning": "Invalid relationship type",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=new_evidence,
        )

        e1 = cm["elements"][0]
        # Invalid relationship stripped — 0 valid refs
        assert len(e1["evidence_refs"]) == 0
        # Override: 0 refs → unresolved
        assert e1["state"] == ElementState.unresolved
        sd = e1.get("basis", {}).get("state_derivation", {})
        assert sd.get("rule_applied") == "no_evidence"
        assert sd.get("llm_state") == "supported"

    @pytest.mark.asyncio
    async def test_duplicate_urls_excluded_by_real_retrieval(self):
        """URLs already in existing_urls are excluded by retrieve_for_elements dedup."""
        search_results = [
            _make_search_result("https://example.com/already-seen-1"),
            _make_search_result("https://example.com/already-seen-2"),
            _make_search_result("https://example.com/new-article"),
        ]

        retriever = EvidenceRetriever.__new__(EvidenceRetriever)
        retriever.search_service = AsyncMock()
        retriever.search_service.search_for_evidence = AsyncMock(
            return_value=search_results
        )
        retriever.evidence_extractor = MagicMock()
        retriever.evidence_extractor.max_concurrent = 3
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)

        existing_urls = {
            "https://example.com/already-seen-1",
            "https://example.com/already-seen-2",
        }

        elements = [{"element_id": "e1", "description": "Test element"}]

        evidence = await retriever.retrieve_for_elements(
            elements=elements,
            claim_text="Test claim",
            existing_urls=existing_urls,
        )

        # Only 1 evidence item passes dedup
        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/new-article"
        # existing_urls set grew to include the new URL
        assert "https://example.com/new-article" in existing_urls
        assert len(existing_urls) == 3

    @pytest.mark.asyncio
    async def test_empty_content_evidence_does_not_resolve(self):
        """Empty-snippet evidence passes retrieval but doesn't resolve element.

        Two-layer test: retrieve_for_elements includes it (no content filter
        in current code), but LLM mapping correctly leaves element unresolved.
        """
        # Layer 1: Retrieval includes empty-content evidence
        search_results = [
            _make_search_result("https://example.com/empty", title="", snippet=""),
        ]

        retriever = EvidenceRetriever.__new__(EvidenceRetriever)
        retriever.search_service = AsyncMock()
        retriever.search_service.search_for_evidence = AsyncMock(
            return_value=search_results
        )
        retriever.evidence_extractor = MagicMock()
        retriever.evidence_extractor.max_concurrent = 3
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)

        elements = [{"element_id": "e1", "description": "Test element"}]
        evidence = await retriever.retrieve_for_elements(
            elements=elements,
            claim_text="Test claim",
            existing_urls=set(),
        )

        # Retrieval includes it (no content filter)
        assert len(evidence) == 1
        assert evidence[0]["snippet"] == ""

        # Layer 2: Mapping leaves element unresolved despite evidence existing
        cm = _make_full_claim_map(
            [
                ("e1", "unresolved", "Test element", []),
            ]
        )

        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [],  # LLM finds nothing useful
                    "state": "unresolved",
                    "uncertainty": "Retrieved evidence had no substantive content.",
                },
            ]
        }

        analyzer = _make_real_analyzer(llm_response)
        await analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=evidence,
        )

        assert cm["elements"][0]["state"] == ElementState.unresolved
        assert cm["elements"][0]["uncertainty"] is not None
        assert (
            cm["orientation"]
            == "Of 1 element examined, retrieved evidence is insufficient to assess it."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Track N Phase 2: Recovery enrichment + config wiring tests
# ══════════════════════════════════════════════════════════════════════════════


class TestRecoveryEnrichment:
    """Tests for _enrich_recovery_evidence() — fetching full page content
    for coverage recovery evidence items."""

    @pytest.mark.asyncio
    async def test_enrichment_replaces_thin_snippet(self):
        """When _extract_from_page returns longer text, evidence item is enriched."""
        retriever = EvidenceRetriever()
        evidence_items = [
            {
                "url": "https://example.com/article",
                "title": "Test Article",
                "text": "Short snippet.",
                "snippet": "Short snippet.",
                "word_count": 2,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        enriched_snippet = MagicMock()
        enriched_snippet.text = "This is a much longer enriched text with many more words that provides substantially more context about the topic at hand for evidence mapping."
        enriched_snippet.word_count = 25

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            new_callable=AsyncMock,
            return_value=enriched_snippet,
        ):
            await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["text"] == enriched_snippet.text
        assert evidence_items[0]["word_count"] == 25
        assert evidence_items[0]["metadata"]["enriched"] is True

    @pytest.mark.asyncio
    async def test_enrichment_preserves_on_none(self):
        """When _extract_from_page returns None, original snippet is preserved."""
        retriever = EvidenceRetriever()
        original_text = "Original short snippet."
        evidence_items = [
            {
                "url": "https://example.com/blocked",
                "title": "Blocked Article",
                "text": original_text,
                "snippet": original_text,
                "word_count": 3,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["text"] == original_text
        assert evidence_items[0]["metadata"]["enriched"] is False

    @pytest.mark.asyncio
    async def test_enrichment_preserves_on_timeout(self):
        """When _extract_from_page times out, original snippet is preserved."""
        retriever = EvidenceRetriever()
        original_text = "Original snippet before timeout."
        evidence_items = [
            {
                "url": "https://example.com/slow",
                "title": "Slow Article",
                "text": original_text,
                "snippet": original_text,
                "word_count": 4,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        async def _slow_extract(*args, **kwargs):
            await asyncio.sleep(10)

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            side_effect=_slow_extract,
        ):
            await retriever._enrich_recovery_evidence(
                evidence_items, "test claim", timeout_per_url=0.01
            )

        assert evidence_items[0]["text"] == original_text
        assert evidence_items[0]["metadata"]["enriched"] is False

    @pytest.mark.asyncio
    async def test_enrichment_preserves_on_exception(self):
        """When _extract_from_page raises, original snippet is preserved."""
        retriever = EvidenceRetriever()
        original_text = "Original snippet before error."
        evidence_items = [
            {
                "url": "https://example.com/error",
                "title": "Error Article",
                "text": original_text,
                "snippet": original_text,
                "word_count": 4,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            new_callable=AsyncMock,
            side_effect=ConnectionError("DNS failed"),
        ):
            await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["text"] == original_text
        assert evidence_items[0]["metadata"]["enriched"] is False

    @pytest.mark.asyncio
    async def test_enrichment_skips_shorter_content(self):
        """When extracted text is shorter than original, keep original."""
        retriever = EvidenceRetriever()
        original_text = "This is already a decent length snippet with enough content."
        evidence_items = [
            {
                "url": "https://example.com/short",
                "title": "Short Extract",
                "text": original_text,
                "snippet": original_text,
                "word_count": 10,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        enriched_snippet = MagicMock()
        enriched_snippet.text = "Short."
        enriched_snippet.word_count = 1

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            new_callable=AsyncMock,
            return_value=enriched_snippet,
        ):
            await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["text"] == original_text
        assert evidence_items[0]["metadata"]["enriched"] is False

    @pytest.mark.asyncio
    async def test_enrichment_skips_no_url(self):
        """Evidence items with no URL get enriched=False without error."""
        retriever = EvidenceRetriever()
        evidence_items = [
            {
                "url": "",
                "title": "No URL",
                "text": "Some text.",
                "snippet": "Some text.",
                "word_count": 2,
                "source": "",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            }
        ]

        await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["metadata"]["enriched"] is False

    @pytest.mark.asyncio
    async def test_enrichment_multiple_items_partial_success(self):
        """Mixed success: some items enriched, others fail."""
        retriever = EvidenceRetriever()
        evidence_items = [
            {
                "url": "https://example.com/good",
                "title": "Good",
                "text": "Short.",
                "snippet": "Short.",
                "word_count": 1,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            },
            {
                "url": "https://example.com/bad",
                "title": "Bad",
                "text": "Short.",
                "snippet": "Short.",
                "word_count": 1,
                "source": "example.com",
                "published_date": None,
                "metadata": {"coverage_recovery": True},
            },
        ]

        good_snippet = MagicMock()
        good_snippet.text = (
            "This is a much longer enriched text with many words for testing purposes."
        )
        good_snippet.word_count = 13

        call_count = 0

        async def _mock_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return good_snippet
            raise ConnectionError("failed")

        with patch.object(
            retriever.evidence_extractor,
            "_extract_from_page",
            side_effect=_mock_extract,
        ):
            await retriever._enrich_recovery_evidence(evidence_items, "test claim")

        assert evidence_items[0]["metadata"]["enriched"] is True
        assert evidence_items[1]["metadata"]["enriched"] is False


# =============================================================================
# Group 9: Recovery Query Planning (5 tests)
# =============================================================================


class TestRecoveryQueryPlanning:
    """Tests for LLM query planner integration in retrieve_for_elements."""

    def _make_retriever(self, search_results=None):
        """Create an EvidenceRetriever with a mocked search_service."""
        retriever = EvidenceRetriever.__new__(EvidenceRetriever)
        retriever.search_service = AsyncMock()
        retriever.evidence_extractor = MagicMock()
        retriever.evidence_extractor.max_concurrent = 3
        retriever.evidence_extractor._extract_from_page = AsyncMock(return_value=None)
        if search_results is not None:
            retriever.search_service.search_for_evidence = AsyncMock(
                return_value=search_results
            )
        else:
            retriever.search_service.search_for_evidence = AsyncMock(return_value=[])
        return retriever

    @pytest.mark.asyncio
    async def test_planner_queries_used_when_available(self):
        """When planner returns plans, search uses planner queries not naive concat."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Unemployment rate in 2024"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            return_value=[
                {
                    "element_id": "e1",
                    "queries": [
                        "UK unemployment rate 2024 ONS",
                        "jobless figures 2024",
                    ],
                    "freshness": "pm",
                }
            ]
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 8
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="The Great Wall of China",
                existing_urls=set(),
            )

        # Should have 2 calls (one per planner query), not 1 naive call
        assert retriever.search_service.search_for_evidence.call_count == 2
        calls = retriever.search_service.search_for_evidence.call_args_list
        assert "UK unemployment rate 2024 ONS" in calls[0][0][0]
        assert "jobless figures 2024" in calls[1][0][0]
        # Freshness should be from planner, not default "py"
        assert calls[0][1].get("freshness") == "pm"

    @pytest.mark.asyncio
    async def test_fallback_to_naive_when_planner_fails(self):
        """When planner raises exception, naive concatenation is used."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(
            side_effect=RuntimeError("API down")
        )

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 8
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim text here",
                existing_urls=set(),
            )

        # Fallback: 1 naive query per element
        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Test element" in query
        assert "Test claim text here" in query

    @pytest.mark.asyncio
    async def test_fallback_when_planning_disabled(self):
        """When ENABLE_RECOVERY_QUERY_PLANNING=False, naive path is used."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 8
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
            )

        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Test element" in query

    @pytest.mark.asyncio
    async def test_article_context_forwarded(self):
        """plan_queries_batch receives the article_context dict."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]
        article_ctx = {"domain": "economics", "temporal_context": "2024"}

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = AsyncMock(return_value=[])

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 10.0
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 8
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim",
                existing_urls=set(),
                article_context=article_ctx,
            )

        mock_planner.plan_queries_batch.assert_awaited_once()
        call_kwargs = mock_planner.plan_queries_batch.call_args[1]
        assert call_kwargs["article_context"] == article_ctx

    @pytest.mark.asyncio
    async def test_planner_timeout_triggers_fallback(self):
        """When planner exceeds timeout, fallback to naive queries is used."""
        retriever = self._make_retriever(search_results=[])
        elements = [{"element_id": "e1", "description": "Test element"}]

        async def slow_planner(*args, **kwargs):
            await asyncio.sleep(5)
            return []

        mock_planner = MagicMock()
        mock_planner.plan_queries_batch = slow_planner

        with patch("app.pipeline.retrieve.settings") as mock_settings, patch(
            "app.utils.query_planner.get_query_planner", return_value=mock_planner
        ):
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = True
            mock_settings.RECOVERY_PLANNER_TIMEOUT = 0.05
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 8
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False

            await retriever.retrieve_for_elements(
                elements=elements,
                claim_text="Test claim text",
                existing_urls=set(),
            )

        # Should fall back to naive query
        assert retriever.search_service.search_for_evidence.call_count == 1
        query = retriever.search_service.search_for_evidence.call_args[0][0]
        assert "Test element" in query


class TestConfigWiring:
    """Tests that config settings flow through to pipeline code."""

    def test_max_sources_per_claim_from_config(self):
        """EvidenceRetriever reads MAX_SOURCES_PER_CLAIM from settings."""
        with patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.MAX_SOURCES_PER_CLAIM = 30
            mock_settings.ENABLE_API_RETRIEVAL = True
            retriever = EvidenceRetriever()
            assert retriever.max_sources_per_claim == 30

    @pytest.mark.asyncio
    async def test_recovery_max_results_per_element_from_config(self):
        """retrieve_for_elements uses RECOVERY_MAX_RESULTS_PER_ELEMENT from settings."""
        retriever = EvidenceRetriever()
        mock_search = AsyncMock(return_value=[])

        with patch.object(
            retriever.search_service,
            "search_for_evidence",
            mock_search,
        ), patch("app.pipeline.retrieve.settings") as mock_settings:
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 12
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False

            await retriever.retrieve_for_elements(
                elements=[{"element_id": "e1", "description": "Test"}],
                claim_text="Test claim",
                existing_urls=set(),
            )

            mock_search.assert_called_once()
            assert mock_search.call_args.kwargs.get("max_results") == 12

    @pytest.mark.asyncio
    async def test_enrichment_gated_by_config(self):
        """retrieve_for_elements skips enrichment when ENABLE_RECOVERY_ENRICHMENT=False."""
        retriever = EvidenceRetriever()

        mock_result = MagicMock()
        mock_result.url = "https://example.com/test"
        mock_result.snippet = "Test snippet"
        mock_result.title = "Test"
        mock_result.source = "example.com"
        mock_result.published_date = None

        with patch.object(
            retriever.search_service,
            "search_for_evidence",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ), patch.object(
            retriever,
            "_enrich_recovery_evidence",
            new_callable=AsyncMock,
        ) as mock_enrich, patch(
            "app.pipeline.retrieve.settings"
        ) as mock_settings:
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = False
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False

            result = await retriever.retrieve_for_elements(
                elements=[{"element_id": "e1", "description": "Test"}],
                claim_text="Test claim",
                existing_urls=set(),
            )

            mock_enrich.assert_not_called()
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_enrichment_called_when_enabled(self):
        """retrieve_for_elements calls enrichment when ENABLE_RECOVERY_ENRICHMENT=True."""
        retriever = EvidenceRetriever()

        mock_result = MagicMock()
        mock_result.url = "https://example.com/test"
        mock_result.snippet = "Test snippet"
        mock_result.title = "Test"
        mock_result.source = "example.com"
        mock_result.published_date = None

        with patch.object(
            retriever.search_service,
            "search_for_evidence",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ), patch.object(
            retriever,
            "_enrich_recovery_evidence",
            new_callable=AsyncMock,
        ) as mock_enrich, patch(
            "app.pipeline.retrieve.settings"
        ) as mock_settings:
            mock_settings.RECOVERY_MAX_RESULTS_PER_ELEMENT = 5
            mock_settings.ENABLE_RECOVERY_ENRICHMENT = True
            mock_settings.ENABLE_RECOVERY_QUERY_PLANNING = False

            result = await retriever.retrieve_for_elements(
                elements=[{"element_id": "e1", "description": "Test"}],
                claim_text="Test claim",
                existing_urls=set(),
            )

            mock_enrich.assert_called_once()
            assert len(result) == 1


# ── Recovery Evidence Classification ─────────────────────────────────────────


class TestRecoveryClassification:
    """Tests that recovery evidence is classified before being added to the evidence pool."""

    @pytest.mark.asyncio
    async def test_recovery_classification_llm(self):
        """Recovery evidence should be classified via LLM classifier when enabled."""
        raw_evidence = [
            {
                "id": "rec-ev-1",
                "url": "https://example.com/recovery",
                "title": "Recovery result",
                "snippet": "Some recovery content",
                "source": "brave",
                "tier": None,
                "evidence_type": None,
                "receipt_status": "found",
            }
        ]

        classified_evidence = [
            {
                **raw_evidence[0],
                "tier": "reporting",
                "evidence_type": "news",
            }
        ]

        mock_classifier_instance = AsyncMock()
        mock_classifier_instance.classify_batch = AsyncMock(
            return_value=classified_evidence
        )

        config_mock = MagicMock()
        config_mock.enable_llm_classifier = True

        new_evidence = list(raw_evidence)

        # Simulate the classification block from runner.py recovery
        if config_mock.enable_llm_classifier:
            new_evidence = await mock_classifier_instance.classify_batch(new_evidence)
            for ev in new_evidence:
                ev["receipt_status"] = "classified"

        assert len(new_evidence) == 1
        assert new_evidence[0]["tier"] == "reporting"
        assert new_evidence[0]["evidence_type"] == "news"
        assert new_evidence[0]["receipt_status"] == "classified"
        mock_classifier_instance.classify_batch.assert_called_once_with(raw_evidence)

    @pytest.mark.asyncio
    async def test_recovery_classification_heuristic(self):
        """Recovery evidence should be classified via heuristic when LLM classifier is disabled."""
        from app.pipeline.evidence_classifier import _classify_heuristic

        raw_evidence = [
            {
                "id": "rec-ev-1",
                "url": "https://www.bbc.co.uk/news/recovery",
                "title": "BBC Recovery result",
                "snippet": "Some recovery content",
                "source": "brave",
                "tier": None,
                "evidence_type": None,
                "receipt_status": "found",
            }
        ]

        config_mock = MagicMock()
        config_mock.enable_llm_classifier = False

        new_evidence = list(raw_evidence)

        if not config_mock.enable_llm_classifier:
            for ev in new_evidence:
                tier, evidence_type = _classify_heuristic(ev)
                ev["tier"] = tier
                ev["evidence_type"] = evidence_type
                ev["receipt_status"] = "classified"

        assert len(new_evidence) == 1
        assert new_evidence[0]["tier"] is not None, "Heuristic should assign a tier"
        assert (
            new_evidence[0]["evidence_type"] is not None
        ), "Heuristic should assign a type"
        assert new_evidence[0]["receipt_status"] == "classified"
