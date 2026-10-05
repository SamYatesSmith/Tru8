"""Derivation chains are OFF by default since 2026-10-01.

The primary -> re-reporter link is a real relay 24-32% of the time
(audit/2026-10-01_echo_link_precision.md). With chains off, the grey echo
note and the echo gate have nothing to read. F4 repetition stays on.
"""

from app.core.config import settings
from app.pipeline.claim_map_analyzer import _compute_element_basis
from app.pipeline.runner import annotate_post_classify_structure

TEXT = (
    "The agency reported 1,234 cases in 2024, up 17.5% on the year, "
    "with 456 in the north and 778 in the south."
)


def _pool():
    return {
        "0": [
            {
                "evidence_id": "ev-p",
                "tier": "primary",
                "url": "https://agency.gov.uk/a",
                "source": "agency.gov.uk",
                "text": TEXT,
            },
            {
                "evidence_id": "ev-r1",
                "tier": "reporting",
                "url": "https://paper-one.com/a",
                "source": "paper-one.com",
                "text": TEXT,
            },
            {
                "evidence_id": "ev-r2",
                "tier": "reporting",
                "url": "https://paper-two.com/a",
                "source": "paper-two.com",
                "text": TEXT,
            },
        ]
    }


def _derivatives(pool):
    elem = {
        "element_id": "e1",
        "evidence_refs": [
            {"evidence_id": e["evidence_id"], "relationship": "supports"}
            for e in pool["0"]
        ],
    }
    return _compute_element_basis(elem, pool["0"])["support_structure"]["derivation"]


def test_default_is_off():
    assert settings.ENABLE_DERIVATION_CHAINS is False


def test_off_writes_no_chain_and_no_echo_counts(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", False)
    pool = _pool()
    annotate_post_classify_structure(pool)
    assert not any(e.get("derivation_chain") for e in pool["0"])
    assert _derivatives(pool) == {"originals": 0, "derivative_count": 0}


def test_off_removes_a_chain_written_earlier(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", False)
    pool = _pool()
    pool["0"][0]["derivation_chain"] = ["ev-r1", "ev-r2"]
    annotate_post_classify_structure(pool)
    assert "derivation_chain" not in pool["0"][0]


def test_on_no_longer_writes_unconfirmed_chains(monkeypatch):
    """2026-10-05 (echo link confirmation, plan rev 2 L4): the unconfirmed
    legacy path is gone. Only confirmed records write chains, at the mapping
    join; the post-classify seam only clears."""
    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", True)
    pool = _pool()
    pool["0"][0]["confirmed_copies"] = [{"id": "ev-r1", "rank": 0}]
    annotate_post_classify_structure(pool)
    assert "derivation_chain" not in pool["0"][0]
    assert "confirmed_copies" not in pool["0"][0]
    assert _derivatives(pool) == {"originals": 0, "derivative_count": 0}


def test_confirmed_records_write_the_chain_the_note_reads(monkeypatch):
    from app.services import echo_link_confirmation as elc

    monkeypatch.setattr(settings, "ENABLE_DERIVATION_CHAINS", True)
    pool = _pool()
    records = [
        {
            "original_id": "ev-p",
            "derivative_id": d,
            "status": "confirmed",
            "rank": n,
            "extent": "whole",
        }
        for n, d in enumerate(["ev-r1", "ev-r2"])
    ]
    elc.apply_records(pool["0"], records)
    assert pool["0"][0]["derivation_chain"] == ["ev-r1", "ev-r2"]
    assert _derivatives(pool) == {"originals": 1, "derivative_count": 2}


def test_phase2_is_still_metered_and_the_helper_is_not():
    """2026-10-01: inserting this helper between `@metered` and
    `run_pipeline_phase2` silently moved the search meter onto the helper."""
    from app.pipeline import runner

    assert hasattr(runner.run_pipeline_phase2, "__wrapped__")
    assert not hasattr(runner.annotate_post_classify_structure, "__wrapped__")
