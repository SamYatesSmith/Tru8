"""Cited-source gap note (Build B, design §§11.8, 12.2, 12.6, 17).

Presence by host across the whole record (verification 2026-10-06), the
citing item must be shown, the runner seam with the gap note alone (no
search), fail-closed behaviour, the re-search recompute, and the payload.
No model, search or fetch is ever called: every external step is a fake.
"""

import asyncio
import inspect
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.services import cited_source as cs

CUE = "a new Bloomberg analysis finds Trump made nearly 28,700 trades"
CLAIM = "Donald Trump made almost 28,700 trades of securities since 2025"


def _item(eid, url, text=None, status="shown"):
    item = {"evidence_id": eid, "url": url, "receipt_status": status, "text": "d"}
    if text is not None:
        item["text_provenance"] = {"original_snippet": text, "passages": []}
    return item


def _name(name="Bloomberg", cue=CUE, status="accepted", citing_id="ev-1"):
    return {
        "name": name,
        "kind": "analysis",
        "cue": cue,
        "status": status,
        "citing_id": citing_id,
    }


COPY = _item("ev-1", "https://finance.yahoo.com/x", "Reporters say " + CUE)
ORIGINAL = _item(
    "ev-2", "https://www.bloomberg.com/graphics/x", "Trump made 28,700 trades"
)


# ---------------------------------------------------------------------------
# Presence (§12.2)
# ---------------------------------------------------------------------------


def _missing(names, claim_items, record_items=None):
    return cs.missing_cited_sources(
        names, claim_items, claim_items if record_items is None else record_items
    )


NOTE = [{"name": "Bloomberg", "cue": CUE}]


@pytest.mark.unit
def test_present_when_the_bodys_own_host_is_shown():
    assert _missing([_name()], [COPY, ORIGINAL]) == []


@pytest.mark.unit
def test_absent_when_only_copies_cite_it():
    assert _missing([_name()], [COPY]) == NOTE


@pytest.mark.unit
def test_snippet_only_page_of_the_body_is_in_the_record():  # MEDIUM-1
    # A paywalled (403) original is listed in the report: never "absent".
    snippet_only = _item("ev-2", "https://www.bloomberg.com/graphics/x")
    assert _missing([_name()], [COPY, snippet_only]) == []


@pytest.mark.unit
def test_any_shown_page_on_the_bodys_host_counts():
    index = _item("ev-2", "https://www.bloomberg.com/", "Markets, news and video")
    assert _missing([_name()], [COPY, index]) == []


@pytest.mark.unit
def test_a_copy_on_another_host_never_counts():
    copy2 = _item("ev-3", "https://fortune.com/bloomberg-trades", "28,700 trades")
    assert _missing([_name()], [COPY, copy2]) == NOTE


@pytest.mark.unit
def test_the_bodys_page_under_another_claim_counts():  # MEDIUM-2
    assert _missing([_name()], [COPY], [COPY, ORIGINAL]) == []


@pytest.mark.unit
def test_excluded_items_do_not_count():
    excluded = {**ORIGINAL, "receipt_status": "excluded"}
    assert _missing([_name()], [COPY, excluded]) == NOTE


@pytest.mark.unit
def test_unmapped_items_are_in_the_record_and_count():
    # The Evidence lens lists unmapped sources; the note must not say a
    # listed source is absent.
    unmapped = {**ORIGINAL, "receipt_status": "unmapped"}
    assert _missing([_name()], [COPY, unmapped]) == []


@pytest.mark.unit
@pytest.mark.parametrize("citing", ["excluded", "absent", "no_id"])
def test_a_cue_whose_source_is_not_shown_writes_no_note(citing):  # LOW-5
    if citing == "excluded":
        items, name = [{**COPY, "receipt_status": "excluded"}], _name()
    elif citing == "absent":
        items, name = [COPY], _name(citing_id="ev-gone")
    else:
        items, name = [COPY], _name(citing_id=None)
    assert _missing([name], items) == []


@pytest.mark.unit
def test_names_are_deduplicated_case_insensitively():
    names = [_name(), _name("bloomberg", "bloomberg said it in a note"), _name()]
    assert _missing(names, [COPY]) == NOTE


@pytest.mark.unit
def test_a_name_without_a_cue_writes_nothing():
    assert _missing([{"name": "Bloomberg", "citing_id": "ev-1"}], [COPY]) == []


@pytest.mark.unit
def test_accepted_names_reads_every_guard_passing_status():
    stored = {
        "names": [
            _name("A", status="accepted"),
            _name("B", status="already_present"),
            _name("C", status="over_query_cap"),
            _name("D", status="self_outlet"),
            _name("E", status="cue_not_found"),
        ]
    }
    assert [n["name"] for n in cs.accepted_names(stored)] == ["A", "B", "C"]
    assert cs.accepted_names(None) == []


# ---------------------------------------------------------------------------
# Runner seam
# ---------------------------------------------------------------------------


@pytest.fixture
def no_network(monkeypatch):
    """Record name calls (the module has no search or fetch path)."""
    calls = {"names": 0}

    async def names(claims, evidence):
        calls["names"] += 1
        return {
            "_stats": {"status": "ok", "items": 1},
            "0": {
                "accepted": [{**_name(), "document": "", "citing_id": "ev-1"}],
                "receipts": [
                    _name(),
                    {**_name("the company"), "status": "vague_name"},
                ],
                "status": "ok",
            },
        }

    monkeypatch.setattr(cs, "name_cited_sources_default", names)
    return calls


def _flags(monkeypatch, note):
    monkeypatch.setattr(settings, "ENABLE_CITED_SOURCE_GAP_NOTE", note)


def _run(evidence, *, frozen=False, quick=False):
    """start -> step 2 -> (B3 receipts) -> finish, as runner.py calls them."""
    claims = [
        {"position": int(pos), "text": CLAIM, "claim_map": {"metadata": {}}}
        for pos in sorted(evidence)
    ]
    cms = {str(c["position"]): c["claim_map"] for c in claims}

    async def go():
        task = cs.start_names(claims, evidence, frozen=frozen, quick=quick)
        await cs.after_post_filter(
            claims, evidence, cms, task, frozen=frozen, quick=quick
        )
        await cs.finish_gap_note(claims, evidence, task)
        return task

    task = asyncio.run(go())
    return claims[0]["claim_map"], task


@pytest.mark.unit
def test_gap_note_alone_names_without_searching_and_writes_missing(
    monkeypatch, no_network
):
    _flags(monkeypatch, note=True)
    cm, task = _run({"0": [dict(COPY)]})
    assert task is not None
    assert no_network == {"names": 1}
    rec = cm["metadata"]["cited_sources"]
    assert rec["missing"] == [{"name": "Bloomberg", "cue": CUE}]
    assert rec["queries"] == []
    assert rec["totals"]["follow"] == "off"
    assert [r["status"] for r in rec["names"]] == ["accepted", "vague_name"]


@pytest.mark.unit
def test_gap_note_alone_clears_when_the_original_is_in_the_record(
    monkeypatch, no_network
):
    _flags(monkeypatch, note=True)
    cm, _ = _run({"0": [dict(COPY), dict(ORIGINAL)]})
    assert cm["metadata"]["cited_sources"]["missing"] == []


@pytest.mark.unit
def test_both_flags_off_start_no_task_and_write_no_field(monkeypatch, no_network):
    _flags(monkeypatch, note=False)
    cm, task = _run({"0": [dict(COPY)]})
    assert task is None
    assert no_network == {"names": 0}
    assert "cited_sources" not in cm["metadata"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "frozen,quick,detail", [(True, False, "frozen_replay"), (False, True, "quick_tier")]
)
def test_gap_note_skips_replay_and_quick_with_a_receipt(
    monkeypatch, no_network, frozen, quick, detail
):
    _flags(monkeypatch, note=True)
    cm, task = _run({"0": [dict(COPY)]}, frozen=frozen, quick=quick)
    assert task is None and no_network["names"] == 0
    rec = cm["metadata"]["cited_sources"]
    assert rec["totals"]["detail"] == detail
    assert "missing" not in rec  # LOW-1: a skip is not "none missing"


@pytest.mark.unit
@pytest.mark.parametrize("fault", ["raises", "times_out", "invalid"])
def test_a_failed_model_call_writes_no_missing(monkeypatch, fault):
    """LOW-1, the PRODUCTION path: the real `name_cited_sources_default` and
    `name_cited_sources` run; only the Gemini call is faked. They catch the
    fault themselves and return status `failed` / `invalid_response`."""
    from app.services import google_ai

    _flags(monkeypatch, note=True)
    monkeypatch.setattr(settings, "CITED_SOURCE_NAME_TIMEOUT_S", 0.05)

    async def call(prompt, **kwargs):
        if fault == "raises":
            raise RuntimeError("model down")
        if fault == "times_out":
            await asyncio.sleep(1)
        return {"not_claims": []}, {}

    monkeypatch.setattr(google_ai, "call_google_ai_with_usage", call)
    cm, task = _run({"0": [dict(COPY)]})
    assert task is not None
    rec = cm["metadata"]["cited_sources"]
    assert rec["totals"]["status"] == (
        "invalid_response" if fault == "invalid" else "failed"
    )
    assert "missing" not in rec


@pytest.mark.unit
def test_the_bodys_page_under_another_claim_clears_the_note(
    monkeypatch, no_network
):  # MEDIUM-2, end to end through the seam
    _flags(monkeypatch, note=True)
    cm, _ = _run({"0": [dict(COPY)], "1": [dict(ORIGINAL)]})
    assert cm["metadata"]["cited_sources"]["missing"] == []


@pytest.mark.unit
def test_a_raising_name_task_means_no_note_and_no_failed_check(monkeypatch):
    _flags(monkeypatch, note=True)

    async def broken(claims, evidence):
        raise RuntimeError("model down")

    monkeypatch.setattr(cs, "name_cited_sources_default", broken)
    cm, _ = _run({"0": [dict(COPY)]})
    rec = cm["metadata"]["cited_sources"]
    assert rec["totals"]["detail"] == "failed"
    assert "missing" not in rec


@pytest.mark.unit
def test_gap_note_is_off_by_default_and_declared_on_quick_only_while_on(
    monkeypatch,
):
    from app.core.tier_limitations import limitations_for_tier

    assert settings.ENABLE_CITED_SOURCE_GAP_NOTE is False
    _flags(monkeypatch, note=False)
    assert "no_cited_source_gap_note" not in limitations_for_tier("quick")
    _flags(monkeypatch, note=True)
    assert "no_cited_source_gap_note" in limitations_for_tier("quick")
    assert "no_cited_source_gap_note" not in limitations_for_tier("full")


@pytest.mark.unit
def test_runner_wires_the_seam_and_decides_the_note_after_recovery_and_receipts():
    from app.pipeline import runner

    src = inspect.getsource(runner)
    start = src.index("_cs.start_names(")
    step2 = src.index("_cs.after_post_filter(")
    recovery = src.index("Stage 5.1: Coverage Recovery")
    receipts = src.index("_apply_post_mapping_receipts(claim.get(")
    finish = src.index("_cs.finish_gap_note(")
    assert start < step2 < recovery < receipts < finish
    assert "name_cited_sources_default" not in src  # only through the seam


@pytest.mark.unit
def test_runner_passes_the_real_tier_and_replay_to_both_seam_calls():
    """LOW-2: kills the `quick=False` / `frozen=False` runner mutants."""
    import re

    from app.pipeline import runner

    src = inspect.getsource(runner)
    for call in ("_cs.start_names(", "_cs.after_post_filter("):
        at = src.index(call)
        body = src[at : src.index("\n    )", at)]
        assert re.search(r"frozen=_is_frozen_evidence_replay,", body), call
        assert re.search(r'quick=config\.mode == "quick",', body), call


# ---------------------------------------------------------------------------
# Re-search recompute (no new name call)
# ---------------------------------------------------------------------------


def _research(monkeypatch, found_url, found_text, record_extra=()):
    from app.pipeline import re_search

    async def no_names(*a, **k):
        raise AssertionError("re-search must not make a name call")

    monkeypatch.setattr(cs, "name_cited_sources_default", no_names)
    monkeypatch.setattr(re_search.settings, "ENABLE_EVIDENCE_DISTILLATION", False)
    planner = SimpleNamespace(
        plan_queries_batch=AsyncMock(return_value=[{"queries": ["q"]}])
    )
    retriever = SimpleNamespace(
        retrieve_evidence_for_claims=AsyncMock(
            return_value={
                "evidence_by_claim": {
                    "0": [
                        {
                            "url": found_url,
                            "title": "New",
                            "text": found_text,
                            "_full_text": found_text,
                            "tier": "primary",
                        }
                    ]
                }
            }
        )
    )
    classifier = SimpleNamespace(classify_batch=AsyncMock(side_effect=lambda x: x))

    async def map_evidence(cm, evidence):
        return cm

    analyzer = SimpleNamespace(map_evidence_to_elements=map_evidence)
    for mod, value in (
        ("app.utils.query_planner", SimpleNamespace(get_query_planner=lambda: planner)),
        ("app.pipeline.retrieve", SimpleNamespace(EvidenceRetriever=lambda: retriever)),
        (
            "app.pipeline.evidence_classifier",
            SimpleNamespace(EvidenceClassifier=lambda: classifier),
        ),
        (
            "app.pipeline.claim_map_analyzer",
            SimpleNamespace(ClaimMapAnalyzer=lambda: analyzer),
        ),
    ):
        monkeypatch.setitem(sys.modules, mod, value)
    claim_map = {
        "elements": [{"element_id": "e1", "description": "Trades"}],
        "metadata": {
            "cited_sources": {
                "names": [_name()],
                "queries": [],
                "missing": [{"name": "Bloomberg", "cue": CUE}],
            }
        },
    }
    stored_copy = {**COPY, "snippet": "Reporters say " + CUE, "id": "row-1"}
    claim = {"text": CLAIM, "claimMap": claim_map, "evidence": [stored_copy]}
    if record_extra:
        claim["record_evidence"] = [stored_copy, *record_extra]
    updated, _ = asyncio.run(
        re_search.research_claim(
            claim,
            ["e1"],
            AsyncMock(),
        )
    )
    return updated["metadata"]["cited_sources"]


@pytest.mark.unit
def test_research_that_finds_the_original_clears_the_note(monkeypatch):
    rec = _research(
        monkeypatch,
        "https://www.bloomberg.com/graphics/trades",
        "Bloomberg analysis: Trump made 28,700 trades",
    )
    assert rec["missing"] == []


@pytest.mark.unit
def test_research_that_finds_only_another_copy_keeps_the_note(monkeypatch):
    rec = _research(
        monkeypatch,
        "https://fortune.com/bloomberg-trades",
        "Per Bloomberg, Trump made 28,700 trades",
    )
    assert rec["missing"] == [{"name": "Bloomberg", "cue": CUE}]


@pytest.mark.unit
def test_research_sees_the_original_under_another_claim(monkeypatch):  # MEDIUM-2
    rec = _research(
        monkeypatch,
        "https://fortune.com/bloomberg-trades",
        "Per Bloomberg, Trump made 28,700 trades",
        record_extra=[dict(ORIGINAL)],
    )
    assert rec["missing"] == []


@pytest.mark.unit
def test_recompute_never_adds_a_note_the_run_did_not_write():
    cm = {"metadata": {"cited_sources": {"names": [_name()]}}}
    assert cs.recompute_missing(cm, [COPY], [COPY]) is False
    assert "missing" not in cm["metadata"]["cited_sources"]


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_camel_case_payload_carries_the_note_verbatim():
    from app.api.v1.response_builder import _claim_map_to_camel_case

    cm = {
        "elements": [],
        "metadata": {
            "cited_sources": {
                "names": [_name()],
                "missing": [{"name": "Bloomberg", "cue": CUE}],
            }
        },
    }
    out = _claim_map_to_camel_case(cm)
    assert out["metadata"]["citedSources"]["missing"] == [
        {"name": "Bloomberg", "cue": CUE}
    ]
