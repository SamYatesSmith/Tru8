"""A copy must never be scoped against an original that is not counted
(2026-09-30, review of audit/2026-09-30_echo_link_design.md, H1/H2).

The echo gate re-labels a derivative to `context` when its original is counted
on the same side. Three paths used to leave a side with neither:
  1. REF ORDER — the gate driver walked refs in order, so a copy listed before
     its original was scoped while the original still counted, and a later gate
     (temporal here) then scoped the original away.
  2. TWO ORIGINALS — `_index_evidence` kept only the first original in pool
     order; a copy of an uncounted original AND a counted one never fired.
  3. RELATIONSHIP REVIEW — it runs after the gates and can demote the original;
     nothing brought the copies back. They are now restored and then reviewed
     themselves, since a copy relays the content the review just rejected.
"""

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    ClaimMapAnalyzer,
    _restore_orphaned_echoes,
)


@pytest.fixture(autouse=True)
def _echo_gate_on(monkeypatch):
    """The echo gate is OFF by default since 2026-10-01 (link precision
    24-32%, audit/2026-10-01_echo_link_precision.md). These tests pin its
    behaviour and its place in the gate order for when it returns."""
    from app.core.config import settings as _s

    monkeypatch.setattr(_s, "ENABLE_ECHO_SCOPE_GATE", True)


ELEMENT = (
    "The measured consumer price index inflation rate in the UK in "
    "September 2024 was less than 2 percent."
)


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing")


def _claim_map(description="Whether the figures rose."):
    return {
        "claim_id": "0",
        "normalised_claim": "The figures rose.",
        "elements": [
            {
                "element_id": "e1",
                "description": description,
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _parse(evidence, rels, description="Whether the figures rose."):
    claim_map = _claim_map(description)
    response = {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "evidence_refs": [
                    {"evidence_id": e, "relationship": r, "reasoning": "test"}
                    for e, r in rels
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(response, claim_map, evidence)
    return claim_map, claim_map["elements"][0]


# ---------------------------------------------------------------------------
# 1. Ref order: echo runs after every other gate, over all refs
# ---------------------------------------------------------------------------

ORDER_EVIDENCE = [
    {
        # Undated copy: the temporal gate leaves it alone.
        "evidence_id": "ev-copy",
        "url": "https://outlet.example/copy",
        "title": "Inflation report",
        "snippet": "Inflation fell below the target, the statistics office said.",
        "tier": "reporting",
    },
    {
        # The original states a different month: temporal scopes it.
        "evidence_id": "ev-orig",
        "url": "https://stats.example/june",
        "title": "Consumer price inflation: June 2024",
        "snippet": "The CPI rose by 1.9% in the 12 months to June 2024.",
        "tier": "primary",
        "confirmed_copies": [{"id": "ev-copy", "rank": 0}, {"id": "ev-other", "rank": 1}],
    },
]


def test_copy_listed_before_its_original_is_not_orphaned_by_a_later_gate():
    _, elem = _parse(
        ORDER_EVIDENCE,
        [("ev-copy", "supports"), ("ev-orig", "supports")],
        description=ELEMENT,
    )
    assert _rel(elem, "ev-orig") == "context"
    assert "temporal_scope" in elem["basis"]
    # Its original no longer counts, so the copy is the only carrier.
    assert _rel(elem, "ev-copy") == "supports"
    assert "echo_scope" not in elem["basis"]


# ---------------------------------------------------------------------------
# 2. A copy of two originals: only the FIRST is used, on purpose
# ---------------------------------------------------------------------------

TWO_ORIGINALS = [
    {
        # Earlier in pool order, NOT referenced by the element.
        "evidence_id": "ev-a",
        "url": "https://agency-a.example/story",
        "title": "Agency A",
        "snippet": "The figures were published this morning.",
        "tier": "primary",
        "confirmed_copies": [{"id": "ev-copy", "rank": 2}, {"id": "ev-x", "rank": 3}],
    },
    {
        "evidence_id": "ev-b",
        "url": "https://agency-b.example/story",
        "title": "Agency B",
        "snippet": "The figures were published this morning.",
        "tier": "primary",
        "confirmed_copies": [{"id": "ev-copy", "rank": 4}, {"id": "ev-y", "rank": 5}],
    },
    {
        "evidence_id": "ev-copy",
        "url": "https://outlet.example/copy",
        "title": "Outlet copy",
        "snippet": "The figures were published this morning.",
        "tier": "reporting",
    },
]


def test_copy_of_two_originals_is_matched_on_the_first_only():
    """Review H2 asked for ANY original; measured on corpus 0004 that widens the
    gate over weak date-only links, so it is deferred until link precision is
    measured. Changing this must be a deliberate, measured decision."""
    _, elem = _parse(TWO_ORIGINALS, [("ev-b", "supports"), ("ev-copy", "supports")])
    assert _rel(elem, "ev-copy") == "supports"
    assert "echo_scope" not in elem["basis"]


# ---------------------------------------------------------------------------
# 3. Orphaned by a later stage (the relationship review)
# ---------------------------------------------------------------------------

ECHO_EVIDENCE = [
    {
        "evidence_id": "ev-orig",
        "url": "https://agency.example/story",
        "title": "Original",
        "snippet": "The figures were published this morning.",
        "tier": "primary",
        "confirmed_copies": [{"id": "ev-d1", "rank": 6}, {"id": "ev-d2", "rank": 7}],
    },
    {
        "evidence_id": "ev-d1",
        "url": "https://one.example/copy",
        "title": "Copy one",
        "snippet": "The figures were published this morning.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-d2",
        "url": "https://two.example/copy",
        "title": "Copy two",
        "snippet": "The figures were published this morning.",
        "tier": "reporting",
    },
]

RELS = [("ev-orig", "supports"), ("ev-d1", "supports"), ("ev-d2", "supports")]


def _demote(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            ref["relationship"] = "context"


def test_restore_brings_back_copies_whose_original_was_demoted_later():
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    assert _rel(elem, "ev-d1") == "context"
    _demote(elem, "ev-orig")

    restored = _restore_orphaned_echoes(claim_map, ECHO_EVIDENCE)

    assert set(restored) == {("e1", "ev-d1"), ("e1", "ev-d2")}
    assert _rel(elem, "ev-d1") == "supports"
    assert _rel(elem, "ev-d2") == "supports"
    receipt = elem["basis"]["echo_scope"]
    assert receipt["scoped"] == []
    assert receipt["scoped_count"] == 0
    assert {e["evidence_id"] for e in receipt["restored"]} == {"ev-d1", "ev-d2"}
    # The state is re-derived over the restored refs, not left stale.
    assert elem["basis"]["state_derivation"]["supports_count"] == 2


def test_restore_is_a_no_op_while_the_original_still_counts():
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    before = [dict(r) for r in elem["evidence_refs"]]
    assert _restore_orphaned_echoes(claim_map, ECHO_EVIDENCE) == []
    assert elem["evidence_refs"] == before
    assert "restored" not in elem["basis"]["echo_scope"]


def test_restore_is_symmetric_on_the_challenge_side():
    claim_map, elem = _parse(ECHO_EVIDENCE, [(e, "challenges") for e, _ in RELS])
    _demote(elem, "ev-orig")
    _restore_orphaned_echoes(claim_map, ECHO_EVIDENCE)
    assert _rel(elem, "ev-d1") == "challenges"


@pytest.mark.asyncio
async def test_restored_copies_are_reviewed_themselves(monkeypatch):
    """The review demotes the original; its copies come back and are sent to
    the review — ONLY those pairs — because they relay the same content."""
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", True)
    analyzer = ClaimMapAnalyzer()
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    calls = []

    async def fake_complete(_cm, _ev):
        return None

    async def fake_review(_analyzer, cm, _evidence, only=None):
        calls.append(only)
        if only is None:
            _demote(cm["elements"][0], "ev-orig")
        else:
            _demote(cm["elements"][0], "ev-d2")

    import app.services.relationship_scope_review as review_module

    monkeypatch.setattr(analyzer, "_complete_unmapped_sources", fake_complete)
    monkeypatch.setattr(review_module, "review_relationship_scope", fake_review)

    await analyzer._complete_unmapped_evidence(claim_map, ECHO_EVIDENCE)

    assert calls == [None, {("e1", "ev-d1"), ("e1", "ev-d2")}]
    assert _rel(elem, "ev-d1") == "supports"
    assert _rel(elem, "ev-d2") == "context"


@pytest.mark.asyncio
async def test_no_second_review_when_nothing_is_restored(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", True)
    analyzer = ClaimMapAnalyzer()
    claim_map, _ = _parse(ECHO_EVIDENCE, RELS)
    calls = []

    async def fake_complete(_cm, _ev):
        return None

    async def fake_review(_analyzer, _cm, _evidence, only=None):
        calls.append(only)

    import app.services.relationship_scope_review as review_module

    monkeypatch.setattr(analyzer, "_complete_unmapped_sources", fake_complete)
    monkeypatch.setattr(review_module, "review_relationship_scope", fake_review)

    await analyzer._complete_unmapped_evidence(claim_map, ECHO_EVIDENCE)
    assert calls == [None]


def test_plan_review_only_limits_the_pairs():
    from app.services.relationship_scope_review import plan_review

    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    _demote(elem, "ev-orig")
    _restore_orphaned_echoes(claim_map, ECHO_EVIDENCE)
    pairs, total = plan_review(claim_map, ECHO_EVIDENCE, only={("e1", "ev-d1")})
    assert [p["evidence_id"] for p in pairs] == ["ev-d1"]
    assert total == 1


# ---------------------------------------------------------------------------
# Verifier findings on the first build (2026-09-30)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_review_does_not_redraw_pairs_decided_in_an_earlier_run(
    monkeypatch,
):
    """After an echo re-review, the main run's decisions sit in `prior_runs`.
    A later (recovery) review must still treat them as decided."""
    from app.services.relationship_scope_review import review_relationship_scope

    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", True)
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    for ref in elem["evidence_refs"]:
        ref["relationship"] = "supports"
    claim_map["metadata"]["scope_review"] = {
        "status": "complete",
        "pairs": [{"element_id": "e1", "evidence_id": "ev-d1", "status": "compatible"}],
        "prior_runs": [
            {
                "pairs": [
                    {
                        "element_id": "e1",
                        "evidence_id": "ev-orig",
                        "status": "compatible",
                    }
                ]
            }
        ],
    }
    sent = []
    analyzer = ClaimMapAnalyzer()

    async def fake_llm(prompt, **_kw):
        sent.append(prompt)
        return {"pairs": []}

    monkeypatch.setattr(analyzer, "_call_llm", fake_llm)
    await review_relationship_scope(analyzer, claim_map, ECHO_EVIDENCE)

    assert sent, "the undecided pair must still be reviewed"
    body = "".join(sent)
    assert '"ev-d2"' in body
    assert '"ev-orig"' not in body
    assert '"ev-d1"' not in body


@pytest.mark.asyncio
async def test_restore_is_undone_when_its_review_is_cancelled(monkeypatch):
    """A cancelled re-review (the completion timeout) must not leave restored
    copies directional and unreviewed."""
    import asyncio

    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", True)
    analyzer = ClaimMapAnalyzer()
    claim_map, elem = _parse(ECHO_EVIDENCE, RELS)
    _demote(elem, "ev-orig")

    import app.services.relationship_scope_review as review_module

    async def cancelled_review(_a, _cm, _ev, only=None):
        raise asyncio.CancelledError()

    monkeypatch.setattr(review_module, "review_relationship_scope", cancelled_review)
    with pytest.raises(asyncio.CancelledError):
        await analyzer._reconcile_echoes(claim_map, ECHO_EVIDENCE)

    elem = claim_map["elements"][0]
    assert _rel(elem, "ev-d1") == "context"
    assert _rel(elem, "ev-d2") == "context"
    assert "restored" not in elem["basis"]["echo_scope"]


def test_gates_after_echo_still_yield_to_echo(monkeypatch):
    """Precedence is list order: a gate listed AFTER echo must not claim a ref
    echo claims, and one BEFORE echo must. No production gate runs after echo
    since 2026-10-07; `fact_applicability` is used here as a stand-in key."""
    from app.pipeline import claim_map_analyzer as cma

    def gate(key, fires=True):
        return cma._ScopeGate(
            key=key,
            label=key.upper(),
            pins="test",
            summary={},
            fires=lambda _i, _r: fires,
            entry=lambda _i, _r: {},
        )

    analyzer = ClaimMapAnalyzer()
    elem = {
        "element_id": "e1",
        "description": "d",
        "evidence_refs": [{"evidence_id": "ev-d1", "relationship": "supports"}],
    }
    index = cma._index_evidence(ECHO_EVIDENCE)

    monkeypatch.setattr(
        analyzer,
        "_armed_scope_gates",
        lambda *_a: [
            gate("temporal_scope", False),
            gate("echo_scope"),
            gate("fact_applicability"),
        ],
    )
    receipts = analyzer._apply_scope_gates(elem, index, {})
    assert list(receipts) == ["echo_scope"]

    elem["evidence_refs"][0]["relationship"] = "supports"
    monkeypatch.setattr(
        analyzer,
        "_armed_scope_gates",
        lambda *_a: [
            gate("temporal_scope"),
            gate("echo_scope"),
            gate("fact_applicability"),
        ],
    )
    receipts = analyzer._apply_scope_gates(elem, index, {})
    assert list(receipts) == ["temporal_scope"]


def test_receipt_merge_keeps_restored_copies():
    from app.pipeline.claim_map_analyzer import _merge_scope_receipts

    old = {
        "echo_scope": {
            "scoped": [],
            "scoped_count": 0,
            "restored": [{"evidence_id": "a"}],
        }
    }
    new = {"echo_scope": {"scoped": [{"evidence_id": "b"}], "scoped_count": 1}}
    merged = _merge_scope_receipts(old, new)["echo_scope"]
    assert merged["restored"] == [{"evidence_id": "a"}]
    assert merged["scoped_count"] == 1


def test_bench_nets_restored_copies_out_of_echo_counts():
    from scripts.replay_bench.capture import PipelineCaptureHandler

    handler = PipelineCaptureHandler()
    handler._dispatch("[ECHO] elem=e1: 2 ref(s) scoped to context — x")
    handler._dispatch(
        "[ECHO RESTORED] elem=e1: 1 ref(s) restored; their original no longer counts"
    )
    summary = handler.observation().to_dict()["echo_scope_summary"]
    assert summary == {"elements": 1, "scoped_refs": 1}
