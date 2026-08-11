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
