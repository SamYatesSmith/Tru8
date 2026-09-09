"""The same-study scope gate (2026-09-09, Track Q — Astra finding 10) through
the real mapping parser.

Three hosts of ONE trial — the journal article, its PubMed abstract and the
PMC full text — share a DOI. The state function weighs each by tier, so they
read as three independent primaries (weight 9) for one observation. The gate
keeps the first carrier on a side (highest tier weight, then earliest in the
element's refs) directional and re-labels every other host of that study on
that side `context`, with a receipt naming the counted carrier (invariant #5).

Identity is a shared persistent identifier ONLY. Two papers about one trial
are two papers; a host mapped to the OTHER side is a disagreement to show.
"""

import pytest

from app.core.config import settings
from app.models.claim_map import ElementState
from app.pipeline.claim_map_analyzer import _SCOPE_RECEIPT_KEYS, ClaimMapAnalyzer
from app.utils.study_identity import study_identifier

DOI = "10.1056/NEJMoa2307563"
EVIDENCE = [
    {
        "evidence_id": "ev-journal",
        "url": f"https://www.nejm.org/doi/full/{DOI}",
        "title": "Semaglutide and cardiovascular outcomes",
        "snippet": "MACE occurred in 6.5% versus 8.0% of participants.",
        "tier": "primary",
    },
    {
        "evidence_id": "ev-pubmed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37952131/",
        "title": "Semaglutide and cardiovascular outcomes [abstract]",
        "snippet": f"doi: {DOI}. MACE occurred in 6.5% versus 8.0%.",
        "tier": "primary",
    },
    {
        "evidence_id": "ev-pmc",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10000001/",
        "title": "Semaglutide and cardiovascular outcomes (full text)",
        "snippet": f"https://doi.org/{DOI} — MACE occurred in 6.5% versus 8.0%.",
        "tier": "reporting",
    },
    {
        "evidence_id": "ev-other",
        "url": "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(24)00001-1",
        "title": "A different study",
        "snippet": "doi: 10.1016/S0140-6736(24)00001-1. Independent finding.",
        "tier": "primary",
    },
    {
        "evidence_id": "ev-news",
        "url": "https://news.example/select-results",
        "title": "News report on the trial",
        "snippet": "The trial reported a 20% reduction.",
        "tier": "reporting",
    },
]


def _claim_map():
    # No subjects, no jurisdiction, no month-pinned wording, no derivation
    # chains: only the same-study gate can arm here.
    return {
        "claim_id": "0",
        "normalised_claim": "The drug reduced events.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Whether the drug reduced events.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": {},
    }


def _parse(rels, evidence=EVIDENCE):
    analyzer = ClaimMapAnalyzer()
    claim_map = _claim_map()
    analyzer._parse_mapping_response(
        {
            "elements": [
                {
                    "element_id": "e1",
                    "state": "supported",
                    "evidence_refs": [
                        {"evidence_id": eid, "relationship": rel, "reasoning": "test"}
                        for eid, rel in rels
                    ],
                }
            ]
        },
        claim_map,
        evidence,
    )
    return claim_map["elements"][0]


def _rel(elem, evidence_id):
    for ref in elem["evidence_refs"]:
        if ref["evidence_id"] == evidence_id:
            return getattr(ref["relationship"], "value", ref["relationship"])
    raise AssertionError(f"{evidence_id} missing from refs")


# ---------------------------------------------------------------------------
# Identity extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ev,expected",
    [
        ({"url": f"https://www.nejm.org/doi/full/{DOI}"}, "doi:10.1056/nejmoa2307563"),
        ({"url": f"https://doi.org/{DOI}?via=x"}, "doi:10.1056/nejmoa2307563"),
        ({"url": "https://pubmed.ncbi.nlm.nih.gov/37952131/"}, "pmid:37952131"),
        (
            {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10000001/"},
            "pmc:PMC10000001",
        ),
        (
            {"url": "https://x.example", "snippet": f"See doi:{DOI}."},
            "doi:10.1056/nejmoa2307563",
        ),
        (
            {"url": "https://x.example", "snippet": "Cites PMID 37952131 in passing."},
            None,
        ),
        ({"url": "https://x.example", "title": "SELECT trial results"}, None),
        ({}, None),
    ],
)
def test_study_identifier_reads_persistent_ids_only(ev, expected):
    assert study_identifier(ev) == expected


# ---------------------------------------------------------------------------
# Hosts of one study count once per side
# ---------------------------------------------------------------------------


def test_three_hosts_of_one_study_count_once():
    elem = _parse(
        [
            ("ev-pubmed", "supports"),
            ("ev-journal", "supports"),
            ("ev-pmc", "supports"),
            ("ev-other", "supports"),
        ]
    )
    # ev-pubmed identifies itself by DOI in its text; ev-journal by URL.
    # Both are primary; ev-pubmed comes first in the refs, so it carries.
    assert _rel(elem, "ev-pubmed") == "supports"
    assert _rel(elem, "ev-journal") == "context"
    assert _rel(elem, "ev-pmc") == "context"
    assert _rel(elem, "ev-other") == "supports"
    sd = elem["basis"]["state_derivation"]
    assert sd["supports_count"] == 2
    assert elem["state"] == ElementState.supported
    assert len(elem["evidence_refs"]) == 4


def test_the_highest_tier_host_carries_even_when_listed_later():
    """A reporting-tier full-text copy listed first must not out-rank the
    primary journal article: weight, then position."""
    elem = _parse([("ev-pmc", "supports"), ("ev-journal", "supports")])
    assert _rel(elem, "ev-journal") == "supports"
    assert _rel(elem, "ev-pmc") == "context"


def test_the_receipt_names_the_counted_carrier():
    elem = _parse([("ev-journal", "supports"), ("ev-pubmed", "supports")])
    receipt = elem["basis"]["same_study_scope"]
    entry = next(e for e in receipt["scoped"] if e["evidence_id"] == "ev-pubmed")
    assert entry["was"] == "supports"
    assert entry["counted_as"] == "ev-journal"
    assert entry["study_id"] == "doi:10.1056/nejmoa2307563"


def test_symmetric_for_challenges():
    elem = _parse([("ev-journal", "challenges"), ("ev-pubmed", "challenges")])
    assert _rel(elem, "ev-journal") == "challenges"
    assert _rel(elem, "ev-pubmed") == "context"


def test_a_host_on_the_other_side_is_a_disagreement_not_a_duplicate():
    elem = _parse([("ev-journal", "supports"), ("ev-pubmed", "challenges")])
    assert _rel(elem, "ev-journal") == "supports"
    assert _rel(elem, "ev-pubmed") == "challenges"
    assert "same_study_scope" not in elem["basis"]


def test_a_trial_name_alone_is_not_identity():
    """ev-news is about the same trial but carries no identifier: two
    papers about one trial are two papers."""
    elem = _parse([("ev-journal", "supports"), ("ev-news", "supports")])
    assert _rel(elem, "ev-news") == "supports"
    assert "same_study_scope" not in elem["basis"]


def test_flag_off_leaves_every_host_directional(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SAME_STUDY_SCOPE_GATE", False)
    elem = _parse([("ev-journal", "supports"), ("ev-pubmed", "supports")])
    assert _rel(elem, "ev-pubmed") == "supports"
    assert "same_study_scope" not in elem["basis"]


def test_receipt_key_registered_and_echo_still_last():
    """Both post-mapping merge paths drop receipts whose key is not in
    _SCOPE_RECEIPT_KEYS; and echo must remain the LAST gate."""
    assert "same_study_scope" in _SCOPE_RECEIPT_KEYS
    assert _SCOPE_RECEIPT_KEYS[-1] == "echo_scope"
    analyzer = ClaimMapAnalyzer()
    from app.pipeline.claim_map_analyzer import _index_evidence

    elem = _claim_map()["elements"][0]
    gates = analyzer._armed_scope_gates(elem, _claim_map(), _index_evidence(EVIDENCE))
    keys = [g.key for g in gates]
    assert keys[-1] == "echo_scope"
    assert keys.index("same_study_scope") == len(keys) - 2
