"""Source exclusion (2026-09-09, Track Q — Astra finding 9, founder decision).

A claim extracted from a submitted page must not be evidenced by THAT page.
The rule used to drop the page's whole domain, so claims taken from
sqlite.org/wal.html could never be evidenced by sqlite.org/changes.html — a
manufactured gap on reference documentation. Now only the submitted page is
dropped; its domain-mates are eligible and tagged `same_domain_as_source`.
"""

import pytest

from app.pipeline.retrieve import _same_page, _source_exclusion

PAGE = "https://www.sqlite.org/wal.html"
DOMAIN = "sqlite.org"


@pytest.mark.parametrize(
    "a,b,same",
    [
        (PAGE, "http://sqlite.org/wal.html", True),
        (PAGE, "https://www.sqlite.org/wal.html#sec9", True),
        (PAGE, "https://www.sqlite.org/wal.html?x=1", True),
        (PAGE, "https://www.sqlite.org/wal.html/", True),
        (PAGE, "https://sqlite.org/changes.html", False),
        (PAGE, "https://sqlite.org/wal.html.bak", False),
        (None, PAGE, False),
        (PAGE, "", False),
    ],
)
def test_same_page_ignores_presentation_not_identity(a, b, same):
    assert _same_page(a, b) is same


def test_the_submitted_page_is_skipped_and_its_domain_mates_are_tagged():
    assert _source_exclusion("https://sqlite.org/wal.html#sec9", DOMAIN, PAGE) == "skip"
    assert (
        _source_exclusion("https://www.sqlite.org/changes.html", DOMAIN, PAGE)
        == "same_domain"
    )
    assert (
        _source_exclusion("https://www.sqlite.org/releaselog/3_22_0.html", DOMAIN, PAGE)
        == "same_domain"
    )


def test_other_domains_and_no_source_are_untouched():
    assert _source_exclusion("https://news.example/story", DOMAIN, PAGE) is None
    assert _source_exclusion("https://sqlite.org/changes.html", None, None) is None
    assert _source_exclusion(None, DOMAIN, PAGE) is None
