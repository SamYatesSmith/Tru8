"""Class-targeted query augmentation (Step 1 of pool-diversity plan, 2026-05-12).

The LLM Query Planner generates 2-3 generic queries per element. Web
search providers tend to surface Wikipedia + DOI for generic queries,
under-representing authoritative news and government sources. The
result on TRU-EA4A-9E9E (2021 PNW heat dome): 3 unique domains per
claim, 4x Wikipedia, 6x doi.org, no BBC/Guardian/Reuters/Met Office
despite extensive mainstream coverage.

This module adds **mechanical** class-targeted queries on top of the
LLM's output — one per element, picked from the claim's domain
profile. Mechanical means: no extra LLM call, no prompt change,
deterministic from the article classification. Mirrors the
mechanical-compensator pattern of B4 freshness injection and NF-20-B
DATE propagation.

Empirical basis: spike on 2026-05-12 confirmed Serper / Brave /
SerpAPI all honour `site:X OR site:Y` at 100% (10-15 results per
query, all from the requested set, naturally distributed). See
``backend/scripts/spike_site_operator.py``.

Cost: one extra provider call per element. ~2x search volume on
claims that match an augmented class. Compute claims that match a
class are typically Politics / Finance / Health / Climate / Sports
/ Legal — narrow enough that General claims stay at 1x cost.
"""

from typing import Any, Dict, List, Optional


# Source classes per domain. Each class is a single `site:X OR site:Y`
# string ready to be appended to the LLM's base query.
#
# Rules of thumb:
#   * Keep each class to ~6-8 sites so the OR-list doesn't dwarf the
#     base query keywords (providers cap query length).
#   * Authoritative news is cross-cutting and appears in nearly every
#     domain profile. Domain-specific lists also include officials
#     and (where appropriate) academic sources.
#   * Sites within a class are listed in rough authority order; many
#     providers honour ordering as a soft ranking hint.

_NEWS_GLOBAL = (
    "site:bbc.co.uk OR site:theguardian.com OR site:reuters.com "
    "OR site:apnews.com OR site:ft.com OR site:economist.com"
)

_NEWS_US_LEANING = (
    "site:reuters.com OR site:apnews.com OR site:nytimes.com "
    "OR site:washingtonpost.com OR site:wsj.com OR site:npr.org"
)

_ACADEMIC_GLOBAL = (
    "site:nature.com OR site:science.org OR site:doi.org "
    "OR site:nejm.org OR site:thelancet.com OR site:plos.org"
)


# Domain → list of class-query strings to fan out. The augmenter
# picks ONE per element to keep per-element cost manageable; the
# first matching class is preferred. Ordered intentionally.
_CLASS_QUERIES_PER_DOMAIN: Dict[str, List[str]] = {
    "Politics": [_NEWS_GLOBAL],
    "Finance": [_NEWS_GLOBAL],
    "Health": [_ACADEMIC_GLOBAL, _NEWS_GLOBAL],
    "Climate": [_ACADEMIC_GLOBAL, _NEWS_GLOBAL],
    "Science": [_ACADEMIC_GLOBAL, _NEWS_GLOBAL],
    "Sports": [_NEWS_GLOBAL],
    "Law": [_NEWS_GLOBAL],
    "Weather": [_NEWS_GLOBAL],
    "Environment": [_ACADEMIC_GLOBAL, _NEWS_GLOBAL],
    "Demographics": [_NEWS_GLOBAL],
    "General": [_NEWS_GLOBAL],
}


# Jurisdiction-aware official-source class. Augments domain-class
# choice when the article classification provides a jurisdiction.
_OFFICIAL_SITES_PER_JURISDICTION: Dict[str, str] = {
    "UK": (
        "site:gov.uk OR site:parliament.uk OR site:ons.gov.uk "
        "OR site:bankofengland.co.uk OR site:nhs.uk"
    ),
    "US": (
        "site:sec.gov OR site:congress.gov OR site:whitehouse.gov "
        "OR site:cdc.gov OR site:nih.gov OR site:federalreserve.gov"
    ),
    "EU": (
        "site:europa.eu OR site:ecb.europa.eu OR site:ec.europa.eu "
        "OR site:eurostat.ec.europa.eu"
    ),
}


# Domains that get an official-source class IN ADDITION to the
# default news/academic class (i.e. 2 class queries per element
# instead of 1). Use sparingly — each extra class is a provider call.
_DOMAINS_WORTH_OFFICIAL: set = {"Politics", "Finance", "Health", "Law"}


def augment_plans_with_class_queries(
    plans: List[Dict[str, Any]],
    article_classification: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Append class-targeted queries to each element plan.

    Mutates each plan dict in place: extends ``queries`` with one or
    two class-targeted strings derived from the article's primary
    domain (and optionally jurisdiction). Each appended query is
    constructed as ``"{base} {class_sites}"`` using the FIRST query
    in the plan as the base (the LLM's most-confident query).

    Returns the same list for caller chaining.

    No-op when:
      * ``article_classification`` is absent
      * ``primary_domain`` is missing or unmapped
      * a plan has no queries (the LLM yielded nothing)

    Why FIRST query as base, not all of them:
      * Search providers return ~10-15 results per query, mostly
        overlapping when the queries are similar. Appending site:
        filters to every LLM query produces duplicate authoritative
        coverage. Using just the first preserves provider call budget.

    Why mechanical, not LLM-driven:
      * NF-11 lesson: prompt-only changes to retrieval behaviour are
        fragile. The LLM Query Planner prompt explicitly forbids
        site: filters (line 163 of query_planner.py) — we honour
        that by augmenting outside the LLM seam.
    """
    if not plans or not article_classification:
        return plans

    domain = article_classification.get("primary_domain") or "General"
    jurisdiction = article_classification.get("jurisdiction")

    class_queries = _CLASS_QUERIES_PER_DOMAIN.get(domain)
    if not class_queries:
        class_queries = _CLASS_QUERIES_PER_DOMAIN["General"]

    # Optional second class for high-value domains: jurisdiction-aware
    # officials.
    official_class: Optional[str] = None
    if domain in _DOMAINS_WORTH_OFFICIAL and jurisdiction:
        official_class = _OFFICIAL_SITES_PER_JURISDICTION.get(jurisdiction)

    for plan in plans:
        queries = plan.get("queries") or []
        if not queries:
            continue

        base = queries[0]
        augmented: List[str] = list(queries)

        # Pick the highest-priority class (first in the per-domain list)
        primary_class = class_queries[0]
        augmented.append(f"{base} {primary_class}")

        if official_class:
            augmented.append(f"{base} {official_class}")

        plan["queries"] = augmented

    return plans
