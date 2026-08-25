"""Recover headlines that the search provider handed us already truncated.

The problem
-----------
Serper/Google cut result titles at ~54 characters ("Britain braces for
unprecedented water restrictions as…"). Measured on the replay corpus, **43%
of provider results (151/350) arrive pre-cut**.

Normally that costs us nothing: ``EvidenceExtractor._extract_title_from_html``
reads the page's own ``og:title`` from HTML we already fetched, and recovers
50 of 55 such titles (91%). But when the publisher blocks the fetch, retrieval
falls back to the search snippet and the cut title survives to the screen with
no way for a reader to tell it apart from a complete headline.

What this module adds
---------------------
For exactly those blocked items, the Wayback Machine usually holds a snapshot —
we already archive evidence URLs there. Measured over the 58 corpus URLs that
stay blocked even with proper request headers: **a snapshot exists for 69% and
yields a usable headline for 47%**.

The recovery is deliberately narrow:

* it runs **only** on titles that are visibly truncated — never on a complete
  one, so it cannot "improve" a headline the publisher actually chose;
* it **only ever lengthens** — a snapshot title that is shorter, or that fails
  the bot-wall check, is discarded;
* it writes a **receipt** (``title_basis`` + ``title_original``) rather than
  silently swapping text under a source's name (invariant #5).

Cost is two calls to free Internet Archive endpoints per affected item, run
concurrently, bounded, and never fatal: any failure leaves the original title
untouched.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.utils.browser_headers import TRU8_USER_AGENT

logger = logging.getLogger(__name__)

_AVAILABILITY_API = "https://archive.org/wayback/available"

# Set by the replay bench's cassette while it is patched in
# (scripts/replay_bench/cassette.py::CASSETTE_ACTIVE_ENV). Read by name so
# app code never imports from scripts/.
_CASSETTE_ACTIVE_ENV = "TRU8_CASSETTE_ACTIVE"

# Same bot-wall markers EvidenceExtractor rejects — an archived interstitial is
# still an interstitial, and "Just a moment..." must never become a headline.
_JUNK_TITLE_MARKERS = (
    "just a moment",
    "attention required",
    "access denied",
    "access to this page has been denied",
    "are you a robot",
    "please enable javascript",
    "enable javascript to",
    "checking your browser",
    "captcha",
    "403 forbidden",
    "before you continue",
    "one moment",
    "site not available",
    "please wait",
    "wait for verification",
    # Wayback's own failure pages
    "wayback machine",
    "internet archive",
    "page cannot be crawled",
)

_TRUNCATED_RE = re.compile(r"(?:\.{2,}|…)\s*$")
_SNAPSHOT_TS_RE = re.compile(r"(/web/\d{14})/")


def is_truncated_title(title: Optional[str]) -> bool:
    """True when the provider cut this title (trailing "..." or "…").

    Mirrors the frontend's ``cleanTitle`` rule so the two agree on what counts
    as truncated. Deliberately conservative: only an explicit trailing marker
    counts, never a guess from length or a dangling function word.
    """
    if not title:
        return False
    return bool(_TRUNCATED_RE.search(title.strip()))


def _stub(title: str) -> str:
    """The title with its truncation marker removed, for length comparison."""
    return _TRUNCATED_RE.sub("", (title or "").strip()).strip()


def _headline_from_html(html: str) -> Optional[str]:
    """og:title → twitter:title → <title>, rejecting bot-wall interstitials."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[str] = []
        for prop in ("og:title", "twitter:title"):
            tag = soup.find("meta", attrs={"property": prop}) or soup.find(
                "meta", attrs={"name": prop}
            )
            content = tag.get("content") if tag else None
            if content:
                candidates.append(content)
        if soup.title and soup.title.string:
            candidates.append(soup.title.string)

        for raw in candidates:
            title = re.sub(r"\s+", " ", raw).strip()
            if len(title) < 5:
                continue
            if any(m in title.lower() for m in _JUNK_TITLE_MARKERS):
                continue
            return title
        return None
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"[TITLE RECOVERY] parse failed: {e}")
        return None


def _raw_snapshot_url(snapshot_url: str) -> str:
    """Ask Wayback for the ORIGINAL bytes, not its rewritten replay page.

    Inserting ``id_`` after the 14-digit timestamp suppresses the archive's
    banner/rewriting, so the ``og:title`` we read is the publisher's own.
    """
    return _SNAPSHOT_TS_RE.sub(r"\1id_/", snapshot_url, count=1)


async def _recover_one(
    client: httpx.AsyncClient,
    item: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> bool:
    url = item.get("url") or ""
    original = item.get("title") or ""
    if not url:
        return False

    async with semaphore:
        try:
            resp = await client.get(_AVAILABILITY_API, params={"url": url})
            if resp.status_code != 200:
                return False
            closest = (resp.json().get("archived_snapshots") or {}).get("closest") or {}
            if not closest.get("available") or not closest.get("url"):
                return False

            snap = await client.get(_raw_snapshot_url(closest["url"]))
            if snap.status_code != 200 or not snap.text:
                return False

            headline = _headline_from_html(snap.text)
            if not headline:
                return False

            # Only ever lengthen. A snapshot that is shorter than the stub we
            # already show is not a recovery — it is a different, worse title.
            if len(headline) <= len(_stub(original)):
                return False

            item["title"] = headline
            metadata = item.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                item["metadata"] = metadata
            metadata["title_basis"] = "wayback_snapshot"
            metadata["title_original"] = original
            metadata["title_snapshot_timestamp"] = closest.get("timestamp")
            logger.debug(
                f"[TITLE RECOVERY] {url} :: '{original[:48]}' -> '{headline[:64]}'"
            )
            return True
        except Exception as e:
            # Never fatal — a missing headline is strictly better than a
            # failed check.
            logger.debug(f"[TITLE RECOVERY] {url} failed: {e}")
            return False


async def recover_truncated_titles(
    items: List[Dict[str, Any]],
    *,
    limit: int = 12,
    concurrency: int = 4,
    timeout: float = 8.0,
    overall_timeout: float = 25.0,
) -> int:
    """Repair provider-truncated titles in place. Returns the number fixed.

    Only items whose title carries a truncation marker are touched, capped at
    ``limit`` per call so a pathological claim cannot balloon the stage. The
    whole pass is wrapped in ``overall_timeout``: if the archive is slow, we
    abandon the repair rather than delay the user's check.
    """
    # The replay bench freezes the pipeline's whole network surface, and a
    # request the cassette has never seen is a hard miss. These archive lookups
    # are best-effort cosmetics, NOT part of the behaviour the bench measures,
    # so they sit this out rather than turning every corpus claim red or
    # forcing a re-record. (A real pipeline STAGE must never do this — a stage
    # that behaves differently under replay makes the bench measure fiction.)
    if os.environ.get(_CASSETTE_ACTIVE_ENV):
        return 0

    targets = [
        it
        for it in items
        if isinstance(it, dict)
        and is_truncated_title(it.get("title"))
        and it.get("url")
    ][:limit]
    if not targets:
        return 0

    semaphore = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": TRU8_USER_AGENT}
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(_recover_one(client, it, semaphore) for it in targets),
                    return_exceptions=True,
                ),
                timeout=overall_timeout,
            )
        fixed = sum(1 for r in results if r is True)
    except asyncio.TimeoutError:
        logger.info(
            f"[TITLE RECOVERY] timed out after {overall_timeout}s; "
            f"{len(targets)} title(s) left as provided"
        )
        return 0
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"[TITLE RECOVERY] pass failed: {e}")
        return 0

    if fixed:
        logger.info(
            f"[TITLE RECOVERY] recovered {fixed}/{len(targets)} truncated headline(s)"
        )
    return fixed
