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
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, derive_orientation


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
        assert result == "The single required element is evidentially supported."

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
        assert result == "All 3 required elements are evidentially supported."

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
        assert result == "All 2 required elements are evidentially disputed."

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
        assert result == "All 4 required elements are evidentially unresolved."

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
        assert "2 of 3 required elements are evidentially supported" in result
        assert "1 is disputed" in result

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
        assert "2 of 4 required elements are" in result
        assert "unresolved" in result

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
        assert result.startswith("Evidence is mixed across 3 required elements:")
        assert "1 supported" in result
        assert "1 disputed" in result
        assert "1 unresolved" in result

    @pytest.mark.parametrize("state", list(ElementState))
    def test_single_element_all_states(self, state):
        """Single element with each state produces correct template."""
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
        assert result == f"The single required element is evidentially {state.value}."

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
