"""Year-window regression tests for the academic paper-search adapters.

The bug (NF-18 Bug-2 / NF-20 historical-recency class): Semantic Scholar,
OpenAlex and CrossRef each hardcoded a ``now-2y`` publication-year filter, so a
claim about an older event (e.g. "A 2021 NEJM trial ...") queried 2024-2026 and
silently excluded the very paper it was about.

The fix anchors the lower bound to the claim's DATE entity, widening *backward*
to include the claim year while never narrowing the default recency window.

These tests assert the request that actually leaves the adapter (the wired
``prepare_query`` -> ``search`` -> HTTP seam), per the
"test the wired prepare_query path" discipline — not just the pure helper.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.api_adapters.academic import (
    HISTORICAL_MIN_YEAR,
    CrossRefAdapter,
    OpenAlexAdapter,
    SemanticScholarAdapter,
    _resolve_min_year,
)
from app.utils.adapter_query_helpers import extract_claim_year


CURRENT_YEAR = datetime.now(timezone.utc).year
DEFAULT_MIN = CURRENT_YEAR - 2

DATE_2021 = [
    {"text": "2021", "label": "DATE"},
    {"text": "New England Journal of Medicine", "label": "ORG"},
]


# ---------- pure helper ----------


class TestExtractClaimYear:
    def test_reads_year_from_date_entity(self):
        assert extract_claim_year(DATE_2021) == 2021

    def test_reads_year_from_iso_date(self):
        assert extract_claim_year([{"text": "2008-10-13", "label": "DATE"}]) == 2008

    def test_longest_date_entity_wins(self):
        ents = [
            {"text": "2022", "label": "DATE"},
            {"text": "19 July 2019", "label": "DATE"},
        ]
        # "19 July 2019" is the longest DATE -> 2019
        assert extract_claim_year(ents) == 2019

    def test_none_when_no_entities(self):
        assert extract_claim_year(None) is None
        assert extract_claim_year([]) is None

    def test_none_when_no_date_label(self):
        assert extract_claim_year([{"text": "Pfizer", "label": "ORG"}]) is None

    def test_none_when_date_has_no_parseable_year(self):
        assert extract_claim_year([{"text": "last summer", "label": "DATE"}]) is None

    def test_ignores_non_year_numbers(self):
        # 95 / 1056 must not be mistaken for a year; only 19xx/20xx match.
        assert extract_claim_year([{"text": "95% in 1056", "label": "DATE"}]) is None


# ---------- resolver semantics ----------


class TestResolveMinYear:
    def test_widens_backward_to_historical_claim_year(self):
        assert _resolve_min_year(2026, DATE_2021) == 2021

    def test_default_window_when_no_date(self):
        assert _resolve_min_year(2026, None) == 2024

    def test_does_not_narrow_for_recent_claim(self):
        # 2025 is inside the default window; keep the wider default.
        assert _resolve_min_year(2026, [{"text": "2025", "label": "DATE"}]) == 2024

    def test_does_not_narrow_for_future_claim(self):
        assert _resolve_min_year(2026, [{"text": "2030", "label": "DATE"}]) == 2024

    # F-R2a (2026-07-09, TRU-C051-3024): historical claims WITHOUT a year
    # token carry no DATE entity — the backward widening never fired and the
    # French-paradox literature was excluded at the API.

    def test_historical_marker_without_year_widens(self):
        assert (
            _resolve_min_year(
                2026,
                None,
                claim_text="Many doctors historically recommended a daily glass of red wine",
            )
            == HISTORICAL_MIN_YEAR
        )

    def test_explicit_date_year_wins_over_marker(self):
        # An explicit older year is the more precise signal — keep it.
        assert (
            _resolve_min_year(
                2026,
                DATE_2021,
                claim_text="Doctors historically recommended this treatment in 2021",
            )
            == 2021
        )

    def test_non_historical_text_keeps_default_window(self):
        assert (
            _resolve_min_year(
                2026, None, claim_text="Moderate alcohol consumption protects the heart"
            )
            == 2024
        )


# ---------- wired HTTP seam ----------


@contextmanager
def _capture_httpx_get(json_payload):
    """Patch httpx.Client so the adapter's inline client records the URL it
    GETs and returns ``json_payload`` instead of hitting the network."""
    captured = {}

    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=json_payload)

    def fake_get(url):
        captured["url"] = url
        return response

    client = MagicMock()
    client.get = MagicMock(side_effect=fake_get)
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)

    with patch("httpx.Client", return_value=client):
        yield captured


class TestSemanticScholarYearWindow:
    def test_historical_claim_widens_year_window(self):
        adapter = SemanticScholarAdapter()
        with _capture_httpx_get({"data": []}) as captured:
            adapter.search("vaccine efficacy", "Health", "Global", entities=DATE_2021)
        assert f"year=2021-{CURRENT_YEAR}" in captured["url"]

    def test_no_date_uses_default_window(self):
        adapter = SemanticScholarAdapter()
        with _capture_httpx_get({"data": []}) as captured:
            adapter.search("vaccine efficacy", "Health", "Global", entities=None)
        assert f"year={DEFAULT_MIN}-{CURRENT_YEAR}" in captured["url"]

    def test_historical_marker_no_year_widens_window(self):
        """F-R2a wired seam: the TRU-C051-3024 claim shape must leave the
        adapter with the widened year filter."""
        adapter = SemanticScholarAdapter()
        with _capture_httpx_get({"data": []}) as captured:
            adapter.search(
                "Many doctors historically recommended a daily glass of red wine",
                "Health",
                "Global",
                entities=[
                    {"text": "Many doctors", "label": "PERSON"},
                    {"text": "red wine", "label": "OTHER"},
                ],
            )
        assert f"year={HISTORICAL_MIN_YEAR}-{CURRENT_YEAR}" in captured["url"]


class TestOpenAlexYearWindow:
    def test_historical_claim_widens_year_window(self):
        adapter = OpenAlexAdapter()
        with _capture_httpx_get({"results": []}) as captured:
            adapter.search("vaccine efficacy", "Health", "Global", entities=DATE_2021)
        assert "from_publication_date:2021-01-01" in captured["url"]

    def test_no_date_uses_default_window(self):
        adapter = OpenAlexAdapter()
        with _capture_httpx_get({"results": []}) as captured:
            adapter.search("vaccine efficacy", "Health", "Global", entities=None)
        assert f"from_publication_date:{DEFAULT_MIN}-01-01" in captured["url"]

    def test_historical_marker_no_year_widens_window(self):
        """F-R2a wired seam (OpenAlex leg of TRU-C051-3024)."""
        adapter = OpenAlexAdapter()
        with _capture_httpx_get({"results": []}) as captured:
            adapter.search(
                "Many doctors historically recommended a daily glass of red wine",
                "Health",
                "Global",
                entities=None,
            )
        assert f"from_publication_date:{HISTORICAL_MIN_YEAR}-01-01" in captured["url"]


class TestCrossRefYearWindow:
    def _run(self, entities):
        adapter = CrossRefAdapter()
        captured = {}

        def fake_make_request(path, params=None):
            captured["params"] = params
            return {"message": {"items": []}}

        with patch.object(adapter, "_make_request", side_effect=fake_make_request):
            adapter.search("vaccine efficacy", "Health", "Global", entities=entities)
        return captured["params"]

    def test_historical_claim_widens_year_window(self):
        params = self._run(DATE_2021)
        assert params["filter"] == "from-pub-date:2021"

    def test_no_date_uses_default_window(self):
        params = self._run(None)
        assert params["filter"] == f"from-pub-date:{DEFAULT_MIN}"
