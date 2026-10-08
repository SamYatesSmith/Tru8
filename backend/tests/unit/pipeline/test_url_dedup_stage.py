"""The REAL cross-claim URL dedup stage (`runner._dedup_urls_across_claims`).

`test_double_cap_dedup.py` exercises a copy of the algorithm; neither the unit
suite nor the replay bench ever ran the runner's own cap (review 2026-10-08,
F8). These tests pin its behaviour, and the receipt for items it drops because
they carry no URL (F9, invariant #5).
"""

import logging

import pytest

from app.pipeline import runner
from app.pipeline.runner import _dedup_urls_across_claims


@pytest.fixture(autouse=True)
def _cap_two(monkeypatch):
    monkeypatch.setattr(runner.settings, "MAX_CLAIMS_PER_URL", 2)


def _ev(url, score=0.5, **extra):
    return {"url": url, "relevance_score": score, "title": f"t:{url}", **extra}


def _urls(evidence):
    return {pos: [e["url"] for e in items] for pos, items in evidence.items()}


def test_a_url_on_two_claims_is_kept_on_both():
    evidence = {"0": [_ev("https://a")], "1": [_ev("https://a")]}
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": ["https://a"], "1": ["https://a"]}


def test_a_third_claim_loses_the_url_to_the_two_best_scores():
    evidence = {
        "0": [_ev("https://a", 0.2)],
        "1": [_ev("https://a", 0.9)],
        "2": [_ev("https://a", 0.5)],
    }
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": [], "1": ["https://a"], "2": ["https://a"]}


def test_a_score_tie_goes_to_the_lower_position():
    evidence = {pos: [_ev("https://a", 0.5)] for pos in ("0", "1", "2")}
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": ["https://a"], "1": ["https://a"], "2": []}


def test_same_claim_duplicates_are_left_alone():
    evidence = {"0": [_ev("https://a"), _ev("https://a")]}
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": ["https://a", "https://a"]}


def test_items_come_back_grouped_by_url_in_first_seen_order():
    """F10: the rebuild groups each claim's items by URL, in the order URLs
    were first seen across the pool — so a repeat moves up beside its twin."""
    evidence = {
        "0": [_ev("https://b"), _ev("https://a"), _ev("https://b")],
        "1": [_ev("https://c"), _ev("https://a")],
    }
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {
        "0": ["https://b", "https://b", "https://a"],
        "1": ["https://a", "https://c"],
    }


def test_every_claim_keeps_its_key():
    evidence = {"0": [_ev("https://a")], "1": []}
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert set(out) == {"0", "1"}


def test_frozen_replay_returns_the_input_untouched():
    evidence = {pos: [_ev("https://a")] for pos in ("0", "1", "2")}
    out = _dedup_urls_across_claims(evidence, True, None, {})
    assert out is evidence


def test_an_empty_pool_is_returned_as_is():
    evidence = {}
    assert _dedup_urls_across_claims(evidence, False, None, {}) is evidence


def test_the_stage_is_timed():
    timings = {}
    _dedup_urls_across_claims({"0": [_ev("https://a")]}, False, None, timings)
    assert "url_dedup" in timings


@pytest.mark.parametrize("missing", ["", None, "absent"])
def test_an_item_without_a_url_is_dropped(missing):
    """Kept as a drop: a `None` URL would fail the whole save (`Evidence.url`
    is a required string), and an empty one gives the reader nothing to open."""
    item = {"title": "No link", "source": "Somewhere"}
    if missing != "absent":
        item["url"] = missing
    evidence = {"0": [_ev("https://a"), item]}
    out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": ["https://a"]}


def test_a_dropped_url_less_item_leaves_a_receipt(caplog):
    """F9 / invariant #5: every exclusion has a receipt."""
    item = {"url": "", "title": "Rate table", "source": "Some API"}
    evidence = {"0": [_ev("https://a")], "1": [item]}
    with caplog.at_level(logging.INFO, logger=runner.logger.name):
        _dedup_urls_across_claims(evidence, False, None, {})
    receipts = [
        r.getMessage() for r in caplog.records if "[URL LEDGER]" in r.getMessage()
    ]
    assert len(receipts) == 1
    line = receipts[0]
    assert "claim=1" in line
    assert "dropped" in line and "stage=url_dedup" in line and "no_url" in line
    assert "Some API" in line and "Rate table" in line


def test_an_odd_source_or_title_does_not_break_the_stage(caplog):
    """The receipt must never turn a drop into a failed stage: on an exception
    the stage returns its input, and the URL-less item would reach the save."""
    item = {"url": None, "title": {"nested": 1}, "source": 42}
    evidence = {"0": [_ev("https://a"), item]}
    with caplog.at_level(logging.INFO, logger=runner.logger.name):
        out = _dedup_urls_across_claims(evidence, False, None, {})
    assert _urls(out) == {"0": ["https://a"]}
    assert any("no_url" in r.getMessage() for r in caplog.records)


class _Ledger:
    def __init__(self):
        self.records = []

    def record(self, stage, **fields):
        self.records.append((stage, fields))


def test_the_ledger_counts_cap_losers_and_url_less_drops():
    """Pins the debug-ledger path (DEBUG_EVIDENCE_LEDGER), which nothing else
    exercises. URL-less drops count in `removed` but are not casualties."""
    ledger = _Ledger()
    evidence = {
        "0": [_ev("https://a", 0.9), {"url": "", "title": "x"}],
        "1": [_ev("https://a", 0.8)],
        "2": [_ev("https://a", 0.1)],
    }
    _dedup_urls_across_claims(evidence, False, ledger, {})
    assert ledger.records == [
        (
            "url_dedup",
            {
                "in_count": 4,
                "out_count": 2,
                "removed": 2,
                "casualties_per_claim": {
                    "2": [{"url": "https://a", "won_by": "0"}],
                },
            },
        )
    ]
