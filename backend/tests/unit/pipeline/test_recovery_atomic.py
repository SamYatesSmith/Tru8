"""D5 (structure plan 2026-10-07, S5): coverage recovery commits a claim's
mapping all-or-nothing.

Before: `map_evidence_to_specific_elements` mutated the live claim map in
place (new refs, rewritten target states) and only then awaited the
relationship review; the pool was extended afterwards. A Phase B timeout
during the review left refs on elements, states rewritten, orientation
stale, and refs pointing at items that never reached `evidence[pos]` (so
were never stored). A late exception did the same, silently
(`return_exceptions=True` results were never read).

After: the mapping runs on a staged copy; the map swap and the pool
extension happen together, synchronously, only when the mapping finished.
"""

import asyncio
import copy

import pytest

from app.core.config import settings
from app.pipeline import runner


def _claim():
    cm = {
        "claim_id": "c1",
        "elements": [
            {"element_id": "e1", "state": "unresolved", "evidence_refs": []},
        ],
        "metadata": {},
    }
    return {"position": 0, "claim_map": cm}


class _Analyzer:
    """Mutates the map it is given, then optionally hangs or raises — the
    shape of the real call: refs merged, then the review awaited."""

    def __init__(self, after_mutation=None):
        self.after_mutation = after_mutation
        self.seen = None

    async def map_evidence_to_specific_elements(
        self, claim_map, unresolved_element_ids, new_evidence, full_evidence
    ):
        self.seen = claim_map
        claim_map["elements"][0]["evidence_refs"].append(
            {"evidence_id": "ev-rec-1", "relationship": "supports"}
        )
        claim_map["elements"][0]["state"] = "supported"
        if self.after_mutation == "hang":
            await asyncio.sleep(5)
        if self.after_mutation == "raise":
            raise RuntimeError("review exploded")


NEW = [{"evidence_id": "ev-rec-1", "tier": "primary"}]


def _run(analyzer, claim, evidence, timeout=1.0):
    async def go():
        return await asyncio.wait_for(
            runner._map_recovery_atomically(analyzer, claim, 0, evidence, ["e1"], NEW),
            timeout=timeout,
        )

    return asyncio.run(go())


def test_success_commits_the_map_and_the_pool_together():
    claim, evidence = _claim(), {0: [{"evidence_id": "ev-main"}]}
    cm = claim["claim_map"]
    assert _run(_Analyzer(), claim, evidence) is True
    assert claim["claim_map"] is cm  # same object: claims/selected_claims alias it
    assert cm["elements"][0]["state"] == "supported"
    assert [e["evidence_id"] for e in evidence[0]] == ["ev-main", "ev-rec-1"]
    assert claim["evidence"] is evidence[0]


def test_the_mapping_never_touches_the_live_map():
    claim, evidence = _claim(), {0: []}
    analyzer = _Analyzer()
    _run(analyzer, claim, evidence)
    assert analyzer.seen is not claim["claim_map"]


def test_a_timeout_mid_review_leaves_map_and_pool_untouched():
    claim, evidence = _claim(), {0: [{"evidence_id": "ev-main"}]}
    before_map = copy.deepcopy(claim["claim_map"])
    with pytest.raises(asyncio.TimeoutError):
        _run(_Analyzer("hang"), claim, evidence, timeout=0.05)
    assert claim["claim_map"] == before_map
    assert [e["evidence_id"] for e in evidence[0]] == ["ev-main"]
    assert "evidence" not in claim


def test_an_exception_after_the_parse_leaves_map_and_pool_untouched(caplog):
    claim, evidence = _claim(), {0: []}
    before_map = copy.deepcopy(claim["claim_map"])
    assert _run(_Analyzer("raise"), claim, evidence) is False
    assert claim["claim_map"] == before_map
    assert evidence[0] == []
    assert any("review exploded" in r.getMessage() for r in caplog.records)


def test_the_grace_window_holds_the_mapping_call_and_one_review(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", True)
    monkeypatch.setattr(settings, "RELATIONSHIP_REVIEW_CALL_TIMEOUT_S", 40)
    monkeypatch.setattr(settings, "RECOVERY_MAPPING_GRACE_SECONDS", 25)
    assert runner._recovery_mapping_grace() == 85  # 35 mapping + 40 review + 10
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", False)
    assert runner._recovery_mapping_grace() == 25


def test_phase_b_logs_failures_and_a_timeout_and_returns(caplog):
    """The Phase B wait (runner `_await_recovery_mappings`): every outcome of
    `return_exceptions=True` is read, and a grace timeout is logged, not raised
    (verification M-c, 2026-10-07)."""

    async def ok():
        return None

    async def bad():
        raise RuntimeError("claim 3 broke")

    async def hang():
        await asyncio.sleep(5)

    asyncio.run(runner._await_recovery_mappings([ok(), bad()], grace=1.0))
    assert any("claim 3 broke" in r.getMessage() for r in caplog.records)

    caplog.clear()
    asyncio.run(runner._await_recovery_mappings([hang()], grace=0.05))
    assert any("grace exceeded (0.05s)" in r.getMessage() for r in caplog.records)


# ── D2 (structure plan S4): recovery gates against the full pool ────────────

_DOI = "10.1056/NEJMoa2307563"


def _recovery_case(main_tier, recovery_tier):
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
    from unittest.mock import AsyncMock

    main = {
        "evidence_id": "ev-main",
        "url": f"https://www.nejm.org/doi/full/{_DOI}",
        "title": "The trial (journal)",
        "snippet": "MACE occurred in 6.5% versus 8.0% of participants.",
        "tier": main_tier,
    }
    rec = {
        "evidence_id": "ev-rec-e1_0_pm",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37952131/",
        "title": "The trial (abstract)",
        "snippet": f"doi: {_DOI}. MACE occurred in 6.5% versus 8.0%.",
        "tier": recovery_tier,
    }
    cm = {
        "claim_id": "c1",
        "normalised_claim": "The drug reduced events.",
        "claim_type": "empirical",
        "metadata": {},
        "elements": [
            {
                "element_id": "e1",
                "description": "The drug reduced events.",
                "state": "unresolved",
                "uncertainty": None,
                "evidence_refs": [
                    {"evidence_id": "ev-main", "relationship": "supports", "reasoning": "r"}
                ],
            }
        ],
    }
    analyzer = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
    analyzer.snippet_length = 200
    analyzer.analyzer_temperature = 0.1
    analyzer.analyzer_max_tokens = 2000
    analyzer._call_llm = AsyncMock(
        return_value={
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-rec-e1_0_pm",
                            "relationship": "supports",
                            "reasoning": "r",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                }
            ]
        }
    )
    asyncio.run(
        analyzer.map_evidence_to_specific_elements(
            claim_map=cm,
            unresolved_element_ids=["e1"],
            new_evidence=[rec],
            full_evidence=[main, rec],
        )
    )
    elem = cm["elements"][0]
    rels = {
        r["evidence_id"]: getattr(r["relationship"], "value", r["relationship"])
        for r in elem["evidence_refs"]
    }
    return elem, rels


@pytest.mark.parametrize(
    "main_tier,recovery_tier,counted",
    [
        ("primary", "reporting", "ev-main"),  # main-pass host is the carrier
        ("reporting", "primary", "ev-rec-e1_0_pm"),  # recovery host outranks it
        ("primary", "primary", "ev-main"),  # tie: the earlier ref carries
    ],
)
def test_recovery_counts_one_study_once_across_passes(
    monkeypatch, main_tier, recovery_tier, counted
):
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", False)
    elem, rels = _recovery_case(main_tier, recovery_tier)
    directional = [e for e, r in rels.items() if r == "supports"]
    assert directional == [counted]
    scoped = elem["basis"]["same_study_scope"]["scoped"]
    assert [s["evidence_id"] for s in scoped] == [
        e for e in rels if e != counted
    ]
