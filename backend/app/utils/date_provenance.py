"""Date provenance — where did an evidence item's published_date come from?

F2 (audit/2026-07-03_f1f2_design_review.md): search engines sometimes
synthesise a "publication" date from a URL upload path — e.g. a 2000-era PDF
hosted under /wp-content/uploads/2026/04/ reported as Apr 2026. Displaying
that guess unlabelled on a signed record misstates the document's age.

Rule of the layer: provenance is LABELLED, never used to drop evidence
(no hidden curation — every item keeps its date and its receipt).

Values stored on Evidence.date_basis:
- "page_metadata"        — parsed from the page's own declared metadata
                           (JSON-LD / OpenGraph / meta / <time>); most trusted
- "engine"               — the search provider's date field, unconfirmed
- "url_inferred_suspect" — the engine's date matches a /YYYY/MM/ segment in
                           the URL and the page offered no date of its own —
                           likely the host's upload date, not publication
- "api_adapter"          — source_date from a government/academic API adapter;
                           authoritative for that source
- None                   — no date available at all
"""

import re
from typing import Optional

from app.utils.date_utils import parse_date

DATE_BASIS_PAGE = "page_metadata"
DATE_BASIS_ENGINE = "engine"
DATE_BASIS_URL_SUSPECT = "url_inferred_suspect"
DATE_BASIS_API = "api_adapter"

# /2026/04/ or /2026/4/ style path segments (WordPress-style upload paths)
_URL_DATE_RE = re.compile(r"/((?:19|20)\d{2})/(0?[1-9]|1[0-2])/")


def derive_date_basis(
    url: Optional[str],
    engine_date,
    page_date=None,
) -> Optional[str]:
    """Classify the provenance of the published_date we are about to store.

    Precedence mirrors the storage rule (F2 decision 3, founder-approved):
    the page's own declared date wins; the engine's date is the fallback;
    an engine date that merely echoes a /YYYY/MM/ URL path segment, with no
    page confirmation, is labelled suspect (kept, not dropped).
    """
    if page_date:
        return DATE_BASIS_PAGE
    if not engine_date:
        return None

    parsed = parse_date(engine_date)
    if parsed is not None:
        match = _URL_DATE_RE.search(url or "")
        if (
            match
            and int(match.group(1)) == parsed.year
            and int(match.group(2)) == parsed.month
        ):
            return DATE_BASIS_URL_SUSPECT
    return DATE_BASIS_ENGINE
