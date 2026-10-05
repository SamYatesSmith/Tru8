"""Echo link confirmation: verbatim-only, verified-cue, fail-closed.

Design: audit/2026-10-01_echo_link_confirmation_design.md rev 2; build plan
audit/2026-10-05_echo_link_confirmation_build_plan.md §2. Hosts and text here
are invented; none comes from the held-out pairs the eval judges on.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.services import echo_link_confirmation as elc

A_TEXT = (
    "Consumer prices in Freedonia rose by 3.4 per cent in the twelve months to "
    "June, the Freedonia Statistics Office said in its monthly bulletin today."
)
B_TEXT = (
    "Inflation picked up again. Consumer prices in Freedonia rose by 3.4 per cent "
    "in the twelve months to June, according to the Freedonia Statistics Office."
)


def _a(**over):
    item = {
        "evidence_id": "ev-a",
        "url": "https://www.fso.gov.fd/bulletins/cpi-june",
        "source": "Freedonia Statistics Office",
        "title": "Consumer price inflation, June",
        "tier": "primary",
        "text": "distilled bullet text, must never be read",
        "snippet": "distilled bullet text, must never be read",
        "text_provenance": {"original_snippet": A_TEXT, "passages": []},
        "published_date": "2026-07-15",
        "date_basis": "page_metadata",
    }
    item.update(over)
    return item


def _b(**over):
    item = {
        "evidence_id": "ev-b",
        "url": "https://news.example.com/freedonia-inflation",
        "source": "Example News",
        "title": "Freedonia inflation rises",
        "tier": "reporting",
        "text": "distilled bullet text, must never be read",
        "snippet": "distilled bullet text, must never be read",
        "text_provenance": {"original_snippet": B_TEXT, "passages": []},
        "published_date": "2026-07-15",
        "date_basis": "page_metadata",
    }
    item.update(over)
    return item


def _pair(a=None, b=None):
    return {"a": a or _a(), "b": b or _b(), "strong": 2, "sim": 0.5}


def _row(**over):
    row = {
        "index": 0,
        "verdict": "relay",
        "extent": "whole",
        "cue_kind": "attribution",
        "cue": "according to the Freedonia Statistics Office",
        "reason": "B attributes the figure to A's publisher.",
    }
    row.update(over)
    return row


def _call(*rows):
    return AsyncMock(return_value={"pairs": list(rows)})


def _run(pairs, call):
    return asyncio.run(elc.confirm_pairs(pairs, call))


class TestVerbatimText:
    @pytest.mark.unit
    def test_reads_provenance_and_opening_never_distilled_text(self):
        item = _a()
        item[elc.PAGE_OPENING_KEY] = "Opening of the page."
        text = elc.verbatim_text(item)
        assert "Opening of the page." in text and A_TEXT in text
        assert "distilled" not in text

    @pytest.mark.unit
    def test_no_provenance_means_no_text(self):
        assert elc.verbatim_text(_a(text_provenance=None)) == ""

    @pytest.mark.unit
    def test_copy_page_opening_is_claim_independent_prefix(self):
        item = {"_full_text": "x" * 5000}
        elc.copy_page_opening(item)
        assert item[elc.PAGE_OPENING_KEY] == "x" * elc.PAGE_OPENING_CHARS


class TestValidate:
    def _v(self, row, a=None, b=None):
        a, b = a or _a(), b or _b()
        return elc.validate(row, a, b, elc.verbatim_text(a), elc.verbatim_text(b))

    @pytest.mark.unit
    def test_attribution_naming_a_confirms(self):
        out = self._v(_row())
        assert out["status"] == elc.CONFIRMED and out["extent"] == "whole"

    @pytest.mark.unit
    def test_attribution_naming_a_different_body_fails(self):
        b = _b(
            text_provenance={
                "original_snippet": B_TEXT
                + " according to the Central Bank of Elbonia.",
                "passages": [],
            }
        )
        out = self._v(_row(cue="according to the Central Bank of Elbonia"), b=b)
        assert out["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    def test_cue_not_in_b_fails(self):
        out = self._v(
            _row(cue="according to the Freedonia Statistics Office, which said")
        )
        assert out["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    def test_cue_only_in_distilled_text_fails(self):
        out = self._v(_row(cue="distilled bullet text"))
        assert out["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    def test_short_cue_fails(self):
        assert self._v(_row(cue="Freedonia"))["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    def test_copied_text_must_be_in_a_and_long_enough(self):
        copied = "Consumer prices in Freedonia rose by 3.4 per cent in the twelve months to June"
        assert (
            self._v(_row(cue_kind="copied_text", cue=copied))["status"] == elc.CONFIRMED
        )
        assert (
            self._v(_row(cue_kind="copied_text", cue="Inflation picked up again."))[
                "status"
            ]
            == elc.CUE_NOT_FOUND
        )
        assert (
            self._v(_row(cue_kind="copied_text", cue="rose by 3.4 per cent"))["status"]
            == elc.CUE_NOT_FOUND
        )

    @pytest.mark.unit
    def test_named_document_must_appear_in_a(self):
        b = _b(
            text_provenance={
                "original_snippet": B_TEXT
                + " The Consumer price inflation, June release shows more.",
                "passages": [],
            }
        )
        ok = self._v(
            _row(
                cue_kind="named_document", cue="Consumer price inflation, June release"
            ),
            b=b,
        )
        assert ok["status"] == elc.CONFIRMED
        bad = self._v(_row(cue_kind="named_document", cue="Inflation picked up again."))
        assert bad["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "over",
        [
            {"extent": None},
            {"extent": "most"},
            {"cue_kind": None},
            {"cue_kind": "vibes"},
        ],
    )
    def test_relay_without_valid_extent_or_kind_fails(self, over):
        assert self._v(_row(**over))["status"] == elc.CUE_NOT_FOUND

    @pytest.mark.unit
    def test_independent_and_unclear_never_link(self):
        assert self._v(_row(verdict="independent"))["status"] == elc.REJECTED
        assert self._v(_row(verdict="unclear"))["status"] == elc.UNCLEAR

    @pytest.mark.unit
    @pytest.mark.parametrize("row", [None, "relay", {}, {"verdict": "copy"}])
    def test_malformed_row_fails_closed(self, row):
        assert self._v(row)["status"] == elc.FAILED


class TestPredates:
    @pytest.mark.unit
    def test_b_before_a_on_trusted_dates_is_rejected_without_a_call(self):
        call = _call(_row())
        out = _run([_pair(b=_b(published_date="2026-07-01"))], call)
        assert out["records"][0]["status"] == elc.REJECTED
        assert out["records"][0]["detail"] == "predates"
        call.assert_not_awaited()

    @pytest.mark.unit
    def test_untrusted_date_basis_is_ignored(self):
        call = _call(_row())
        b = _b(published_date="2026-07-01", date_basis="url_inferred_suspect")
        out = _run([_pair(b=b)], call)
        assert out["records"][0]["status"] == elc.CONFIRMED

    @pytest.mark.unit
    def test_one_day_apart_is_allowed(self):
        assert not elc.predates(_a(), _b(published_date="2026-07-14"))


class TestConfirmPairs:
    @pytest.mark.unit
    def test_confirmed_record_has_no_reason(self):
        out = _run([_pair()], _call(_row()))
        rec = out["records"][0]
        assert rec["status"] == elc.CONFIRMED
        assert "reason" not in rec
        assert rec == {
            "original_id": "ev-a",
            "derivative_id": "ev-b",
            "status": "confirmed",
            "rank": 0,
            "extent": "whole",
            "cue_kind": "attribution",
            "cue": "according to the Freedonia Statistics Office",
        }
        assert out["reasons"][0]["reason"].startswith("B attributes")

    @pytest.mark.unit
    def test_prompt_never_carries_distilled_text(self):
        call = _call(_row())
        _run([_pair()], call)
        prompt = call.await_args.args[0]
        assert "distilled bullet text" not in prompt
        assert A_TEXT in prompt and B_TEXT in prompt

    @pytest.mark.unit
    def test_no_verbatim_text_is_not_inspected(self):
        call = _call()
        out = _run([_pair(b=_b(text_provenance=None))], call)
        assert out["records"][0] == {
            "original_id": "ev-a",
            "derivative_id": "ev-b",
            "status": "not_inspected",
            "rank": 0,
            "detail": "no_verbatim_text",
        }
        call.assert_not_awaited()

    @pytest.mark.unit
    def test_over_cap_pairs_are_not_inspected(self, monkeypatch):
        monkeypatch.setattr(elc, "max_pairs", lambda: 1)
        pairs = [_pair(), _pair(b=_b(evidence_id="ev-c"))]
        out = _run(pairs, _call(_row()))
        assert [r["status"] for r in out["records"]] == ["confirmed", "not_inspected"]

    @pytest.mark.unit
    def test_chunks_of_six(self):
        pairs = [_pair(b=_b(evidence_id=f"ev-b{i}")) for i in range(8)]
        call = _call(*[_row(index=i) for i in range(6)])
        out = _run(pairs, call)
        assert call.await_count == 2
        assert out["stats"]["calls"] == 2

    @pytest.mark.unit
    def test_missing_row_is_failed_not_linked(self):
        out = _run([_pair(), _pair(b=_b(evidence_id="ev-c"))], _call(_row(index=0)))
        assert [r["status"] for r in out["records"]] == ["confirmed", "failed"]
        assert out["records"][1]["detail"] == "not_returned"

    @pytest.mark.unit
    def test_duplicate_index_keeps_first(self):
        out = _run([_pair()], _call(_row(), _row(verdict="independent")))
        assert out["records"][0]["status"] == elc.CONFIRMED

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "side_effect", [RuntimeError("provider"), asyncio.TimeoutError()]
    )
    def test_call_failure_links_nothing(self, side_effect):
        call = AsyncMock(side_effect=side_effect)
        out = _run([_pair()], call)
        assert out["records"][0]["status"] == elc.FAILED

    @pytest.mark.unit
    @pytest.mark.parametrize("reply", [None, {}, {"pairs": "nope"}, ["x"]])
    def test_invalid_reply_links_nothing(self, reply):
        out = _run([_pair()], AsyncMock(return_value=reply))
        assert out["records"][0]["status"] == elc.FAILED
        assert out["records"][0]["detail"] == "invalid_response"

    @pytest.mark.unit
    def test_slow_call_times_out(self, monkeypatch):
        monkeypatch.setattr(elc, "timeout_s", lambda: 0.01)

        async def slow(_prompt):
            await asyncio.sleep(1)
            return {"pairs": [_row()]}

        out = _run([_pair()], slow)
        assert out["records"][0]["status"] == elc.FAILED

    @pytest.mark.unit
    def test_prompt_is_stable_for_the_same_pairs(self):
        c1, c2 = _call(_row()), _call(_row())
        _run([_pair()], c1)
        _run([_pair()], c2)
        assert c1.await_args.args[0] == c2.await_args.args[0]


class TestCandidates:
    @pytest.mark.unit
    def test_only_primary_to_reporting_or_commentary(self):
        a = _a(text=A_TEXT)
        b = _b(text=B_TEXT)
        c = _b(evidence_id="ev-c", tier="primary", text=B_TEXT)
        pairs = elc.candidates([a, b, c])
        assert {(p["a"]["evidence_id"], p["b"]["evidence_id"]) for p in pairs} == {
            ("ev-a", "ev-b")
        }

    @pytest.mark.unit
    def test_order_is_strength_then_ids(self):
        items = [_a(text=A_TEXT)] + [
            _b(evidence_id=f"ev-b{i}", text=B_TEXT) for i in (2, 1)
        ]
        ids = [p["b"]["evidence_id"] for p in elc.candidates(items)]
        assert ids == sorted(ids)


class TestSchema:
    @pytest.mark.unit
    def test_schema_enums_match_constants(self):
        props = elc.RESPONSE_SCHEMA["properties"]["pairs"]["items"]["properties"]
        assert props["verdict"]["enum"] == elc.VERDICTS
        assert props["extent"]["enum"] == elc.EXTENTS
        assert props["cue_kind"]["enum"] == elc.CUE_KINDS
        json.dumps(elc.RESPONSE_SCHEMA)


class TestGuardsFromMutation:
    """Each pins a guard a mutation run showed was otherwise untested."""

    @pytest.mark.unit
    def test_long_copied_text_absent_from_a_fails(self):
        extra = "Analysts at three banks had expected a smaller rise this summer."
        b = _b(text_provenance={"original_snippet": B_TEXT + " " + extra, "passages": []})
        out = elc.validate(
            _row(cue_kind="copied_text", cue=extra), _a(), b,
            elc.verbatim_text(_a()), elc.verbatim_text(b),
        )
        assert out["status"] == elc.CUE_NOT_FOUND
        assert out["detail"] == "copied_text_not_in_a"

    @pytest.mark.unit
    def test_attribution_cue_under_twelve_chars_fails(self):
        b = _b(text_provenance={"original_snippet": B_TEXT + " FSO said.", "passages": []})
        out = elc.validate(
            _row(cue="FSO said"), _a(), b, elc.verbatim_text(_a()), elc.verbatim_text(b)
        )
        assert out["status"] == elc.CUE_NOT_FOUND
        assert out["detail"] == "cue_not_in_b"

    @pytest.mark.unit
    def test_record_never_stores_reason(self):
        rec = elc._record(_pair(), elc.CONFIRMED, reason="model text", cue="c" * 20)
        assert "reason" not in rec and rec["cue"] == "c" * 20


class TestAttributionNames:
    """Plan review M6: whole words, bodies only."""

    def _ok(self, cue, a_over=None):
        a = _a(**(a_over or {}))
        b = _b(text_provenance={"original_snippet": B_TEXT + " " + cue, "passages": []})
        return elc.validate(
            _row(cue=cue), a, b, elc.verbatim_text(a), elc.verbatim_text(b)
        )["status"] == elc.CONFIRMED

    @pytest.mark.unit
    def test_short_host_label_inside_a_word_does_not_match(self):
        a = {"url": "https://www.ons.gov.uk/x", "source": "", "title": ""}
        assert not self._ok("the figures raised several questions today", a)

    @pytest.mark.unit
    def test_short_host_label_as_acronym_or_capitalised_matches(self):
        a = {"url": "https://www.ons.gov.uk/x", "source": "", "title": ""}
        assert self._ok("figures published by the ONS on Wednesday", a)
        assert self._ok("figures published by the Ons on Wednesday", a)

    @pytest.mark.unit
    def test_common_word_label_matches_only_as_acronym(self):
        a = {"url": "https://www.who.int/news/x", "source": "", "title": ""}
        assert self._ok("guidance issued by the WHO last week", a)
        assert not self._ok("people who said they were affected", a)

    @pytest.mark.unit
    def test_topic_word_from_title_does_not_validate(self):
        a = {"url": "https://stats.example.fd/x", "source": "", "title": "Inflation falls to 2%"}
        assert not self._ok("inflation was the main story this week", a)

    @pytest.mark.unit
    def test_body_named_in_title_validates(self):
        a = {"url": "https://stats.example.fd/x", "source": "", "title": "Bulletin from the Office for Freedonian Statistics"}
        assert self._ok("according to the Office for Freedonian Statistics", a)

    @pytest.mark.unit
    def test_place_acronym_in_title_is_not_a_body(self):
        a = {"url": "https://stats.example.fd/x", "source": "", "title": "UK GDP grows"}
        assert not self._ok("the UK economy grew slightly faster", a)

    @pytest.mark.unit
    def test_domain_shaped_source_reduces_to_its_label(self):
        a = {"url": "https://mirror.example.net/x", "source": "nasa.gov", "title": ""}
        assert self._ok("a statement from Nasa on Tuesday said", a)

    @pytest.mark.unit
    def test_compound_host_label_matches_as_words(self):
        a = {"url": "https://www.metoffice.gov.uk/x", "source": "", "title": ""}
        assert self._ok("records increasingly frequently, the Met Office said", a)
        g = {"url": "https://www.universityofgalway.ie/x", "source": "", "title": ""}
        assert self._ok("researchers at the University of Galway found", g)
        assert not self._ok("the met at the office yesterday was short", a)

    @pytest.mark.unit
    def test_long_host_label_inside_a_longer_word_does_not_match(self):
        a = {"url": "https://www.census.gov/x", "source": "", "title": ""}
        assert not self._ok("several national censuses show the same pattern", a)
        assert self._ok("figures from the Census bureau released on Monday", a)

    @pytest.mark.unit
    def test_title_proper_name_without_an_organisation_word_is_not_a_body(self):
        a = {"url": "https://stats.example.fd/x", "source": "", "title": "Consumer Prices Index, July"}
        assert not self._ok("the Consumer Prices Index rose again in July", a)
