"""Cited-source follow-up lane (A− H3), design rev 2.1.

Host identity, presence, name guards, round-robin selection and query caps,
the follow step's identity filter and caps, fail-closed naming, the per-item
interested party, receipts. Hosts mirror the 2026-10-05 probe; texts invented.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import settings
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


@pytest.mark.unit
def test_the_bodys_page_without_the_claims_figure_is_not_present():
    legend = _item(
        "ev-j",
        "https://effis.emergency.copernicus.eu/",
        "|Fire Danger Classes |FWI |FFMC | DMC",
    )
    name = "European Forest Fire Information System"
    cue = "data collected by the European Forest Fire Information System (EFFIS)"
    claim = "EU wildfires burned 678,978 hectares in 2026"
    assert cs.already_present([legend], name, cue, claim) is None
    real = _item(
        "ev-e",
        "https://effis.emergency.copernicus.eu/est",
        "Burnt area 678,978 ha in the EU",
    )
    assert cs.already_present([legend, real], name, cue, claim) == "ev-e"


@pytest.mark.unit
def test_a_copy_carrying_the_figure_is_not_the_original():
    copy = _item(
        "ev-y",
        "https://finance.yahoo.com/x",
        "Trump made 28,700 trades, Bloomberg said",
    )
    assert cs.already_present([copy], "Bloomberg", BLOOMBERG_CUE, CLAIM_TRADES) is None


@pytest.mark.unit
def test_name_tokens_never_count_as_claim_terms():
    page = _item("ev-b", "https://www.bloomberg.com/x", "Bloomberg markets homepage")
    claim = "Bloomberg says markets are calm"  # no figure; only the name overlaps
    assert not cs.carries_claim(cs.stored_text(page), claim, "Bloomberg")


@pytest.mark.unit
def test_snippet_only_items_never_count_as_present():
    bare = {
        "evidence_id": "ev-b",
        "url": "https://www.bloomberg.com/x",
        "text": "28,700 trades",
    }
    assert cs.already_present([bare], "Bloomberg", BLOOMBERG_CUE, CLAIM_TRADES) is None


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_query_keeps_every_claim_figure_and_drops_the_name_from_terms():
    q = cs.build_query(
        "Bloomberg",
        "",
        "Donald Trump made almost 28,700 trades of securities with a total value of $898 million to $2.87 billion since 2025",
    )
    assert q.startswith("Bloomberg ")
    for fig in ("28,700", "$898", "$2.87"):
        assert fig in q


@pytest.mark.unit
def test_query_keeps_short_acronyms():
    q = cs.build_query(
        "NHS England",
        "",
        "AI triage through the NHS App cut GP phone queues by 29 per cent",
    )
    assert " AI " in q and " GP " in q and "29" in q


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


class _Urls(set):
    def twin(self, url):
        return url if url in self else None


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


def _run_follow(names, results_by_query, claims=None, evidence=None):
    claims = claims or [{"position": 0, "text": CLAIM_TRADES}]
    evidence = evidence if evidence is not None else {"0": []}
    issued = []

    async def search(q):
        issued.append(q)
        return [_result(u) for u in results_by_query(q)]

    async def extract(r, claim_text):
        return {
            "url": r.url,
            "text": "x",
            "metadata": {"source_path": "query_planning"},
            "_full_text": "full",
        }

    receipts = asyncio.run(
        cs.follow_names(claims, evidence, names, search, extract, _Urls())
    )
    return receipts, evidence, issued


@pytest.mark.unit
def test_issued_query_is_exactly_the_built_query():
    _, _, issued = _run_follow(_names(_accepted()), lambda q: [])
    assert issued == [cs.build_query("Bloomberg", "", CLAIM_TRADES)]


@pytest.mark.unit
def test_only_the_cited_bodys_own_page_is_kept():
    hits = [
        "https://finance.yahoo.com/a",
        "https://www.msn.com/b",
        "https://www.bloomberg.com/graphics/x",
        "https://www.bloomberg.com/other",
    ]
    receipts, ev, _ = _run_follow(_names(_accepted()), lambda q: hits)
    assert [i["url"] for i in ev["0"]] == ["https://www.bloomberg.com/graphics/x"]
    item = ev["0"][0]
    assert item["evidence_id"] == "ev-cs-0_0"
    assert item["metadata"]["source_path"] == "cited_source"
    assert item["metadata"]["cited_source"]["name"] == "Bloomberg"
    assert item["_full_text"] == "full"
    q = receipts["0"]["queries"][0]
    assert q["dropped_not_cited_body"] == 2 and q["kept"] == ["ev-cs-0_0"]


@pytest.mark.unit
def test_at_most_two_kept_per_claim():
    names = _names(
        _accepted("Bloomberg"),
        _accepted(
            "Daily Telegraph", "wrote in the Daily Telegraph that", "news_first_report"
        ),
        _accepted("Bank of England", "the Bank of England estimated it", "data"),
    )
    hosts = {
        "Bloomberg": "https://www.bloomberg.com/a",
        "Daily": "https://www.telegraph.co.uk/b",
        "Bank": "https://www.bankofengland.co.uk/c",
    }
    receipts, ev, _ = _run_follow(names, lambda q: [hosts[q.split()[0]]])
    assert len(ev["0"]) == 2


@pytest.mark.unit
def test_queries_are_round_robin_and_capped_per_check(monkeypatch):
    monkeypatch.setattr(cs, "QUERIES_PER_CHECK", 3)
    claims = [{"position": 0, "text": "a 1"}, {"position": 1, "text": "b 2"}]
    names = {
        "0": {
            "accepted": [
                _accepted(f"Alpha{n} Agency", f"according to Alpha{n} Agency x", "data")
                for n in range(3)
            ],
            "receipts": [],
        },
        "1": {
            "accepted": [
                _accepted(f"Beta{n} Agency", f"according to Beta{n} Agency x", "data")
                for n in range(3)
            ],
            "receipts": [],
        },
    }
    _, _, issued = _run_follow(
        names, lambda q: [], claims=claims, evidence={"0": [], "1": []}
    )
    assert [q.split()[0] for q in issued] == ["Alpha0", "Beta0", "Alpha1"]


@pytest.mark.unit
def test_present_original_is_not_searched():
    present = _item("ev-b", "https://www.bloomberg.com/x", "Trump made 28,700 trades")
    receipts, ev, issued = _run_follow(
        _names(_accepted()),
        lambda q: ["https://www.bloomberg.com/y"],
        evidence={"0": [present]},
    )
    assert issued == []
    assert receipts["0"]["names"][0]["status"] == "already_present"


@pytest.mark.unit
def test_announcement_marks_the_body_as_interested_for_its_own_page():
    names = _names(
        _accepted("NHS England", "NHS England announced the rollout", "announcement")
    )
    _, ev, _ = _run_follow(names, lambda q: ["https://www.england.nhs.uk/2026/07/x"])
    assert ev["0"][0]["metadata"]["cited_source"]["interested_subject"] == "nhs england"


@pytest.mark.unit
def test_an_analysis_is_not_an_interested_party():
    _, ev, _ = _run_follow(
        _names(_accepted()), lambda q: ["https://www.bloomberg.com/x"]
    )
    assert "interested_subject" not in ev["0"][0]["metadata"]["cited_source"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "cue,expected",
    [
        ("NHS England said the trial", True),
        ("data published by NHS England", False),
        ("as reported by NHS England", False),
    ],
)
def test_statement_verbs_only(cue, expected):
    assert (cs.interested_subject("NHS England", "data", cue) is not None) is expected


@pytest.mark.unit
def test_deadline_cancels_slow_searches(monkeypatch):
    monkeypatch.setattr(cs, "stage_deadline_s", lambda: 0.05)
    claims = [{"position": 0, "text": CLAIM_TRADES}]

    async def search(q):
        await asyncio.sleep(5)
        return []

    async def extract(r, t):
        return None

    receipts = asyncio.run(
        cs.follow_names(
            claims, {"0": []}, _names(_accepted()), search, extract, _Urls()
        )
    )
    assert receipts["0"]["deadline_hit"] is True


@pytest.mark.unit
def test_receipts_and_skip():
    cms = {"0": {"metadata": {}}}
    cs.skip(cms, "quick_tier")
    assert cms["0"]["metadata"]["cited_sources"]["totals"]["detail"] == "quick_tier"


@pytest.mark.unit
def test_search_bypasses_the_fact_check_rewriter(monkeypatch):
    from app.services import search as search_mod

    seen = {}

    async def fake(self, query, max_results, freshness=None, country="gb"):
        seen.update(query=query, freshness=freshness, country=country)
        return []

    monkeypatch.setattr(search_mod.SearchService, "_try_providers", fake)
    asyncio.run(cs._search_exact("Bloomberg said Trump trades 28,700"))
    assert seen == {
        "query": "Bloomberg said Trump trades 28,700",
        "freshness": None,
        "country": None,
    }


@pytest.mark.unit
def test_lane_is_off_by_default():
    assert settings.ENABLE_CITED_SOURCE_LANE is False


@pytest.mark.unit
def test_quick_tier_declares_the_lane_only_while_it_is_on(monkeypatch):
    from app.core.tier_limitations import limitations_for_tier

    monkeypatch.setattr(settings, "ENABLE_CITED_SOURCE_LANE", False)
    assert "no_cited_source_lane" not in limitations_for_tier("quick")
    monkeypatch.setattr(settings, "ENABLE_CITED_SOURCE_LANE", True)
    assert "no_cited_source_lane" in limitations_for_tier("quick")


# ---------------------------------------------------------------------------
# Interested-party gate: per-item subject from the lane
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lane_item_from_an_announcing_body_is_scoped_by_the_gate():
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    lane = {
        "evidence_id": "ev-cs-0_0",
        "url": "https://www.england.nhs.uk/2026/07/x",
        "title": "NHS accelerates AI rollout",
        "snippet": "AI triage resulted in a 29% reduction in queues",
        "tier": "primary",
        "metadata": {
            "cited_source": {"name": "NHS England", "interested_subject": "nhs england"}
        },
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
                        "evidence_id": "ev-cs-0_0",
                        "relationship": "supports",
                        "reasoning": "t",
                    },
                ],
            }
        ]
    }
    ClaimMapAnalyzer()._parse_mapping_response(raw, cm, [lane])
    ref = cm["elements"][0]["evidence_refs"][0]
    assert getattr(ref["relationship"], "value", ref["relationship"]) == "context"
    assert "interested_party" in cm["elements"][0]["basis"]


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


@pytest.mark.unit
def test_figures_past_the_word_cap_are_still_queried():
    claim = (
        "Officials in the regional health authority confirmed yesterday afternoon that "
        "waiting lists across several large hospitals had fallen to 7,412 patients"
    )
    q = cs.build_query("Health Authority", "", claim)
    assert "7,412" in q


# ---------------------------------------------------------------------------
# Verification fixes (2026-10-05): race, submitted page, host equality,
# statement verbs, fetch conversion, runner seam
# ---------------------------------------------------------------------------


def _yielding_follow(names, hits, claims=None, source_url=None):
    """Mocks that YIELD at every await, so concurrent queries interleave."""
    claims = claims or [{"position": 0, "text": CLAIM_TRADES}]
    evidence = {"0": []}

    async def search(q):
        await asyncio.sleep(0)
        return [_result(u) for u in hits(q)]

    async def extract(r, claim_text):
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return {"url": r.url, "text": "x", "metadata": {}, "_full_text": "full"}

    receipts = asyncio.run(
        cs.follow_names(claims, evidence, names, search, extract, _Urls(), source_url)
    )
    return receipts, evidence


@pytest.mark.unit
def test_cap_holds_when_queries_interleave():
    names = _names(
        _accepted("Bloomberg"),
        _accepted(
            "Daily Telegraph", "wrote in the Daily Telegraph that", "news_first_report"
        ),
        _accepted("Bank of England", "the Bank of England estimated it", "data"),
    )
    hosts = {
        "Bloomberg": "https://www.bloomberg.com/a",
        "Daily": "https://www.telegraph.co.uk/b",
        "Bank": "https://www.bankofengland.co.uk/c",
    }
    _, ev = _yielding_follow(names, lambda q: [hosts[q.split()[0]]])
    assert len(ev["0"]) == 2


@pytest.mark.unit
def test_same_url_is_never_added_twice_when_queries_interleave():
    names = _names(
        _accepted("Bloomberg"),
        _accepted("Bloomberg News", "a Bloomberg News analysis finds it", "analysis"),
    )
    _, ev = _yielding_follow(names, lambda q: ["https://www.bloomberg.com/same"])
    assert [i["url"] for i in ev["0"]] == ["https://www.bloomberg.com/same"]


@pytest.mark.unit
def test_failed_fetch_frees_the_slot_and_tries_the_next_result():
    claims = [{"position": 0, "text": CLAIM_TRADES}]
    evidence = {"0": []}

    async def search(q):
        return [
            _result("https://www.bloomberg.com/paywalled"),
            _result("https://www.bloomberg.com/open"),
        ]

    async def extract(r, t):
        return (
            None
            if "paywalled" in r.url
            else {"url": r.url, "text": "x", "metadata": {}}
        )

    receipts = asyncio.run(
        cs.follow_names(claims, evidence, _names(_accepted()), search, extract, _Urls())
    )
    assert [i["url"] for i in evidence["0"]] == ["https://www.bloomberg.com/open"]
    assert receipts["0"]["queries"][0]["not_extracted"]


@pytest.mark.unit
def test_the_submitted_page_is_never_evidence_for_itself():
    page = "https://www.bloomberg.com/graphics/2026-trump-stock-trades-congress/"
    receipts, ev = _yielding_follow(
        _names(_accepted()), lambda q: [page], source_url=page
    )
    assert ev["0"] == []
    assert receipts["0"]["queries"][0]["dropped_submitted_page"] == 1


@pytest.mark.unit
def test_same_domain_pages_are_kept_and_tagged():
    receipts, ev = _yielding_follow(
        _names(_accepted()),
        lambda q: ["https://www.bloomberg.com/other-story"],
        source_url="https://www.bloomberg.com/graphics/x",
    )
    assert ev["0"][0]["metadata"]["same_domain_as_source"] is True


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


@pytest.mark.unit
@pytest.mark.parametrize(
    "cue",
    [
        "data from the United States Census Bureau",
        "a Bloomberg analysis of insurance claims found",
        "Ben Delo wrote in the Daily Telegraph that he was giving",
    ],
)
def test_no_false_statement_triggers(cue):
    assert cs.interested_subject("Body", "data", cue) is None


@pytest.mark.unit
def test_snippet_conversion_keeps_full_text_and_provenance_fields():
    snippet = SimpleNamespace(
        text="t",
        source="bloomberg.com",
        url="https://www.bloomberg.com/x",
        title="T",
        published_date="2026-09-16",
        date_basis="page_metadata",
        relevance_score=0.7,
        word_count=900,
        metadata={"is_snippet_fallback": False},
        content_basis="full_text",
        _full_text="the whole page",
    )
    item = cs._snippet_to_item(snippet)
    assert item["_full_text"] == "the whole page"
    assert item["date_basis"] == "page_metadata"
    assert item["content_basis"] == "full_text"
    assert item["receipt_status"] == "extracted"
    assert item["metadata"] == {"is_snippet_fallback": False}
    assert item["metadata"] is not snippet.metadata


@pytest.mark.unit
def test_default_extract_unwindows_and_converts(monkeypatch):
    from app.pipeline import retrieve

    seen = {}

    class FakeRetriever:
        async def _extract_with_fallback(self, result, claim_text, semaphore):
            seen["freshness"] = getattr(result, "_freshness", None)
            seen["claim"] = claim_text
            return SimpleNamespace(
                text="t",
                source="s",
                url=result.url,
                title="T",
                published_date=None,
                date_basis=None,
                relevance_score=0.0,
                word_count=10,
                metadata={},
                content_basis="full_text",
                _full_text="page",
            )

    monkeypatch.setattr(retrieve, "EvidenceRetriever", FakeRetriever)
    extract = cs._default_extract()
    item = asyncio.run(extract(_result("https://www.bloomberg.com/x"), CLAIM_TRADES))
    assert seen == {"freshness": "none", "claim": CLAIM_TRADES}
    assert item["_full_text"] == "page"


@pytest.mark.unit
def test_follow_for_check_end_to_end_with_receipts(monkeypatch):
    claims = [{"position": 0, "text": CLAIM_TRADES}]
    citer = _item(
        "ev-1", "https://finance.yahoo.com/x", "Reporters say " + BLOOMBERG_CUE + "."
    )
    evidence = {"0": [citer]}
    cms = {"0": {"metadata": {}}}

    async def names():
        return {
            "_stats": {"status": "ok"},
            "0": {
                "accepted": [_accepted()],
                "receipts": [{"name": "Bloomberg", "status": "accepted"}],
            },
        }

    async def search(q):
        return [
            _result("https://finance.yahoo.com/y"),
            _result("https://www.bloomberg.com/graphics/x"),
        ]

    def fake_extract():
        async def extract(r, t):
            return {"url": r.url, "text": "x", "metadata": {}, "_full_text": "page"}

        return extract

    monkeypatch.setattr(cs, "_search_exact", search)
    monkeypatch.setattr(cs, "_default_extract", fake_extract)

    async def go():
        await cs.follow_for_check(
            claims, evidence, cms, asyncio.ensure_future(names()), None
        )

    asyncio.run(go())
    rec = cms["0"]["metadata"]["cited_sources"]
    assert rec["totals"]["kept"] == 1
    assert rec["queries"][0]["dropped_not_cited_body"] == 1
    assert [i["evidence_id"] for i in evidence["0"]] == ["ev-1", "ev-cs-0_0"]


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
