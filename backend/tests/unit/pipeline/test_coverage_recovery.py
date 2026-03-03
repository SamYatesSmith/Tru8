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
        assert "unresolved" in before_orientation

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
            cm["orientation"] == "All 3 required elements are evidentially supported."
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

        assert "unresolved" in cm["orientation"]

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
        # Orientation mentions disputed, not unresolved
        assert "disputed" in cm["orientation"]
        assert "unresolved" not in cm["orientation"]

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
            == "The single required element is evidentially unresolved."
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
        assert e1["state"] == ElementState.disputed
        assert len(e1["evidence_refs"]) == 3
        # Verify mixed relationships survived validation
        relationships = {r["relationship"] for r in e1["evidence_refs"]}
        assert EvidenceRelationship.supports in relationships
        assert EvidenceRelationship.challenges in relationships
        assert (
            cm["orientation"] == "The single required element is evidentially disputed."
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
            == "The single required element is evidentially supported."
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
        assert "unresolved" in before_orientation

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
        assert "2 of 4" in orientation
        assert "supported" in orientation
        assert "disputed" in orientation
        assert "unresolved" in orientation


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
            before_orientation == "All 3 required elements are evidentially unresolved."
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

        Documents state-vs-ref independence: LLM-assigned state persists even
        when all evidence refs are invalid (claim_map_analyzer.py:857-861).
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
        # State still set by LLM (state-vs-ref independence)
        assert e1["state"] == ElementState.supported

    @pytest.mark.asyncio
    async def test_invalid_relationship_stripped(self):
        """Valid evidence_id but invalid relationship ('proves') is stripped.

        Documents that only 3 relationship types pass validation:
        supports, challenges, context.
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
        # State still set by LLM (state-vs-ref independence)
        assert e1["state"] == ElementState.supported

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
            == "The single required element is evidentially unresolved."
        )
