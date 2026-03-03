"""Tests for ClaimMapAnalyzer batch operations, LLM fallback chain, and validation helpers.

Covers:
- _call_llm fallback chain (Google primary, OpenAI fallback)
- decompose_claims_batch (batch decomposition with fallback to per-claim)
- map_evidence_batch (batch mapping with fallback to per-claim)
- map_evidence_to_elements no-evidence path
- _validate_evidence_refs (ref filtering)
- _fallback_mapping (all-unresolved fallback)
- _call_openai (HTTP-level tests)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.claim_map import (
    ClaimElement,
    ClaimMap,
    ClaimMapMetadata,
    ClaimType,
    ElementState,
    EvidenceRef,
    EvidenceRelationship,
)
from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, derive_orientation

_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0}


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_openai_response(payload: dict) -> MagicMock:
    """Build a fake httpx response matching OpenAI chat completions shape."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return resp


def _make_partial_claim_map(
    claim_id: str = "test-claim-1", num_elements: int = 3
) -> ClaimMap:
    """Build a partial ClaimMap (post-decomposition, pre-mapping)."""
    elements = [
        ClaimElement(
            element_id=f"e{i}",
            description=f"Element {i} description",
            evidence_refs=[],
            state=None,
            uncertainty=None,
            bounty_text=None,
        )
        for i in range(1, num_elements + 1)
    ]
    return ClaimMap(
        claim_id=claim_id,
        normalised_claim=f"Normalised claim for {claim_id}",
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


def _make_evidence_list(count: int = 3, prefix: str = "ev") -> list[dict]:
    return [
        {
            "evidence_id": f"{prefix}{i}",
            "title": f"Evidence {i}",
            "snippet": f"Snippet content for evidence {i}",
            "url": f"http://example.com/{i}",
        }
        for i in range(1, count + 1)
    ]


def _make_decomposition_payload(
    normalised: str = "Test claim normalised",
    claim_type: str = "empirical",
    elements: list | None = None,
) -> dict:
    if elements is None:
        elements = [
            {"description": "Element one must hold"},
            {"description": "Element two must hold"},
        ]
    return {
        "normalised_claim": normalised,
        "claim_type": claim_type,
        "elements": elements,
    }


def _make_batch_decomposition_payload(count: int = 3) -> dict:
    """Build a batch decomposition response with `count` claims."""
    claims = []
    for i in range(count):
        claims.append(
            {
                "claim_index": i,
                "normalised_claim": f"Normalised claim {i}",
                "claim_type": "empirical",
                "elements": [
                    {"description": f"Claim {i} element 1"},
                    {"description": f"Claim {i} element 2"},
                ],
            }
        )
    return {"claims": claims}


def _make_batch_mapping_payload(
    count: int = 3, element_ids_per: list[str] | None = None
) -> dict:
    """Build a batch mapping response with `count` claims."""
    claims = []
    for i in range(count):
        eids = element_ids_per or ["e1", "e2"]
        elements = []
        for eid in eids:
            elements.append(
                {
                    "element_id": eid,
                    "evidence_refs": [
                        {
                            "evidence_id": f"ev{i+1}_1",
                            "relationship": "supports",
                            "reasoning": "Test reason",
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            )
        claims.append({"claim_index": i, "elements": elements})
    return {"claims": claims}


def _mock_async_client(response: MagicMock) -> MagicMock:
    """Create a mock httpx.AsyncClient context manager returning the given response."""
    mock_client = AsyncMock()
    mock_client.post.return_value = response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ── _call_llm fallback chain ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestCallLlmFallback:

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_google_success_returns_parsed(self, mock_client_cls, mock_google):
        """Google succeeds -> returns parsed dict, no OpenAI call."""
        expected = {"normalised_claim": "test", "elements": []}
        mock_google.return_value = (expected, {"input_tokens": 10, "output_tokens": 5})

        analyzer = ClaimMapAnalyzer()
        result = await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert result == expected
        mock_client_cls.assert_not_called()

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_google_fails_openai_succeeds(self, mock_client_cls, mock_google):
        """Google raises Exception -> falls back to OpenAI -> returns dict."""
        mock_google.side_effect = Exception("Google down")

        expected = {"normalised_claim": "from openai", "elements": []}
        mock_client_cls.return_value = _mock_async_client(
            _make_openai_response(expected)
        )

        analyzer = ClaimMapAnalyzer()
        result = await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert result == expected

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_both_fail_returns_none(self, mock_client_cls, mock_google):
        """Google raises, OpenAI returns None -> returns None."""
        mock_google.side_effect = Exception("Google down")

        error_resp = MagicMock()
        error_resp.status_code = 500
        mock_client_cls.return_value = _mock_async_client(error_resp)

        analyzer = ClaimMapAnalyzer()
        result = await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert result is None

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_sets_last_model_used_google(self, mock_client_cls, mock_google):
        """After Google success, _last_model_used == self.google_model."""
        mock_google.return_value = (
            {"test": True},
            {"input_tokens": 0, "output_tokens": 0},
        )

        analyzer = ClaimMapAnalyzer()
        await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert analyzer._last_model_used == analyzer.google_model

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_sets_last_model_used_openai(self, mock_client_cls, mock_google):
        """After Google failure + OpenAI fallback, _last_model_used == decomposition_model."""
        mock_google.side_effect = Exception("Google down")

        mock_client_cls.return_value = _mock_async_client(
            _make_openai_response({"test": True})
        )

        analyzer = ClaimMapAnalyzer()
        await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert analyzer._last_model_used == analyzer.decomposition_model


# ── decompose_claims_batch ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDecomposeClaimsBatch:

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_single_claim_delegates(self, mock_google):
        """1-claim input -> calls decompose_claim directly (not batch)."""
        mock_google.return_value = (
            _make_decomposition_payload(normalised="Single claim normalised"),
            _ZERO_USAGE,
        )

        analyzer = ClaimMapAnalyzer()
        claims = [{"text": "One claim", "claim_id": "c1"}]
        result = await analyzer.decompose_claims_batch(claims)

        assert "c1" in result
        assert result["c1"]["normalised_claim"] == "Single claim normalised"

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_multi_claim_returns_all(self, mock_google):
        """3 claims -> batch LLM call returns 3 ClaimMaps."""
        mock_google.return_value = (_make_batch_decomposition_payload(3), _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()
        claims = [{"text": f"Claim {i}", "claim_id": f"c{i}"} for i in range(3)]
        result = await analyzer.decompose_claims_batch(claims)

        assert len(result) == 3
        for i in range(3):
            assert f"c{i}" in result
            assert result[f"c{i}"]["claim_id"] == f"c{i}"
            assert len(result[f"c{i}"]["elements"]) == 2

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_missing_claim_falls_back(self, mock_google):
        """Batch response missing claim_index=2 -> individual decompose_claim called for it."""
        # Batch response with only claim_index 0 and 1 (missing 2)
        batch_resp = {
            "claims": [
                {
                    "claim_index": 0,
                    "normalised_claim": "Claim 0",
                    "claim_type": "empirical",
                    "elements": [{"description": "E0"}],
                },
                {
                    "claim_index": 1,
                    "normalised_claim": "Claim 1",
                    "claim_type": "empirical",
                    "elements": [{"description": "E1"}],
                },
            ]
        }
        # First call = batch, subsequent calls = per-claim fallback
        fallback_resp = _make_decomposition_payload(normalised="Fallback claim 2")
        mock_google.side_effect = [
            (batch_resp, _ZERO_USAGE),
            (fallback_resp, _ZERO_USAGE),
        ]

        analyzer = ClaimMapAnalyzer()
        claims = [{"text": f"Claim {i}", "claim_id": f"c{i}"} for i in range(3)]
        result = await analyzer.decompose_claims_batch(claims)

        assert len(result) == 3
        assert result["c0"]["normalised_claim"] == "Claim 0"
        assert result["c1"]["normalised_claim"] == "Claim 1"
        # c2 was retried individually
        assert "c2" in result

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_parse_failure_falls_back(self, mock_google):
        """_call_llm returns None -> all claims retried individually via decompose_claim."""
        individual_payload = _make_decomposition_payload(
            normalised="Individual fallback"
        )

        # First call (batch) returns None, then each individual call succeeds
        mock_google.side_effect = [
            (None, None),
            (individual_payload, _ZERO_USAGE),
            (individual_payload, _ZERO_USAGE),
        ]

        analyzer = ClaimMapAnalyzer()
        claims = [{"text": f"Claim {i}", "claim_id": f"c{i}"} for i in range(2)]
        result = await analyzer.decompose_claims_batch(claims)

        assert len(result) == 2
        for cid in ["c0", "c1"]:
            assert cid in result

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_caps_elements_per_claim(self, mock_google):
        """Each claim in batch gets max 5 elements (MAX_ELEMENTS_PER_CLAIM)."""
        # Batch response with 7 elements per claim
        batch_resp = {
            "claims": [
                {
                    "claim_index": i,
                    "normalised_claim": f"Claim {i}",
                    "claim_type": "empirical",
                    "elements": [{"description": f"E{j}"} for j in range(7)],
                }
                for i in range(2)
            ]
        }
        mock_google.return_value = (batch_resp, _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()
        claims = [{"text": f"Claim {i}", "claim_id": f"c{i}"} for i in range(2)]
        result = await analyzer.decompose_claims_batch(claims)

        for cid in ["c0", "c1"]:
            assert len(result[cid]["elements"]) <= 5


# ── map_evidence_batch ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMapEvidenceBatch:

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_no_evidence_marks_unresolved(self, mock_client_cls, mock_google):
        """Claims without evidence -> all elements state=ElementState.unresolved."""
        analyzer = ClaimMapAnalyzer()

        cm = _make_partial_claim_map("c1", 2)
        claim_data = [{"claim_map": cm, "evidence": []}]

        await analyzer.map_evidence_batch(claim_data)

        for elem in cm["elements"]:
            assert elem["state"] == ElementState.unresolved
            assert elem["evidence_refs"] == []
            assert elem["uncertainty"] == "No evidence was retrieved for this element."
        assert cm["metadata"]["mapping_model"] == "none"
        assert cm["metadata"]["completed_at"] is not None

        # No LLM calls should have been made
        mock_google.assert_not_called()

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_single_claim_delegates(self, mock_google):
        """1 claim with evidence -> calls map_evidence_to_elements (not batch)."""
        mapping_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": "Test",
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": None,
                },
            ]
        }
        mock_google.return_value = (mapping_payload, _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 2)
        evidence = _make_evidence_list(2)
        claim_data = [{"claim_map": cm, "evidence": evidence}]

        await analyzer.map_evidence_batch(claim_data)

        assert cm["elements"][0]["state"] == ElementState.supported
        assert cm["orientation"] is not None

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_multi_claim_maps_all(self, mock_google):
        """3 claims with evidence -> all claim_maps mutated with states + refs."""
        # Build batch mapping response with per-claim evidence IDs
        batch_resp = {"claims": []}
        for i in range(3):
            batch_resp["claims"].append(
                {
                    "claim_index": i,
                    "elements": [
                        {
                            "element_id": "e1",
                            "evidence_refs": [
                                {
                                    "evidence_id": f"ev{i}_1",
                                    "relationship": "supports",
                                    "reasoning": "R",
                                },
                            ],
                            "state": "supported",
                            "uncertainty": None,
                        },
                        {
                            "element_id": "e2",
                            "evidence_refs": [],
                            "state": "unresolved",
                            "uncertainty": None,
                        },
                    ],
                }
            )
        mock_google.return_value = (batch_resp, _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()
        claim_data = []
        for i in range(3):
            cm = _make_partial_claim_map(f"c{i}", 2)
            ev = [
                {"evidence_id": f"ev{i}_1", "title": f"Ev {i}", "snippet": "S"},
            ]
            claim_data.append({"claim_map": cm, "evidence": ev})

        await analyzer.map_evidence_batch(claim_data)

        for i in range(3):
            cm = claim_data[i]["claim_map"]
            assert cm["elements"][0]["state"] == ElementState.supported
            assert cm["elements"][1]["state"] == ElementState.unresolved
            assert cm["orientation"] is not None
            assert cm["metadata"]["mapping_model"] is not None
            assert cm["metadata"]["completed_at"] is not None

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_batch_failure_retries_individually(self, mock_google):
        """_call_llm returns None -> each claim retried via map_evidence_to_elements."""
        # First call (batch) returns None, then per-claim calls succeed
        per_claim_mapping = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": "R",
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        mock_google.side_effect = [
            (None, None),
            (per_claim_mapping, _ZERO_USAGE),
            (per_claim_mapping, _ZERO_USAGE),
        ]

        analyzer = ClaimMapAnalyzer()
        claim_data = []
        for i in range(2):
            cm = _make_partial_claim_map(f"c{i}", 1)
            ev = _make_evidence_list(1)
            claim_data.append({"claim_map": cm, "evidence": ev})

        await analyzer.map_evidence_batch(claim_data)

        for item in claim_data:
            cm = item["claim_map"]
            # Should have been retried individually and completed
            assert cm["metadata"]["completed_at"] is not None
            assert cm["orientation"] is not None

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_mixed_evidence_and_empty(self, mock_google):
        """2 claims with evidence + 1 without -> correct handling of both."""
        batch_resp = {
            "claims": [
                {
                    "claim_index": 0,
                    "elements": [
                        {
                            "element_id": "e1",
                            "evidence_refs": [
                                {
                                    "evidence_id": "evA1",
                                    "relationship": "supports",
                                    "reasoning": "R",
                                },
                            ],
                            "state": "supported",
                            "uncertainty": None,
                        },
                    ],
                },
                {
                    "claim_index": 1,
                    "elements": [
                        {
                            "element_id": "e1",
                            "evidence_refs": [
                                {
                                    "evidence_id": "evB1",
                                    "relationship": "challenges",
                                    "reasoning": "R",
                                },
                            ],
                            "state": "disputed",
                            "uncertainty": "Conflicting data",
                        },
                    ],
                },
            ]
        }
        mock_google.return_value = (batch_resp, _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()

        cm_empty = _make_partial_claim_map("c_empty", 1)
        cm_a = _make_partial_claim_map("cA", 1)
        cm_b = _make_partial_claim_map("cB", 1)

        claim_data = [
            {"claim_map": cm_empty, "evidence": []},
            {
                "claim_map": cm_a,
                "evidence": [{"evidence_id": "evA1", "title": "A", "snippet": "S"}],
            },
            {
                "claim_map": cm_b,
                "evidence": [{"evidence_id": "evB1", "title": "B", "snippet": "S"}],
            },
        ]

        await analyzer.map_evidence_batch(claim_data)

        # Empty evidence -> unresolved
        assert cm_empty["elements"][0]["state"] == ElementState.unresolved
        assert cm_empty["metadata"]["mapping_model"] == "none"

        # With evidence -> mapped
        assert cm_a["elements"][0]["state"] == ElementState.supported
        assert cm_b["elements"][0]["state"] == ElementState.disputed


# ── map_evidence_to_elements no-evidence path ────────────────────────────


@pytest.mark.asyncio
class TestMapEvidenceNoEvidence:

    async def test_empty_evidence_all_unresolved(self):
        """Empty evidence list -> all elements state=ElementState.unresolved."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 3)

        result = await analyzer.map_evidence_to_elements(cm, [])

        for elem in result["elements"]:
            assert elem["state"] == ElementState.unresolved
            assert elem["evidence_refs"] == []
            assert elem["uncertainty"] == "No evidence was retrieved for this element."

    async def test_empty_evidence_sets_metadata(self):
        """mapping_model='none' in metadata, completed_at set."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 2)

        result = await analyzer.map_evidence_to_elements(cm, [])

        assert result["metadata"]["mapping_model"] == "none"
        assert result["metadata"]["completed_at"] is not None
        assert result["metadata"]["element_count"] == 2
        assert result["orientation"] is not None


# ── _validate_evidence_refs ───────────────────────────────────────────────


class TestValidateEvidenceRefs:

    def test_strips_unknown_evidence_ids(self):
        """ID not in evidence list -> removed."""
        analyzer = ClaimMapAnalyzer()
        evidence_list = [{"evidence_id": "ev1"}, {"evidence_id": "ev2"}]
        refs = [
            {"evidence_id": "ev1", "relationship": "supports", "reasoning": "R"},
            {
                "evidence_id": "hallucinated",
                "relationship": "supports",
                "reasoning": "R",
            },
        ]

        result = analyzer._validate_evidence_refs(refs, evidence_list)

        assert len(result) == 1
        assert result[0]["evidence_id"] == "ev1"

    def test_strips_invalid_relationships(self):
        """Invalid relationship value -> removed."""
        analyzer = ClaimMapAnalyzer()
        evidence_list = [{"evidence_id": "ev1"}, {"evidence_id": "ev2"}]
        refs = [
            {"evidence_id": "ev1", "relationship": "supports", "reasoning": "R"},
            {"evidence_id": "ev2", "relationship": "invalid_rel", "reasoning": "R"},
        ]

        result = analyzer._validate_evidence_refs(refs, evidence_list)

        assert len(result) == 1
        assert result[0]["evidence_id"] == "ev1"

    def test_valid_refs_pass_through(self):
        """Good refs returned unchanged as EvidenceRef TypedDicts."""
        analyzer = ClaimMapAnalyzer()
        evidence_list = [{"evidence_id": "ev1"}, {"evidence_id": "ev2"}]
        refs = [
            {
                "evidence_id": "ev1",
                "relationship": "supports",
                "reasoning": "Confirms the data",
            },
            {
                "evidence_id": "ev2",
                "relationship": "challenges",
                "reasoning": "Contradicts claim",
            },
        ]

        result = analyzer._validate_evidence_refs(refs, evidence_list)

        assert len(result) == 2
        assert result[0]["evidence_id"] == "ev1"
        assert result[0]["relationship"] == EvidenceRelationship.supports
        assert result[0]["reasoning"] == "Confirms the data"
        assert result[1]["evidence_id"] == "ev2"
        assert result[1]["relationship"] == EvidenceRelationship.challenges
        assert result[1]["reasoning"] == "Contradicts claim"


# ── _fallback_mapping ─────────────────────────────────────────────────────


class TestFallbackMapping:

    def test_all_unresolved_empty_refs(self):
        """All elements set to ElementState.unresolved, empty refs."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 3)

        analyzer._fallback_mapping(cm)

        for elem in cm["elements"]:
            assert elem["state"] == ElementState.unresolved
            assert elem["evidence_refs"] == []
            assert elem["uncertainty"] is None

    def test_orientation_reset(self):
        """After _fallback_mapping, re-derive orientation reflects all-unresolved."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 2)
        # Set some initial states that should be overwritten
        cm["elements"][0]["state"] = ElementState.supported
        cm["elements"][1]["state"] = ElementState.disputed

        analyzer._fallback_mapping(cm)
        # Re-derive orientation as map_evidence_to_elements would
        cm["orientation"] = derive_orientation(cm["elements"])

        assert "unresolved" in cm["orientation"]
        assert "supported" not in cm["orientation"]
        assert "disputed" not in cm["orientation"]


# ── _call_openai ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCallOpenai:

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_non_200_returns_none(self, mock_client_cls):
        """Mock httpx to return status 500 -> returns (None, None)."""
        error_resp = MagicMock()
        error_resp.status_code = 500
        mock_client_cls.return_value = _mock_async_client(error_resp)

        analyzer = ClaimMapAnalyzer()
        parsed, usage = await analyzer._call_openai("prompt", 0.2, 2000, "gpt-4o")

        assert parsed is None
        assert usage is None

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_valid_response_returns_parsed(self, mock_client_cls):
        """Mock httpx to return 200 with valid JSON -> (parsed dict, usage)."""
        expected = {"normalised_claim": "test", "elements": [{"description": "E1"}]}
        mock_client_cls.return_value = _mock_async_client(
            _make_openai_response(expected)
        )

        analyzer = ClaimMapAnalyzer()
        parsed, usage = await analyzer._call_openai("prompt", 0.2, 2000, "gpt-4o")

        assert parsed == expected
        assert isinstance(usage, dict)

    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_json_parse_failure_returns_none(self, mock_client_cls):
        """Mock httpx to return 200 with invalid JSON -> raises (caller handles)."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": "not valid json {{{"}}]
        }
        mock_client_cls.return_value = _mock_async_client(resp)

        analyzer = ClaimMapAnalyzer()
        # _call_openai does json.loads on content; invalid JSON raises json.JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            await analyzer._call_openai("prompt", 0.2, 2000, "gpt-4o")


# ── Mapping model routing ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMappingModelRouting:

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_mapping_label_uses_mapping_model(self, mock_google):
        """mapping label -> uses mapping_google_model, not google_model."""
        mock_google.return_value = (
            {"elements": []},
            {"input_tokens": 0, "output_tokens": 0},
        )

        analyzer = ClaimMapAnalyzer()
        # Ensure they're different for the test
        analyzer.mapping_google_model = "gemini-2.5-flash"
        analyzer.google_model = "gemini-2.5-flash-lite"

        await analyzer._call_llm("prompt", 0.2, 4000, "mapping")

        # Verify _last_model_used is the mapping-specific model
        assert analyzer._last_model_used == "gemini-2.5-flash"

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_batch_mapping_label_uses_mapping_model(self, mock_google):
        """batch_mapping label -> uses mapping_google_model."""
        mock_google.return_value = (
            {"claims": []},
            {"input_tokens": 0, "output_tokens": 0},
        )

        analyzer = ClaimMapAnalyzer()
        analyzer.mapping_google_model = "gemini-2.5-flash"
        analyzer.google_model = "gemini-2.5-flash-lite"

        await analyzer._call_llm("prompt", 0.2, 8000, "batch_mapping")

        assert analyzer._last_model_used == "gemini-2.5-flash"

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_decomposition_label_uses_base_model(self, mock_google):
        """decomposition label -> uses google_model, not mapping model."""
        mock_google.return_value = (
            {"normalised_claim": "test", "elements": []},
            {"input_tokens": 0, "output_tokens": 0},
        )

        analyzer = ClaimMapAnalyzer()
        analyzer.mapping_google_model = "gemini-2.5-flash"
        analyzer.google_model = "gemini-2.5-flash-lite"

        await analyzer._call_llm("prompt", 0.2, 2000, "decomposition")

        assert analyzer._last_model_used == "gemini-2.5-flash-lite"


# ── Null reasoning retry ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestNullReasoningRetry:

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_null_reasoning_triggers_retry(self, mock_google):
        """Mapping with null reasoning retries once with the same prompt."""
        # First call returns mapping with null reasoning
        null_reasoning_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": None,
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        # Retry returns mapping with proper reasoning
        good_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": "Confirms the data point",
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        mock_google.side_effect = [
            (null_reasoning_payload, _ZERO_USAGE),
            (good_payload, _ZERO_USAGE),
        ]

        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        evidence = _make_evidence_list(1)

        await analyzer.map_evidence_to_elements(cm, evidence)

        # Should have been called twice (original + retry)
        assert mock_google.call_count == 2
        # Reasoning should now be populated from the retry
        assert (
            cm["elements"][0]["evidence_refs"][0]["reasoning"]
            == "Confirms the data point"
        )

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    async def test_no_retry_when_reasoning_present(self, mock_google):
        """Mapping with valid reasoning does not trigger retry."""
        good_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": "Confirms the data point",
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        mock_google.return_value = (good_payload, _ZERO_USAGE)

        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        evidence = _make_evidence_list(1)

        await analyzer.map_evidence_to_elements(cm, evidence)

        # Should only be called once (no retry needed)
        assert mock_google.call_count == 1

    @patch("app.pipeline.claim_map_analyzer.call_google_ai_with_usage")
    @patch("app.pipeline.claim_map_analyzer.httpx.AsyncClient")
    async def test_retry_failure_keeps_original(self, mock_client_cls, mock_google):
        """If retry also fails, keep the original (null reasoning) result."""
        null_reasoning_payload = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev1",
                            "relationship": "supports",
                            "reasoning": None,
                        },
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
            ]
        }
        # Block OpenAI fallback
        error_resp = MagicMock()
        error_resp.status_code = 500
        mock_client_cls.return_value = _mock_async_client(error_resp)

        mock_google.side_effect = [
            (null_reasoning_payload, _ZERO_USAGE),
            (None, None),  # Retry fails
        ]

        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        evidence = _make_evidence_list(1)

        await analyzer.map_evidence_to_elements(cm, evidence)

        # Should have been called twice (original + retry)
        assert mock_google.call_count == 2
        # Original result preserved (state should still be set)
        assert cm["elements"][0]["state"] == ElementState.supported


# ── _has_null_reasoning ───────────────────────────────────────────────────


class TestHasNullReasoning:

    def test_detects_null_reasoning(self):
        """Returns True when any evidence_ref has null reasoning."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        cm["elements"][0]["evidence_refs"] = [
            {
                "evidence_id": "ev1",
                "relationship": "supports",
                "reasoning": None,
            }
        ]
        assert analyzer._has_null_reasoning(cm) is True

    def test_returns_false_when_all_present(self):
        """Returns False when all evidence_refs have reasoning."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        cm["elements"][0]["evidence_refs"] = [
            {
                "evidence_id": "ev1",
                "relationship": "supports",
                "reasoning": "Valid reasoning",
            }
        ]
        assert analyzer._has_null_reasoning(cm) is False

    def test_returns_false_for_empty_refs(self):
        """Returns False when no evidence_refs exist."""
        analyzer = ClaimMapAnalyzer()
        cm = _make_partial_claim_map("c1", 1)
        cm["elements"][0]["evidence_refs"] = []
        assert analyzer._has_null_reasoning(cm) is False
