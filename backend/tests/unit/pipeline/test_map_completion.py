"""Tests for the per-element mapper completion pass (Step 2 of pool-diversity, 2026-05-12).

NF-19 mitigation. The main batched mapper is instructed by
MAPPING_PROMPT to be conservative — "Padding every element with the
same items is a quality failure, not thoroughness" (line 296 of
claim_map_analyzer.py). That's correct for primary assignment but
leaves rich pool content unmapped, especially after Step 1's
class-targeted query augmentation feeds more news/officials/academic
material into the pool.

The completion pass runs after `_parse_mapping_response` succeeds.
It:
  1. Identifies evidence items not referenced by any element.
  2. Calls the LLM with COMPLETION_PROMPT — a more permissive prompt
     that explicitly invites context-tier matches.
  3. Merges additional refs (deduped by evidence_id).
  4. Re-derives state via _derive_element_state_with_authority.

Test discipline mirrors test_coverage_recovery.py's TestRecoveryFutility
and TestRecoverySuccess shapes — same _make_real_analyzer + claim_map
helpers, same LLM-mocking pattern.
"""

from unittest.mock import AsyncMock

import pytest

from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import (
    ClaimMapAnalyzer,
    derive_orientation,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _make_analyzer(completion_response):
    """Analyzer with mocked _call_llm but real _validate_evidence_refs."""
    analyzer = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
    analyzer.snippet_length = 200
    analyzer.analyzer_temperature = 0.1
    analyzer.analyzer_max_tokens = 2000
    analyzer._call_llm = AsyncMock(return_value=completion_response)
    return analyzer


def _evi(eid, tier="primary", title=None, snippet="snippet"):
    return {
        "evidence_id": eid,
        "tier": tier,
        "evidence_type": "data",
        "title": title or f"Title for {eid}",
        "snippet": snippet,
    }


def _ref(eid, relationship, reasoning=None):
    return {
        "evidence_id": eid,
        "relationship": relationship,
        "reasoning": reasoning or "reason",
    }


def _claim_map(elements_spec, claim_id="c1"):
    elements = []
    for eid, state, desc, refs in elements_spec:
        elements.append(
            {
                "element_id": eid,
                "description": desc,
                "evidence_refs": list(refs),
                "state": ElementState(state),
                "uncertainty": None,
            }
        )
    return {
        "claim_id": claim_id,
        "normalised_claim": "Test claim",
        "claim_type": "empirical",
        "elements": elements,
        "metadata": {
            "decomposition_model": "test",
            "mapping_model": "test",
            "element_count": len(elements),
            "completed_at": None,
        },
    }


# ── No-op cases ────────────────────────────────────────────────────────


class TestCompletionNoOpCases:
    """The completion pass must be invisible when there's nothing to do."""

    @pytest.mark.asyncio
    async def test_no_op_when_no_evidence_list(self):
        cm = _claim_map([("e1", "unresolved", "Element A", [])])
        analyzer = _make_analyzer(None)
        await analyzer._complete_unmapped_evidence(cm, [])
        analyzer._call_llm.assert_not_called()
        assert cm["elements"][0]["state"] == ElementState.unresolved

    @pytest.mark.asyncio
    async def test_no_op_when_no_elements(self):
        cm = _claim_map([])
        evi = [_evi("ev-1")]
        analyzer = _make_analyzer(None)
        await analyzer._complete_unmapped_evidence(cm, evi)
        analyzer._call_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_runs_even_for_small_leftover_set(self):
        # NF-19 (2026-06-16): the gate dropped 3→1. The census now runs
        # whenever ANY item is unmapped, because even one missed support
        # can flip the mechanical state. 2 leftovers used to skip; now it
        # runs.
        cm = _claim_map(
            [
                ("e1", "supported", "Element A", [_ref("ev-mapped", "supports")]),
            ]
        )
        evi = [
            _evi("ev-mapped"),
            _evi("ev-leftover-1"),
            _evi("ev-leftover-2"),
        ]
        analyzer = _make_analyzer({"elements": []})
        await analyzer._complete_unmapped_evidence(cm, evi)
        analyzer._call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_op_when_everything_already_mapped(self):
        # All 5 evidence items are referenced — 0 leftovers
        cm = _claim_map(
            [
                (
                    "e1",
                    "supported",
                    "Element A",
                    [
                        _ref("ev-1", "supports"),
                        _ref("ev-2", "supports"),
                        _ref("ev-3", "context"),
                    ],
                ),
                (
                    "e2",
                    "supported",
                    "Element B",
                    [_ref("ev-4", "supports"), _ref("ev-5", "context")],
                ),
            ]
        )
        evi = [_evi(f"ev-{i}") for i in range(1, 6)]
        analyzer = _make_analyzer(None)
        await analyzer._complete_unmapped_evidence(cm, evi)
        analyzer._call_llm.assert_not_called()


# ── LLM-call cases: leftovers exist, LLM responds ─────────────────────


class TestCompletionAddsAdditionalRefs:
    """The success path — leftovers exist, LLM returns context-tier
    matches, refs merge in, states re-derive."""

    @pytest.mark.asyncio
    async def test_context_refs_promote_unresolved_to_contextual(self):
        # Element starts unresolved (0 refs). 4 leftover primary items.
        # LLM maps 2 of them as context. Element becomes contextual.
        cm = _claim_map([("e1", "unresolved", "Ocean heat anomalies in Coral Sea", [])])
        evi = [
            _evi("ev-bleach-2016", title="2016 GBR bleaching paper"),
            _evi("ev-coral-wiki", title="Wikipedia: Coral reef"),
            _evi("ev-climate-ocean", title="Effects of climate change on oceans"),
            _evi("ev-attribution", title="Attribution study"),
        ]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-bleach-2016",
                            "relationship": "context",
                            "reasoning": "Adjacent event, same region",
                        },
                        {
                            "evidence_id": "ev-climate-ocean",
                            "relationship": "context",
                            "reasoning": "Broader phenomenon",
                        },
                    ],
                }
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # Element now has 2 refs, both context — state = contextual.
        elem = cm["elements"][0]
        assert len(elem["evidence_refs"]) == 2
        assert {r["evidence_id"] for r in elem["evidence_refs"]} == {
            "ev-bleach-2016",
            "ev-climate-ocean",
        }
        assert elem["state"] == ElementState.contextual
        assert elem["basis"]["state_derivation"]["rule_applied"] == "context_only"

    @pytest.mark.asyncio
    async def test_supports_refs_promote_unresolved_to_supported(self):
        cm = _claim_map([("e1", "unresolved", "BoE intervened in 2022", [])])
        evi = [
            _evi("ev-guardian", title="Guardian: BoE emergency intervention"),
            _evi("ev-bbc", title="BBC: BoE bond market"),
            _evi("ev-ft", title="FT: BoE markets"),
        ]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-guardian",
                            "relationship": "supports",
                            "reasoning": "Guardian directly reports the intervention",
                        },
                    ],
                }
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        elem = cm["elements"][0]
        assert len(elem["evidence_refs"]) == 1
        assert elem["state"] == ElementState.supported
        assert elem["basis"]["state_derivation"]["rule_applied"] == "all_supports"

    @pytest.mark.asyncio
    async def test_distributes_refs_across_multiple_elements(self):
        cm = _claim_map(
            [
                ("e1", "unresolved", "Element A: location aspect", []),
                ("e2", "unresolved", "Element B: temperature aspect", []),
                ("e3", "unresolved", "Element C: attribution aspect", []),
            ]
        )
        evi = [_evi(f"ev-{i}", title=f"Item {i}") for i in range(1, 6)]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-1",
                            "relationship": "context",
                            "reasoning": "Geographic relevance",
                        },
                        {
                            "evidence_id": "ev-2",
                            "relationship": "supports",
                            "reasoning": "Direct location confirmation",
                        },
                    ],
                },
                {
                    "element_id": "e2",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-3",
                            "relationship": "supports",
                            "reasoning": "Temperature data",
                        },
                    ],
                },
                {
                    "element_id": "e3",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-4",
                            "relationship": "context",
                            "reasoning": "Broader attribution science",
                        },
                    ],
                },
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # All three elements got refs
        assert len(cm["elements"][0]["evidence_refs"]) == 2
        assert len(cm["elements"][1]["evidence_refs"]) == 1
        assert len(cm["elements"][2]["evidence_refs"]) == 1

        # States re-derived correctly
        assert (
            cm["elements"][0]["state"] == ElementState.supported
        )  # 1 sup + 1 ctx → supports rules
        assert cm["elements"][1]["state"] == ElementState.supported
        assert cm["elements"][2]["state"] == ElementState.contextual

    @pytest.mark.asyncio
    async def test_same_item_can_map_to_multiple_elements(self):
        # The LLM may legitimately attach one piece of evidence to
        # multiple elements (cross-element relevance).
        cm = _claim_map(
            [
                ("e1", "unresolved", "Element A", []),
                ("e2", "unresolved", "Element B", []),
                ("e3", "unresolved", "Element C", []),
            ]
        )
        evi = [_evi(f"ev-{i}") for i in range(1, 5)]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-1",
                            "relationship": "context",
                            "reasoning": "r",
                        }
                    ],
                },
                {
                    "element_id": "e2",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-1",
                            "relationship": "context",
                            "reasoning": "r",
                        },
                        {
                            "evidence_id": "ev-2",
                            "relationship": "context",
                            "reasoning": "r",
                        },
                    ],
                },
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # ev-1 attached to both e1 and e2
        assert {r["evidence_id"] for r in cm["elements"][0]["evidence_refs"]} == {
            "ev-1"
        }
        assert {r["evidence_id"] for r in cm["elements"][1]["evidence_refs"]} == {
            "ev-1",
            "ev-2",
        }


# ── Defensive cases: malformed input / LLM failure ────────────────────


class TestCompletionRobustness:
    """The completion pass must never corrupt the main mapping output."""

    @pytest.mark.asyncio
    async def test_llm_returns_none_preserves_main_mapping(self):
        cm = _claim_map(
            [
                (
                    "e1",
                    "supported",
                    "Element A",
                    [_ref("ev-mapped", "supports")],
                ),
            ]
        )
        evi = [_evi(f"ev-{i}") for i in range(1, 6)] + [_evi("ev-mapped")]
        analyzer = _make_analyzer(None)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # Original mapping intact
        elem = cm["elements"][0]
        assert len(elem["evidence_refs"]) == 1
        assert elem["evidence_refs"][0]["evidence_id"] == "ev-mapped"
        assert elem["state"] == ElementState.supported

    @pytest.mark.asyncio
    async def test_malformed_llm_response_preserves_main_mapping(self):
        cm = _claim_map(
            [("e1", "supported", "Element A", [_ref("ev-mapped", "supports")])]
        )
        evi = [_evi(f"ev-{i}") for i in range(1, 5)] + [_evi("ev-mapped")]
        # Malformed: missing required fields
        analyzer = _make_analyzer({"elements": "not-a-list"})
        await analyzer._complete_unmapped_evidence(cm, evi)

        elem = cm["elements"][0]
        assert len(elem["evidence_refs"]) == 1
        assert elem["state"] == ElementState.supported

    @pytest.mark.asyncio
    async def test_hallucinated_evidence_ids_filtered_out(self):
        # LLM returns refs to evidence_ids not in the leftover set —
        # _validate_evidence_refs strips them.
        cm = _claim_map([("e1", "unresolved", "Element A", [])])
        evi = [_evi(f"ev-{i}") for i in range(1, 5)]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-1",
                            "relationship": "context",
                            "reasoning": "r",
                        },
                        {
                            "evidence_id": "ev-HALLUCINATED",
                            "relationship": "supports",
                            "reasoning": "r",
                        },
                    ],
                }
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # Only the valid ref survived
        elem = cm["elements"][0]
        refs = elem["evidence_refs"]
        assert len(refs) == 1
        assert refs[0]["evidence_id"] == "ev-1"

    @pytest.mark.asyncio
    async def test_empty_additional_refs_per_element_skipped(self):
        # An element returned with additional_refs=[] doesn't get
        # state re-derived (no change).
        cm = _claim_map(
            [
                ("e1", "supported", "Element A", [_ref("ev-mapped-1", "supports")]),
                ("e2", "unresolved", "Element B", []),
            ]
        )
        evi = [
            _evi("ev-mapped-1"),
            _evi("ev-leftover-1"),
            _evi("ev-leftover-2"),
            _evi("ev-leftover-3"),
        ]
        llm_response = {
            "elements": [
                {"element_id": "e1", "additional_refs": []},
                {
                    "element_id": "e2",
                    "additional_refs": [
                        {
                            "evidence_id": "ev-leftover-1",
                            "relationship": "context",
                            "reasoning": "r",
                        }
                    ],
                },
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        # e1 unchanged
        assert cm["elements"][0]["state"] == ElementState.supported
        assert len(cm["elements"][0]["evidence_refs"]) == 1

        # e2 promoted to contextual
        assert cm["elements"][1]["state"] == ElementState.contextual

    @pytest.mark.asyncio
    async def test_only_leftover_evidence_visible_to_llm(self):
        # Verify the leftover-only contract: items already in
        # evidence_refs from the main pass should NOT appear in the
        # LLM prompt. We check this via the leftover identification
        # logic by counting items in the prompt.
        cm = _claim_map(
            [
                (
                    "e1",
                    "supported",
                    "Element A",
                    [_ref("ev-already-1", "supports"), _ref("ev-already-2", "context")],
                ),
            ]
        )
        evi = [
            _evi("ev-already-1"),
            _evi("ev-already-2"),
            _evi("ev-leftover-A"),
            _evi("ev-leftover-B"),
            _evi("ev-leftover-C"),
        ]
        # Empty response — we just want to check the LLM was called
        # with the right leftover set.
        analyzer = _make_analyzer({"elements": []})
        await analyzer._complete_unmapped_evidence(cm, evi)

        # Inspect the prompt that the LLM was called with
        analyzer._call_llm.assert_called_once()
        call_kwargs = analyzer._call_llm.call_args.kwargs
        prompt = call_kwargs.get("prompt", "")

        # Leftovers appear; already-mapped items do not.
        assert "ev-leftover-A" in prompt
        assert "ev-leftover-B" in prompt
        assert "ev-leftover-C" in prompt
        assert "ev-already-1" not in prompt
        assert "ev-already-2" not in prompt


# ── NF-19 SOLVE (2026-06-16): census fixes state, not just visibility ──
#
# The bug NF-19 actually was: element state is derived by COUNTING the
# mapped evidence_refs, but the main mapper maps only a representative
# sample → the count is over a biased sample → wrong state. The census
# backstop merges the missed supports/challenges so state is counted over
# the complete set. See audit/2026-06-16_nf19_design_review.md (Option D).


from app.pipeline.claim_map_analyzer import _derive_element_state_with_authority


class TestCensusFixesState:
    """The core NF-19 fix: a complete supports/challenges census corrects
    the mechanical element state."""

    @pytest.mark.asyncio
    async def test_census_flips_close_split_to_supported(self):
        # Reproduces the TRU-EF20 shape: main pass mapped only 1 of 8
        # supports plus the lone (erroneous) challenger. With just those
        # two refs the mechanical rule sees a close split → "disputed".
        cm = _claim_map(
            [
                (
                    "e1",
                    "disputed",
                    "Reform UK won 5 seats",
                    [
                        _ref("ev-royalholloway", "supports"),
                        _ref("ev-statista", "challenges"),  # "4 seats" data error
                    ],
                ),
            ]
        )
        leftover_support_ids = [f"ev-support-{i}" for i in range(7)]
        evi = [_evi("ev-royalholloway"), _evi("ev-statista")] + [
            _evi(e) for e in leftover_support_ids
        ]

        # BEFORE the census: the 2 mapped refs derive "disputed" (close_split).
        pre_state, pre_basis = _derive_element_state_with_authority(
            cm["elements"][0], evi
        )
        assert pre_state == ElementState.disputed
        assert pre_basis["rule_applied"] == "close_split"

        # Census returns the 7 missed supports.
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": e,
                            "relationship": "supports",
                            "reasoning": "Independent source confirming 5 seats",
                        }
                        for e in leftover_support_ids
                    ],
                }
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        elem = cm["elements"][0]
        # AFTER: 8 supports + 1 challenge → supports dominate → supported.
        assert len(elem["evidence_refs"]) == 9
        assert elem["state"] == ElementState.supported
        sd = elem["basis"]["state_derivation"]
        assert sd["rule_applied"] == "supports_dominant_2x"
        assert sd["supports_count"] == 8
        assert sd["challenges_count"] == 1
        # The lone challenger is surfaced as a caveat, not buried.
        assert sd["caveat"]

    @pytest.mark.asyncio
    async def test_census_preserves_disputed_when_challenges_are_real(self):
        # Guard against a supported-bias: if the census surfaces genuine
        # challenges, the element stays disputed. Main mapped 1 support;
        # 5 leftover challenges get mapped → challenges dominate.
        cm = _claim_map(
            [
                (
                    "e1",
                    "supported",
                    "Drug X cures disease Y",
                    [_ref("ev-pro", "supports")],
                ),
            ]
        )
        challenge_ids = [f"ev-con-{i}" for i in range(5)]
        evi = [_evi("ev-pro")] + [_evi(e) for e in challenge_ids]
        llm_response = {
            "elements": [
                {
                    "element_id": "e1",
                    "additional_refs": [
                        {
                            "evidence_id": e,
                            "relationship": "challenges",
                            "reasoning": "Trial found no effect",
                        }
                        for e in challenge_ids
                    ],
                }
            ]
        }
        analyzer = _make_analyzer(llm_response)
        await analyzer._complete_unmapped_evidence(cm, evi)

        elem = cm["elements"][0]
        assert len(elem["evidence_refs"]) == 6
        assert elem["state"] == ElementState.disputed
        sd = elem["basis"]["state_derivation"]
        assert sd["supports_count"] == 1
        assert sd["challenges_count"] == 5
        assert sd["rule_applied"] == "challenges_dominant_2x"
