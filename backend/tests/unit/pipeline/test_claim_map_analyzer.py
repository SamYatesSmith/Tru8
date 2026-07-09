"""Tests for PR-B02: ClaimMapAnalyzer and derive_orientation.

Covers:
- Decomposition (Phase 1): scaffold shape, element cap, IDs, claim type, fallback
- Evidence mapping (Phase 2): refs populated, valid relationships, hallucination strip,
  states assigned, metadata set
- Orientation derivation: unanimous, majority, mixed, single element, all-state combos
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.claim_map import (
    ClaimElement,
    ClaimMap,
    ClaimMapMetadata,
    ClaimType,
    ElementState,
    EvidenceRelationship,
)
from app.pipeline.claim_map_analyzer import (
    ClaimMapAnalyzer,
    derive_orientation,
    compute_orientation_basis,
    _compute_element_basis,
    _derive_element_state_with_authority,
)


# ── Fixtures / helpers ──────────────────────────────────────────────────────


def _make_google_response(payload: dict) -> MagicMock:
    """Build a fake httpx response matching Google Gemini JSON shape."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]
    }
    return resp


def _make_openai_response(payload: dict) -> MagicMock:
    """Build a fake httpx response matching OpenAI chat completions shape."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return resp


def _make_decomposition_payload(
    normalised: str = "Test claim normalised",
    claim_type: str = "empirical",
    elements: list | None = None,
) -> dict:
    if elements is None:
        elements = [
            {"description": "Element one must hold"},
            {"description": "Element two must hold"},
            {"description": "Element three must hold"},
        ]
    return {
        "normalised_claim": normalised,
        "claim_type": claim_type,
        "elements": elements,
    }


def _make_mapping_payload(element_ids: list[str], evidence_ids: list[str]) -> dict:
    """Build a mapping response for given element IDs using provided evidence IDs."""
    elements = []
    for eid in element_ids:
        refs = [
            {"evidence_id": ev_id, "relationship": "supports"}
            for ev_id in evidence_ids[:2]
        ]
        elements.append(
            {
                "element_id": eid,
                "evidence_refs": refs,
                "state": "supported",
                "uncertainty": None,
            }
        )
    return {"elements": elements}


def _make_evidence_list(count: int = 3) -> list[dict]:
    return [
        {
            "evidence_id": f"ev{i}",
            "title": f"Evidence {i}",
            "snippet": f"Snippet content for evidence {i}",
            "url": f"http://example.com/{i}",
        }
        for i in range(1, count + 1)
    ]


def _make_partial_claim_map(num_elements: int = 3) -> ClaimMap:
    """Build a partial ClaimMap (post-decomposition, pre-mapping)."""
    elements = [
        ClaimElement(
            element_id=f"e{i}",
            description=f"Element {i} description",
            evidence_refs=[],
            state=None,
            uncertainty=None,
        )
        for i in range(1, num_elements + 1)
    ]
    return ClaimMap(
        claim_id="test-claim-1",
        normalised_claim="Test claim normalised",
        claim_type=ClaimType.empirical,
        elements=elements,
        orientation=None,
        metadata=ClaimMapMetadata(
            decomposition_model="gpt-4o",
            mapping_model=None,
            element_count=num_elements,
            completed_at=None,
        ),
    )


# ── Decomposition tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDecomposition:

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_returns_valid_scaffold(self, mock_client_cls):
        """Phase 1 output has correct shape: claim_id, elements, no evidence_refs."""
        payload = _make_decomposition_payload()
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Some claim", "c1")

        assert result["claim_id"] == "c1"
        assert result["normalised_claim"] == "Test claim normalised"
        assert result["claim_type"] == ClaimType.empirical
        assert len(result["elements"]) == 3
        assert result["orientation"] is None
        # All evidence_refs should be empty
        for elem in result["elements"]:
            assert elem["evidence_refs"] == []
            assert elem["state"] is None

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_element_count_cap(self, mock_client_cls):
        """LLM returns 7 elements, code caps to MAX_ELEMENTS_PER_CLAIM (5)."""
        elements = [{"description": f"Element {i}"} for i in range(7)]
        payload = _make_decomposition_payload(elements=elements)
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Overcrowded claim", "c2")

        assert len(result["elements"]) <= 5

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_single_element_valid(self, mock_client_cls):
        """1 element is acceptable for atomic claims."""
        payload = _make_decomposition_payload(
            elements=[{"description": "Single atomic assertion"}]
        )
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Atomic claim", "c3")

        assert len(result["elements"]) == 1
        assert result["elements"][0]["element_id"] == "e1"

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_claim_type_enum(self, mock_client_cls):
        """Only valid ClaimType values are accepted; invalid falls back to empirical."""
        payload = _make_decomposition_payload(claim_type="causal_interpretive")
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Causal claim", "c4")
        assert result["claim_type"] == ClaimType.causal_interpretive

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_invalid_claim_type_defaults(self, mock_client_cls):
        """Invalid claim_type from LLM falls back to empirical."""
        payload = _make_decomposition_payload(claim_type="made_up_type")
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Bad type claim", "c5")
        assert result["claim_type"] == ClaimType.empirical

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_element_ids_sequential(self, mock_client_cls):
        """Element IDs are e1, e2, e3 in order."""
        payload = _make_decomposition_payload()
        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Sequential claim", "c6")

        ids = [e["element_id"] for e in result["elements"]]
        assert ids == ["e1", "e2", "e3"]

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_decompose_fallback_on_parse_error(self, mock_client_cls):
        """Bad JSON from LLM triggers single-element fallback."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "not valid json {{{"}]}}]
        }
        mock_client = AsyncMock()
        mock_client.post.return_value = resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.decompose_claim("Bad JSON claim", "c7")

        assert len(result["elements"]) == 1
        assert result["elements"][0]["element_id"] == "e1"
        assert result["claim_type"] == ClaimType.empirical
        assert result["metadata"]["decomposition_model"] == "fallback"


# ── Evidence mapping tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEvidenceMapping:

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_map_evidence_populates_refs(self, mock_client_cls):
        """evidence_refs are populated with valid IDs after mapping."""
        claim_map = _make_partial_claim_map(2)
        evidence = _make_evidence_list(3)
        mapping_payload = _make_mapping_payload(["e1", "e2"], ["ev1", "ev2"])

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(mapping_payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.map_evidence_to_elements(claim_map, evidence)

        for elem in result["elements"]:
            assert len(elem["evidence_refs"]) > 0
            for ref in elem["evidence_refs"]:
                assert ref["evidence_id"] in {"ev1", "ev2"}

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_map_evidence_valid_relationships(self, mock_client_cls):
        """Only supports/challenges/context relationships are kept."""
        mapping_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev1", "relationship": "supports"},
                        {"evidence_id": "ev2", "relationship": "challenges"},
                        {"evidence_id": "ev3", "relationship": "context"},
                    ],
                    "state": "disputed",
                    "uncertainty": None,
                }
            ]
        }
        claim_map = _make_partial_claim_map(1)
        evidence = _make_evidence_list(3)

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(mapping_payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.map_evidence_to_elements(claim_map, evidence)

        rels = {ref["relationship"] for ref in result["elements"][0]["evidence_refs"]}
        assert rels <= {
            EvidenceRelationship.supports,
            EvidenceRelationship.challenges,
            EvidenceRelationship.context,
        }

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_map_evidence_no_hallucinated_ids(self, mock_client_cls):
        """Evidence IDs not in the input list are stripped."""
        mapping_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev1", "relationship": "supports"},
                        {"evidence_id": "hallucinated_99", "relationship": "supports"},
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ]
        }
        claim_map = _make_partial_claim_map(1)
        evidence = _make_evidence_list(3)

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(mapping_payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.map_evidence_to_elements(claim_map, evidence)

        ref_ids = {ref["evidence_id"] for ref in result["elements"][0]["evidence_refs"]}
        assert "hallucinated_99" not in ref_ids
        assert "ev1" in ref_ids

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_map_evidence_assigns_states(self, mock_client_cls):
        """All elements get a state after mapping."""
        claim_map = _make_partial_claim_map(2)
        evidence = _make_evidence_list(2)
        mapping_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev1", "relationship": "supports"}
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {"evidence_id": "ev2", "relationship": "challenges"}
                    ],
                    "state": "disputed",
                    "uncertainty": "Conflicting sources found.",
                },
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(mapping_payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.map_evidence_to_elements(claim_map, evidence)

        assert result["elements"][0]["state"] == ElementState.supported
        assert result["elements"][1]["state"] == ElementState.disputed

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_map_evidence_sets_metadata(self, mock_client_cls):
        """mapping_model, element_count, completed_at are set after mapping."""
        claim_map = _make_partial_claim_map(2)
        evidence = _make_evidence_list(2)
        mapping_payload = _make_mapping_payload(["e1", "e2"], ["ev1", "ev2"])

        mock_client = AsyncMock()
        mock_client.post.return_value = _make_google_response(mapping_payload)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        analyzer = ClaimMapAnalyzer()
        result = await analyzer.map_evidence_to_elements(claim_map, evidence)

        meta = result["metadata"]
        assert meta["mapping_model"] is not None
        assert meta["element_count"] == 2
        assert meta["completed_at"] is not None


# ── derive_orientation tests (synchronous, pure function) ───────────────────


class TestDeriveOrientation:

    def test_single_element(self):
        elements = [
            ClaimElement(
                element_id="e1",
                description="Only one",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence predominantly supports it."
        )

    def test_unanimous_supported(self):
        elements = [
            ClaimElement(
                element_id=f"e{i}",
                description=f"Elem {i}",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            )
            for i in range(1, 4)
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 3 elements examined, retrieved evidence predominantly supports all 3."
        )

    def test_unanimous_disputed(self):
        elements = [
            ClaimElement(
                element_id=f"e{i}",
                description=f"Elem {i}",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            )
            for i in range(1, 3)
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 2 elements examined, retrieved evidence both supports and conflicts with all 2."
        )

    def test_unanimous_disputed_challenges_only(self):
        """2026-07-09: disputed elements whose refs are all challenges (zero
        supports) must not render as "both supports and conflicts" — that
        manufactures false balance on a one-sided record (TRU-D64E-0520)."""
        elements = [
            ClaimElement(
                element_id=f"e{i}",
                description=f"Elem {i}",
                evidence_refs=[
                    {
                        "evidence_id": f"ev-{i}a",
                        "relationship": "challenges",
                        "reasoning": None,
                    },
                    {
                        "evidence_id": f"ev-{i}b",
                        "relationship": "context",
                        "reasoning": None,
                    },
                ],
                state=ElementState.disputed,
                uncertainty=None,
            )
            for i in range(1, 4)
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 3 elements examined, retrieved evidence challenges all 3, with none supporting."
        )

    def test_single_disputed_challenges_only(self):
        elements = [
            ClaimElement(
                element_id="e1",
                description="Only one",
                evidence_refs=[
                    {
                        "evidence_id": "ev-1",
                        "relationship": "challenges",
                        "reasoning": None,
                    }
                ],
                state=ElementState.disputed,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence challenges it, with none supporting."
        )

    def test_disputed_with_both_sides_keeps_original_phrase(self):
        """Regression: a genuinely split disputed element keeps the
        "both supports and conflicts" phrasing."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="Split",
                evidence_refs=[
                    {
                        "evidence_id": "ev-1",
                        "relationship": "supports",
                        "reasoning": None,
                    },
                    {
                        "evidence_id": "ev-2",
                        "relationship": "challenges",
                        "reasoning": None,
                    },
                ],
                state=ElementState.disputed,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence both supports and conflicts with it."
        )

    def test_disputed_with_empty_refs_keeps_original_phrase(self):
        """Regression: disputed with no refs at all (shouldn't occur under the
        mechanical state rule, but LLM states can persist) is left as-is."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="No refs",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence both supports and conflicts with it."
        )

    def test_mixed_supported_and_challenges_only(self):
        """Listing branch uses the challenges-only item phrase."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[
                    {
                        "evidence_id": "ev-1",
                        "relationship": "challenges",
                        "reasoning": None,
                    }
                ],
                state=ElementState.disputed,
                uncertainty=None,
            ),
        ]
        result = derive_orientation(elements)
        assert "1 predominantly supported" in result
        assert "1 challenged with none supporting" in result

    def test_enum_relationship_values_also_detected(self):
        """EvidenceRelationship enum members (not just plain strings) count."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="Enum refs",
                evidence_refs=[
                    {
                        "evidence_id": "ev-1",
                        "relationship": EvidenceRelationship.challenges,
                        "reasoning": None,
                    }
                ],
                state=ElementState.disputed,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence challenges it, with none supporting."
        )

    def test_unanimous_unresolved(self):
        elements = [
            ClaimElement(
                element_id=f"e{i}",
                description=f"Elem {i}",
                evidence_refs=[],
                state=ElementState.unresolved,
                uncertainty=None,
            )
            for i in range(1, 5)
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 4 elements examined, retrieved evidence is insufficient to assess any."
        )

    def test_unanimous_contextual(self):
        # 2026-05-12: contextual state has its own unanimous phrasing —
        # honest about having related evidence without claiming
        # substantiation. Distinct from "insufficient to assess".
        elements = [
            ClaimElement(
                element_id=f"e{i}",
                description=f"Elem {i}",
                evidence_refs=[],
                state=ElementState.contextual,
                uncertainty=None,
            )
            for i in range(1, 4)
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 3 elements examined, retrieved evidence provides context for all without directly substantiating."
        )

    def test_single_contextual(self):
        elements = [
            ClaimElement(
                element_id="e1",
                description="Only one",
                evidence_refs=[],
                state=ElementState.contextual,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        assert (
            result
            == "Of 1 element examined, retrieved evidence provides context for it without directly substantiating."
        )

    def test_mixed_with_contextual(self):
        # 1 supported, 1 contextual, 1 unresolved — orientation must
        # enumerate the distinct buckets with their own phrasing.
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[],
                state=ElementState.contextual,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e3",
                description="C",
                evidence_refs=[],
                state=ElementState.unresolved,
                uncertainty=None,
            ),
        ]
        result = derive_orientation(elements)
        assert "Of 3 elements examined" in result
        # Tied 3-way → "evidence is mixed:" template.
        assert "1 predominantly supported" in result
        assert "1 informed by contextual evidence" in result
        assert "1 lacking sufficient evidence" in result

    def test_majority_supported(self):
        """2 of 3 supported, 1 disputed → majority template."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e3",
                description="C",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            ),
        ]
        result = derive_orientation(elements)
        assert "Of 3 elements examined" in result
        assert "2 predominantly supported" in result
        assert "1 with conflicting evidence" in result

    def test_majority_unresolved(self):
        """2 of 4 unresolved, 1 supported, 1 disputed → majority template."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e3",
                description="C",
                evidence_refs=[],
                state=ElementState.unresolved,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e4",
                description="D",
                evidence_refs=[],
                state=ElementState.unresolved,
                uncertainty=None,
            ),
        ]
        result = derive_orientation(elements)
        assert "Of 4 elements examined" in result
        assert "2 lacking sufficient evidence" in result

    def test_mixed_no_majority(self):
        """1 of each state → 'Evidence is mixed' template."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e3",
                description="C",
                evidence_refs=[],
                state=ElementState.unresolved,
                uncertainty=None,
            ),
        ]
        result = derive_orientation(elements)
        assert result.startswith("Of 3 elements examined, evidence is mixed:")
        assert "1 predominantly supported" in result
        assert "1 with conflicting evidence" in result
        assert "1 lacking sufficient evidence" in result

    @pytest.mark.parametrize("state", list(ElementState))
    def test_single_element_all_states(self, state):
        """Single element with each state produces correct template."""
        expected_phrases = {
            "supported": "predominantly supports it",
            "disputed": "both supports and conflicts with it",
            "unresolved": "is insufficient to assess it",
            "contextual": "provides context for it without directly substantiating",
        }
        elements = [
            ClaimElement(
                element_id="e1",
                description="Only",
                evidence_refs=[],
                state=state,
                uncertainty=None,
            )
        ]
        result = derive_orientation(elements)
        phrase = expected_phrases[state.value]
        assert result == f"Of 1 element examined, retrieved evidence {phrase}."

    def test_empty_elements(self):
        assert derive_orientation([]) == "No elements to assess."

    def test_deterministic(self):
        """Same input always produces same output."""
        elements = [
            ClaimElement(
                element_id="e1",
                description="A",
                evidence_refs=[],
                state=ElementState.supported,
                uncertainty=None,
            ),
            ClaimElement(
                element_id="e2",
                description="B",
                evidence_refs=[],
                state=ElementState.disputed,
                uncertainty=None,
            ),
        ]
        r1 = derive_orientation(elements)
        r2 = derive_orientation(elements)
        assert r1 == r2


# ── Prompt regression tests ───────────────────────────────────────────────


class TestMappingPromptRules:
    """Ensure critical mapping rules aren't accidentally removed."""

    def test_mapping_prompt_contains_data_provenance_rule(self):
        from app.pipeline.claim_map_analyzer import MAPPING_PROMPT

        assert "DATA PROVENANCE" in MAPPING_PROMPT

    def test_mapping_prompt_contains_topic_vs_figure_rule(self):
        from app.pipeline.claim_map_analyzer import MAPPING_PROMPT

        assert "TOPIC vs FIGURE" in MAPPING_PROMPT

    def test_batch_mapping_prompt_contains_data_provenance_rule(self):
        from app.pipeline.claim_map_analyzer import BATCH_MAPPING_PROMPT

        assert "DATA PROVENANCE" in BATCH_MAPPING_PROMPT

    def test_batch_mapping_prompt_contains_topic_vs_figure_rule(self):
        from app.pipeline.claim_map_analyzer import BATCH_MAPPING_PROMPT

        assert "TOPIC vs FIGURE" in BATCH_MAPPING_PROMPT


# ── PQ-07: content_basis_breakdown in element basis ───────────────────────


class TestContentBasisBreakdown:
    """PQ-07: _compute_element_basis includes content_basis_breakdown."""

    def test_content_basis_breakdown_populated(self):
        """content_basis_breakdown counts by basis type."""
        evidence_list = [
            {"evidence_id": "ev-1", "tier": "primary", "content_basis": "full"},
            {"evidence_id": "ev-2", "tier": "reporting", "content_basis": "snippet"},
            {"evidence_id": "ev-3", "tier": "reporting", "content_basis": "snippet"},
        ]
        elem = {
            "evidence_refs": [
                {"evidence_id": "ev-1", "relationship": "supports"},
                {"evidence_id": "ev-2", "relationship": "supports"},
                {"evidence_id": "ev-3", "relationship": "context"},
            ]
        }
        basis = _compute_element_basis(elem, evidence_list)
        assert basis["content_basis_breakdown"] == {"full": 1, "snippet": 2}

    def test_content_basis_breakdown_empty_refs(self):
        """Elements with no evidence get empty content_basis_breakdown."""
        elem = {"evidence_refs": []}
        basis = _compute_element_basis(elem, [])
        assert basis["content_basis_breakdown"] == {}

    def test_content_basis_breakdown_api_and_pdf(self):
        """API and PDF basis types are counted correctly."""
        evidence_list = [
            {"evidence_id": "ev-1", "content_basis": "api"},
            {"evidence_id": "ev-2", "content_basis": "pdf"},
            {"evidence_id": "ev-3", "content_basis": "api"},
        ]
        elem = {
            "evidence_refs": [
                {"evidence_id": "ev-1", "relationship": "supports"},
                {"evidence_id": "ev-2", "relationship": "supports"},
                {"evidence_id": "ev-3", "relationship": "context"},
            ]
        }
        basis = _compute_element_basis(elem, evidence_list)
        assert basis["content_basis_breakdown"] == {"api": 2, "pdf": 1}

    def test_content_basis_breakdown_missing_field(self):
        """Evidence without content_basis is excluded from breakdown."""
        evidence_list = [
            {"evidence_id": "ev-1", "content_basis": "full"},
            {"evidence_id": "ev-2"},  # no content_basis
        ]
        elem = {
            "evidence_refs": [
                {"evidence_id": "ev-1", "relationship": "supports"},
                {"evidence_id": "ev-2", "relationship": "supports"},
            ]
        }
        basis = _compute_element_basis(elem, evidence_list)
        assert basis["content_basis_breakdown"] == {"full": 1}


# ── Authority-weighted state derivation (V1 acceptance fix 2026-05-08) ──────


class TestDeriveElementStateWithAuthority:
    """Tier-weighted majority rule that overrides the LLM mapper's state.

    Reason for fix: TRU-EF20 (UK election 2024) showed Statista's outlier
    'Reform UK won 4 seats' marking the element disputed despite Royal
    Holloway, Wikipedia, Commons Library all stating 5 seats. The LLM
    mapper was binary: any 'challenges' relationship → state=disputed.
    The fix counts evidence_refs by relationship and weighs by source
    tier (primary=3, reporting=2, commentary=1).
    """

    def _evi(self, evidence_id, tier):
        return {"evidence_id": evidence_id, "tier": tier}

    def _ref(self, evidence_id, relationship):
        return {"evidence_id": evidence_id, "relationship": relationship}

    def test_no_evidence_returns_unresolved(self):
        elem = {"evidence_refs": []}
        state, basis = _derive_element_state_with_authority(elem, [])
        assert state == ElementState.unresolved
        assert basis["rule_applied"] == "no_evidence"
        assert basis["caveat"] is None

    def test_only_supports_returns_supported(self):
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "supports"),
            ]
        }
        evi = [self._evi("ev-1", "primary"), self._evi("ev-2", "reporting")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert basis["rule_applied"] == "all_supports"
        assert basis["caveat"] is None

    def test_only_challenges_returns_disputed(self):
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "challenges"),
            ]
        }
        evi = [self._evi("ev-1", "primary")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "all_challenges"

    def test_one_primary_support_one_commentary_challenge_supports_dominant(
        self,
    ):
        # Layer 2 — tier weighting protects against single low-authority
        # outliers. 1 primary support (weight 3) vs 1 commentary
        # challenge (weight 1) → 3 ≥ 2*1 → supported with caveat.
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "challenges"),
            ]
        }
        evi = [
            self._evi("ev-1", "primary"),
            {
                "evidence_id": "ev-2",
                "tier": "commentary",
                "url": "https://outlier.example/x",
            },
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert basis["rule_applied"] == "supports_dominant_2x"
        assert basis["weighted_supports"] == 3
        assert basis["weighted_challenges"] == 1
        assert basis["caveat"] is not None
        assert "outlier.example" in basis["caveat"]

    def test_two_primary_supports_one_primary_challenge_supports_dominant(
        self,
    ):
        # 2 primary supports (6) vs 1 primary challenge (3) → 6 ≥ 2*3 → supported.
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "supports"),
                self._ref("ev-3", "challenges"),
            ]
        }
        evi = [
            self._evi("ev-1", "primary"),
            self._evi("ev-2", "primary"),
            {"evidence_id": "ev-3", "tier": "primary", "url": "https://statista.com/x"},
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.supported
        assert basis["weighted_supports"] == 6
        assert basis["weighted_challenges"] == 3
        assert basis["caveat"] is not None
        assert "statista.com" in basis["caveat"]

    def test_one_one_same_tier_close_split_disputed(self):
        # TRU-EF20 Reform UK / Royal Holloway vs Statista — both
        # primary tier, weights 3 vs 3. Neither rule fires → close_split
        # → disputed. This is the case Layer 1+2 alone cannot fix; needs
        # Layer 3 (mapping efficiency) to surface more supports.
        elem = {
            "evidence_refs": [
                self._ref("ev-rh", "supports"),
                self._ref("ev-stat", "challenges"),
            ]
        }
        evi = [
            self._evi("ev-rh", "primary"),
            self._evi("ev-stat", "primary"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "close_split"
        # Caveat surfaces the breakdown so UI can render mixed-evidence
        assert basis["caveat"] is not None
        assert "mixed" in basis["caveat"].lower()

    def test_three_challenges_one_support_disputed(self):
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "challenges"),
                self._ref("ev-3", "challenges"),
                self._ref("ev-4", "challenges"),
            ]
        }
        evi = [
            self._evi("ev-1", "commentary"),  # 1
            self._evi("ev-2", "primary"),  # 3
            self._evi("ev-3", "primary"),  # 3
            self._evi("ev-4", "primary"),  # 3
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.disputed
        assert basis["rule_applied"] == "challenges_dominant_2x"
        assert basis["weighted_supports"] == 1
        assert basis["weighted_challenges"] == 9

    def test_context_only_returns_contextual(self):
        # 2026-05-12: context-only evidence is now its own state — pre-fix
        # this conflated with "unresolved" / "no_evidence" rule, hiding
        # the fact that related evidence was actually mapped to the
        # element. The new "contextual" state surfaces this distinction
        # in the UI (sky-blue badge, distinct from grey unresolved).
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "context"),
                self._ref("ev-2", "context"),
            ]
        }
        evi = [self._evi("ev-1", "primary"), self._evi("ev-2", "reporting")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        assert state == ElementState.contextual
        assert basis["rule_applied"] == "context_only"
        assert basis["context_count"] == 2
        assert basis["supports_count"] == 0
        assert basis["challenges_count"] == 0
        assert basis["caveat"] is None

    def test_truly_empty_returns_unresolved(self):
        # Pinned 2026-05-12: a refs list with ZERO context entries (and
        # zero supports/challenges) is the only state that maps to
        # unresolved + rule_applied="no_evidence". Context-only inputs
        # now route to contextual (see test above).
        elem = {"evidence_refs": []}
        state, basis = _derive_element_state_with_authority(elem, [])
        assert state == ElementState.unresolved
        assert basis["rule_applied"] == "no_evidence"
        assert basis["context_count"] == 0
        assert basis["supports_count"] == 0
        assert basis["challenges_count"] == 0

    def test_context_does_not_count_toward_supports(self):
        # Mixed: 1 support, 1 challenge, 2 context. Context excluded
        # from the support/challenge counts.
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "challenges"),
                self._ref("ev-3", "context"),
                self._ref("ev-4", "context"),
            ]
        }
        evi = [
            self._evi("ev-1", "primary"),
            self._evi("ev-2", "primary"),
            self._evi("ev-3", "reporting"),
            self._evi("ev-4", "commentary"),
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        # 1v1 same tier → close split
        assert state == ElementState.disputed
        assert basis["supports_count"] == 1
        assert basis["challenges_count"] == 1
        assert basis["context_count"] == 2

    def test_unknown_evidence_id_falls_back_to_weight_one(self):
        # Defensive: if the mapper somehow refs an evidence_id we can't
        # resolve, weight=1 (treat as commentary). Don't crash.
        elem = {
            "evidence_refs": [
                self._ref("ev-known", "supports"),
                self._ref("ev-missing", "challenges"),
            ]
        }
        evi = [self._evi("ev-known", "primary")]  # ev-missing absent
        state, basis = _derive_element_state_with_authority(elem, evi)
        # 3 vs 1 — supports dominant 2x.
        assert state == ElementState.supported
        assert basis["weighted_supports"] == 3
        assert basis["weighted_challenges"] == 1

    def test_caveat_lists_up_to_three_domains(self):
        # When supports dominant but multiple challenger domains exist,
        # caveat lists the first 3 for legibility.
        elem = {
            "evidence_refs": [
                self._ref("ev-1", "supports"),
                self._ref("ev-2", "supports"),
                self._ref("ev-3", "supports"),
                self._ref("ev-4", "supports"),
                self._ref("ev-5", "challenges"),
                self._ref("ev-6", "challenges"),
                self._ref("ev-7", "challenges"),
                self._ref("ev-8", "challenges"),
            ]
        }
        evi = [
            self._evi("ev-1", "primary"),
            self._evi("ev-2", "primary"),
            self._evi("ev-3", "primary"),
            self._evi("ev-4", "primary"),
            {"evidence_id": "ev-5", "tier": "commentary", "url": "https://a.com/"},
            {"evidence_id": "ev-6", "tier": "commentary", "url": "https://b.com/"},
            {"evidence_id": "ev-7", "tier": "commentary", "url": "https://c.com/"},
            {"evidence_id": "ev-8", "tier": "commentary", "url": "https://d.com/"},
        ]
        state, basis = _derive_element_state_with_authority(elem, evi)
        # Weighted supports 12, challenges 4 — supports dominant 2x (12 >= 2*4).
        assert state == ElementState.supported
        assert basis["caveat"] is not None
        # First 3 domains listed, 4th omitted.
        assert "a.com" in basis["caveat"]
        assert "b.com" in basis["caveat"]
        assert "c.com" in basis["caveat"]
        assert "d.com" not in basis["caveat"]

    def test_state_basis_includes_llm_state_when_attached(self):
        # The wired-seam path attaches llm_state to state_basis. Pure
        # helper doesn't (it's the caller's responsibility), but the
        # field is reserved on the basis dict shape.
        elem = {"evidence_refs": [self._ref("ev-1", "supports")]}
        evi = [self._evi("ev-1", "primary")]
        state, basis = _derive_element_state_with_authority(elem, evi)
        # llm_state is added by the caller, not by this function
        assert "llm_state" not in basis
        # All other keys present
        for key in [
            "supports_count",
            "challenges_count",
            "context_count",
            "weighted_supports",
            "weighted_challenges",
            "rule_applied",
            "caveat",
        ]:
            assert key in basis


class TestCleanUncertainty:
    """LLM sentinel normalisation — the mapping schema types uncertainty as a
    plain string, so the model emits the literal "null" when there is nothing
    to say. Found verbatim in the 2026-06-12 /compare capture."""

    def test_literal_null_string_becomes_none(self):
        from app.pipeline.claim_map_analyzer import _clean_uncertainty

        assert _clean_uncertainty("null") is None
        assert _clean_uncertainty("None") is None
        assert _clean_uncertainty("NULL") is None
        assert _clean_uncertainty("n/a") is None
        assert _clean_uncertainty("  null  ") is None

    def test_falsy_and_non_string_become_none(self):
        from app.pipeline.claim_map_analyzer import _clean_uncertainty

        assert _clean_uncertainty(None) is None
        assert _clean_uncertainty("") is None
        assert _clean_uncertainty(0) is None
        assert _clean_uncertainty({"text": "x"}) is None

    def test_real_sentence_passes_through(self):
        from app.pipeline.claim_map_analyzer import _clean_uncertainty

        sentence = "Newer research challenges the protective effect."
        assert _clean_uncertainty(sentence) == sentence
