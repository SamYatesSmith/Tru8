"""Signup-source attribution rules (2026-08-11, audit/OUTREACH.md).

Two mechanical rules, kept pure so they are testable without a database:

- ``normalise_signup_source``: what counts as a valid tag. Lowercased,
  restricted charset, bounded length. Anything else is rejected (None), and a
  rejected tag is simply not recorded — the user stays UNKNOWN.
- ``attribution_window_open``: the tag may only be written shortly after the
  account was created. Without this, an EXISTING user landing on a tagged link
  months later would have their NULL backfilled by a visit that had nothing to
  do with why they signed up — mis-attribution, which is worse than none.
"""

from datetime import datetime, timedelta
import re

# Tags are minted by us for outreach links; the pattern is deliberately narrow.
_SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")

# How long after account creation a source may still be recorded. Generous
# enough to survive "signed up on the phone, opened the laptop next morning"
# via a re-click of the same tagged link; short enough that a later organic
# visit cannot rewrite history.
ATTRIBUTION_WINDOW = timedelta(hours=72)


def normalise_signup_source(raw: object) -> str | None:
    """Return the canonical tag, or None if the input is not a valid tag."""
    if not isinstance(raw, str):
        return None
    tag = raw.strip().lower()
    if not _SOURCE_RE.match(tag):
        return None
    return tag


def attribution_window_open(created_at: datetime, now: datetime) -> bool:
    """True while a signup source may still be recorded for this account."""
    return (now - created_at) <= ATTRIBUTION_WINDOW


# Self-reported "How did you hear about us?" (2026-10-01). The codes are
# stored; the labels are the frontend's. "skipped" records a dismissal so the
# question is never asked twice.
HEARD_ABOUT_CODES = frozenset(
    {
        "search",
        "ai_assistant",
        "bluesky",
        "linkedin",
        "newsletter",
        "colleague",
        "shared_record",
        "mcp_directory",
        "other",
        "skipped",
    }
)
HEARD_ABOUT_DETAIL_MAX = 200


def normalise_heard_about(answer: object, detail: object) -> tuple | None:
    """(code, detail) for a valid answer, else None. Detail is kept only for
    "other", trimmed, control characters removed, capped."""
    if not isinstance(answer, str) or answer not in HEARD_ABOUT_CODES:
        return None
    if answer != "other" or not isinstance(detail, str):
        return answer, None
    clean = "".join(ch for ch in detail if ch.isprintable()).strip()
    return answer, (clean[:HEARD_ABOUT_DETAIL_MAX] or None)
