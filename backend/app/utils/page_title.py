"""Choose a page's own headline from fetched HTML (shared by evidence fetch and
Wayback title recovery).

Order: ``og:title`` -> ``twitter:title`` -> ``<title>``, with bot-wall
interstitials rejected, as before. Added 2026-10-06 (grader check S6): a
candidate shaped like a breadcrumb or section label ("September - University
of Galway", "News | Site") is skipped, and the first ``<h1>`` is tried after
``<title>`` - but ONLY to replace a breadcrumb, and only an ``<h1>`` of five or
more visible words that is not an error/cookie/sign-in heading and not the
site's name or a masthead variant of it (host label or ``<title>`` suffix). If no candidate survives, the
previous behaviour stands (the first non-junk meta/title candidate), so no
page becomes title-less and a bot wall's ``<h1>`` (often just the hostname)
never becomes a headline.

The breadcrumb rule is deliberately narrow. ``url_identity.is_shell_title``
also rejects any body under five words, which would discard real short
headlines ("Inflation hits 10%", "Climate change - Wikipedia"); here only a
body that is wholly a month, a year, a section word, or a platform/gate shell
counts.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

from bs4 import BeautifulSoup

from app.utils.url_identity import _SHELL_PREFIX, _SHELL_TITLES, title_parts

logger = logging.getLogger(__name__)

_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|"
    "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_SECTIONS = (
    "news|latest news|all news|news archive|news and events|news events|"
    "press|press releases?|press centre|press center|newsroom|media|"
    "media centre|media center|media releases?|blog|blogs|articles?|stories|"
    "updates|events|publications|insights|category|categories|archives?|"
    "home|homepage|index|search results?|tag|tags|topics?"
)
_BREADCRUMB = re.compile(
    rf"^(?:"
    rf"(?:{_MONTHS})(?: \d{{4}})?"  # "September", "September 2026"
    rf"|\d{{4}}(?: (?:{_MONTHS}))?"  # "2026", "2026 September"
    rf"|(?:{_SECTIONS})(?: (?:{_MONTHS}))?(?: \d{{4}})?"  # "News", "News 2026"
    rf"|page \d+"
    rf")(?: (?:archives?|news))?$"
)
# Content a browser does not show: screen-reader breadcrumbs inside an <h1>
# ("<span class="hidden">September </span> University of Galway ...").
_HIDDEN_CLASSES = frozenset(
    {
        "hidden",
        "sr-only",
        "visually-hidden",
        "visuallyhidden",
        "screen-reader-text",
        "screenreader-only",
        "element-invisible",
        "u-hidden",
    }
)


# An <h1> that is a page-state or chrome heading, not a headline.
_NOT_A_HEADLINE = re.compile(
    r"\b(?:not (?:be )?found|404|403|500|error|oops|page (?:cannot|could not|can ?t)|"
    r"no longer available|unavailable|cookies?|consent|privacy (?:settings|choices|preferences)|"
    r"sign ?in|log ?in|sign ?up|subscribe|subscription|register|my account|"
    r"access denied|forbidden|javascript)\b",
    re.IGNORECASE,
)
_MIN_H1_WORDS = 5
# Words a logo or masthead adds to a site's name ("Example News").
_MASTHEAD_WORDS = frozenset(
    {"the", "news", "online", "official", "website", "site", "home", "uk", "com", "www"}
)


def _compact(text: str) -> str:
    return "".join(
        w for w in _norm(text).split() if w not in _MASTHEAD_WORDS
    )


def _site_label(url: Optional[str]) -> Optional[str]:
    """``www.universityofgalway.ie`` -> ``universityofgalway``."""
    host = re.sub(r"^[a-z]+://", "", (url or "").lower()).split("/")[0].split(":")[0]
    parts = [p for p in host.split(".") if p and p != "www"]
    if not parts:
        return None
    # Drop the public suffix: one label, or two for a ccSLD (co.uk, ac.uk ...).
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in (
        "co", "ac", "gov", "org", "com", "net", "edu", "nhs", "ltd", "plc", "sch",
    ):
        parts = parts[:-2]
    elif len(parts) >= 2:
        parts = parts[:-1]
    return parts[-1] if parts else None


def _names_the_site(heading: str, sites) -> bool:
    """The heading is the site's name or a masthead variant of it."""
    mine = _compact(heading)
    if not mine:
        return True
    # Equal, or a shorter form of it. NOT "contains the site name": a headline
    # often names its own publisher ("University of Galway part of ...").
    return any(site and mine in site for site in sites)


def _usable_h1(heading: str, sites) -> bool:
    return (
        len(_norm(heading).split()) >= _MIN_H1_WORDS
        and not _NOT_A_HEADLINE.search(heading)
        and not is_breadcrumb_title(heading)
        and not _names_the_site(heading, sites)
    )


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def is_breadcrumb_title(title: Optional[str]) -> bool:
    """True when the title body (site suffix stripped) is only a month, a
    year, a generic section word, or a platform/gate shell."""
    norm, _suffix, _truncated = title_parts(title)
    if not norm:
        return True
    if norm in _SHELL_TITLES or norm.startswith(_SHELL_PREFIX):
        return True
    return bool(_BREADCRUMB.match(norm))


def _is_hidden(child) -> bool:
    """Hidden from the screen, not just from screen readers (so never
    ``aria-hidden``). A hiding class counts only when no responsive or state
    variant in the same class list can show it again (Tailwind
    ``hidden md:inline``: any token containing ':')."""
    classes = child.get("class") or []
    if set(classes) & _HIDDEN_CLASSES and not any(":" in c for c in classes):
        return True
    return child.has_attr("hidden") or bool(
        re.search(r"display\s*:\s*none", child.get("style") or "", re.I)
    )


def _visible_text(tag) -> str:
    for child in [c for c in tag.find_all(True) if _is_hidden(c)]:
        child.extract()
    return tag.get_text(" ", strip=True)


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", raw or "").strip()


def pick_page_title(
    html: str, junk_markers: Iterable[str], url: Optional[str] = None
) -> Optional[str]:
    """The page's own headline, or None when it has no usable one. ``url``
    (optional) supplies the host's site label for the <h1> site-name check."""
    junk = tuple(junk_markers)

    def usable(title: str) -> bool:
        return len(title) >= 5 and not any(m in title.lower() for m in junk)

    soup = BeautifulSoup(html, "html.parser")
    candidates: List[str] = []
    for prop in ("og:title", "twitter:title"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        content = tag.get("content") if tag else None
        if content:
            candidates.append(_clean(content))
    if soup.title and soup.title.string:
        candidates.append(_clean(soup.title.string))

    fallback = None
    sites = {_compact(_site_label(url) or "")} - {""}
    for title in candidates:
        if not usable(title):
            continue
        if not is_breadcrumb_title(title):
            return title
        fallback = fallback or title
        _body, suffix, _t = title_parts(title)
        if suffix:
            sites.add(_compact(suffix))
    if fallback is None:
        return None

    # Every usable meta/title candidate was a breadcrumb: try the first <h1>.
    h1 = soup.find("h1")
    heading = _clean(_visible_text(h1)) if h1 else ""
    if heading and usable(heading) and _usable_h1(heading, sites - {""}):
        logger.debug(f"[PAGE TITLE] breadcrumb {fallback!r} -> <h1> {heading!r}")
        return heading
    return fallback
