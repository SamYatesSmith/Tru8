"""Cited-source follow-up lane (A− H3), design rev 2.1.

Host identity, presence, name guards, round-robin selection and query caps,
the follow step's identity filter and caps, fail-closed naming, the per-item
interested party, receipts. Hosts mirror the 2026-10-05 probe; texts invented.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.services import cited_source as cs

BLOOMBERG_CUE = "a new Bloomberg analysis finds Trump made nearly 28,700 trades"
CLAIM_TRADES = "Donald Trump made almost 28,700 trades of securities since 2025"


def _item(eid, url, text, title="T"):
    return {
        "evidence_id": eid,
        "url": url,
        "title": title,
        "text": "distilled, never read",
        "text_provenance": {"original_snippet": text, "passages": []},
    }


# ---------------------------------------------------------------------------
# Host identity (rev 2.1 §12.1, R2, R3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,name,cue,expected",
    [
        ("https://www.bloomberg.com/graphics/x", "Bloomberg", BLOOMBERG_CUE, True),
        ("https://finance.yahoo.com/x", "Bloomberg", BLOOMBERG_CUE, False),
        (
            "https://fortune.com/2026/bloomberg-analysis-trump",
            "Bloomberg",
            BLOOMBERG_CUE,
            False,
        ),
        ("https://www.msn.com/en-us/bloomberg", "Bloomberg", BLOOMBERG_CUE, False),
        (
            "https://www.telegraph.co.uk/politics/x",
            "Daily Telegraph",
            "wrote in the Daily Telegraph",
            True,
        ),
        (
            "https://www.england.nhs.uk/2026/07/x",
            "NHS England",
            "NHS England announced it",
            True,
        ),
        (
            "https://www.surreysussex.icb.nhs.uk/news",
            "NHS England",
            "NHS England announced it",
            False,
        ),
        (
            "https://nhsaccelerator.com/x",
            "NHS England",
            "NHS England announced it",
            False,
        ),
        (
            "https://effis.emergency.copernicus.eu/",
            "European Forest Fire Information System",
            "data collected by the European Forest Fire Information System (EFFIS)",
            True,
        ),
        (
            "https://forest-fire.emergency.copernicus.eu/apps",
            "European Forest Fire Information System",
            "data collected by the European Forest Fire Information System (EFFIS)",
            False,
        ),
        (
            "https://www.ons.gov.uk/x",
            "Office for National Statistics",
            "the Office for National Statistics (ONS) said",
            True,
        ),
        (
            "https://www.gov.uk/x",
            "Office for National Statistics",
            "the Office for National Statistics (ONS) said",
            False,
        ),
        (
            "https://www.bankofengland.co.uk/x",
            "Bank of England",
            "the Bank of England said",
            True,
        ),
        (
            "https://www.washingtonpost.com/x",
            "Washington Post",
            "first reported by the Washington Post",
            True,
        ),
        ("https://www.example.com/x", "", "x", False),
    ],
)
def test_host_identity(url, name, cue, expected):
    assert cs.host_identifies(url, name, cue) is expected


@pytest.mark.unit
def test_tokens_are_lowercased_and_generic_words_dropped():
    assert cs.name_tokens("The Daily Telegraph") == ["telegraph"]
    assert cs.name_tokens("NHS England") == ["nhs", "england"]


# ---------------------------------------------------------------------------
# Presence by content, not by name (rev 2.1 §12.2)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Name guards (rev 2 §11.4)
# ---------------------------------------------------------------------------


def _chosen(*items):
    return [(it, cs.stored_text(it)) for it in items]


@pytest.mark.unit
def test_guards():
    citer = _item(
        "ev-1",
        "https://finance.yahoo.com/x",
        "Analysts note that " + BLOOMBERG_CUE + " in 17 months.",
    )
    own = _item(
        "ev-2",
        "https://www.bloomberg.com/x",
        "Bloomberg analysis: Trump made nearly 28,700 trades",
    )
    chosen = _chosen(citer, own)
    rows = [
        {"name": "Bloomberg", "kind": "analysis", "cue": BLOOMBERG_CUE, "item": 0},
        {
            "name": "Bloomberg",
            "kind": "analysis",
            "cue": BLOOMBERG_CUE,
            "item": 0,
        },  # duplicate
        {
            "name": "Reuters",
            "kind": "analysis",
            "cue": BLOOMBERG_CUE,
            "item": 0,
        },  # name not in cue
        {
            "name": "Bloomberg",
            "kind": "analysis",
            "cue": "a Bloomberg analysis says nothing",
            "item": 0,
        },  # cue absent
        {
            "name": "Bloomberg",
            "kind": "analysis",
            "cue": "Bloomberg analysis: Trump made",
            "item": 1,
        },  # own outlet
        {"name": "Bloomberg", "kind": "vibes", "cue": BLOOMBERG_CUE, "item": 0},
        {"name": "Bloomberg", "kind": "analysis", "cue": BLOOMBERG_CUE, "item": 9},
        "garbage",
    ]
    accepted, receipts = cs.validate_names(rows, chosen)
    assert [a["name"] for a in accepted] == ["Bloomberg"]
    assert accepted[0]["citing_id"] == "ev-1"
    # The gap note keys on the receipt's citing_id (verification R2-LOW-1).
    assert [r.get("citing_id") for r in receipts if r["status"] == "accepted"] == [
        "ev-1"
    ]
    statuses = [r["status"] for r in receipts]
    assert statuses.count("accepted") == 1
    for s in ("name_not_in_cue", "cue_not_found", "self_outlet", "invalid"):
        assert s in statuses


@pytest.mark.unit
def test_cue_must_match_case():
    citer = _item("ev-1", "https://finance.yahoo.com/x", BLOOMBERG_CUE)
    rows = [
        {
            "name": "Bloomberg",
            "kind": "analysis",
            "cue": BLOOMBERG_CUE.upper(),
            "item": 0,
        }
    ]
    accepted, receipts = cs.validate_names(rows, _chosen(citer))
    assert not accepted and receipts[0]["status"] == "cue_not_found"


@pytest.mark.unit
def test_at_most_three_names_per_claim():
    text = " ".join(f"according to Body{n} Agency the figure rose." for n in range(5))
    citer = _item("ev-1", "https://news.example.com/x", text)
    rows = [
        {
            "name": f"Body{n} Agency",
            "kind": "data",
            "cue": f"according to Body{n} Agency the figure rose",
            "item": 0,
        }
        for n in range(5)
    ]
    accepted, receipts = cs.validate_names(rows, _chosen(citer))
    assert len(accepted) == 3
    assert sum(r["status"] == "over_cap" for r in receipts) == 2


# ---------------------------------------------------------------------------
# Selection: round-robin across claims, caps (invariant #2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_selection_is_round_robin_and_capped(monkeypatch):
    monkeypatch.setattr(cs, "ITEMS_PER_CLAIM", 2)
    claims = [{"position": 0, "text": "a"}, {"position": 1, "text": "b"}]
    ev = {
        "0": [
            _item(
                f"a{i}", "https://x.example/a", f"according to Agency {i} the rate rose"
            )
            for i in range(5)
        ],
        "1": [
            _item(f"b{i}", "https://y.example/b", f"data from Office {i} show it")
            for i in range(5)
        ],
    }
    ev["0"].append(
        _item("a-noattr", "https://x.example/n", "no attribution here at all")
    )
    chosen = cs.select_items(claims, ev)
    assert [it["evidence_id"] for it, _ in chosen["0"]] == ["a0", "a1"]
    assert [it["evidence_id"] for it, _ in chosen["1"]] == ["b0", "b1"]


@pytest.mark.unit
def test_prompt_never_sees_distilled_text():
    claims = [{"position": 0, "text": CLAIM_TRADES}]
    ev = {"0": [_item("ev-1", "https://finance.yahoo.com/x", BLOOMBERG_CUE)]}
    prompt, order = cs.build_prompt(claims, cs.select_items(claims, ev))
    assert "distilled, never read" not in prompt
    assert BLOOMBERG_CUE in prompt and order == ["0"]


# ---------------------------------------------------------------------------
# Naming: fail closed
# ---------------------------------------------------------------------------


def _claims_and_pool():
    claims = [{"position": 0, "text": CLAIM_TRADES}]
    ev = {
        "0": [
            _item(
                "ev-1",
                "https://finance.yahoo.com/x",
                "Reporters say " + BLOOMBERG_CUE + ".",
            )
        ]
    }
    return claims, ev


@pytest.mark.unit
@pytest.mark.parametrize(
    "reply,status", [(None, "invalid_response"), ({"claims": "x"}, "invalid_response")]
)
def test_bad_replies_name_nothing(reply, status):
    claims, ev = _claims_and_pool()

    async def call(prompt):
        return reply

    out = asyncio.run(cs.name_cited_sources(claims, ev, call))
    assert out["_stats"]["status"] == status and "0" not in out


@pytest.mark.unit
def test_failed_call_names_nothing():
    claims, ev = _claims_and_pool()

    async def call(prompt):
        raise RuntimeError("down")

    out = asyncio.run(cs.name_cited_sources(claims, ev, call))
    assert out["_stats"]["status"] == "failed"


@pytest.mark.unit
def test_slow_call_times_out(monkeypatch):
    monkeypatch.setattr(cs, "name_timeout_s", lambda: 0.01)
    claims, ev = _claims_and_pool()

    async def call(prompt):
        await asyncio.sleep(1)
        return {"claims": []}

    out = asyncio.run(cs.name_cited_sources(claims, ev, call))
    assert out["_stats"]["status"] == "failed"


@pytest.mark.unit
def test_missing_claim_row_is_receipted():
    claims, ev = _claims_and_pool()

    async def call(prompt):
        return {"claims": []}

    out = asyncio.run(cs.name_cited_sources(claims, ev, call))
    assert out["0"]["status"] == "not_returned"


# ---------------------------------------------------------------------------
# Follow: exact query, identity filter, caps, receipts, interested party
# ---------------------------------------------------------------------------


def _result(url):
    return SimpleNamespace(
        url=url, title="t", snippet="s", published_date=None, source=None
    )


def _names(*accepted):
    return {
        "0": {
            "accepted": list(accepted),
            "receipts": [{"name": a["name"], "status": "accepted"} for a in accepted],
        }
    }


def _accepted(name="Bloomberg", cue=BLOOMBERG_CUE, kind="analysis"):
    return {"name": name, "cue": cue, "kind": kind, "document": "", "citing_id": "ev-1"}


@pytest.mark.unit
def test_receipts_and_skip():
    cms = {"0": {"metadata": {}}}
    cs.skip(cms, "quick_tier")
    assert cms["0"]["metadata"]["cited_sources"]["totals"]["detail"] == "quick_tier"


# ---------------------------------------------------------------------------
# Interested-party gate: per-item subject from the lane
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_same_page_without_the_lane_mark_is_not_scoped():
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    page = {
        "evidence_id": "ev-x",
        "url": "https://www.england.nhs.uk/2026/07/x",
        "title": "NHS accelerates AI rollout",
        "snippet": "AI triage resulted in a 29% reduction in queues",
        "tier": "primary",
    }
    cm = {
        "claim_id": "0",
        "normalised_claim": "AI triage cut GP phone queues by 29%.",
        "elements": [
            {
                "element_id": "e1",
                "description": "AI triage cut phone queues by 29%.",
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
                        "evidence_id": "ev-x",
                        "relationship": "supports",
                        "reasoning": "t",
                    },
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(raw, cm, [page])
    ref = cm["elements"][0]["evidence_refs"][0]
    assert getattr(ref["relationship"], "value", ref["relationship"]) == "supports"


@pytest.mark.unit
def test_shared_suffix_needs_whole_labels_not_prefixes():
    # "digital" starts the label "digitalservices", but on a shared public
    # suffix every token must be a whole label.
    assert not cs.host_identifies(
        "https://digitalservices.nhs.uk/x", "NHS Digital", "NHS Digital said"
    )
    assert cs.host_identifies(
        "https://digital.nhs.uk/x", "NHS Digital", "NHS Digital said"
    )


@pytest.mark.unit
def test_acronym_must_be_the_site_name_or_leftmost_label():
    cue = "data from the European Forest Fire Information System (EFFIS)"
    name = "European Forest Fire Information System"
    assert not cs.host_identifies("https://maps.effis.example.com/x", name, cue)


@pytest.mark.unit
def test_squashed_name_matches_a_joined_host_only_off_shared_suffixes():
    assert cs.host_identifies(
        "https://www.bankofengland.co.uk/x",
        "Bank of England",
        "the Bank of England said",
    )
    assert not cs.host_identifies(
        "https://bankofengland.gov.uk/x", "Bank of England", "the Bank of England said"
    )


# ---------------------------------------------------------------------------
# Verification fixes (2026-10-05): race, submitted page, host equality,
# statement verbs, fetch conversion, runner seam
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,name,cue",
    [
        ("https://www.whoscored.com/x", "WHO", "the WHO said"),
        ("https://www.cdcgaming.com/x", "CDC", "the CDC said"),
        ("https://onsitenews.com/x", "ONS", "the ONS said"),
        ("https://bloomberg.substack.com/p/x", "Bloomberg", BLOOMBERG_CUE),
        (
            "https://www.telegraphindia.com/x",
            "Daily Telegraph",
            "wrote in the Daily Telegraph",
        ),
    ],
)
def test_prefix_lookalike_hosts_are_not_the_body(url, name, cue):
    assert not cs.host_identifies(url, name, cue)


@pytest.mark.unit
def test_who_acronym_still_matches_its_own_site():
    assert cs.host_identifies("https://www.who.int/news/x", "WHO", "the WHO said")


# ---------------------------------------------------------------------------
# Vague names and the citing page's own publisher (eval step 1, 2026-10-06)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "name,expected",
    [
        ("government", True),
        ("the company", True),
        ("Australian government", True),
        ("UK government", False),
        ("Ministry of Health", False),
        ("State Department", False),
        ("Biden administration", False),
        ("NHS England", False),
        ("Climate Prediction Center", False),
    ],
)
def test_is_vague_name(name, expected):
    assert cs.is_vague_name(name) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,name,expected",
    [
        (
            "https://www.gov.uk/government/news/cma-fines-pharma-companies-45-million",
            "CMA",
            True,
        ),
        (
            "https://www.who.int/news/item/x",
            "WHO global expert committee on vaccine safety",
            True,
        ),
        (
            "https://hsph.harvard.edu/news/ultra-processed-foods",
            "Harvard T.H. Chan School of Public Health",
            True,
        ),
        ("https://www.bbc.co.uk/news/cma-fines-pharma", "CMA", False),
        ("https://www.gov.uk/government/news/ons-figures", "CMA", False),
        ("https://www.ons.gov.uk/economy/x", "Office for National Statistics", False),
        ("https://www.who.int/news/item/x", "Lancet", False),
    ],
)
def test_published_by(url, name, expected):
    assert cs.published_by(url, name) is expected


@pytest.mark.unit
def test_vague_and_self_publisher_names_are_refused_with_receipts():
    cue = "The government said the CMA had fined the firms"
    citer = _item("ev-1", "https://www.gov.uk/government/news/cma-fines-firms", cue)
    rows = [
        {"name": "government", "kind": "announcement", "cue": cue, "item": 0},
        {"name": "CMA", "kind": "announcement", "cue": cue, "item": 0},
    ]
    accepted, receipts = cs.validate_names(rows, _chosen(citer))
    assert accepted == []
    assert [r["status"] for r in receipts] == ["vague_name", "self_outlet"]
