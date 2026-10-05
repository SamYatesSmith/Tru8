"""Echo link confirmation at the pipeline seam (build plan rev 2).

The shared join (H1), the deadline and clean-up (M1/M2), explicit rank (M3),
the note's same-side rule (M5), Strengthen (H3), frozen replay (M4), per-check
dedupe (L5), the flag matrix (L4), the no-op join (L9) and the public payload
(H4). Hosts and text are invented.
"""

import asyncio

import pytest

from app.core.config import settings
from app.pipeline.claim_map_analyzer import (
    ClaimMapAnalyzer,
    _compute_element_basis,
    _index_evidence,
)
from app.services import echo_link_confirmation as elc

ORIG_TEXT = (
    "Consumer prices in Freedonia rose by 3.4 per cent in the twelve months to "
    "June, the Freedonia Statistics Office said in its monthly bulletin today."
)
COPY_TEXT = (
    "Inflation picked up. Consumer prices in Freedonia rose by 3.4 per cent in "
    "the twelve months to June, according to the Freedonia Statistics Office."
)
CUE = "according to the Freedonia Statistics Office"


def _pool():
    def item(eid, tier, url, text):
        return {
            "evidence_id": eid,
            "url": url,
            "source": "Freedonia Statistics Office" if tier == "primary" else "News",
            "title": (
                "Consumer price inflation, June"
                if tier == "primary"
                else "Inflation rises"
            ),
            "tier": tier,
            "text": text,
            "snippet": text,
            "text_provenance": {"original_snippet": text, "passages": []},
        }

    return [
        item("ev-a", "primary", "https://www.fso.gov.fd/cpi", ORIG_TEXT),
        item("ev-b", "reporting", "https://news-one.example/cpi", COPY_TEXT),
        item("ev-c", "reporting", "https://news-two.example/cpi", COPY_TEXT),
    ]


def _relay(n=2):
    rows = [
        {
            "index": i,
            "verdict": "relay",
            "extent": "whole",
            "cue_kind": "attribution",
            "cue": CUE,
            "reason": "r",
        }
        for i in range(n)
    ]
    return rows


def _caller(rows, delay=0.0, calls=None):
    async def call(prompt):
        if calls is not None:
            calls.append(prompt)
        await asyncio.sleep(delay)
        return {"pairs": rows}

    return call


@pytest.fixture
def readers_on(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", True)
    monkeypatch.setattr(settings, "ENABLE_ECHO_SCOPE_GATE", True)
    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", True)


# ---------------------------------------------------------------------------
# Flag matrix (L4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "conf,chains,gate,runs,warn",
    [
        (False, False, False, False, False),
        (True, False, False, False, False),
        (True, True, False, True, False),
        (True, False, True, True, False),
        (True, True, True, True, False),
        (False, True, False, False, True),
        (False, False, True, False, True),
    ],
)
def test_flag_matrix(monkeypatch, conf, chains, gate, runs, warn):
    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", conf)
    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", chains)
    monkeypatch.setattr(settings, "ENABLE_ECHO_SCOPE_GATE", gate)
    assert elc.should_run() is runs
    assert elc.misconfigured() is warn


@pytest.mark.unit
def test_defaults_are_all_off():
    assert settings.ENABLE_ECHO_LINK_CONFIRMATION is False
    assert not elc.should_run()


# ---------------------------------------------------------------------------
# The shared join (H1) and clean-up (M1/M2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_concurrent_callers_all_see_the_links(readers_on):
    pool = _pool()
    evidence = {"0": pool}
    cm = {"metadata": {}}

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=0.05)
        )
        analyzer = ClaimMapAnalyzer()
        analyzer.echo_join = join
        seen = []

        async def caller():
            await analyzer._join_echo_links()
            seen.append(_index_evidence(pool)["ev-b"].original_id)

        await asyncio.gather(caller(), caller(), caller())
        join.close()
        return seen

    assert asyncio.run(go()) == ["ev-a", "ev-a", "ev-a"]
    assert [r["status"] for r in cm["metadata"]["echo_links"]["records"]] == [
        "confirmed",
        "confirmed",
    ]


@pytest.mark.unit
def test_join_wait_is_capped_and_unfinished_pairs_are_receipted(
    readers_on, monkeypatch
):
    monkeypatch.setattr(elc, "JOIN_WAIT_S", 0.05)
    evidence = {"0": _pool()}
    cm = {"metadata": {}}

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=5)
        )
        await join.wait()
        join.close()
        return join

    join = asyncio.run(go())
    recs = cm["metadata"]["echo_links"]["records"]
    assert {r["status"] for r in recs} == {"not_inspected"}
    assert {r["detail"] for r in recs} == {"deadline"}
    assert join.wait_seconds < 1
    assert not any(e.get("confirmed_copies") for e in evidence["0"])


@pytest.mark.unit
def test_finished_calls_survive_the_deadline(readers_on, monkeypatch):
    """Two chunks: one fast, one slow. The fast one's verdicts are kept."""
    monkeypatch.setattr(elc, "CALL_PAIRS", 1)
    monkeypatch.setattr(elc, "JOIN_WAIT_S", 0.3)
    evidence = {"0": _pool()}
    cm = {"metadata": {}}
    n = {"i": 0}

    async def call(prompt):
        n["i"] += 1
        if n["i"] == 2:
            await asyncio.sleep(5)
        return {
            "pairs": [
                {
                    "index": 0,
                    "verdict": "relay",
                    "extent": "whole",
                    "cue_kind": "attribution",
                    "cue": CUE,
                    "reason": "r",
                }
            ]
        }

    async def go():
        join = elc.EchoJoin.start(elc.prepare(evidence), evidence, {"0": cm}, call)
        await join.wait()
        join.close()

    asyncio.run(go())
    statuses = sorted(r["status"] for r in cm["metadata"]["echo_links"]["records"])
    assert statuses == ["confirmed", "not_inspected"]


@pytest.mark.unit
def test_close_without_a_join_says_mapping_failed_and_cancels(readers_on):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=5)
        )
        await asyncio.sleep(0)
        join.close()
        await asyncio.sleep(0)
        return join

    join = asyncio.run(go())
    assert cm["metadata"]["echo_links"]["totals"]["detail"] == "mapping_failed"


@pytest.mark.unit
def test_a_failing_run_leaves_no_links(readers_on):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}

    async def boom(prompt):
        raise RuntimeError("provider down")

    async def go():
        join = elc.EchoJoin.start(elc.prepare(evidence), evidence, {"0": cm}, boom)
        await join.wait()
        join.close()

    asyncio.run(go())
    assert {r["status"] for r in cm["metadata"]["echo_links"]["records"]} == {"failed"}
    assert not any(e.get("confirmed_copies") for e in evidence["0"])


@pytest.mark.unit
def test_no_join_is_a_no_op():
    analyzer = ClaimMapAnalyzer()
    assert analyzer.echo_join is None
    asyncio.run(analyzer._join_echo_links())


@pytest.mark.unit
def test_prepare_drops_the_page_opening(readers_on):
    pool = _pool()
    pool[0][elc.PAGE_OPENING_KEY] = "opening"
    elc.prepare({"0": pool})
    assert elc.PAGE_OPENING_KEY not in pool[0]


@pytest.mark.unit
def test_frozen_replay_skip_writes_a_receipt_and_no_links(readers_on):
    pool = _pool()
    pool[0]["confirmed_copies"] = [{"id": "ev-b", "rank": 0}]
    cm = {"metadata": {}}
    elc.skip({"0": pool}, {"0": cm}, "frozen_replay")
    assert cm["metadata"]["echo_links"]["totals"]["detail"] == "frozen_replay"
    assert "confirmed_copies" not in pool[0]


# ---------------------------------------------------------------------------
# Per-check dedupe (L5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_a_pair_shared_by_two_claims_is_judged_once(readers_on):
    import copy

    p0, p1 = _pool(), copy.deepcopy(_pool())
    for e in p1:
        e["evidence_id"] = e["evidence_id"] + "-c1"
    evidence = {"0": p0, "1": p1}
    cms = {"0": {"metadata": {}}, "1": {"metadata": {}}}
    calls = []

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, cms, _caller(_relay(), calls=calls)
        )
        await join.wait()
        join.close()

    asyncio.run(go())
    assert len(calls) == 1
    assert cms["1"]["metadata"]["echo_links"]["records"][0]["original_id"] == "ev-a-c1"
    assert _index_evidence(p1)["ev-b-c1"].original_id == "ev-a-c1"


# ---------------------------------------------------------------------------
# Rank, not pool order (M3); the cue reaches the receipt
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lowest_rank_original_wins_in_any_pool_order():
    a = {
        "evidence_id": "ev-a",
        "confirmed_copies": [{"id": "ev-x", "rank": 3, "cue": "a cue"}],
    }
    b = {
        "evidence_id": "ev-b",
        "confirmed_copies": [{"id": "ev-x", "rank": 1, "cue": "b cue"}],
    }
    x = {"evidence_id": "ev-x"}
    for order in ([a, b, x], [x, b, a]):
        item = _index_evidence(order)["ev-x"]
        assert item.original_id == "ev-b"
        assert item.echo_cue == "b cue"


@pytest.mark.unit
def test_only_whole_extent_copies_feed_the_gate(readers_on):
    pool = _pool()
    elc.apply_records(
        pool,
        [
            {
                "original_id": "ev-a",
                "derivative_id": "ev-b",
                "status": "confirmed",
                "rank": 0,
                "extent": "whole",
                "cue": CUE,
                "cue_kind": "attribution",
            },
            {
                "original_id": "ev-a",
                "derivative_id": "ev-c",
                "status": "confirmed",
                "rank": 1,
                "extent": "part",
                "cue": CUE,
                "cue_kind": "attribution",
            },
        ],
    )
    assert [c["id"] for c in pool[0]["confirmed_copies"]] == ["ev-b"]
    assert pool[0]["derivation_chain"] == ["ev-b", "ev-c"]
    idx = _index_evidence(pool)
    assert idx["ev-b"].original_id == "ev-a" and idx["ev-c"].original_id is None


@pytest.mark.unit
def test_echo_receipt_carries_the_cue(readers_on):
    pool = _pool()
    elc.apply_records(
        pool,
        [
            {
                "original_id": "ev-a",
                "derivative_id": "ev-b",
                "status": "confirmed",
                "rank": 0,
                "extent": "whole",
                "cue": CUE,
                "cue_kind": "attribution",
            }
        ],
    )
    cm = {
        "claim_id": "c",
        "normalised_claim": "Freedonia inflation was 3.4%.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Freedonia CPI inflation rose.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }
    raw = {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-a",
                        "relationship": "supports",
                        "reasoning": "t",
                    },
                    {
                        "evidence_id": "ev-b",
                        "relationship": "supports",
                        "reasoning": "t",
                    },
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(raw, cm, pool)
    entry = cm["elements"][0]["basis"]["echo_scope"]["scoped"][0]
    assert entry["original_id"] == "ev-a"
    assert entry["cue"] == CUE and entry["cue_kind"] == "attribution"


@pytest.mark.unit
def test_unconfirmed_derivation_chain_never_feeds_the_gate():
    pool = _pool()
    pool[0]["derivation_chain"] = ["ev-b", "ev-c"]
    assert _index_evidence(pool)["ev-b"].original_id is None


# ---------------------------------------------------------------------------
# The note counts only same-side copies (M5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_note_ignores_a_copy_whose_original_is_on_the_other_side():
    pool = [
        {
            "evidence_id": "A",
            "tier": "primary",
            "url": "https://a.example",
            "derivation_chain": ["B1", "B2"],
        },
        {"evidence_id": "B1", "tier": "reporting", "url": "https://b1.example"},
        {"evidence_id": "B2", "tier": "reporting", "url": "https://b2.example"},
        {
            "evidence_id": "D",
            "tier": "primary",
            "url": "https://d.example",
            "derivation_chain": ["C", "E"],
        },
        {"evidence_id": "C", "tier": "reporting", "url": "https://c.example"},
        {"evidence_id": "E", "tier": "reporting", "url": "https://e.example"},
    ]
    elem = {
        "element_id": "e1",
        "evidence_refs": [
            {"evidence_id": "A", "relationship": "supports"},
            {"evidence_id": "B1", "relationship": "supports"},
            {"evidence_id": "C", "relationship": "supports"},
            {"evidence_id": "D", "relationship": "challenges"},
        ],
    }
    d = _compute_element_basis(elem, pool)["support_structure"]["derivation"]
    assert d == {"originals": 1, "derivative_count": 1}


@pytest.mark.unit
def test_note_still_counts_same_side_copies():
    pool = [
        {
            "evidence_id": "A",
            "tier": "primary",
            "url": "https://a.example",
            "derivation_chain": ["B1", "B2"],
        },
        {"evidence_id": "B1", "tier": "reporting", "url": "https://b1.example"},
        {"evidence_id": "B2", "tier": "reporting", "url": "https://b2.example"},
    ]
    elem = {
        "element_id": "e1",
        "evidence_refs": [
            {"evidence_id": e, "relationship": "supports"} for e in ("A", "B1", "B2")
        ],
    }
    d = _compute_element_basis(elem, pool)["support_structure"]["derivation"]
    assert d == {"originals": 1, "derivative_count": 2}


# ---------------------------------------------------------------------------
# Strengthen keeps the links (H3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_strengthen_rebuilds_links_and_receipts_new_pairs(readers_on):
    pool = _pool()
    new = {
        **_pool()[2],
        "evidence_id": "ev-new",
        "url": "https://news-three.example/cpi",
    }
    cm = {
        "metadata": {
            "echo_links": {
                "records": [
                    {
                        "original_id": "ev-a",
                        "derivative_id": "ev-b",
                        "status": "confirmed",
                        "rank": 0,
                        "extent": "whole",
                        "cue": CUE,
                        "cue_kind": "attribution",
                    },
                ],
                "totals": {},
            }
        }
    }
    combined = pool + [new]
    elc.rebuild_after_research(combined, cm, {"ev-new"})
    assert _index_evidence(combined)["ev-b"].original_id == "ev-a"
    added = [
        r
        for r in cm["metadata"]["echo_links"]["records"]
        if r.get("detail") == "re_search"
    ]
    assert ("ev-a", "ev-new") in {(r["original_id"], r["derivative_id"]) for r in added}
    assert _index_evidence(combined)["ev-new"].original_id is None


@pytest.mark.unit
def test_strengthen_with_confirmation_off_has_no_links(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", False)
    pool = _pool()
    pool[0]["confirmed_copies"] = [{"id": "ev-b", "rank": 0}]
    cm = {
        "metadata": {
            "echo_links": {
                "records": [
                    {
                        "original_id": "ev-a",
                        "derivative_id": "ev-b",
                        "status": "confirmed",
                        "rank": 0,
                        "extent": "whole",
                    },
                ]
            }
        }
    }
    elc.rebuild_after_research(pool, cm, set())
    assert "confirmed_copies" not in pool[0]


# ---------------------------------------------------------------------------
# Public payload (H4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_public_payload_has_no_model_reason(readers_on):
    from app.api.v1.response_builder import _claim_map_to_camel_case

    evidence = {"0": _pool()}
    cm = {"elements": [], "metadata": {}}

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay())
        )
        await join.wait()
        join.close()

    asyncio.run(go())
    out = _claim_map_to_camel_case(cm)
    links = out["metadata"]["echoLinks"]
    assert links["records"]
    assert all("reason" not in r for r in links["records"])
    assert "reason" not in str(links)


@pytest.mark.unit
def test_the_join_runs_once_for_every_caller(readers_on, monkeypatch):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}
    applied = []
    real = elc.apply_records
    monkeypatch.setattr(elc, "apply_records", lambda ev, recs: applied.append(1) or real(ev, recs))

    async def go():
        join = elc.EchoJoin.start(elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=0.05))
        analyzer = ClaimMapAnalyzer()
        analyzer.echo_join = join
        await asyncio.gather(*(analyzer._join_echo_links() for _ in range(3)))
        await analyzer._join_echo_links()
        join.close()

    asyncio.run(go())
    assert applied == [1]


@pytest.mark.unit
def test_one_confirmed_copy_writes_no_note_chain(readers_on):
    pool = _pool()
    elc.apply_records(
        pool,
        [{"original_id": "ev-a", "derivative_id": "ev-b", "status": "confirmed", "rank": 0, "extent": "whole"}],
    )
    assert "derivation_chain" not in pool[0]
    assert [c["id"] for c in pool[0]["confirmed_copies"]] == ["ev-b"]


@pytest.mark.unit
def test_note_counts_copies_per_original_not_in_total():
    """Verification M3: two originals, each with two confirmed copies, and one
    copy of each on the side: no single original is repeated, so no note."""
    pool = [
        {"evidence_id": "A", "tier": "primary", "url": "https://a.example", "derivation_chain": ["A1", "A2"]},
        {"evidence_id": "A1", "tier": "reporting", "url": "https://a1.example"},
        {"evidence_id": "A2", "tier": "reporting", "url": "https://a2.example"},
        {"evidence_id": "D", "tier": "primary", "url": "https://d.example", "derivation_chain": ["D1", "D2"]},
        {"evidence_id": "D1", "tier": "reporting", "url": "https://d1.example"},
        {"evidence_id": "D2", "tier": "reporting", "url": "https://d2.example"},
    ]
    elem = {"element_id": "e1", "evidence_refs": [
        {"evidence_id": e, "relationship": "supports"} for e in ("A", "A1", "D", "D1")
    ]}
    d = _compute_element_basis(elem, pool)["support_structure"]["derivation"]
    assert d == {"originals": 2, "derivative_count": 1}
# ---------------------------------------------------------------------------
# Verification H1 (2026-10-05): the REAL mapping paths wait for the join
# ---------------------------------------------------------------------------


def _scaffold(cid="0"):
    return {
        "claim_id": cid,
        "normalised_claim": "Freedonia inflation rose.",
        "claim_type": "empirical",
        "elements": [
            {
                "element_id": "e1",
                "description": "Whether Freedonia inflation rose.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "orientation": None,
        "metadata": {
            "decomposition_model": "t",
            "mapping_model": None,
            "element_count": 1,
            "completed_at": None,
        },
    }


def _mapping(ids):
    return {
        "elements": [
            {
                "element_id": "e1",
                "state": "supported",
                "uncertainty": None,
                "evidence_refs": [
                    {"evidence_id": i, "relationship": "supports", "reasoning": "t"}
                    for i in ids
                ],
            }
        ]
    }


def _rel(cm, eid):
    for ref in cm["elements"][0]["evidence_refs"]:
        if ref["evidence_id"] == eid:
            return getattr(ref["relationship"], "value", ref["relationship"])


@pytest.fixture
def quiet_mapping(monkeypatch, readers_on):
    monkeypatch.setattr(settings, "ENABLE_RELATIONSHIP_REVIEW", False)
    monkeypatch.setattr(settings, "ENABLE_PASSAGE_MAPPING", False)


@pytest.mark.unit
def test_single_claim_mapping_waits_for_the_join(quiet_mapping):
    pool = _pool()
    evidence = {"0": pool}
    cm = _scaffold()

    async def fake_llm(prompt, temperature, max_tokens, label):
        return _mapping(["ev-a", "ev-b"]) if label == "mapping" else None

    async def go():
        analyzer = ClaimMapAnalyzer()
        analyzer._call_llm = fake_llm
        analyzer._last_model_used = "fake"
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=0.05)
        )
        await elc.map_with_join(
            analyzer, [{"claim_map": cm, "evidence": pool}], join, 120, {}
        )

    asyncio.run(go())
    assert _rel(cm, "ev-a") == "supports"
    assert _rel(cm, "ev-b") == "context"
    assert cm["elements"][0]["basis"]["echo_scope"]["scoped"][0]["cue"] == CUE


def _two_claims():
    import copy

    p0, p1 = _pool(), copy.deepcopy(_pool())
    for e in p1:
        e["evidence_id"] += "-1"
    return {"0": p0, "1": p1}, {"0": _scaffold("0"), "1": _scaffold("1")}


@pytest.mark.unit
def test_batch_mapping_waits_for_the_join(quiet_mapping):
    evidence, cms = _two_claims()

    async def fake_llm(prompt, temperature, max_tokens, label):
        if label == "batch_mapping":
            return {
                "claims": [
                    {"claim_index": 0, **_mapping(["ev-a", "ev-b"])},
                    {"claim_index": 1, **_mapping(["ev-a-1", "ev-b-1"])},
                ]
            }
        return None

    async def go():
        analyzer = ClaimMapAnalyzer()
        analyzer._call_llm = fake_llm
        analyzer._last_model_used = "fake"
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, cms, _caller(_relay(), delay=0.05)
        )
        batch = [{"claim_map": cms[k], "evidence": evidence[k]} for k in ("0", "1")]
        await elc.map_with_join(analyzer, batch, join, 120, {})

    asyncio.run(go())
    assert _rel(cms["0"], "ev-b") == "context"
    assert _rel(cms["1"], "ev-b-1") == "context"


@pytest.mark.unit
def test_failed_batch_retries_all_see_the_links(quiet_mapping):
    """The concurrent per-claim retries after a bad batch reply (review H1)."""
    evidence, cms = _two_claims()

    async def fake_llm(prompt, temperature, max_tokens, label):
        if label == "batch_mapping":
            return {"nonsense": True}
        if label == "mapping":
            ids = ["ev-a-1", "ev-b-1"] if "ev-a-1" in prompt else ["ev-a", "ev-b"]
            return _mapping(ids)
        return None

    async def go():
        analyzer = ClaimMapAnalyzer()
        analyzer._call_llm = fake_llm
        analyzer._last_model_used = "fake"
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, cms, _caller(_relay(), delay=0.05)
        )
        batch = [{"claim_map": cms[k], "evidence": evidence[k]} for k in ("0", "1")]
        await elc.map_with_join(analyzer, batch, join, 120, {})

    asyncio.run(go())
    assert _rel(cms["0"], "ev-b") == "context"
    assert _rel(cms["1"], "ev-b-1") == "context"


class _FakeJoin:
    run_seconds, wait_seconds = 1.5, 0.5

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_map_with_join_adds_the_join_wait_to_the_timeout(monkeypatch):
    seen = {}
    real_wait_for = asyncio.wait_for

    async def spy_wait_for(aw, timeout):
        seen["timeout"] = timeout
        return await real_wait_for(aw, timeout)

    monkeypatch.setattr(elc.asyncio, "wait_for", spy_wait_for)
    analyzer = ClaimMapAnalyzer()

    async def ok(batch):
        return None

    analyzer.map_evidence_batch = ok
    asyncio.run(elc.map_with_join(analyzer, [], _FakeJoin(), 120, {}))
    assert seen["timeout"] == 120 + int(elc.JOIN_WAIT_S)
    asyncio.run(elc.map_with_join(analyzer, [], None, 120, {}))
    assert seen["timeout"] == 120


@pytest.mark.unit
@pytest.mark.parametrize(
    "failure", [RuntimeError("mapping broke"), asyncio.TimeoutError()]
)
def test_map_with_join_closes_the_join_when_mapping_fails(failure):
    join = _FakeJoin()
    analyzer = ClaimMapAnalyzer()

    async def boom(batch):
        raise failure

    analyzer.map_evidence_batch = boom
    timings = {}
    with pytest.raises(type(failure)):
        asyncio.run(elc.map_with_join(analyzer, [], join, 120, timings))
    assert join.closed
    assert analyzer.echo_join is None
    assert timings == {"echo_link_confirmation": 1.5, "echo_link_wait": 0.5}


@pytest.mark.unit
def test_close_cancels_a_running_call(readers_on):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}
    state = {}

    async def go():
        join = elc.EchoJoin.start(
            elc.prepare(evidence), evidence, {"0": cm}, _caller(_relay(), delay=5)
        )
        await asyncio.sleep(0.01)
        join.close()
        for _ in range(5):
            await asyncio.sleep(0)
        state["cancelled"] = join._task.cancelled()

    asyncio.run(go())
    assert state["cancelled"] is True


# ---------------------------------------------------------------------------
# Runner steps: plan and start (quick tier, frozen replay, faults)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quick_tier_skips_with_a_receipt_and_drops_openings(readers_on):
    pool = _pool()
    pool[0][elc.PAGE_OPENING_KEY] = "opening"
    evidence = {"0": pool}
    cm = {"metadata": {}}
    plan = elc.plan_for_check(evidence, frozen=False, quick=True)
    assert plan is None and elc.PAGE_OPENING_KEY not in pool[0]

    async def go():
        return elc.start_for_check(
            plan, evidence, {"0": cm}, _caller(_relay()), frozen=False, quick=True
        )

    assert asyncio.run(go()) is None
    assert cm["metadata"]["echo_links"]["totals"]["detail"] == "quick_tier"


@pytest.mark.unit
def test_quick_tier_declares_the_omission_only_while_the_stage_is_on(monkeypatch):
    from app.core.tier_limitations import limitations_for_tier

    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", False)
    assert "no_echo_link_confirmation" not in limitations_for_tier("quick")
    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", True)
    monkeypatch.setattr(settings, "ENABLE_ECHO_SCOPE_GATE", True)
    assert "no_echo_link_confirmation" in limitations_for_tier("quick")
    assert "no_echo_link_confirmation" not in limitations_for_tier("full")


@pytest.mark.unit
def test_planning_fault_means_no_links_and_a_receipt(readers_on, monkeypatch):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}

    def broken(_ev):
        raise RuntimeError("bad pool")

    monkeypatch.setattr(elc, "prepare", broken)
    plan = elc.plan_for_check(evidence, frozen=False, quick=False)
    assert plan is None

    async def go():
        return elc.start_for_check(
            plan, evidence, {"0": cm}, _caller(_relay()), frozen=False, quick=False
        )

    assert asyncio.run(go()) is None
    assert cm["metadata"]["echo_links"]["totals"]["detail"] == "planning_failed"


@pytest.mark.unit
def test_frozen_replay_start_writes_a_receipt(readers_on):
    evidence = {"0": _pool()}
    cm = {"metadata": {}}

    async def go():
        return elc.start_for_check(
            None, evidence, {"0": cm}, _caller(_relay()), frozen=True, quick=False
        )

    assert asyncio.run(go()) is None
    assert cm["metadata"]["echo_links"]["totals"]["detail"] == "frozen_replay"


@pytest.mark.unit
def test_stage_off_writes_nothing(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_ECHO_LINK_CONFIRMATION", False)
    evidence = {"0": _pool()}
    cm = {"metadata": {}}
    assert elc.plan_for_check(evidence, frozen=False, quick=False) is None

    async def go():
        return elc.start_for_check(
            None, evidence, {"0": cm}, _caller(_relay()), frozen=True, quick=True
        )

    assert asyncio.run(go()) is None
    assert cm == {"metadata": {}}


@pytest.mark.unit
def test_cue_must_match_case():
    a = {**_pool()[0], "url": "https://www.who.int/x", "source": "", "title": ""}
    b = {
        **_pool()[1],
        "text_provenance": {
            "original_snippet": "Experts who said the rise was expected.",
            "passages": [],
        },
    }
    row = {
        "verdict": "relay",
        "extent": "whole",
        "cue_kind": "attribution",
        "cue": "Experts WHO said the rise",
    }
    out = elc.validate(row, a, b, elc.verbatim_text(a), elc.verbatim_text(b))
    assert out["status"] == elc.CUE_NOT_FOUND


@pytest.mark.unit
def test_note_ignores_two_copies_of_an_other_side_original():
    pool = [
        {"evidence_id": "A", "tier": "primary", "url": "https://a.example", "derivation_chain": ["A1", "A2"]},
        {"evidence_id": "A1", "tier": "reporting", "url": "https://a1.example"},
        {"evidence_id": "A2", "tier": "reporting", "url": "https://a2.example"},
        {"evidence_id": "D", "tier": "primary", "url": "https://d.example", "derivation_chain": ["C1", "C2"]},
        {"evidence_id": "C1", "tier": "reporting", "url": "https://c1.example"},
        {"evidence_id": "C2", "tier": "reporting", "url": "https://c2.example"},
    ]
    elem = {"element_id": "e1", "evidence_refs": [
        {"evidence_id": "A", "relationship": "supports"},
        {"evidence_id": "C1", "relationship": "supports"},
        {"evidence_id": "C2", "relationship": "supports"},
        {"evidence_id": "D", "relationship": "challenges"},
    ]}
    d = _compute_element_basis(elem, pool)["support_structure"]["derivation"]
    assert d == {"originals": 1, "derivative_count": 0}
