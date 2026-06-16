"""P2 regression tests — UK-gov adapter cluster (legal.py).

Pins the empirically-found root causes of the UK Politics+Finance 0-yield ceiling
(see audit/2026-05-15_adapter_prepare_query_audit.md, revised 2026-06-15 after a
live wired probe):
  1. GOV.UK & Hansard wrongly excluded the Finance domain — fiscal/monetary claims
     classify as Finance and were self-excluded from the only UK primary-source
     adapters (a live probe showed GOV.UK: Finance=0 vs Politics=10, same query).
  2. Hansard discarded Contributions when Debates was empty — real speech text
     binned (a topic-keyword query returns 0 Debates but >0 Contributions).

Pure routing + response-transform logic; no LLM, no network.
"""

from app.services.api_adapters.legal import GovUKAdapter, HansardAdapter


# --- (1) domain routing --------------------------------------------------------


def test_govuk_relevant_for_uk_finance():
    a = GovUKAdapter()
    assert a.is_relevant_for_domain("Finance", "UK") is True  # the fix
    assert a.is_relevant_for_domain("Politics", "UK") is True  # existing, unbroken
    assert a.is_relevant_for_domain("Finance", "US") is False  # jurisdiction enforced
    assert a.is_relevant_for_domain("Sports", "UK") is False  # unrelated still excluded


def test_hansard_relevant_for_uk_finance():
    a = HansardAdapter()
    assert a.is_relevant_for_domain("Finance", "UK") is True  # the fix
    assert a.is_relevant_for_domain("Law", "UK") is True
    assert a.is_relevant_for_domain("Finance", "Global") is False
    assert a.is_relevant_for_domain("Health", "UK") is False


# --- (2) Hansard contribution surfacing ---------------------------------------


def _contribution(
    ext="D1",
    text="The Chancellor set out fiscal plans.",
    member="Rachel Reeves",
    section="Autumn Statement",
):
    return {
        "DebateSectionExtId": ext,
        "ContributionText": text,
        "ContributionTextFull": text,
        "DebateSection": section,
        "MemberName": member,
        "House": "Commons",
        "SittingDate": "2023-11-22T00:00:00",
        "ContributionExtId": "C1",
    }


def test_hansard_surfaces_contributions_when_no_debates():
    a = HansardAdapter()
    out = a._transform_response({"Debates": [], "Contributions": [_contribution()]})
    assert len(out) == 1
    ev = out[0]
    assert "Chancellor set out fiscal plans" in ev["snippet"]
    assert "Autumn Statement" in ev["title"]
    assert "Rachel Reeves" in ev["title"]
    assert ev["url"].startswith(
        "https://hansard.parliament.uk/Commons/2023-11-22/debates/D1/"
    )


def test_hansard_does_not_double_count_matched_contribution():
    a = HansardAdapter()
    resp = {
        "Debates": [
            {
                "Title": "Autumn Statement",
                "DebateSectionExtId": "D1",
                "SittingDate": "2023-11-22T00:00:00",
                "House": "Commons",
                "DebateSection": "Autumn Statement",
            }
        ],
        "Contributions": [_contribution(ext="D1")],
    }
    out = a._transform_response(resp)
    # The contribution enriches its debate's snippet; it must not appear twice.
    assert len(out) == 1


def test_hansard_contributions_capped_at_max_results():
    a = HansardAdapter()
    many = [
        _contribution(ext=f"D{i}", text=f"point {i}") for i in range(a.max_results + 5)
    ]
    out = a._transform_response({"Debates": [], "Contributions": many})
    assert len(out) <= a.max_results


def test_hansard_skips_empty_contribution_text():
    a = HansardAdapter()
    blank = _contribution(text="")
    blank["ContributionTextFull"] = ""
    out = a._transform_response({"Debates": [], "Contributions": [blank]})
    assert out == []


def test_hansard_surfaces_nonmatching_contribution_alongside_debate():
    """Headline real-world case (G5 gap): a Debate IS returned, plus a
    Contribution from a DIFFERENT debate — both must surface."""
    a = HansardAdapter()
    resp = {
        "Debates": [
            {
                "Title": "Autumn Statement",
                "DebateSectionExtId": "D1",
                "SittingDate": "2023-11-22T00:00:00",
                "House": "Commons",
                "DebateSection": "Autumn Statement",
            }
        ],
        "Contributions": [
            _contribution(
                ext="D2", text="A separate point on fiscal policy.", section="Treasury"
            )
        ],
    }
    out = a._transform_response(resp)
    assert len(out) == 2  # debate D1 + standalone contribution D2
    assert any("separate point on fiscal policy" in e["snippet"] for e in out)


def test_hansard_contribution_missing_id_and_date_uses_fallback_url():
    """G5 gap: a contribution with no DebateSectionExtId / SittingDate still
    surfaces, with the bare-host fallback URL and no exception."""
    a = HansardAdapter()
    c = _contribution(ext=None)
    c["SittingDate"] = None
    out = a._transform_response({"Debates": [], "Contributions": [c]})
    assert len(out) == 1
    assert out[0]["url"] == "https://hansard.parliament.uk/"
