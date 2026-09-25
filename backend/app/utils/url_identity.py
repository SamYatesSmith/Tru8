"""URL identity and copy detection — A− Build C (2026-09-25).

Design: audit/2026-09-24_a_minus_build_c_design.md §9 (revised after the
review, audit/2026-09-24_a_minus_build_c_review.md).

WHY THIS EXISTS
---------------
S4 failed on 10 of 19 graded records: one article counted twice. URL dedup
was a raw-string ``in`` test, so ``bbc.co.uk/…`` and ``bbc.com/…``, a Wiley
``/doi/`` and ``/doi/epdf/``, a Galway ``…reefs`` and ``…reefs-1``, and the
same PA copy in two papers all entered the pool as separate sources and could
be counted separately on one side of an element.

WHAT IT DOES
------------
* ``canonical_url_key`` — an EQUALITY key. Stored URLs are never rewritten
  (goldens' Jaccard sets hold raw URLs).
* ``copy_groups`` — groups pre-fetch candidates that are the same article,
  by three rules: (i) equal canonical keys, (ii) the same host and slug stem,
  (iii) the same normalised title. Each rule carries the review's false-merge
  guards (shell titles, the series guard, the 45-day date guard, the
  truncated-title floor).
* ``choose_survivor`` — the deterministic survivor order of design §9.5.

Phase 1 is SHADOW: callers log what would collapse and drop nothing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit

# ── C1: canonical URL key ─────────────────────────────────────────────────────

#: Host aliases: one publication under two hostnames. Deliberately short —
#: ``news.bgov.com`` is NOT bloomberg.com (a separate property); its twin is
#: caught by the title rule.
_HOST_ALIASES = {"bbc.co.uk": "bbc.com"}

#: Query parameters that track a visit and never identify a page. Measured on
#: the 19 payloads: srsltid (Google SERP click id) on Statista, syn-* (FT
#: syndication). Every other parameter is KEPT — Eurostat pages differ only by
#: ``?title=``, YouTube identity is ``?v=``.
_TRACKING_EXACT = frozenset(
    {
        "fbclid",
        "gclid",
        "ref",
        "cmp",
        "srsltid",
        "mc_cid",
        "mc_eid",
        "ocid",
        "smid",
        "_ga",
    }
)
_TRACKING_PREFIX = ("utm_", "syn-")

#: ``/doi/epdf/10.…`` → ``/doi/10.…`` — narrow on purpose; DOI identity across
#: hosts is the same-study gate's job, post-fetch.
_DOI_VARIANT = re.compile(r"/doi/(?:epdf|pdf|full|abs)/(?=10\.)", re.IGNORECASE)


def _is_tracking(name: str) -> bool:
    low = name.lower()
    return low in _TRACKING_EXACT or low.startswith(_TRACKING_PREFIX)


def canonical_url_key(url: Optional[str]) -> str:
    """Equality key for a URL: host case, ``www.``, host aliases, a trailing
    slash, the DOI variant path, tracking parameters, the fragment and the
    scheme are presentation, not identity."""
    parts = urlsplit((url or "").strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    host = _HOST_ALIASES.get(host, host)
    path = _DOI_VARIANT.sub("/doi/", parts.path or "")
    path = path.rstrip("/") or ""
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(k)
    ]
    key = host + path
    if query:
        key += "?" + urlencode(query)
    return key


def same_url(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and canonical_url_key(a) == canonical_url_key(b)


# ── C2a: title normalisation and shells ───────────────────────────────────────

_TAG = re.compile(r"<[^>]+>")
_DIGIT_COMMA = re.compile(r"(?<=\d),(?=\d{3}\b)")
_TRAILING_COUNTER = re.compile(r"\s*\(\d+\)\s*$")
_SITE_SUFFIX = re.compile(r"\s+[-|–—]\s+([^-|–—]{2,60})$")
_TRUNCATED = re.compile(r"(?:\.\.\.|…)\s*$")
_HANDLE_SHELL = re.compile(
    r"\(@[\w.]+\)\s+on\s+(?:x|threads|instagram|tiktok|bluesky)\s*$", re.IGNORECASE
)
_SHELL_TITLES = frozenset(
    {
        "reddit",
        "tiktok make your day",
        "youtube",
        "home",
        "untitled",
        "just a moment",
        "access denied",
        "log in",
        "x",
        "threads",
    }
)
_SHELL_PREFIX = ("news tagged ",)
_MIN_TITLE_WORDS = 5
_MIN_TRUNCATED_TOKENS = 8
_MIN_TRUNCATED_CHARS = 45


def _strip_site_suffix(title: str) -> Tuple[str, Optional[str]]:
    match = _SITE_SUFFIX.search(title)
    if not match:
        return title, None
    return title[: match.start()], match.group(1).strip()


def title_parts(title: Optional[str]) -> Tuple[str, Optional[str], bool]:
    """(normalised body, site suffix, truncated?) for a SERP title."""
    raw = _TAG.sub("", title or "").strip()
    truncated = bool(_TRUNCATED.search(raw))
    raw = _TRUNCATED.sub("", raw).strip()
    raw = _DIGIT_COMMA.sub("", raw)
    raw = _TRAILING_COUNTER.sub("", raw)
    body, suffix = _strip_site_suffix(raw)
    body = _TRAILING_COUNTER.sub("", body)
    norm = re.sub(r"[^a-z0-9]+", " ", body.lower()).strip()
    return norm, suffix, truncated


def is_shell_title(title: Optional[str]) -> bool:
    """A title that names a platform or a gate, not an article."""
    raw = _TAG.sub("", title or "").strip()
    if _HANDLE_SHELL.search(raw):
        return True
    norm, _suffix, _t = title_parts(raw)
    if not norm or norm in _SHELL_TITLES or norm.startswith(_SHELL_PREFIX):
        return True
    full = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
    if full in _SHELL_TITLES:
        return True
    return len(norm.split()) < _MIN_TITLE_WORDS


# ── C2a: slug rule ────────────────────────────────────────────────────────────

_SLUG_COUNTER = re.compile(r"-(\d{1,2})$")
_SERIES_TOKENS = frozenset(
    {
        "part",
        "day",
        "week",
        "episode",
        "chapter",
        "vol",
        "no",
        "round",
        "stage",
        "phase",
        "series",
    }
)
_MIN_SLUG_STEM = 20


def _slug_stem(url: Optional[str]) -> Optional[str]:
    path = (urlsplit(url or "").path or "").rstrip("/")
    segment = path.rsplit("/", 1)[-1].lower()
    for ext in (".html", ".htm"):
        if segment.endswith(ext):
            segment = segment[: -len(ext)]
    match = _SLUG_COUNTER.search(segment)
    if match:
        head = segment[: match.start()]
        if head.rsplit("-", 1)[-1] in _SERIES_TOKENS:
            return None
        segment = head
    return segment if len(segment) >= _MIN_SLUG_STEM else None


def _host(url: Optional[str]) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return _HOST_ALIASES.get(host, host)


# ── Dates ─────────────────────────────────────────────────────────────────────

_RELATIVE = re.compile(
    r"^(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago$", re.IGNORECASE
)
_DATE_FORMATS = ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y")
_UNIT_DAYS = {
    "minute": 1 / 1440,
    "hour": 1 / 24,
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}
DATE_GUARD_DAYS = 45


def parse_serp_date(value: Any, now: Optional[datetime] = None) -> Optional[datetime]:
    """A SERP date: ISO, "Aug 20, 2025", "20 Aug 2025", or "3 days ago"."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip()
    rel = _RELATIVE.match(text)
    if rel:
        base = now or datetime.utcnow()
        return base - timedelta(
            days=int(rel.group(1)) * _UNIT_DAYS[rel.group(2).lower()]
        )
    head = text[:10] if re.match(r"\d{4}-\d{2}-\d{2}", text) else text
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(head, fmt)
        except ValueError:
            continue
    return None


def _dates_far_apart(a: Optional[datetime], b: Optional[datetime]) -> bool:
    return bool(a and b) and abs((a - b).days) > DATE_GUARD_DAYS


# ── Grouping ──────────────────────────────────────────────────────────────────


class Candidate:
    """What the copy key reads from a search result (or a pooled item)."""

    __slots__ = (
        "index",
        "url",
        "title",
        "date",
        "key",
        "host",
        "slug",
        "item",
        "norm",
        "suffix",
        "truncated",
        "shell",
    )

    def __init__(
        self, index: int, url: str, title: str, date: Optional[datetime], item: Any
    ):
        self.index = index
        self.url = url or ""
        self.title = title or ""
        self.date = date
        self.key = canonical_url_key(url)
        self.host = _host(url)
        self.slug = _slug_stem(url)
        self.item = item
        self.norm, self.suffix, self.truncated = title_parts(title)
        self.shell = is_shell_title(title)


#: Shadow read 2026-09-25 over the corpus pre-fetch pools: two different pages
#: titled "Inflation Reduction Act of 2022" (energy.gov, irs.gov) merged. A
#: short exact title is a topic, not an article, once it spans two hosts.
_MIN_CROSS_HOST_TITLE_WORDS = 7
#: Same read: "Safety and Efficacy of the BNT162b2 mRNA Covid-19 …" linked the
#: 2020 trial to its 2021 six-month follow-up. A truncated prefix is weak, so
#: it also needs a second signal: the same site, or dates within a week.
_TRUNCATED_DATE_DAYS = 7


def _cand_titles_match(a: "Candidate", b: "Candidate") -> bool:
    if a.shell or b.shell:
        return False
    same_site = _label(a.host) == _label(b.host)
    if not (a.truncated or b.truncated):
        if not same_site and len(a.norm.split()) < _MIN_CROSS_HOST_TITLE_WORDS:
            return False
        return a.norm == b.norm
    short, long_ = (a.norm, b.norm) if len(a.norm) <= len(b.norm) else (b.norm, a.norm)
    if len(short.split()) < _MIN_TRUNCATED_TOKENS or len(short) < _MIN_TRUNCATED_CHARS:
        return False
    close_dates = (
        bool(a.date and b.date) and abs((a.date - b.date).days) <= _TRUNCATED_DATE_DAYS
    )
    # Dates only: "the same site" is no signal on a database host. Two PubMed
    # papers (the 2020 trial and its 2021 follow-up) share a truncated prefix.
    if not close_dates:
        return False
    return long_.startswith(short)


def copy_rule(a: Candidate, b: Candidate) -> Optional[str]:
    """The rule under which two candidates are the same article, else None."""
    if _dates_far_apart(a.date, b.date):
        return None
    if a.key and a.key == b.key:
        return "i"
    if (
        a.host
        and a.host == b.host
        and a.slug
        and a.slug == b.slug
        and (_cand_titles_match(a, b) or (a.shell and b.shell) or a.norm == b.norm)
    ):
        return "ii"
    if _cand_titles_match(a, b):
        return "iii"
    return None


def copy_groups(candidates: Sequence[Candidate]) -> List[List[Tuple[Candidate, str]]]:
    """Groups of ≥2 candidates that are one article, each member paired with
    the rule that first linked it. Linking is transitive (union-find); indices
    are dict lookups for rules i and iii, pairwise only within a host for ii."""
    parent = list(range(len(candidates)))
    rule_of: Dict[int, str] = {}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int, rule: str) -> None:
        ri, rj = find(i), find(j)
        if ri == rj:
            return
        lo, hi = min(ri, rj), max(ri, rj)
        parent[hi] = lo
        rule_of.setdefault(i, rule)
        rule_of.setdefault(j, rule)

    for j in range(len(candidates)):
        for i in range(j):
            rule = copy_rule(candidates[i], candidates[j])
            if rule:
                union(i, j, rule)

    groups: Dict[int, List[Tuple[Candidate, str]]] = {}
    for idx, cand in enumerate(candidates):
        groups.setdefault(find(idx), []).append((cand, rule_of.get(idx, "")))
    return [members for members in groups.values() if len(members) > 1]


# ── Survivor ──────────────────────────────────────────────────────────────────

REPRINT_HOSTS = frozenset(
    {
        "rocketnews.com",
        "msn.com",
        "yahoo.com",
        "news.yahoo.com",
        "newsbreak.com",
        "flipboard.com",
        "ground.news",
        "publicnow.com",
        "biggo.com",
        "sigmaearth.com",
    }
)
_OPEN_ACADEMIC = re.compile(
    r"(?:^|\.)(?:ncbi\.nlm\.nih\.gov|pmc\.ncbi\.nlm\.nih\.gov|europepmc\.org|arxiv\.org|"
    r"biorxiv\.org|medrxiv\.org|ssrn\.com|researchgate\.net|zenodo\.org|osf\.io|"
    r"lu\.se|diva-portal\.org)$|\.(?:ac\.uk|edu|edu\.au|ac\.nz)$"
)
#: A group is academic when a member is a journal copy: a DOI path or a
#: publisher host. Only then does the open copy outrank the version of record.
_PUBLISHER_HOSTS = re.compile(
    r"(?:^|\.)(?:sagepub|oup|academic\.oup|wiley|onlinelibrary\.wiley|springer|"
    r"link\.springer|sciencedirect|nature|tandfonline|jamanetwork|thelancet|bmj|"
    r"cell|plos|frontiersin|mdpi|cambridge)\.(?:com|org)$"
)


def _label(host: str) -> str:
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "ac", "gov", "net"}:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")


def suffix_names_host(suffix: Optional[str], host: str) -> bool:
    """A title suffix names a host when, lower-cased and reduced to
    alphanumerics, it equals the host's registrable label or begins with it:
    " - Carbon Brief" names carbonbrief.org, " - BBC News" names bbc.com,
    " - Cato Institute" names cato.org. The label must be >= 3 chars. The
    reverse direction (the label begins with the suffix) is refused: " - The"
    would otherwise name theguardian.com."""
    if not suffix or not host:
        return False
    compact = re.sub(r"[^a-z0-9]", "", suffix.lower())
    label = _label(host)
    return len(label) >= 3 and compact.startswith(label)


#: Platforms rank with reprints: a publisher's own page beats its upload (the
#: Guardian's video page over the same video on YouTube, shadow read 2026-09-25).
PLATFORM_HOSTS = frozenset(
    {
        "youtube.com",
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "x.com",
        "twitter.com",
        "reddit.com",
        "threads.com",
        "threads.net",
        "linkedin.com",
    }
)


def _is_reprint(host: str) -> bool:
    hosts = REPRINT_HOSTS | PLATFORM_HOSTS
    return host in hosts or any(host.endswith("." + h) for h in hosts)


def choose_survivor(
    group: Sequence[Candidate], pooled: Optional[Callable[[Candidate], bool]] = None
) -> Candidate:
    """Design §9.5 order: pooled item; host named by ANOTHER member's suffix;
    not a reprint host; open academic copy; earliest date; earliest position;
    smallest key."""

    def named_by_other(c: Candidate) -> bool:
        return any(
            o.host != c.host and suffix_names_host(o.suffix, c.host) for o in group
        )

    academic = any(
        "/doi/" in c.url.lower() or _PUBLISHER_HOSTS.search(c.host) for c in group
    )

    def rank(c: Candidate) -> Tuple:
        return (
            0 if (pooled and pooled(c)) else 1,
            0 if named_by_other(c) else 1,
            1 if _is_reprint(c.host) else 0,
            0 if (academic and _OPEN_ACADEMIC.search(c.host)) else 1,
            c.date or datetime.max,
            c.index,
            c.key,
        )

    return min(group, key=rank)


def shadow_report(
    items: Sequence[Any],
    url_of: Callable[[Any], str],
    title_of: Callable[[Any], str],
    date_of: Callable[[Any], Any],
    now: Optional[datetime] = None,
    pooled: Optional[Callable[[Candidate], bool]] = None,
) -> List[Dict[str, str]]:
    """What a collapse WOULD drop: one entry per non-survivor. Drops nothing."""
    candidates = [
        Candidate(i, url_of(it), title_of(it), parse_serp_date(date_of(it), now), it)
        for i, it in enumerate(items)
    ]
    report: List[Dict[str, str]] = []
    for group in copy_groups(candidates):
        survivor = choose_survivor([c for c, _r in group], pooled)
        for cand, rule in group:
            if cand is survivor:
                continue
            report.append(
                {"would_drop": cand.url, "survivor": survivor.url, "rule": rule}
            )
    return report
