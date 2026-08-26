"""Fetch one article WHOLE, for the COMPARE tab.

Deliberately NOT EvidenceExtractor._extract_from_page: that path is
claim-scoped (returns a relevance window, not the article) and carries side
effects Compare must not inherit — in particular it feeds
domain_tracker.record_access_result, which describes PIPELINE domain health;
letting user-driven Compare fetches into that table would let user behaviour
distort retrieval statistics.

What it shares with the pipeline path: the honest Tru8Bot headers
(app/utils/browser_headers.py) and the same trafilatura → readability
extraction cascade via EvidenceExtractor._extract_main_content.

Whole-article is a measured design decision (2026-08-26, 88 live fetches):
median evidence article is 811 words, so reading everything costs ~0.09p more
per comparison than truncating — and the over-cap tail is ONS bulletins, PMC
papers and Wikipedia, exactly the documents where fragmenting is least
defensible. The 32k-token rail below is a safety valve against a pathological
input, not a budget lever; it never bound on the sample. PDFs are out of
scope for v1 (pypdf parses under a module-wide semaphore of 1 shared with
live pipeline work).

Design: audit/2026-08-26_compare_tab_design.md §10.1–10.2.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import httpx

from app.utils.browser_headers import browser_headers

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_SECONDS = 15
# ~4 chars/token — the rail exists so one pathological page cannot blow the
# call; on the measured distribution it never binds.
MAX_ARTICLE_CHARS = 32_000 * 4

# One extractor per process: its __init__ builds a SearchService, which is
# too heavy to construct per fetch just to borrow _extract_main_content.
_extractor = None


def _get_extractor():
    global _extractor
    if _extractor is None:
        from app.services.evidence import EvidenceExtractor

        _extractor = EvidenceExtractor()
    return _extractor


async def fetch_article_text(url: str) -> Tuple[Optional[str], str, Optional[int]]:
    """Fetch a URL and extract its full article text.

    Returns ``(text, basis, word_count)``:
      - ``(text, "full", words)`` — the whole article, extracted.
      - ``(None, "failed", None)`` — blocked, non-HTML, PDF, empty
        extraction, or any error. The caller falls back to the STORED
        pipeline text and labels it (§6.4); there is no second fetch
        mechanism and no fragmenting.
    """
    if not url or url.lower().endswith(".pdf"):
        return None, "failed", None

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=browser_headers(),
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.info(f"[COMPARE FETCH] {response.status_code} for {url}")
                return None, "failed", None
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                return None, "failed", None

            # Same extraction cascade as the pipeline (trafilatura →
            # readability → sanitise), via the extractor's stateless method.
            text = _get_extractor()._extract_main_content(response.text, url)
            if not text or len(text.strip()) < 200:
                return None, "failed", None

            if len(text) > MAX_ARTICLE_CHARS:
                logger.warning(
                    f"[COMPARE FETCH] {url} exceeds the 32k-token rail "
                    f"({len(text)} chars) — falling back to stored text "
                    f"rather than fragmenting"
                )
                return None, "failed", None

            return text, "full", len(text.split())

    except Exception as e:
        logger.info(f"[COMPARE FETCH] {type(e).__name__} for {url}")
        return None, "failed", None
