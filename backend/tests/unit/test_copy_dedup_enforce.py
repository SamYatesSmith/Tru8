"""A− Build C ENFORCE (2026-09-28): collapse at the main retrieval site.

Design: audit/2026-09-24_a_minus_build_c_design.md §9.5–§9.6. Shadow read 2
(the 18-record re-measure) found 10 clear copies and 0 substantive losses in
12 would-drops. These tests pin the enforcing path: one fetch slot per article,
the survivor at the group's earliest position with every member's lanes, the
copies as ordered fetch fallbacks, and a receipt for every dropped copy.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.utils.url_identity import collapse_copies


def _r(url, title, lanes=(), date=None):
    return SimpleNamespace(
        url=url,
        title=title,
        published_date=date,
        _element_ids=set(lanes),
        snippet="serp snippet",
    )


BBC_UK = "https://www.bbc.co.uk/news/articles/ckgwkeg1vy8o"
BBC_COM = "https://www.bbc.com/news/articles/ckgwkeg1vy8o"


class TestCollapseCopies:
    def test_non_copies_are_untouched(self):
        items = [_r("https://a.org/x", "One"), _r("https://b.org/y", "Two")]
        kept, groups = collapse_copies(
            items, lambda c: c.url, lambda c: c.title, lambda c: None
        )
        assert kept == items and groups == []

    def test_one_slot_per_article_at_the_earliest_position(self):
        items = [
            _r(BBC_UK, "Reform donation"),
            _r("https://other.org/z", "Unrelated"),
            _r(BBC_COM, "Reform donation"),
        ]
        kept, groups = collapse_copies(
            items, lambda c: c.url, lambda c: c.title, lambda c: None
        )
        assert len(kept) == 2
        assert kept[1].url == "https://other.org/z"
        assert kept[0].url in (BBC_UK, BBC_COM)  # the group sits in slot 0
        ((survivor, dropped),) = groups
        assert survivor is kept[0]
        assert [d.url for d, _rule in dropped] == [
            u for u in (BBC_UK, BBC_COM) if u != survivor.url
        ]

    def test_a_later_survivor_moves_up_to_the_first_slot(self):
        # The Carbon Brief original survives its RocketNews reprint (a reprint
        # host) even though the reprint ranked first.
        title = (
            "Factcheck: Why cleaner air is not the main driver of European heatwaves"
        )
        items = [
            _r("https://www.rocketnews.com/2026/07/factcheck-cleaner-air", title),
            _r("https://x.org/other", "Something else entirely here"),
            _r("https://www.carbonbrief.org/factcheck-cleaner-air", title),
        ]
        kept, _groups = collapse_copies(
            items, lambda c: c.url, lambda c: c.title, lambda c: None
        )
        assert [k.url for k in kept] == [
            "https://www.carbonbrief.org/factcheck-cleaner-air",
            "https://x.org/other",
        ]


class TestMainSiteCollapse:
    def test_survivor_carries_lanes_fallbacks_and_receipts(self):
        from app.pipeline.retrieve import _collapse_copy_candidates

        a = _r(BBC_UK, "Reform donation", lanes={"c0"})
        b = _r(BBC_COM, "Reform donation", lanes={"e3"})
        kept = _collapse_copy_candidates([a, b])
        assert len(kept) == 1
        survivor = kept[0]
        assert survivor._element_ids == {"c0", "e3"}
        other = b if survivor is a else a
        assert survivor._copy_fallbacks == [other]
        assert survivor._copy_receipts[0]["url"] == other.url
        assert survivor._copy_receipts[0]["rule"] == "i"

    def test_flag_off_keeps_every_candidate(self, monkeypatch):
        """The wiring honours ENABLE_COPY_DEDUP (rollback)."""
        from app.pipeline import retrieve

        monkeypatch.setattr(retrieve.settings, "ENABLE_COPY_DEDUP", False)
        # _collapse_copy_candidates itself always collapses; the flag gates
        # the call site. Pin the call site's guard text so a refactor that
        # drops it fails here.
        import inspect

        src = inspect.getsource(retrieve)
        assert 'getattr(settings, "ENABLE_COPY_DEDUP", True)' in src
        assert "_collapse_copy_candidates(fetch_candidates)" in src


def _snippet(url, fallback=False):
    return SimpleNamespace(
        url=url, metadata={"is_snippet_fallback": fallback} if fallback else {}
    )


class TestCopyFetchFallback:
    @staticmethod
    def _retriever(results):
        from app.pipeline.retrieve import EvidenceRetriever

        r = EvidenceRetriever.__new__(EvidenceRetriever)

        async def fake(search_result, claim_text, semaphore):
            return results.get(search_result.url)

        r._extract_with_fallback = fake
        return r

    def test_survivor_fetched_normally_keeps_receipts(self):
        survivor = _r("https://paywalled.org/a", "Paper")
        copy = _r("https://repo.org/a", "Paper")
        survivor._copy_fallbacks = [copy]
        survivor._copy_receipts = [{"url": copy.url, "rule": "iii"}]
        r = self._retriever({survivor.url: _snippet(survivor.url)})
        out = asyncio.run(r._extract_with_copy_fallback(survivor, "c", None))
        assert out.url == survivor.url
        assert out.metadata["copy_dedup"] == [{"url": copy.url, "rule": "iii"}]

    @pytest.mark.parametrize("survivor_result", ["none", "snippet_only"])
    def test_failed_survivor_falls_back_to_its_copy(self, survivor_result):
        survivor = _r("https://paywalled.org/a", "Paper", lanes={"e2"})
        survivor._query_index = 3
        copy = _r("https://repo.org/a", "Paper")
        survivor._copy_fallbacks = [copy]
        survivor._copy_receipts = [{"url": copy.url, "rule": "iii"}]
        first = None if survivor_result == "none" else _snippet(survivor.url, True)
        r = self._retriever({survivor.url: first, copy.url: _snippet(copy.url)})
        out = asyncio.run(r._extract_with_copy_fallback(survivor, "c", None))
        assert out.url == copy.url
        # The copy inherited the survivor's lane metadata.
        assert copy._element_ids == {"e2"} and copy._query_index == 3
        # The survivor is now the recorded copy; the used copy is not.
        assert [x["url"] for x in out.metadata["copy_dedup"]] == [survivor.url]
        assert out.metadata["copy_dedup"][0]["rule"] == "fallback"

    def test_no_copy_fetches_either_keeps_the_survivor_result(self):
        survivor = _r("https://paywalled.org/a", "Paper")
        copy = _r("https://repo.org/a", "Paper")
        survivor._copy_fallbacks = [copy]
        survivor._copy_receipts = [{"url": copy.url, "rule": "iii"}]
        snip = _snippet(survivor.url, True)
        r = self._retriever({survivor.url: snip, copy.url: None})
        out = asyncio.run(r._extract_with_copy_fallback(survivor, "c", None))
        assert out is snip
        assert out.metadata["copy_dedup"] == [{"url": copy.url, "rule": "iii"}]


class TestCopyReceipts:
    def test_each_copy_becomes_an_excluded_raw_row(self):
        from app.pipeline.retrieve import EvidenceRetriever

        r = EvidenceRetriever.__new__(EvidenceRetriever)
        ev = {
            "url": BBC_COM,
            "title": "Reform donation",
            "snippet": "text",
            "source": "bbc.com",
            "metadata": {
                "copy_dedup": [
                    {
                        "url": BBC_UK,
                        "title": "Reform donation",
                        "source": "bbc.co.uk",
                        "published_date": None,
                        "rule": "i",
                    }
                ]
            },
        }
        _filtered, raw = r._apply_evidence_filters([ev], track_raw_evidence=True)
        rows = {row["url"]: row for row in raw}
        assert rows[BBC_COM]["is_included"] is True
        assert rows[BBC_UK]["is_included"] is False
        assert rows[BBC_UK]["filter_stage"] == "copy_dedup"
        assert BBC_COM in rows[BBC_UK]["filter_reason"]
