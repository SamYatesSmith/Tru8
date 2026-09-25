"""A− Build C — URL identity and copy detection (design §9, 2026-09-25).

True pairs are the review's, taken from the 19 graded payloads; negatives are
the review's false-merge cases (§3.4). Each guard has a test that fails if the
guard is removed.
"""

from datetime import datetime

import pytest

from app.utils.url_identity import (
    Candidate,
    canonical_url_key,
    choose_survivor,
    copy_rule,
    is_shell_title,
    parse_serp_date,
    shadow_report,
    suffix_names_host,
)


def _c(i, url, title, date=None):
    return Candidate(i, url, title, parse_serp_date(date), None)


# ── C1 ────────────────────────────────────────────────────────────────────────


class TestCanonicalUrlKey:
    def test_bbc_host_alias(self):
        assert canonical_url_key(
            "https://www.bbc.co.uk/news/articles/c3v4zvyde15o"
        ) == canonical_url_key("https://www.bbc.com/news/articles/c3v4zvyde15o/")

    def test_doi_epdf_variant(self):
        assert canonical_url_key(
            "https://shmpublications.onlinelibrary.wiley.com/doi/epdf/10.1002/jhm.70435"
        ) == canonical_url_key(
            "https://shmpublications.onlinelibrary.wiley.com/doi/10.1002/jhm.70435"
        )

    def test_doi_rule_needs_a_doi(self):
        assert canonical_url_key("https://x.org/doi/pdf/guide") != canonical_url_key(
            "https://x.org/doi/guide"
        )

    @pytest.mark.parametrize(
        "param",
        ["utm_source=a", "srsltid=AfmBOo", "syn-25a6b1a6=1", "fbclid=z", "gclid=q"],
    )
    def test_tracking_parameters_dropped(self, param):
        assert canonical_url_key(
            f"https://www.statista.com/statistics/1/x/?{param}"
        ) == canonical_url_key("https://statista.com/statistics/1/x")

    def test_identity_query_kept_eurostat(self):
        a = "https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Government_expenditure_by_function_-_COFOG"
        b = "https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Government_finance_statistics"
        assert canonical_url_key(a) != canonical_url_key(b)

    def test_identity_query_kept_youtube(self):
        assert canonical_url_key("https://youtube.com/watch?v=a1") != canonical_url_key(
            "https://youtube.com/watch?v=b2"
        )

    def test_fragment_and_scheme_ignored(self):
        assert canonical_url_key("http://example.com/a#x") == canonical_url_key(
            "https://example.com/a"
        )


# ── C2a: rules ────────────────────────────────────────────────────────────────


class TestCopyRules:
    def test_rule_ii_galway_counter_twin(self):
        base = "https://www.universityofgalway.ie/news/2026/september/university-of-galway-reefs"
        assert (
            copy_rule(
                _c(0, base, "September - University of Galway"),
                _c(1, base + "-1", "September - University of Galway"),
            )
            == "ii"
        )

    def test_rule_ii_series_guard(self):
        a = _c(
            0,
            "https://site.com/news/budget-statement-explained-part-1",
            "Budget explained",
        )
        b = _c(
            1,
            "https://site.com/news/budget-statement-explained-part-2",
            "Budget explained",
        )
        assert copy_rule(a, b) is None

    def test_rule_iii_pa_copy_across_papers(self):
        t = "'Encouraging' results from bid to restore coral habitats using artificial reefs"
        assert (
            copy_rule(
                _c(0, "https://www.belfasttelegraph.co.uk/news/a", t),
                _c(1, "https://www.irishnews.com/news/b", t.replace("'", "‘", 1)),
            )
            == "iii"
        )

    def test_rule_iii_bgov_commas_and_counter(self):
        assert (
            copy_rule(
                _c(
                    0,
                    "https://news.bgov.com/x/trump-disclosure",
                    "Trump Financial Disclosure Shows 21,000 Trades in 2025 (1)",
                ),
                _c(
                    1,
                    "https://www.bloomberg.com/news/articles/y",
                    "Trump Financial Disclosure Shows 21000 Trades in 2025",
                ),
            )
            == "iii"
        )

    def test_truncated_prefix_needs_eight_tokens(self):
        a = _c(0, "https://a.org/1", "Excess mortality during the COVID ...")
        b = _c(
            1,
            "https://b.org/2",
            "Excess mortality during the COVID-19 pandemic in Peru",
        )
        assert copy_rule(a, b) is None

    def test_html_tags_stripped_so_eurostat_pages_do_not_merge(self):
        a = _c(
            0,
            "https://ec.europa.eu/e?title=A",
            '<span class="mw-page-title-main">Government expenditure by function – COFOG</span>',
        )
        b = _c(
            1,
            "https://ec.europa.eu/e?title=B",
            '<span class="mw-page-title-main">Government finance statistics</span>',
        )
        assert copy_rule(a, b) is None

    def test_date_guard(self):
        t = "Budget statement to Parliament by the Chancellor of the Exchequer"
        a = _c(0, "https://gov.uk/news/2025/budget", t, "2025-03-01")
        b = _c(1, "https://gov.uk/news/2026/budget", t, "2026-03-01")
        assert copy_rule(a, b) is None

    def test_date_guard_allows_rocketnews_spread(self):
        t = "Factcheck: No, Europe's heatwaves are not being caused by declining air pollution"
        a = _c(
            0, "https://rocketnews.com/2026/07/x/", t + " - RocketNews", "2026-07-24"
        )
        b = _c(
            1, "https://rocketnews.com/2026/08/x-2/", t + " - RocketNews", "2026-08-14"
        )
        assert copy_rule(a, b) == "iii"


class TestShellTitles:
    @pytest.mark.parametrize(
        "title",
        [
            "The Journal (@thejournal_ie) on Threads",
            "Pippa Crerar (@PippaCrerar) on X",
            "TikTok - Make Your Day",
            "Just a moment...",
            "Access denied",
            "Reddit",
            "News tagged climate change and weather",
        ],
    )
    def test_shells(self, title):
        assert is_shell_title(title)

    def test_two_posts_from_one_handle_do_not_merge(self):
        t = "Unbelievable Facts (@unbfacts) on Threads"
        assert (
            copy_rule(
                _c(0, "https://threads.com/@u/post/1", t),
                _c(1, "https://threads.com/@u/post/2", t),
            )
            is None
        )

    def test_real_title_is_not_a_shell(self):
        assert not is_shell_title(
            "Trump Financial Disclosure Shows 21000 Trades in 2025"
        )


# ── Survivor ──────────────────────────────────────────────────────────────────


class TestSurvivor:
    T = "Factcheck: No, Europe's heatwaves are not being caused by declining air pollution"

    def test_original_beats_reprints(self):
        group = [
            _c(
                0,
                "https://rocketnews.com/2026/07/x/",
                self.T + " - RocketNews",
                "2026-07-24",
            ),
            _c(
                1,
                "https://www.carbonbrief.org/x",
                self.T + " - Carbon Brief",
                "2026-07-24",
            ),
            _c(
                2,
                "https://rocketnews.com/2026/08/x-2/",
                self.T + " - RocketNews",
                "2026-08-14",
            ),
        ]
        assert choose_survivor(group).host == "carbonbrief.org"

    def test_reprint_carrying_the_originals_suffix(self):
        group = [
            _c(0, "https://www.msn.com/en-gb/x", self.T + " - Carbon Brief"),
            _c(1, "https://www.carbonbrief.org/x", self.T),
        ]
        assert choose_survivor(group).host == "carbonbrief.org"

    def test_open_academic_copy_over_paywalled_journal(self):
        t = "Sweden's excess mortality in 2020-2022 and reporting in the media"
        group = [
            _c(0, "https://journals.sagepub.com/doi/full/10.1177/14034948241239353", t),
            _c(1, "https://portal.research.lu.se/en/publications/swedens-excess", t),
        ]
        assert choose_survivor(group).host == "portal.research.lu.se"

    def test_open_preference_only_in_academic_groups(self):
        t = "University announces new climate research centre for coastal flooding"
        group = [
            _c(0, "https://www.bbc.com/news/a", t, "2026-01-01"),
            _c(1, "https://www.ox.ac.uk/news/b", t, "2026-01-05"),
        ]
        assert choose_survivor(group).host == "bbc.com"

    def test_pooled_item_always_survives(self):
        group = [
            _c(
                0,
                "https://www.bbc.co.uk/news/articles/c3v",
                "Reform receives record donation from crypto billionaire",
            ),
            _c(
                1,
                "https://www.bbc.com/news/articles/c3v",
                "Reform receives record donation from crypto billionaire",
            ),
        ]
        pooled = lambda c: c.index == 1  # noqa: E731
        assert choose_survivor(group, pooled).index == 1

    @pytest.mark.parametrize(
        "suffix,host",
        [
            ("The", "theguardian.com"),
            ("PMC - NIH", "pmc.ncbi.nlm.nih.gov"),
            ("Office for National Statistics", "ons.gov.uk"),
            ("Scientific Reports", "nature.com"),
        ],
    )
    def test_suffix_negatives(self, suffix, host):
        assert not suffix_names_host(suffix, host)

    @pytest.mark.parametrize(
        "suffix,host",
        [
            ("Carbon Brief", "carbonbrief.org"),
            ("BBC", "bbc.com"),
            ("RocketNews", "rocketnews.com"),
            ("BBC News", "bbc.com"),
            ("Cato Institute", "cato.org"),
        ],
    )
    def test_suffix_positives(self, suffix, host):
        assert suffix_names_host(suffix, host)


class TestShadowReport:
    def test_reports_without_dropping(self):
        items = [
            {
                "url": "https://www.bbc.co.uk/news/articles/c3v",
                "title": "One",
                "date": None,
            },
            {
                "url": "https://www.bbc.com/news/articles/c3v",
                "title": "Two",
                "date": None,
            },
            {"url": "https://example.com/other", "title": "Three", "date": None},
        ]
        before = list(items)
        report = shadow_report(
            items, lambda i: i["url"], lambda i: i["title"], lambda i: i["date"]
        )
        assert items == before
        assert report == [
            {
                "would_drop": "https://www.bbc.com/news/articles/c3v",
                "survivor": "https://www.bbc.co.uk/news/articles/c3v",
                "rule": "i",
            }
        ]

    def test_transitive_groups(self):
        t = "Excess mortality in Denmark, Finland, Norway and Sweden during the pandemic years"
        items = [
            {"url": "https://a.org/doi/10.1/x", "title": t},
            {
                "url": "https://a.org/doi/epdf/10.1/x",
                "title": "Different wording entirely here now",
            },
            {"url": "https://b.org/y", "title": t},
        ]
        report = shadow_report(
            items, lambda i: i["url"], lambda i: i["title"], lambda i: None
        )
        assert len(report) == 2


def test_parse_serp_date_formats():
    now = datetime(2026, 9, 25)
    assert parse_serp_date("3 days ago", now) == datetime(2026, 9, 22)
    assert parse_serp_date("Aug 20, 2025") == datetime(2025, 8, 20)
    assert parse_serp_date("20 Aug 2025") == datetime(2025, 8, 20)
    assert parse_serp_date("2025-08-20T00:00:00") == datetime(2025, 8, 20)
    assert parse_serp_date("sometime") is None


# ── Shadow read 2026-09-25 (corpus pre-fetch pools) ───────────────────────────


def test_generic_short_title_across_hosts_does_not_merge():
    t = "Inflation Reduction Act of 2022"
    assert (
        copy_rule(
            _c(0, "https://www.energy.gov/edf/inflation-reduction-act-2022", t),
            _c(1, "https://www.irs.gov/inflation-reduction-act-of-2022", t),
        )
        is None
    )


def test_truncated_prefix_across_hosts_needs_close_dates():
    trial = _c(
        0,
        "https://pubmed.ncbi.nlm.nih.gov/33301246/",
        "Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine",
    )
    followup = _c(
        1,
        "https://www.nejm.org/doi/full/10.1056/NEJMoa2110345",
        "Safety and Efficacy of the BNT162b2 mRNA Covid-19 ...",
    )
    assert copy_rule(trial, followup) is None


def test_truncated_prefix_with_close_dates_still_matches():
    a = _c(0, "https://academic.oup.com/x", "Excess mortality in Denmark, Finland, Norway and Sweden during ...", "2024-03-01")
    b = _c(1, "https://www.healthdata.org/y", "Excess mortality in Denmark, Finland, Norway and Sweden during the COVID-19 pandemic", "2024-03-03")
    assert copy_rule(a, b) == "iii"


def test_publisher_page_beats_its_platform_upload():
    t = "Fact-checking Donald Trump's false and misleading claims during his UN address"
    group = [
        _c(0, "https://www.youtube.com/watch?v=_vnBOobf7jY", t),
        _c(1, "https://www.theguardian.com/us-news/video/2025/sep/24/fact-checking-video", t),
    ]
    assert choose_survivor(group).host == "theguardian.com"


def test_truncated_prefix_on_one_database_host_needs_close_dates():
    trial = _c(0, "https://pubmed.ncbi.nlm.nih.gov/33301246/", "Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine")
    followup = _c(1, "https://pubmed.ncbi.nlm.nih.gov/34525277/", "Safety and Efficacy of the BNT162b2 mRNA Covid-19 ...")
    assert copy_rule(trial, followup) is None
