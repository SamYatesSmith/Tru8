"""Study identity from persistent identifiers — pure lexical, no network.

Two URLs can carry ONE study: the journal article, its PubMed abstract, the
PMC full text, a DOI resolver link, a preprint mirror. The state function
weighs references by tier, so three primary hosts of one trial read as three
independent primaries (weight 9) for what is one observation. Astra finding 10
(2026-09-07): "group multiple URLs describing one study … adding duplicate
URLs does not strengthen a state by arithmetic alone."

This module answers only "do these two items carry the same persistent
identifier?" — DOI first, then PubMed id, then PMC id. It never infers
identity from a shared trial acronym, title similarity or matching numbers:
two papers ABOUT one trial are still two papers, and the honest failure mode
for an identity rule is to miss a duplicate, not to merge two studies.
"""

import re
from typing import Any, Dict, Optional

# DOI: prefix 10.<registrant>/<suffix>; suffix stops at whitespace, quotes or
# angle brackets. Trailing sentence punctuation is stripped afterwards.
_DOI_CORE = r"(10\.\d{4,9}/[^\s\"'<>]+)"
_DOI_IN_URL = re.compile(r"\b" + _DOI_CORE, re.I)
_DOI_IN_TEXT = re.compile(r"(?:\bdoi:?\s*|doi\.org/)" + _DOI_CORE, re.I)
_PMID = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,9})\b", re.I)
_PMC = re.compile(r"\b(PMC\d{5,9})\b", re.I)
_TRAILING = ".,;:)]}'\""


def _clean_doi(raw: str) -> str:
    doi = raw.strip().rstrip(_TRAILING).lower()
    # Publisher URLs append routes after the DOI: /full, /abstract, ?query.
    for stop in ("/full", "/abstract", "/pdf", "/epdf", "?", "#"):
        cut = doi.find(stop)
        if cut > 0:
            doi = doi[:cut]
    return doi


def study_identifier(ev: Dict[str, Any]) -> Optional[str]:
    """`doi:…` / `pmid:…` / `pmc:…` for the study this item carries, else None.

    DOI first, from the URL and then the text: a PubMed or PMC page prints the
    article's DOI, and reading the DOI before the host's own id is what lets
    the journal page, the abstract and the full text resolve to ONE study. An
    item that prints a DOI is carrying that study (a report citing the paper
    is a copy of its content, not an independent observation). PMID/PMC ids
    are read from the URL only: in running text they are commonly citations
    of other papers.
    """
    url = ev.get("url") or ""
    text = " ".join(
        part for part in (ev.get("title"), ev.get("snippet") or ev.get("text")) if part
    )
    m = _DOI_IN_URL.search(url)
    if m:
        return "doi:" + _clean_doi(m[1])
    m = _DOI_IN_TEXT.search(text)
    if m:
        return "doi:" + _clean_doi(m[1])
    m = _PMID.search(url)
    if m:
        return "pmid:" + m[1]
    m = _PMC.search(url)
    if m:
        return "pmc:" + m[1].upper()
    return None
