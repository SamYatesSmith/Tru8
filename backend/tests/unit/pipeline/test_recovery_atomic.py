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
    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", True)
    # 35 mapping + 40 relationship review + 20 originator review + 10 slack
    assert runner._recovery_mapping_grace() == 105
    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", False)
    assert runner._recovery_mapping_grace() == 85
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", False)
    assert runner._recovery_mapping_grace() == 25
    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", True)
    assert runner._recovery_mapping_grace() == 65  # 35 + 20 + 10


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


# ── D3 (structure plan S6): originator review on recovered items, Phase B ───


def _phase_a_item(eid="ev-rec-1"):
    """A recovered item as Phase A leaves it: LLM-classified primary, marked
    not reviewed because the review cannot fit Phase A's budget."""
    return {
        "evidence_id": eid,
        "tier": "primary",
        "classification_method": "llm",
        "url": "https://relay.example/page",
        "metadata": {
            "originator_review": {"status": "not_reviewed", "reason": "recovery_budget"}
        },
    }


class _TierAnalyzer(_Analyzer):
    def __init__(self):
        super().__init__()
        self.tiers_seen = None

    async def map_evidence_to_specific_elements(
        self, claim_map, unresolved_element_ids, new_evidence, full_evidence
    ):
        self.tiers_seen = [e["tier"] for e in new_evidence]
        await super().map_evidence_to_specific_elements(
            claim_map, unresolved_element_ids, new_evidence, full_evidence
        )


class _FakeClassifier:
    async def _call_originator_review(self, prompt):
        return None


def _run_with_review(monkeypatch, review):
    from app.services import originator_review

    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", True)
    monkeypatch.setattr(originator_review, "review_originators", review)
    item = _phase_a_item()
    claim, evidence = _claim(), {0: []}
    analyzer = _TierAnalyzer()

    async def go():
        return await runner._map_recovery_atomically(
            analyzer, claim, 0, evidence, ["e1"], [item], classifier=_FakeClassifier()
        )

    committed = asyncio.run(go())
    return committed, item, analyzer


def test_recovered_items_are_reviewed_before_the_mapping(monkeypatch):
    seen = {}

    async def review(items, call):
        seen["receipt_cleared"] = all(
            "originator_review" not in (i.get("metadata") or {}) for i in items
        )
        for i in items:
            i["tier"] = "reporting"
            i["metadata"]["originator_review"] = {"status": "reviewed"}
        return {"candidates": len(items), "lowered": len(items)}

    committed, item, analyzer = _run_with_review(monkeypatch, review)
    assert committed is True
    assert seen["receipt_cleared"] is True  # else is_candidate() skips it
    assert analyzer.tiers_seen == ["reporting"]  # the mapping weighed the review
    assert item["metadata"]["originator_review"]["status"] == "reviewed"


def test_a_slow_review_marks_not_reviewed_and_recovery_goes_on(monkeypatch):
    monkeypatch.setattr(runner, "_RECOVERY_ORIGINATOR_REVIEW_S", 0.05)

    async def slow(items, call):
        await asyncio.sleep(5)

    committed, item, analyzer = _run_with_review(monkeypatch, slow)
    assert committed is True
    assert analyzer.tiers_seen == ["primary"]
    receipt = item["metadata"]["originator_review"]
    assert receipt["status"] == "not_reviewed" and receipt["reason"] == "recovery_timeout"


def test_no_review_without_a_classifier_or_with_the_flag_off(monkeypatch):
    from app.services import originator_review

    calls = []

    async def review(items, call):
        calls.append(items)
        return {}

    monkeypatch.setattr(originator_review, "review_originators", review)
    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", True)
    asyncio.run(
        runner._map_recovery_atomically(
            _Analyzer(), _claim(), 0, {0: []}, ["e1"], [_phase_a_item()], classifier=None
        )
    )
    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", False)
    asyncio.run(
        runner._map_recovery_atomically(
            _Analyzer(), _claim(), 0, {0: []}, ["e1"], [_phase_a_item()], classifier=_FakeClassifier()
        )
    )
    assert calls == []


def test_a_review_fault_costs_the_review_not_the_recovery(monkeypatch):
    async def broken(items, call):
        raise ValueError("bad row")

    committed, item, analyzer = _run_with_review(monkeypatch, broken)
    assert committed is True
    assert analyzer.tiers_seen == ["primary"]
    assert item["metadata"]["originator_review"]["reason"] == "recovery_review_failed"


def test_recovered_items_are_reviewed_on_the_page_opening_and_it_is_dropped(
    monkeypatch,
):
    """Verification M1: the review reads the claim-independent page opening
    kept at enrichment (not the 500-char claim-selected snippet), and no
    opening survives the review on any path."""
    from app.services import originator_review

    seen = {}

    async def review(items, call):
        seen["inputs"] = [originator_review.review_text(i) for i in items]
        return {}

    monkeypatch.setattr(settings, "ENABLE_ORIGINATOR_REVIEW", True)
    monkeypatch.setattr(originator_review, "review_originators", review)
    item = _phase_a_item()
    item["snippet"] = "A passage chosen for the claim."
    item[originator_review.RECOVERY_OPENING_KEY] = "Opening of the page itself."

    asyncio.run(runner._review_recovery_originators(_FakeClassifier(), [item]))
    assert seen["inputs"] == [("page_opening", "Opening of the page itself.")]
    assert originator_review.RECOVERY_OPENING_KEY not in item
    assert originator_review.PAGE_OPENING_KEY not in item

    # Flag off / no classifier: nothing reviewed, the opening still dropped.
    other = _phase_a_item()
    other[originator_review.RECOVERY_OPENING_KEY] = "x"
    asyncio.run(runner._review_recovery_originators(None, [other]))
    assert originator_review.RECOVERY_OPENING_KEY not in other


def test_the_runner_wires_the_classifier_into_phase_b():
    """Verification M2: the helpers are tested directly, so pin the runner's
    wiring too — without it the review silently never runs."""
    import inspect

    src = inspect.getsource(runner)
    prepare = src[src.index("async def _recover_prepare") : src.index("async def _recover_map")]
    assert '"classifier": classifier,' in prepare
    recover_map = src[src.index("async def _recover_map") :]
    recover_map = recover_map[: recover_map.index("# Phase A")]
    assert 'classifier=prep.get("classifier")' in recover_map
    atomic = src[src.index("async def _map_recovery_atomically") :]
    assert atomic.index("_review_recovery_originators(") < atomic.index(
        "map_evidence_to_specific_elements("
    )
