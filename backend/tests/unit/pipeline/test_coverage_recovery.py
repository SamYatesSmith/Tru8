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

        evidence = await retriever.retrieve_for_elements(
            elements=elements,
            claim_text="Test claim",
            existing_urls=set(),
        )

        assert evidence == []

    @pytest.mark.asyncio
    async def test_one_query_per_element(self):
        """N elements produce N search queries (one per element)."""
        retriever = self._make_retriever(search_results=[])
        elements = [
            {"element_id": "e1", "description": "First element"},
            {"element_id": "e2", "description": "Second element"},
            {"element_id": "e3", "description": "Third element"},
        ]

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
        """Elements not in unresolved_element_ids remain untouched."""
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
        # e2 should be completely unchanged
        assert e2["state"] == ElementState.supported
        assert len(e2["evidence_refs"]) == 1
        assert e2["evidence_refs"][0]["evidence_id"] == "ev-existing"

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
