import copy
import hashlib
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple, Union
import os
from app.services.search import SearchService, SearchResult, JURISDICTION_TO_COUNTRY
from app.services.title_recovery import recover_truncated_titles
from app.services.evidence import (
    EvidenceExtractor,
    EvidenceSnippet,
    get_runtime_blocked_domains,
    is_domain_blocked,
)
from app.utils.date_provenance import DATE_BASIS_API, derive_date_basis
from app.utils.url_utils import extract_domain
from app.services.government_api_client import get_api_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

# M-05: Jurisdiction-aware adapter routing (config-driven)
# Loaded from settings.JURISDICTION_ADAPTERS JSON string.
import json as _json


def _load_jurisdiction_adapters() -> dict:
    """Parse jurisdiction→adapter-name mapping from config."""
    raw = getattr(settings, "JURISDICTION_ADAPTERS", "{}")
    try:
        return _json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return {}


def get_adapters_for_jurisdiction(jurisdiction: str | None) -> list[str] | None:
    """Return allowed adapter names for a jurisdiction, or None for unrestricted.

    - None jurisdiction → global adapters only
    - Known jurisdiction → global + jurisdiction-specific (deduped, order preserved)
    - Returns None if config is empty (no filtering applied)

    Adapters intentionally listed in both `global` and a jurisdiction-specific
    list (e.g. ONS in `uk` + `global` post-B2) are deduped here so callers see
    each name once.
    """
    mapping = _load_jurisdiction_adapters()
    if not mapping:
        return None  # No config — don't filter
    global_names = mapping.get("global", [])
    if not jurisdiction:
        return list(dict.fromkeys(global_names))
    specific = mapping.get(jurisdiction.lower(), mapping.get(jurisdiction, []))
    return list(dict.fromkeys(global_names + specific))


# B1 (audit §2.2): Per-domain adapter caps (config-driven).
# Loaded from settings.ADAPTER_CAPS_PER_DOMAIN JSON string.
_DEFAULT_ADAPTER_CAP = 3


def _load_adapter_caps() -> dict:
    """Parse domain→cap mapping from config. Always returns a dict with a DEFAULT key."""
    raw = getattr(settings, "ADAPTER_CAPS_PER_DOMAIN", "{}")
    try:
        parsed = _json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    parsed.setdefault("DEFAULT", _DEFAULT_ADAPTER_CAP)
    return parsed


def get_adapter_cap_for_domain(domain: str | None) -> int:
    """Return the max adapters per claim for the given article domain.

    Unknown domains fall back to the DEFAULT cap. Guarantees a valid integer
    even if the env override is malformed or missing a DEFAULT key.
    """
    caps = _load_adapter_caps()
    value = caps.get(domain, caps["DEFAULT"]) if domain else caps["DEFAULT"]
    try:
        return int(value)
    except (TypeError, ValueError):
        return _DEFAULT_ADAPTER_CAP


# NF-09: cross-domain claims need extra cap headroom. The article classifier
# returns up to 2 secondary domains (article_classifier.py — "Any secondary
# domains (max 2) if the article crosses topics") and retrieve.py merges
# their adapters into the selection pool. Without widening the cap they get
# silently dropped — observed on TRU-DD26-16FE ("Climate Change Act 2008"
# classified as Climate; Law specialists Bills/Hansard/GOV.UK/Companies
# House all cap-victimised by Climate cap=4).
_NF09_SLOTS_PER_SECONDARY = 2
_NF09_MAX_SECONDARIES = 2  # defensive clip — matches the classifier contract


def get_effective_adapter_cap(
    primary_domain: str | None,
    secondary_domains: Optional[List[str]] = None,
) -> int:
    """NF-09: cap for the merged primary+secondary adapter pool.

    Adds 2 slots per secondary domain on top of the primary cap. With the
    classifier's max-2-secondaries constraint the worst case is
    primary_cap + 4 (e.g. Climate=4 + 2 secondaries = 8 adapters), keeping
    latency bounded while letting cross-domain specialists survive.

    Defensively clips secondary count at 2 to match the classifier's
    documented contract — guards against a future prompt regression
    silently inflating the cap and blowing the latency budget.
    """
    base = get_adapter_cap_for_domain(primary_domain)
    if not secondary_domains:
        return base
    secondary_count = min(len(secondary_domains), _NF09_MAX_SECONDARIES)
    return base + _NF09_SLOTS_PER_SECONDARY * secondary_count


def _resolve_search_country(claim: Dict[str, Any]) -> Optional[str]:
    """Resolve claim jurisdiction to a search provider country code.

    Returns 2-letter lowercase country code (e.g., 'gb', 'us') or None
    (meaning omit country filter for EU/Global jurisdictions).
    """
    article_classification = claim.get("article_classification", {})
    jurisdiction = (
        article_classification.get("jurisdiction") if article_classification else None
    )
    if not jurisdiction:
        return "gb"  # Default: UK (preserves current behaviour)
    return JURISDICTION_TO_COUNTRY.get(jurisdiction, "gb")


SATIRE_DOMAINS = {
    "theonion.com",
    "babylonbee.com",
    "clickhole.com",
    "thebeaverton.com",
    "waterfordwhispersnews.com",
    "thedailymash.co.uk",
    "newsthump.com",
    "borowitz-report.newyorker.com",
    "reductress.com",
    "hard-drive.net",
}


# ---------------------------------------------------------------------------
# Element-level retrieval lanes (Phase 2, 2026-07-27)
#
# Design: audit/2026-07-27_phase2_element_retrieval_build_design.md
#
# A "lane" is one target the query planner plans for. Until 2026-07-27 there
# was exactly one lane per claim — a synthetic element carrying the raw claim
# text — because the seam that was supposed to feed real elements read a key
# (claim["elements"]) that nothing ever wrote. Now each claim gets:
#
#   * the CLAIM lane: the claim text, identical in every respect to the old
#     synthetic element, so the factual path keeps the route that works;
#   * one lane per Claim Map element, so the questions the map actually asks
#     are searched rather than inferred from the claim's own wording.
#
# The claim lane's id is deliberately NOT "e1": every result it returns is
# stamped with its lane id, and "e1" silently attributed the whole pool to the
# first real element.
# ---------------------------------------------------------------------------

CLAIM_LANE_ELEMENT_ID = "c0"

# Claim Map contract ceiling (1-5 elements). Defensive: a malformed map
# cannot fan retrieval out without bound.
MAX_ELEMENT_LANES = 5

# Queries per element lane. The planner emits at most 2 per element
# (query_planner._validate_plans), and class-targeted site: augmentation is
# claim-lane only, so this is the natural ceiling rather than a cost trim.
# More queries would not buy more evidence — the fetch budget binds, so extra
# lanes only thin each lane's allocation.
ELEMENT_LANE_MAX_QUERIES = 2

# Results requested per element-lane query. Providers bill per call, not per
# result (search.py caps `num` at 20), so this is about candidate diversity,
# not cost. The claim lane keeps its historical depth: max_sources // n.
ELEMENT_RESULTS_PER_QUERY = 5

# Ceiling on results requested per CLAIM-lane query. The depth rule is
# "the depth the claim lane would have had on its own" — max_sources // its own
# query count — which lands on 13 for the designed 3 queries. A SYNTHESISED
# claim lane has only one query, so the same rule asked for the entire budget
# (40) and skewed the candidate pool. Capping at the designed depth leaves the
# 3-query case untouched (40 // 3 == 13) and makes the 1-query case sane.
CLAIM_LANE_MAX_RESULTS_PER_QUERY = 13

# Fetch-budget weighting. The claim lane draws this many URLs per
# round-robin round against 1 for each element lane.
CLAIM_LANE_FETCH_WEIGHT = 2
ELEMENT_LANE_FETCH_WEIGHT = 1


def _build_retrieval_lanes(claim: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build the planner's lane list for one claim.

    Returns ``[claim lane] + [element lanes]`` when the claim carries a
    decomposed Claim Map and ``ENABLE_ELEMENT_RETRIEVAL`` is on; otherwise the
    single synthetic claim-text lane the planner has always received (id
    "e1"), byte-for-byte.

    Elements are read from ``claim["claim_map"]["elements"]`` — where decompose
    and the grounds stage actually write them.

    A caller that populates ``claim["elements"]`` itself gets those lanes
    verbatim, with **no** claim lane added, **whatever the flag says**: the one
    such caller is the Seeker's re-search (``re_search.py``), whose whole
    contract is to search ONE named element. Adding the claim text there would
    spend half the fetch budget re-searching what the user already has.
    """
    claim_text = claim.get("text", "") or ""

    # Checked BEFORE the flag, because pre-Phase-2 this was the first thing the
    # seam did and there was no flag at all. ENABLE_ELEMENT_RETRIEVAL=False
    # promises "today, byte-for-byte" — and today, a caller that names its own
    # elements gets them. Gating this on the flag would make rolling back
    # silently re-point the Seeker's targeted re-query at the claim text: the
    # exact defect this phase exists to kill, arriving down the rollback path,
    # at the moment of most pressure and least attention.
    caller_supplied = claim.get("elements") or []
    if caller_supplied:
        # Byte-identical to the pre-Phase-2 branch for this caller.
        return [
            {
                "element_id": el.get("element_id", f"e{j + 1}"),
                "description": el.get("description", ""),
            }
            for j, el in enumerate(caller_supplied)
        ]

    if not settings.ENABLE_ELEMENT_RETRIEVAL:
        return [{"element_id": "e1", "description": claim_text}]

    claim_map = claim.get("claim_map") or {}
    elements = claim_map.get("elements") or []

    element_lanes: List[Dict[str, str]] = []
    for j, el in enumerate(elements):
        if not isinstance(el, dict):
            continue
        description = (el.get("description") or "").strip()
        if not description:
            continue
        element_id = el.get("element_id") or f"e{j + 1}"
        if element_id == CLAIM_LANE_ELEMENT_ID:
            # A real element must never collide with the claim lane.
            continue
        element_lanes.append({"element_id": element_id, "description": description})
        if len(element_lanes) >= MAX_ELEMENT_LANES:
            break

    if not element_lanes:
        # Pre-decomposition (or an empty map): unchanged single-lane behaviour.
        return [{"element_id": "e1", "description": claim_text}]

    return [
        {"element_id": CLAIM_LANE_ELEMENT_ID, "description": claim_text}
    ] + element_lanes


def _class_augmentation_targets(
    query_plans: List[Dict[str, Any]], wired_claim_idxs: set
) -> List[Dict[str, Any]]:
    """Plans that receive class-targeted ``site:`` variants.

    On an element-wired claim these go to the CLAIM lane only: they are derived
    from the article's domain/jurisdiction and exist to fix pool-wide outlet
    diversity, so one authoritative lane serves the whole claim. Per-element
    copies would spend queries without adding evidence — the fetch budget
    binds, so extra queries only thin each lane's share of it.

    Claims that are not wired (pre-decomposition, or the flag off) are
    augmented exactly as before.
    """
    return [
        p
        for p in query_plans
        if p.get("claim_index", 0) not in wired_claim_idxs
        or p.get("element_id") == CLAIM_LANE_ELEMENT_ID
    ]


def _lane_of(query_index: Optional[int], query_element_ids: List[str]) -> str:
    """Lane id that produced a search result, or "?" when unattributable."""
    if query_index is None:
        return "?"
    if 0 <= query_index < len(query_element_ids):
        return query_element_ids[query_index] or "?"
    return "?"


def _lane_histogram(results: List[Any], query_element_ids: List[str]) -> Dict[str, int]:
    """Count results per lane — the per-lane share of the fetch budget."""
    histogram: Dict[str, int] = {}
    for result in results:
        lane = _lane_of(getattr(result, "_query_index", None), query_element_ids)
        histogram[lane] = histogram.get(lane, 0) + 1
    return histogram


def _allocate_fetch_budget(
    results: List[Any],
    query_element_ids: List[str],
) -> List[Any]:
    """Order search results so the fetch budget is shared across lanes.

    ``results`` arrives in query order, so truncating it funds the earliest
    queries and starves the latest — which, once element lanes exist, means
    the last element of a claim can contribute nothing while its queries are
    logged as having run.

    This re-orders (never drops) by weighted round-robin over the queries:
    each round takes ``CLAIM_LANE_FETCH_WEIGHT`` results from each claim-lane
    query and ``ELEMENT_LANE_FETCH_WEIGHT`` from each element-lane query,
    preserving each query's own ranking within its bucket. The caller applies
    the ``max_sources`` cut, so every lane is represented before any lane goes
    deep.
    """
    if not results:
        return results

    buckets: Dict[int, List[Any]] = {}
    order: List[int] = []
    for result in results:
        qi = getattr(result, "_query_index", None)
        key = qi if isinstance(qi, int) else -1
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(result)

    ordered: List[Any] = []
    cursors = {key: 0 for key in order}
    while len(ordered) < len(results):
        progressed = False
        for key in order:
            bucket = buckets[key]
            cursor = cursors[key]
            if cursor >= len(bucket):
                continue
            lane = _lane_of(key if key >= 0 else None, query_element_ids)
            weight = (
                CLAIM_LANE_FETCH_WEIGHT
                if lane == CLAIM_LANE_ELEMENT_ID
                else ELEMENT_LANE_FETCH_WEIGHT
            )
            take = bucket[cursor : cursor + weight]
            ordered.extend(take)
            cursors[key] = cursor + len(take)
            progressed = True
        if not progressed:
            break

    return ordered


def _synthesise_claim_lane_plan(
    plans: List[Dict[str, Any]], claim_index: int, claim_text: str
) -> List[Dict[str, Any]]:
    """Guarantee the claim lane has a plan, whatever the planner returned.

    The planner is handed a ``c0`` lane carrying the claim text and, live, does
    not plan for it. Three networked checks on 2026-07-28 each logged
    ``Lane shortfall | unqueried_lanes=['c0']`` — consistently, not flakily:
    the planner prompt's only JSON example shows an element id of the form
    "e1", so ``c0`` reads as unfamiliar.

    The damage was not one missing query. ``element_wired`` was derived from
    the plans RETURNED, so a missing ``c0`` silently made it False and the
    per-lane request sizes and weighted round-robin never executed at all —
    green in unit tests, dead in production.

    The claim lane's query IS the claim text: that is exactly what the single
    synthetic lane searched pre-Phase-2. So this needs no model call and cannot
    fail. Mechanical post-processing, never a prompt tweak — NF-11.
    """
    if not claim_text:
        return plans
    if any(p.get("element_id") == CLAIM_LANE_ELEMENT_ID for p in plans):
        return plans

    logger.info(
        f"[RETRIEVE] Claim lane synthesised | claim={claim_index} — planner "
        f"returned no {CLAIM_LANE_ELEMENT_ID} plan; using claim text verbatim"
    )
    return [
        {
            "claim_index": claim_index,
            "element_id": CLAIM_LANE_ELEMENT_ID,
            "queries": [claim_text],
            # Inherit the batch's freshness rather than inventing one; "py" is
            # the planner's own default when it has no reason to narrow.
            "freshness": next(
                (p.get("freshness") for p in plans if p.get("freshness")), "py"
            ),
            "reasoning": "synthesised claim lane (planner omitted it)",
        }
    ] + plans


def _hedged_query_freshness(element_freshness: str, query_position: int) -> str:
    """F1-D3 recency hedge (2026-07-06, design audit/2026-07-03_f1f2_design_review.md).

    Of each element's planned queries, the SECOND (position 1) runs with no
    freshness window so historical/contemporaneous material always has a
    retrieval lane. Claims about the past that carry no explicit year token
    were structurally windowed to the last 12 months (report-quality review
    F1 — the all-2026 evidence set for a 1998-2008 topic): the planner's
    default freshness is "py" and B4's unwindowing only triggers on an
    explicit past-year DATE entity.

    Breaking-news elements are exempt (founder decision #2): when the planner
    chose pd/pw, every lane stays recent. Positions 0 and 2+ (class-augmented
    extras) keep the element's freshness; B4's "none" is already unwindowed.
    """
    if query_position == 1 and element_freshness not in ("pd", "pw"):
        return "none"
    return element_freshness


def _merge_element_plans(
    plans: List[Dict[str, Any]],
    max_queries_per_element: int,
    element_wired: Optional[bool] = None,
) -> Dict[str, Any]:
    """Merge one claim's per-element query plans into a claim-level query_plan.

    Builds the parallel arrays consumed by execute_planned_queries
    (queries / query_element_ids / query_freshness), applying the per-element
    query cap (L-04) and the F1-D3 recency hedge per position. Plan-level
    freshness/reasoning fall back to the first element's plan, matching the
    pre-extraction behaviour (2026-07-06 — pulled out of retrieve_evidence's
    inline loop so the hedge is testable at the wired seam).
    """
    # Phase 2: a claim lane alongside ≥1 element lane means element-level
    # retrieval is live for this claim.
    #
    # `element_wired` is passed in by callers that KNOW which lanes they built.
    # Deriving it from the plans returned made a budget guarantee contingent on
    # the LLM's cooperation, and live it did not cooperate (2026-07-28: c0
    # omitted on 3/3 checks, so the per-lane sizing and round-robin never ran).
    # The derivation survives only for callers that supply their own plans
    # wholesale — re_search.py — where it correctly yields False.
    if element_wired is None:
        lane_ids = {p.get("element_id", "e1") for p in plans}
        element_wired = CLAIM_LANE_ELEMENT_ID in lane_ids and len(lane_ids) > 1

    # Claim lane first, deterministically; element order otherwise preserved.
    if element_wired:
        plans = sorted(
            plans,
            key=lambda p: 0 if p.get("element_id") == CLAIM_LANE_ELEMENT_ID else 1,
        )

    merged_queries: List[str] = []
    query_element_ids: List[str] = []
    query_freshness: List[str] = []
    for p in plans:
        element_id = p.get("element_id", "e1")
        element_freshness = p.get("freshness", "py")
        # Cap queries per element (L-04). Element lanes take the tighter
        # Phase 2 cap: the planner emits ≤2 per element and class-targeted
        # augmentation is claim-lane only, so a third query would only thin
        # the fetch allocation.
        lane_cap = max_queries_per_element
        if element_wired and element_id != CLAIM_LANE_ELEMENT_ID:
            lane_cap = min(max_queries_per_element, ELEMENT_LANE_MAX_QUERIES)
        elem_queries = (p.get("queries") or [])[:lane_cap]
        for pos, q in enumerate(elem_queries):
            merged_queries.append(q)
            query_element_ids.append(element_id)
            query_freshness.append(_hedged_query_freshness(element_freshness, pos))
    return {
        "queries": merged_queries,
        "query_element_ids": query_element_ids,
        "query_freshness": query_freshness,
        "freshness": plans[0].get("freshness", "py") if plans else "py",
        "reasoning": plans[0].get("reasoning", "") if plans else "",
        "element_wired": element_wired,
    }


class EvidenceRetriever:
    """Retrieve and rank evidence for claims using search, embeddings, and vector storage"""

    # Minimum evidence per claim - triggers recovery search if below this threshold
    MIN_EVIDENCE_PER_CLAIM = 2

    # Authoritative sources by domain for targeted recovery searches
    AUTHORITATIVE_SOURCES_BY_DOMAIN = {
        "health": [
            "who.int",
            "cdc.gov",
            "nih.gov",
            "nhs.uk",
            "pubmed.ncbi.nlm.nih.gov",
        ],
        "science": ["nature.com", "science.org", "ncbi.nlm.nih.gov", "arxiv.org"],
        "government": ["gov.uk", "usa.gov", "congress.gov", "govinfo.gov"],
        "finance": ["sec.gov", "federalreserve.gov", "imf.org", "worldbank.org"],
        "sports": ["transfermarkt.com", "espn.com", "bbc.com/sport"],
        "general": ["reuters.com", "apnews.com", "bbc.com"],
    }

    def __init__(self):
        self.search_service = SearchService()
        self.evidence_extractor = EvidenceExtractor()
        self.max_sources_per_claim = settings.MAX_SOURCES_PER_CLAIM
        self.max_concurrent_claims = (
            10  # High ceiling — shared URL pool governs total concurrency
        )
        # Per-element query cap. Raised 3 → 5 on 2026-05-12 to accommodate
        # Step 1 class-targeted query augmentation. LLM Planner produces
        # 2-3 queries; mechanical augmentation adds 1-2 class-targeted
        # queries; total caps at 5 so we never run >5 provider calls per
        # element regardless of how many classes apply.
        self.max_queries_per_element = 5

        # Phase 5: Government API Integration
        self.api_registry = get_api_registry()
        self.enable_api_retrieval = True  # Feature flag (set via settings)

    async def retrieve_evidence_for_claims(
        self,
        claims: List[Dict[str, Any]],
        exclude_source_url: Optional[str] = None,
        progressive_results: Optional[Dict] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve evidence for multiple claims concurrently.

        Args:
            progressive_results: Optional shared dict. If provided, results are
                written progressively as each claim completes so the caller can
                read partial results on timeout.
        """
        import time as _time

        _func_start = _time.time()
        logger.info(
            f"[RETRIEVER DEBUG] retrieve_evidence_for_claims called with {len(claims)} claims"
        )
        try:
            # Extract excluded domain if provided
            excluded_domain = None
            if exclude_source_url:
                excluded_domain = extract_domain(exclude_source_url)
                logger.debug(f"Excluding source domain: {excluded_domain}")

            # Query Planning Agent: Generate targeted queries for all claims (single LLM call)
            query_plans = None
            logger.info(
                f"[RETRIEVE] QUERY_PLANNING_ENABLED: {settings.ENABLE_QUERY_PLANNING}"
            )
            if settings.ENABLE_QUERY_PLANNING:
                try:
                    from app.utils.query_planner import get_query_planner

                    planner = get_query_planner()

                    # Phase 4: Pass article context to query planner for dynamic freshness decisions
                    article_context = None
                    if claims and claims[0].get("article_classification"):
                        article_context = claims[0]["article_classification"]
                        logger.info(
                            f"[RETRIEVE] Passing article context to query planner: domain={article_context.get('primary_domain')}"
                        )

                    # Build claims_with_elements for element-level query planning
                    claims_with_elements = []
                    wired_claim_idxs = set()
                    for i, claim in enumerate(claims):
                        elem_list = _build_retrieval_lanes(claim)
                        if any(
                            el["element_id"] == CLAIM_LANE_ELEMENT_ID
                            for el in elem_list
                        ):
                            wired_claim_idxs.add(i)
                            logger.info(
                                f"[RETRIEVE] Element lanes wired | claim={i} "
                                f"lanes={len(elem_list)} "
                                f"element_lanes={len(elem_list) - 1} "
                                f"ids={[el['element_id'] for el in elem_list]}"
                            )
                        else:
                            logger.info(
                                f"[RETRIEVE] Claim-level lane only | claim={i} "
                                f"(no decomposed elements or element retrieval off)"
                            )
                        claims_with_elements.append(
                            {
                                "text": claim.get("text", ""),
                                "claim_index": i,
                                "elements": elem_list,
                                # B4: typed entities for freshness injection
                                # (NF-15 DATE entities → mechanical "none" override
                                # for historical claims).
                                "key_entities": claim.get("key_entities") or [],
                            }
                        )

                    _qp_start = _time.time()
                    query_plans = await planner.plan_queries_batch(
                        claims_with_elements, article_context=article_context
                    )
                    _qp_elapsed = _time.time() - _qp_start
                    if query_plans:
                        logger.info(
                            f"Query planning complete: {len(query_plans)} element plans "
                            f"for {len(claims)} claims"
                        )

                        # Step 3 (2026-05-12): mechanical date-anchor
                        # augmentation. When a claim has a single
                        # specific year in its DATE entities and the
                        # LLM-generated query doesn't include the
                        # year, append it. Addresses the recency-bias
                        # failure mode surfaced by Prompt 1 (November
                        # 2023 Autumn Statement returning 2025 Budget
                        # content). Runs BEFORE class augmentation so
                        # class-targeted variants inherit the year.
                        from app.utils.query_date_anchor import (
                            augment_plans_with_date_anchor,
                        )

                        query_plans = augment_plans_with_date_anchor(
                            query_plans, claims_with_elements
                        )

                        # Step 1 (2026-05-12): mechanical class-targeted
                        # query augmentation. Adds one or two
                        # site:-filtered queries per element targeting
                        # authoritative news / official / academic
                        # sources for the claim's domain. Mirrors the
                        # mechanical-compensator pattern of B4 freshness
                        # injection and NF-20-B DATE propagation.
                        # See app/utils/query_class_augmentation.py.
                        from app.utils.query_class_augmentation import (
                            augment_plans_with_class_queries,
                        )

                        pre_count = sum(
                            len(p.get("queries") or []) for p in query_plans
                        )
                        augment_plans_with_class_queries(
                            _class_augmentation_targets(query_plans, wired_claim_idxs),
                            article_context,
                        )
                        post_count = sum(
                            len(p.get("queries") or []) for p in query_plans
                        )
                        if post_count > pre_count:
                            logger.info(
                                f"[QUERY AUGMENT] Added "
                                f"{post_count - pre_count} class-targeted queries "
                                f"(domain={article_context.get('primary_domain') if article_context else 'unknown'}, "
                                f"jurisdiction={article_context.get('jurisdiction') if article_context else 'unknown'}, "
                                f"base={pre_count}, total={post_count})"
                            )

                        # Group plans by claim_index and build merged query plans
                        plans_by_claim = {}
                        for plan in query_plans:
                            idx = plan.get("claim_index", 0)
                            if idx not in plans_by_claim:
                                plans_by_claim[idx] = []
                            plans_by_claim[idx].append(plan)

                        for claim_idx, plans in plans_by_claim.items():
                            if claim_idx < len(claims):
                                # The claim lane is a guarantee, not a request:
                                # if the planner skipped c0, synthesise it from
                                # the claim text before merging. Without this,
                                # "add, don't replace" silently became
                                # "replace" on every live check.
                                claim_wired = claim_idx in wired_claim_idxs
                                if claim_wired:
                                    plans = _synthesise_claim_lane_plan(
                                        plans,
                                        claim_idx,
                                        claims[claim_idx].get("text", ""),
                                    )
                                # Merge element plans into one query_plan with
                                # element tracking + the F1-D3 recency hedge
                                # (see _merge_element_plans).
                                merged_plan = _merge_element_plans(
                                    plans,
                                    self.max_queries_per_element,
                                    element_wired=claim_wired or None,
                                )
                                merged_plan["claim_index"] = claim_idx
                                claims[claim_idx]["query_plan"] = merged_plan
                                lane_counts: Dict[str, int] = {}
                                for eid in merged_plan["query_element_ids"]:
                                    lane_counts[eid] = lane_counts.get(eid, 0) + 1
                                logger.info(
                                    f"[RETRIEVE] Query lanes | claim={claim_idx} "
                                    f"wired={merged_plan['element_wired']} "
                                    f"lanes={len(lane_counts)} "
                                    f"queries={len(merged_plan['queries'])} "
                                    f"per_lane={lane_counts}"
                                )
                                # A lane the planner was given but returned no
                                # queries for is an element that will never be
                                # searched. The planner's own shortfall warning
                                # is batch-level; this names the element.
                                expected_lanes = [
                                    el["element_id"]
                                    for el in claims_with_elements[claim_idx][
                                        "elements"
                                    ]
                                ]
                                unqueried = [
                                    eid
                                    for eid in expected_lanes
                                    if eid not in lane_counts
                                ]
                                if unqueried:
                                    logger.warning(
                                        f"[RETRIEVE] Lane shortfall | claim={claim_idx} "
                                        f"unqueried_lanes={unqueried} — these elements "
                                        f"will not be searched"
                                    )
                    else:
                        logger.warning(
                            "Query planning returned no plans, using fallback"
                        )
                except Exception as e:
                    logger.warning(f"Query planning failed: {e}, using fallback")

            # Process claims with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_claims)

            # Shared URL fetch pool — all claims draw from this single pool.
            # Fast-finishing claims free slots for slow claims (work-stealing).
            url_fetch_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_URL_FETCHES)

            # Shared accumulators — written progressively as each claim completes
            evidence_by_claim = {}
            all_raw_evidence = []
            pre_weighting_by_claim = {}
            total_search_results = 0

            # Expose accumulators to caller for partial recovery on timeout
            if progressive_results is not None:
                progressive_results["evidence_by_claim"] = evidence_by_claim
                progressive_results["raw_evidence"] = all_raw_evidence
                progressive_results["pre_weighting_evidence"] = pre_weighting_by_claim

            async def _retrieve_and_store(claim_index: int, claim: Dict):
                """Retrieve evidence for one claim and store immediately.

                Keys evidence_by_claim / pre_weighting_by_claim by the claim's
                actual position (e.g. "3" for a claim at position=3), not by
                the enumerate index. The previous keying-by-index caused
                cross-attribution whenever selected positions were not
                contiguous: _ensure_minimum_evidence (line 454) and every
                downstream consumer (runner.py result-building at L2454,
                workers/pipeline.py cache merge at L296) look up evidence
                by claim["position"], so an index-keyed entry for the
                selected claim at position=3 ended up attributed to the
                claim at position=1, while position=3 then looked empty
                and re-triggered recovery. The dict accumulated both sets
                of keys (index + position), and unselected claims silently
                absorbed mis-attributed evidence at save time.
                """
                claim_position_key = str(claim.get("position", claim_index))
                try:
                    result = await self._retrieve_evidence_for_single_claim(
                        claim,
                        semaphore,
                        excluded_domain,
                        url_fetch_semaphore=url_fetch_semaphore,
                    )
                except Exception as exc:
                    logger.error(
                        f"[RETRIEVER DEBUG] Result idx={claim_index} pos={claim_position_key}: "
                        f"EXCEPTION {type(exc).__name__}: {exc}"
                    )
                    evidence_by_claim[claim_position_key] = []
                    return

                if isinstance(result, dict):
                    evidence_by_claim[claim_position_key] = result.get(
                        "filtered_evidence", []
                    )
                    pre_weighting_by_claim[claim_position_key] = result.get(
                        "pre_weighting_evidence", []
                    )
                    raw_evidence = result.get("raw_evidence", [])
                    claim_position = result.get("claim_position", claim_position_key)
                    claim_text = result.get("claim_text", "")
                    for raw_item in raw_evidence:
                        raw_item["claim_position"] = claim_position
                        raw_item["claim_text"] = claim_text
                    all_raw_evidence.extend(raw_evidence)
                    nonlocal total_search_results
                    total_search_results += result.get(
                        "search_results_count", len(raw_evidence)
                    )
                    logger.info(
                        f"[RETRIEVER DEBUG] Result idx={claim_index} pos={claim_position_key}: "
                        f"dict with {len(result.get('filtered_evidence', []))} filtered, "
                        f"{len(result.get('raw_evidence', []))} raw"
                    )
                else:
                    # Legacy list format (backward compatibility).
                    evidence_by_claim[claim_position_key] = (
                        result if isinstance(result, list) else []
                    )

            _gather_start = _time.time()
            logger.info(f"[RETRIEVER DEBUG] Gathering results for {len(claims)} tasks")
            await asyncio.gather(
                *[_retrieve_and_store(i, claim) for i, claim in enumerate(claims)],
                return_exceptions=True,
            )
            _gather_elapsed = _time.time() - _gather_start
            logger.info(
                f"[RETRIEVER DEBUG] Gather complete in {_gather_elapsed:.2f}s. "
                f"Claims completed: {len(evidence_by_claim)}"
            )

            # RECOVERY: Ensure minimum evidence per claim
            # This catches claims that ended up with insufficient evidence after initial retrieval
            _recovery_start = _time.time()
            evidence_by_claim, recovery_raw = await self._ensure_minimum_evidence(
                evidence_by_claim=evidence_by_claim,
                claims=claims,
                excluded_domain=excluded_domain,
            )
            _recovery_elapsed = _time.time() - _recovery_start
            all_raw_evidence.extend(recovery_raw)

            # Return both filtered evidence and raw evidence
            _func_elapsed = _time.time() - _func_start
            total_evidence = sum(len(ev) for ev in evidence_by_claim.values())
            return {
                "evidence_by_claim": evidence_by_claim,
                "raw_evidence": all_raw_evidence,
                "raw_sources_count": len(all_raw_evidence),
                "total_search_results": total_search_results,
                "pre_weighting_evidence": pre_weighting_by_claim,
            }

        except Exception as e:
            import traceback

            logger.error(
                f"[RETRIEVER DEBUG] Evidence retrieval EXCEPTION: {type(e).__name__}: {e}"
            )
            logger.error(f"[RETRIEVER DEBUG] Full traceback:\n{traceback.format_exc()}")
            return {"evidence_by_claim": {}, "raw_evidence": [], "raw_sources_count": 0}

    async def _ensure_minimum_evidence(
        self,
        evidence_by_claim: Dict[str, List[Dict[str, Any]]],
        claims: List[Dict[str, Any]],
        excluded_domain: Optional[str] = None,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """
        Ensure each claim has minimum evidence, triggering recovery search if needed.

        This runs AFTER initial retrieval to catch claims that ended up with
        insufficient evidence. Recovery uses targeted authoritative-source queries.

        Args:
            evidence_by_claim: Current evidence dict (claim_position -> evidence list)
            claims: List of claim dicts with text and metadata
            excluded_domain: Domain to exclude from search

        Returns:
            Tuple of (updated evidence_by_claim, raw_evidence from recovery)
        """
        # Identify claims needing recovery
        claims_needing_recovery = []
        for claim in claims:
            claim_pos = str(claim.get("position", 0))
            current_evidence = evidence_by_claim.get(claim_pos, [])

            if len(current_evidence) < self.MIN_EVIDENCE_PER_CLAIM:
                claims_needing_recovery.append(
                    {
                        "claim": claim,
                        "position": claim_pos,
                        "current_count": len(current_evidence),
                    }
                )

        if not claims_needing_recovery:
            return evidence_by_claim, []

        logger.warning(
            f"[RECOVERY] {len(claims_needing_recovery)} claims below minimum evidence "
            f"(min={self.MIN_EVIDENCE_PER_CLAIM}): positions {[c['position'] for c in claims_needing_recovery]}"
        )

        # Collect existing URLs to avoid duplicates
        existing_urls = set()
        for ev_list in evidence_by_claim.values():
            for ev in ev_list:
                if ev.get("url"):
                    existing_urls.add(ev.get("url"))

        # Run recovery for all claims in parallel (with rate limiting via semaphore)
        all_recovery_raw = []
        semaphore = asyncio.Semaphore(2)  # Limit concurrent recovery searches

        async def recover_single_claim(claim_info):
            async with semaphore:
                return await self._recover_evidence_for_claim(
                    claim=claim_info["claim"],
                    claim_position=claim_info["position"],
                    existing_urls=existing_urls,
                    excluded_domain=excluded_domain,
                )

        recovery_tasks = [recover_single_claim(c) for c in claims_needing_recovery]
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)

        # Process recovery results
        for claim_info, result in zip(claims_needing_recovery, recovery_results):
            claim_pos = claim_info["position"]

            if isinstance(result, Exception):
                logger.error(f"[RECOVERY] Failed for claim {claim_pos}: {result}")
                continue

            recovered_evidence, raw_evidence = result

            if recovered_evidence:
                # Add recovered evidence to the claim
                if claim_pos not in evidence_by_claim:
                    evidence_by_claim[claim_pos] = []
                evidence_by_claim[claim_pos].extend(recovered_evidence)

                # Add URLs to existing set to prevent duplicates in subsequent claims
                for ev in recovered_evidence:
                    if ev.get("url"):
                        existing_urls.add(ev.get("url"))

                logger.info(
                    f"[RECOVERY] Claim {claim_pos}: recovered {len(recovered_evidence)} items "
                    f"(now has {len(evidence_by_claim[claim_pos])} total)"
                )
            else:
                logger.warning(f"[RECOVERY] Claim {claim_pos}: no evidence recovered")

            all_recovery_raw.extend(raw_evidence)

        return evidence_by_claim, all_recovery_raw

    async def _recover_evidence_for_claim(
        self,
        claim: Dict[str, Any],
        claim_position: str,
        existing_urls: set,
        excluded_domain: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run targeted recovery search for a single claim with insufficient evidence.

        Uses authoritative-source-focused queries based on claim domain.

        Args:
            claim: Claim dict with text and metadata
            claim_position: Position string for logging
            existing_urls: URLs already in evidence pool (for deduplication)
            excluded_domain: Domain to exclude

        Returns:
            Tuple of (filtered_evidence, raw_evidence_metadata)
        """
        claim_text = claim.get("text", "")
        if not claim_text:
            return [], []

        try:
            # Determine domain for authoritative source selection
            article_classification = claim.get("article_classification", {})
            primary_domain = article_classification.get(
                "primary_domain", "general"
            ).lower()

            # Map to our domain categories
            domain_key = "general"
            if any(
                d in primary_domain for d in ["health", "medical", "disease", "virus"]
            ):
                domain_key = "health"
            elif any(d in primary_domain for d in ["science", "research", "study"]):
                domain_key = "science"
            elif any(d in primary_domain for d in ["government", "politics", "law"]):
                domain_key = "government"
            elif any(d in primary_domain for d in ["finance", "economic", "market"]):
                domain_key = "finance"
            elif any(d in primary_domain for d in ["sport"]):
                domain_key = "sports"

            authoritative_sources = self.AUTHORITATIVE_SOURCES_BY_DOMAIN.get(
                domain_key, []
            )

            logger.info(
                f"[RECOVERY] Claim {claim_position}: domain={domain_key}, "
                f"authoritative sources={authoritative_sources[:3]}"
            )

            # Runtime blocklist for recovery URL filtering. The main retrieve
            # path filters at fetch time in EvidenceService._extract_from_page;
            # this recovery loop uses search snippets directly (no fetch), so
            # the blocklist must be applied here. Same pattern as the
            # post-filter-recovery fix in 330ab44 — the bot_blocked-domains
            # (notably facebook.com / instagram.com, pre-seeded since
            # 2025-12-01) leaked into the evidence pool via this path on
            # TRU-E317-4192 because no check existed between search return
            # and EvidenceSnippet construction.
            blocked_domains = get_runtime_blocked_domains()

            # Generate targeted queries
            # Query 1: Direct claim text with site filter for authoritative sources
            # Query 2: Simplified key phrase extraction
            queries = self._generate_recovery_queries(claim_text, authoritative_sources)

            if not queries:
                logger.warning(
                    f"[RECOVERY] No queries generated for claim {claim_position}"
                )
                return [], []

            # Execute searches
            all_snippets = []
            for query in queries[:2]:  # Limit to 2 queries to control latency
                try:
                    search_country = _resolve_search_country(claim)
                    results = await self.search_service.search_for_evidence(
                        query,
                        max_results=5,
                        freshness="py",  # Past year - stable facts
                        country=search_country,
                    )
                    if results:
                        # Convert SearchResult to EvidenceSnippet format
                        for r in results:
                            # Skip if URL already exists
                            url = (
                                getattr(r, "url", "")
                                if hasattr(r, "url")
                                else r.get("url", "")
                            )
                            if url in existing_urls:
                                continue

                            if is_domain_blocked(url, blocked_domains):
                                logger.info(
                                    f"[URL LEDGER] claim={claim_position} "
                                    f"dropped(recovery) "
                                    f"reason='runtime_blocked_domain' "
                                    f"url={url[:120]}"
                                )
                                continue

                            snippet = EvidenceSnippet(
                                text=(
                                    getattr(r, "snippet", "")
                                    if hasattr(r, "snippet")
                                    else r.get("snippet", "")
                                ),
                                source=(
                                    getattr(r, "source", "")
                                    if hasattr(r, "source")
                                    else r.get("source", "")
                                ),
                                url=url,
                                title=(
                                    getattr(r, "title", "")
                                    if hasattr(r, "title")
                                    else r.get("title", "")
                                ),
                                published_date=(
                                    getattr(r, "published_date", None)
                                    if hasattr(r, "published_date")
                                    else r.get("published_date")
                                ),
                                relevance_score=0.0,  # No hardcoded score, LLM scorer decides
                                # word_count is calculated automatically in EvidenceSnippet.__init__
                                metadata={
                                    "recovery_search": True,
                                    "domain_key": domain_key,
                                },
                                # No page fetched here — engine date, unconfirmed
                                date_basis=derive_date_basis(
                                    url,
                                    (
                                        getattr(r, "published_date", None)
                                        if hasattr(r, "published_date")
                                        else r.get("published_date")
                                    ),
                                ),
                            )
                            all_snippets.append(snippet)

                except Exception as e:
                    logger.warning(
                        f"[RECOVERY] Search failed for query '{query[:50]}...': {e}"
                    )
                    continue

            if not all_snippets:
                return [], []

            # Apply same evidence filtering as main retrieval
            # This ensures satire exclusion, dedup, etc. are applied
            ranked_evidence = []
            for idx, snippet in enumerate(
                all_snippets[:10]
            ):  # Cap at 10 for processing
                ev_hash = hashlib.sha256((snippet.url or "").encode()).hexdigest()[:8]
                ranked_evidence.append(
                    {
                        "id": f"recovery_{claim_position}_{idx}",
                        "evidence_id": f"ev-rec-{claim_position}_{idx}_{ev_hash}",
                        "element_ids": [],
                        "text": snippet.text,
                        "source": snippet.source,
                        "url": snippet.url,
                        "title": snippet.title,
                        "published_date": snippet.published_date,
                        "date_basis": snippet.date_basis,
                        "relevance_score": float(snippet.relevance_score),
                        "semantic_similarity": 0.0,
                        "combined_score": 0.0,
                        "word_count": snippet.word_count,
                        "receipt_status": "extracted",
                        "metadata": snippet.metadata,
                        "content_basis": snippet.content_basis,
                        "is_recovery": True,
                    }
                )

            # Apply evidence filters (satire exclusion + dedup)
            result = self._apply_evidence_filters(
                ranked_evidence, claim, track_raw_evidence=True
            )
            final_evidence, raw_evidence = (
                result if isinstance(result, tuple) else (result, [])
            )

            # Mark raw evidence as from recovery
            for raw_item in raw_evidence:
                raw_item["is_recovery"] = True
                raw_item["claim_position"] = claim_position

            for raw in raw_evidence:
                url_short = (raw.get("url") or "")[:120]
                provider = raw.get("external_source_provider")
                source_type = "api" if provider else "web"
                if raw.get("is_included"):
                    logger.info(
                        f"[URL LEDGER] claim={claim_position} kept(recovery) "
                        f"type={source_type} provider={provider or '-'} "
                        f"url={url_short}"
                    )
                else:
                    stage = raw.get("filter_stage") or "unknown"
                    reason = (raw.get("filter_reason") or "")[:80]
                    logger.info(
                        f"[URL LEDGER] claim={claim_position} dropped(recovery) "
                        f"type={source_type} provider={provider or '-'} "
                        f"stage={stage} reason='{reason}' url={url_short}"
                    )

            return final_evidence, raw_evidence

        except Exception as e:
            logger.error(
                f"[RECOVERY] Error recovering evidence for claim {claim_position}: {e}"
            )
            return [], []

    def _generate_recovery_queries(
        self, claim_text: str, authoritative_sources: List[str]
    ) -> List[str]:
        """
        Generate targeted queries for recovery search.

        Focuses on authoritative sources and simplified query formulation.

        Args:
            claim_text: Original claim text
            authoritative_sources: List of authoritative domains for this claim type

        Returns:
            List of search queries
        """
        import re

        queries = []

        # Extract key phrases (nouns, numbers, proper nouns)
        # Simple extraction: words > 3 chars, exclude common words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "this",
            "that",
            "with",
            "from",
            "they",
            "their",
            "there",
            "what",
            "when",
            "where",
            "which",
            "about",
            "into",
            "than",
            "then",
            "can",
            "may",
            "also",
            "some",
            "only",
            "more",
            "most",
            "other",
        }

        words = re.findall(r"\b[a-zA-Z]{4,}\b", claim_text)
        key_words = [w for w in words if w.lower() not in stop_words][:6]

        # Also extract numbers (important for factual claims)
        numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", claim_text)

        # Query 1: Key words + numbers (general search)
        base_query = " ".join(key_words[:4])
        if numbers:
            base_query += " " + " ".join(numbers[:2])
        queries.append(base_query)

        # Query 2: With site filter for top authoritative source
        if authoritative_sources:
            site_query = f"{base_query} site:{authoritative_sources[0]}"
            queries.append(site_query)

        # Query 3: Alternative formulation with "official" or "fact sheet"
        if key_words:
            alt_query = f"{key_words[0]} official information"
            queries.append(alt_query)

        return queries

    async def retrieve_for_elements(
        self,
        elements: List[Dict[str, Any]],
        claim_text: str,
        existing_urls: set,
        article_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Targeted retrieval for specific unresolved elements.

        Used by the coverage recovery stage after evidence mapping. Generates
        one search query per element and returns evidence items in the standard
        format, deduplicated against existing_urls.

        Args:
            elements: [{"element_id": "e1", "description": "..."}]
            claim_text: Parent claim text for search context
            existing_urls: URLs to exclude (already in evidence pool)
            article_context: Article classification for query planning context

        Returns:
            List of evidence dicts in standard pipeline format.
        """
        all_evidence = []
        claim_context = claim_text[:100]

        # Runtime blocklist for recovery URL filtering (same rationale as
        # _recover_evidence_for_claim above). The main retrieve path's
        # blocklist check at EvidenceService._extract_from_page fires at
        # fetch time, but Stage 5.1 coverage recovery uses search snippets
        # directly — so blocked domains (facebook.com, instagram.com)
        # leaked through this path on TRU-E317-4192. The drop is mirrored
        # to the URL ledger so the receipt-disclosure stays honest.
        blocked_domains = get_runtime_blocked_domains()

        # Use LLM query planner for targeted recovery queries
        element_queries = {}  # element_id -> [{"query": str, "freshness": str}]

        if settings.ENABLE_RECOVERY_QUERY_PLANNING:
            try:
                from app.utils.query_planner import get_query_planner

                planner = get_query_planner()

                claims_with_elements = [
                    {
                        "text": claim_text,
                        "claim_index": 0,
                        "elements": [
                            {
                                "element_id": e["element_id"],
                                "description": e["description"],
                            }
                            for e in elements
                        ],
                    }
                ]

                plans = await asyncio.wait_for(
                    planner.plan_queries_batch(
                        claims_with_elements, article_context=article_context
                    ),
                    timeout=settings.RECOVERY_PLANNER_TIMEOUT,
                )

                if plans:
                    for plan in plans:
                        eid = plan.get("element_id", "")
                        queries = plan.get("queries", [])[:2]
                        freshness = plan.get("freshness", "py")
                        element_queries[eid] = [
                            {"query": q, "freshness": freshness} for q in queries
                        ]
                    logger.info(
                        f"[COVERAGE RECOVERY] Query planner: {len(plans)} element plans, "
                        f"{sum(len(v) for v in element_queries.values())} queries"
                    )
            except Exception as e:
                logger.warning(
                    f"[COVERAGE RECOVERY] Query planner failed ({e}), using naive queries"
                )

        for elem in elements:
            queries_for_elem = element_queries.get(elem["element_id"])

            if queries_for_elem:
                search_pairs = [
                    (qp["query"], qp["freshness"]) for qp in queries_for_elem
                ]
            else:
                search_pairs = [(f"{elem['description']} {claim_context}", "py")]

            for query, freshness in search_pairs:
                try:
                    # Resolve geo scope from article context
                    recovery_country = "gb"
                    if article_context:
                        j = article_context.get("jurisdiction")
                        if j:
                            recovery_country = JURISDICTION_TO_COUNTRY.get(j, "gb")
                    results = await self.search_service.search_for_evidence(
                        query,
                        max_results=settings.RECOVERY_MAX_RESULTS_PER_ELEMENT,
                        freshness=freshness,
                        country=recovery_country,
                    )
                    if not results:
                        continue

                    for idx, r in enumerate(results):
                        url = (
                            getattr(r, "url", "")
                            if hasattr(r, "url")
                            else r.get("url", "")
                        )
                        if url in existing_urls:
                            continue

                        if is_domain_blocked(url, blocked_domains):
                            logger.info(
                                f"[URL LEDGER] element={elem['element_id']} "
                                f"dropped(recovery) "
                                f"reason='runtime_blocked_domain' "
                                f"url={url[:120]}"
                            )
                            continue

                        ev_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                        snippet_text = (
                            getattr(r, "snippet", "")
                            if hasattr(r, "snippet")
                            else r.get("snippet", "")
                        )
                        title = (
                            getattr(r, "title", "")
                            if hasattr(r, "title")
                            else r.get("title", "")
                        )
                        source = (
                            getattr(r, "source", "")
                            if hasattr(r, "source")
                            else r.get("source", "")
                        )
                        pub_date = (
                            getattr(r, "published_date", None)
                            if hasattr(r, "published_date")
                            else r.get("published_date")
                        )

                        all_evidence.append(
                            {
                                "id": f"recovery_{elem['element_id']}_{idx}",
                                "evidence_id": f"ev-rec-{elem['element_id']}_{idx}_{ev_hash}",
                                "element_ids": [],
                                "text": snippet_text,
                                "snippet": snippet_text,
                                "source": source,
                                "url": url,
                                "title": title,
                                "published_date": pub_date,
                                # No page fetched here — engine date, unconfirmed
                                "date_basis": derive_date_basis(url, pub_date),
                                "relevance_score": 0.0,
                                "semantic_similarity": 0.0,
                                "combined_score": 0.0,
                                "word_count": (
                                    len(snippet_text.split()) if snippet_text else 0
                                ),
                                "receipt_status": "extracted",
                                "metadata": {
                                    "coverage_recovery": True,
                                    "target_element": elem["element_id"],
                                },
                                "content_basis": (
                                    r.get("content_basis", "snippet")
                                    if isinstance(r, dict)
                                    else "snippet"
                                ),
                                "is_recovery": True,
                            }
                        )
                        existing_urls.add(url)

                except Exception as e:
                    logger.warning(
                        f"[COVERAGE RECOVERY] Search failed for element {elem['element_id']}: {e}"
                    )
                    continue

        # Enrich recovery evidence with full page content
        if all_evidence and settings.ENABLE_RECOVERY_ENRICHMENT:
            await self._enrich_recovery_evidence(all_evidence, claim_text)

        return all_evidence

    async def _enrich_recovery_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        claim_text: str,
        timeout_per_url: float = 8.0,
    ) -> None:
        """Fetch full page content for coverage recovery evidence items.

        Uses the existing EvidenceExtractor._extract_from_page() pipeline
        (trafilatura → readability → fallback) to replace thin search snippets
        with rich content excerpts.

        Modifies evidence_items in place. On failure, keeps original snippet.
        """
        semaphore = asyncio.Semaphore(self.evidence_extractor.max_concurrent)

        async def _enrich_single(ev: Dict[str, Any]) -> None:
            url = ev.get("url", "")
            if not url:
                ev.setdefault("metadata", {})["enriched"] = False
                return

            try:
                search_result = SearchResult(
                    title=ev.get("title", ""),
                    url=url,
                    snippet=ev.get("snippet", ""),
                    published_date=ev.get("published_date"),
                    source=ev.get("source", ""),
                )
                snippet = await asyncio.wait_for(
                    self.evidence_extractor._extract_from_page(
                        search_result, claim_text, semaphore
                    ),
                    timeout=timeout_per_url,
                )
                if (
                    snippet
                    and snippet.text
                    and len(snippet.text) > len(ev.get("text", ""))
                ):
                    ev["text"] = snippet.text
                    ev["snippet"] = snippet.text[:500]
                    ev["word_count"] = snippet.word_count
                    # F2: the fetch may have surfaced the page's own declared
                    # date — upgrade the engine guess (precedence rule)
                    if snippet.date_basis == "page_metadata":
                        ev["published_date"] = snippet.published_date
                        ev["date_basis"] = snippet.date_basis
                    ev.setdefault("metadata", {})["enriched"] = True
                    logger.debug(
                        f"[RECOVERY ENRICHMENT] {url}: {snippet.word_count} words"
                    )
                else:
                    ev.setdefault("metadata", {})["enriched"] = False
                    if snippet and snippet.text:
                        logger.debug(
                            f"[RECOVERY ENRICHMENT] Skipped {url}: extracted {len(snippet.text)} chars <= original {len(ev.get('text', ''))}"
                        )
                    else:
                        logger.debug(f"[RECOVERY ENRICHMENT] No content from {url}")
            except asyncio.TimeoutError:
                logger.debug(f"[RECOVERY ENRICHMENT] Timeout for {url}")
                ev.setdefault("metadata", {})["enriched"] = False
            except Exception as e:
                logger.debug(
                    f"[RECOVERY ENRICHMENT] Failed for {url}: {type(e).__name__}: {e}"
                )
                ev.setdefault("metadata", {})["enriched"] = False

        await asyncio.gather(
            *[_enrich_single(ev) for ev in evidence_items],
            return_exceptions=True,
        )

        enriched_count = sum(
            1 for ev in evidence_items if ev.get("metadata", {}).get("enriched")
        )
        logger.info(
            f"[RECOVERY ENRICHMENT] {enriched_count}/{len(evidence_items)} items enriched"
        )

    async def _retrieve_evidence_for_single_claim(
        self,
        claim: Dict[str, Any],
        semaphore: asyncio.Semaphore,
        excluded_domain: Optional[str] = None,
        url_fetch_semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Dict[str, Any]:
        """Retrieve evidence for a single claim.

        Returns:
            Dict with keys: filtered_evidence, raw_evidence, claim_position, claim_text
        """
        async with semaphore:
            try:
                claim_text = claim.get("text", "")
                claim_position = claim.get("position", 0)

                if not claim_text:
                    return []

                logger.debug(f"Processing claim {claim_position}")

                # FROZEN EVIDENCE REPLAY: Skip ALL network, construct evidence directly
                frozen_evidence_items = claim.get("frozen_evidence")
                if frozen_evidence_items is not None:
                    logger.info(
                        f"[FROZEN EVIDENCE REPLAY] Claim {claim_position}: "
                        f"replaying {len(frozen_evidence_items)} frozen evidence items (zero network)"
                    )

                    if not frozen_evidence_items:
                        return {
                            "filtered_evidence": [],
                            "raw_evidence": [],
                            "pre_weighting_evidence": [],
                            "claim_position": claim_position,
                            "claim_text": claim_text[:500] if claim_text else "",
                            "search_mode": "frozen_evidence_replay",
                        }

                    # Reconstruct ranked_evidence from frozen data (same shape as lines 763-777)
                    ranked_evidence = []
                    for idx, item in enumerate(frozen_evidence_items):
                        text = item.get("text", "")
                        ranked_evidence.append(
                            {
                                "id": f"evidence_{idx}",
                                "evidence_id": item.get(
                                    "evidence_id",
                                    f"ev-{hashlib.sha256((item.get('url', '') + item.get('text', '')).encode()).hexdigest()[:12]}",
                                ),
                                "element_ids": item.get("element_ids", []),
                                "text": text,
                                "source": item.get("source", ""),
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "published_date": item.get("published_date"),
                                "date_basis": item.get("date_basis"),
                                "relevance_score": float(
                                    item.get("relevance_score", 0.0)
                                ),
                                "semantic_similarity": 0.0,
                                "combined_score": 0.0,
                                "word_count": len(text.split()) if text else 0,
                                "external_source_provider": item.get(
                                    "external_source_provider"
                                ),
                                "is_factcheck": item.get("is_factcheck", False),
                                "source_type": item.get("source_type"),
                                "receipt_status": "shown",
                                "metadata": item.get("metadata", {}),
                                "content_basis": item.get("content_basis", "full"),
                            }
                        )

                    # Run through evidence filters — SAME path as normal pipeline
                    result = self._apply_evidence_filters(
                        ranked_evidence, claim, track_raw_evidence=True
                    )
                    final_evidence, raw_evidence = (
                        result if isinstance(result, tuple) else (result, [])
                    )

                    return {
                        "filtered_evidence": final_evidence[
                            : self.max_sources_per_claim
                        ],
                        "raw_evidence": raw_evidence,
                        "pre_weighting_evidence": ranked_evidence,
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                        "search_mode": "frozen_evidence_replay",
                    }

                # Step 1: Parallel retrieval from web search AND government APIs
                subject_context = claim.get("subject_context")
                key_entities = claim.get("key_entities", [])

                # Context logging moved to DEBUG to reduce noise
                if subject_context:
                    logger.debug(
                        f"Using context: '{subject_context}' with entities: {key_entities[:3]}"
                    )

                # Check for query plan (from Query Planning Agent)
                query_plan = claim.get("query_plan")

                # Run web search and API retrieval in parallel
                if query_plan and query_plan.get("queries"):
                    # Use Query Planning Agent's targeted queries
                    search_country = _resolve_search_country(claim)
                    web_search_task = self._execute_planned_queries(
                        claim_text,
                        query_plan,
                        excluded_domain=excluded_domain,
                        max_sources=self.max_sources_per_claim * 2,
                        url_fetch_semaphore=url_fetch_semaphore,
                        search_country=search_country,
                    )
                    queries_preview = query_plan["queries"][:2]  # Show first 2 queries
                    logger.info(
                        f"[RETRIEVE] QUERY PLAN | Claim {claim_position} | Type: {query_plan.get('claim_type')} | Queries: {queries_preview}"
                    )
                else:
                    # Fallback: Standard query formulation
                    search_country = _resolve_search_country(claim)
                    web_search_task = (
                        self.evidence_extractor.extract_evidence_for_claim(
                            claim_text,
                            max_sources=self.max_sources_per_claim
                            * 2,  # Get extra for filtering
                            subject_context=subject_context,
                            key_entities=key_entities,
                            excluded_domain=excluded_domain,
                            url_fetch_semaphore=url_fetch_semaphore,
                            search_country=search_country,
                        )
                    )

                # Phase 5: Government API retrieval (parallel with web search)
                api_results_task = self._retrieve_from_government_apis(
                    claim_text, claim
                )

                # Await both tasks concurrently with per-claim timeout
                # IMPORTANT: Use asyncio.wait instead of wait_for+gather to preserve partial results
                # If one task completes but the other times out, we keep the completed results
                # Env override exists for OFFLINE PROBES ONLY (e.g.
                # scripts/pool_balance_probe.py, where local cold-cache fetch
                # latency starves the web lane and Stage 3.8 recovery does not
                # run). Unset in prod → 45, behaviour unchanged.
                CLAIM_TIMEOUT = int(os.getenv("RETRIEVE_CLAIM_TIMEOUT_S", "45"))
                logger.info(
                    f"[SINGLE CLAIM DEBUG] Awaiting web search + API tasks for claim {claim_position} (timeout={CLAIM_TIMEOUT}s)"
                )

                # Wrap coroutines in named tasks so we can identify them after wait()
                web_task = asyncio.create_task(web_search_task, name="web_search")
                api_task = asyncio.create_task(api_results_task, name="api_retrieval")

                # Wait for tasks with timeout - returns (done, pending) sets
                done, pending = await asyncio.wait(
                    {web_task, api_task},
                    timeout=CLAIM_TIMEOUT,
                    return_when=asyncio.ALL_COMPLETED,
                )

                # Extract results from completed tasks, use defaults for timed-out ones
                web_evidence_snippets = []
                web_search_hits = 0
                api_evidence = {"evidence": [], "api_stats": {}}
                timed_out_tasks = []

                for task in done:
                    try:
                        result = task.result()
                        if task.get_name() == "web_search":
                            if isinstance(result, Exception):
                                logger.error(
                                    f"[CLAIM {claim_position}] Web search exception: {result}"
                                )
                            elif isinstance(result, tuple) and len(result) == 2:
                                web_evidence_snippets, web_search_hits = result
                            else:
                                web_evidence_snippets = (
                                    result if isinstance(result, list) else []
                                )
                                web_search_hits = len(web_evidence_snippets)
                        elif task.get_name() == "api_retrieval":
                            api_evidence = (
                                result
                                if not isinstance(result, Exception)
                                else {"evidence": [], "api_stats": {}}
                            )
                            if isinstance(result, Exception):
                                logger.error(
                                    f"[CLAIM {claim_position}] API retrieval exception: {result}"
                                )
                    except Exception as e:
                        logger.error(
                            f"[CLAIM {claim_position}] Error extracting task result: {e}"
                        )

                # Cancel any still-pending tasks and log what timed out
                for task in pending:
                    task.cancel()
                    timed_out_tasks.append(task.get_name())

                if timed_out_tasks:
                    logger.warning(
                        f"[CLAIM {claim_position}] Tasks timed out after {CLAIM_TIMEOUT}s: {timed_out_tasks}"
                    )
                    api_evidence["api_stats"]["timeout"] = True
                else:
                    logger.info(
                        f"[SINGLE CLAIM DEBUG] All tasks complete for claim {claim_position}"
                    )

                # M-02: Track web search provider status
                if "web_search" in timed_out_tasks:
                    web_search_status = {"status": "timeout", "count": 0}
                elif web_evidence_snippets:
                    web_search_status = {
                        "status": "ok",
                        "count": len(web_evidence_snippets),
                    }
                else:
                    web_search_status = {"status": "0_results", "count": 0}
                claim["web_search_status"] = web_search_status

                # Merge web search and API results
                evidence_snippets = web_evidence_snippets

                # Mine Wikipedia references for authority sources
                from app.pipeline.wikipedia_miner import mine_wikipedia_references

                wiki_ref_snippets = await mine_wikipedia_references(
                    evidence_snippets,
                    claim_text,
                    self.evidence_extractor,
                    semaphore,
                )
                if wiki_ref_snippets:
                    logger.info(
                        f"[WIKI MINING] Found {len(wiki_ref_snippets)} authority references from Wikipedia"
                    )
                    evidence_snippets = evidence_snippets + wiki_ref_snippets
                api_evidence_items = api_evidence.get("evidence", [])

                # Store API stats in claim for later tracking
                claim["api_stats"] = api_evidence.get("api_stats", {})

                # Log evidence counts (single consolidated log)
                web_count = (
                    len(web_evidence_snippets)
                    if isinstance(web_evidence_snippets, list)
                    else 0
                )
                api_count = len(api_evidence_items)
                logger.info(
                    f"[RETRIEVE] Claim {claim_position}: {web_count} web + {api_count} API sources"
                )

                if not evidence_snippets and not api_evidence_items:
                    logger.warning(f"[RETRIEVE] NO EVIDENCE for claim {claim_position}")
                    return {
                        "filtered_evidence": [],
                        "raw_evidence": [],
                        "claim_position": claim_position,
                        "claim_text": claim_text[:500] if claim_text else "",
                    }

                # Step 2: Merge and rank ALL evidence (web + API) using embeddings (bi-encoder)
                api_snippets = self._convert_api_evidence_to_snippets(
                    api_evidence_items
                )
                # A8b: diagnostic instrumentation, demoted from CRITICAL → INFO.
                logger.info(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(evidence_snippets)} web snippets + {len(api_snippets)} API snippets (from {len(api_evidence_items)} API items)"
                )
                all_evidence_snippets = evidence_snippets + api_snippets
                # Total search hits: web search results (pre-extraction) + API items queried
                search_results_count = web_search_hits + len(api_evidence_items)

                # Fix 0c: Cap combined evidence before expensive ranking
                MAX_EVIDENCE_FOR_RANKING = settings.MAX_EVIDENCE_FOR_RANKING
                if len(all_evidence_snippets) > MAX_EVIDENCE_FOR_RANKING:
                    logger.info(
                        f"[EVIDENCE CAP] Reducing {len(all_evidence_snippets)} items to {MAX_EVIDENCE_FOR_RANKING} before ranking"
                    )
                    # Round-robin: alternate web and API to ensure source diversity
                    web = evidence_snippets
                    api = api_snippets
                    interleaved = []
                    wi, ai = 0, 0
                    while len(interleaved) < MAX_EVIDENCE_FOR_RANKING and (
                        wi < len(web) or ai < len(api)
                    ):
                        if wi < len(web):
                            interleaved.append(web[wi])
                            wi += 1
                        if (
                            ai < len(api)
                            and len(interleaved) < MAX_EVIDENCE_FOR_RANKING
                        ):
                            interleaved.append(api[ai])
                            ai += 1
                    all_evidence_snippets = interleaved

                # Build evidence dicts (LLM scorer handles relevance downstream in Stage 3.7)
                ranked_evidence = []
                for idx, snippet in enumerate(all_evidence_snippets):
                    external_source = (
                        snippet.metadata.get("external_source_provider")
                        if snippet.metadata
                        else None
                    )
                    ev_hash = hashlib.sha256(
                        (snippet.url + snippet.text).encode()
                    ).hexdigest()[:12]
                    ranked_evidence.append(
                        {
                            "id": f"evidence_{idx}",
                            "evidence_id": f"ev-{ev_hash}",
                            "element_ids": (
                                snippet.metadata.get("element_ids", [])
                                if snippet.metadata
                                else []
                            ),
                            "text": snippet.text,
                            "source": snippet.source,
                            "url": snippet.url,
                            "title": snippet.title,
                            "published_date": snippet.published_date,
                            "date_basis": snippet.date_basis,
                            "relevance_score": float(snippet.relevance_score),
                            "semantic_similarity": 0.0,
                            "combined_score": 0.0,
                            "word_count": snippet.word_count,
                            "external_source_provider": external_source,
                            "receipt_status": "extracted",
                            "metadata": snippet.metadata,
                            "content_basis": snippet.content_basis,
                            "_full_text": getattr(snippet, "_full_text", None),
                        }
                    )

                # Step 3: Apply credibility and recency weighting (with raw evidence tracking)
                # A8b: diagnostic instrumentation, demoted from CRITICAL → INFO.
                logger.info(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(ranked_evidence)} items BEFORE evidence filtering"
                )
                pre_weighting_snapshot = copy.deepcopy(ranked_evidence)
                result = self._apply_evidence_filters(
                    ranked_evidence, claim, track_raw_evidence=True
                )
                final_evidence, raw_evidence = (
                    result if isinstance(result, tuple) else (result, [])
                )
                # A8b: diagnostic instrumentation, demoted from CRITICAL → INFO.
                logger.info(
                    f"[EVIDENCE TRACE] Claim {claim_position}: {len(final_evidence)} items AFTER evidence filtering"
                )

                for raw in raw_evidence:
                    url_short = (raw.get("url") or "")[:120]
                    provider = raw.get("external_source_provider")
                    source_type = "api" if provider else "web"
                    if raw.get("is_included"):
                        logger.info(
                            f"[URL LEDGER] claim={claim_position} kept "
                            f"type={source_type} provider={provider or '-'} "
                            f"url={url_short}"
                        )
                    else:
                        stage = raw.get("filter_stage") or "unknown"
                        reason = (raw.get("filter_reason") or "")[:80]
                        logger.info(
                            f"[URL LEDGER] claim={claim_position} dropped "
                            f"type={source_type} provider={provider or '-'} "
                            f"stage={stage} reason='{reason}' url={url_short}"
                        )

                # Repair provider-truncated headlines on the evidence that
                # actually survives to the screen. Runs here, after filtering,
                # so archive calls are never spent on items the user will not
                # see. Never fatal: on any failure the provider's title stands.
                shown_evidence = final_evidence[: self.max_sources_per_claim]
                if settings.ENABLE_TITLE_RECOVERY:
                    try:
                        await recover_truncated_titles(
                            shown_evidence,
                            limit=settings.TITLE_RECOVERY_MAX_PER_CLAIM,
                        )
                    except Exception as e:
                        logger.debug(f"[TITLE RECOVERY] skipped: {e}")

                # Return top evidence along with raw evidence metadata
                return {
                    "filtered_evidence": shown_evidence,
                    "raw_evidence": raw_evidence,
                    "pre_weighting_evidence": pre_weighting_snapshot,
                    "claim_position": claim_position,
                    "claim_text": claim_text[:500] if claim_text else "",
                    "search_results_count": search_results_count,
                }

            except Exception as e:
                logger.error(f"Single claim evidence retrieval error: {e}")
                return {
                    "filtered_evidence": [],
                    "raw_evidence": [],
                    "claim_position": claim.get("position", 0),
                    "claim_text": (
                        claim.get("text", "")[:500] if claim.get("text") else ""
                    ),
                }

    async def _execute_planned_queries(
        self,
        claim_text: str,
        query_plan: Dict[str, Any],
        excluded_domain: Optional[str] = None,
        max_sources: int = 20,
        url_fetch_semaphore: Optional[asyncio.Semaphore] = None,
        search_country: Optional[str] = "gb",
    ) -> List[EvidenceSnippet]:
        """
        Execute multiple targeted queries from Query Planning Agent.

        Args:
            claim_text: Original claim text
            query_plan: Query plan with targeted queries and source priorities
            excluded_domain: Domain to exclude from results
            max_sources: Maximum total sources to return

        Returns:
            List of deduplicated EvidenceSnippet from all queries

        Freshness is sourced from the query plan itself (per-query via
        ``query_freshness`` array, plan-level fallback via ``freshness``)
        rather than as a caller-supplied parameter. The Query Planning
        Agent owns freshness decisions; mechanical overrides happen via
        ``_inject_freshness_for_historical_dates`` upstream of plan
        consumption.
        """
        try:
            queries = query_plan.get("queries", [])
            claim_type = query_plan.get("claim_type", "general")

            # ============================================================
            # DYNAMIC FRESHNESS: Per-query freshness from query plan
            # ============================================================
            # Each query carries its own freshness from the element it targets.
            # The plan-level freshness is a fallback for backward compatibility.
            query_freshness_list = query_plan.get("query_freshness", [])
            default_freshness = query_plan.get("freshness", "py")
            plan_reasoning = query_plan.get("reasoning", "default")

            logger.info(
                f"[FRESHNESS] Per-query freshness: {query_freshness_list[:4]}... (default: {default_freshness}, reasoning: {plan_reasoning[:50]})"
            )

            if not queries:
                logger.warning(f"No queries in plan for claim: {claim_text[:50]}...")
                return []

            logger.debug(f"Executing {len(queries)} planned queries")

            # Execute all queries concurrently
            query_tasks = []
            plan_element_ids = query_plan.get("query_element_ids", [])
            element_wired = bool(query_plan.get("element_wired"))

            # Results requested per query.
            #
            # Unwired (and every pre-Phase-2 caller, e.g. re-search): one
            # uniform share of the budget, exactly as before.
            #
            # Wired: the claim lane keeps the depth it would have had on its
            # own — the factual path's route is not thinned by the arrival of
            # element lanes — and each element-lane query asks for a smaller,
            # fixed slice. Asking for more results costs nothing extra;
            # providers bill per call and cap `num` at 20. The scarce budget
            # is the FETCH cap below, not the search results.
            sources_per_query = max(
                3, max_sources // len(queries)
            )  # Distribute sources across queries
            per_query_sources = [sources_per_query] * len(queries)
            if element_wired:
                claim_lane_positions = [
                    i
                    for i in range(len(queries))
                    if i < len(plan_element_ids)
                    and plan_element_ids[i] == CLAIM_LANE_ELEMENT_ID
                ]
                if claim_lane_positions:
                    claim_lane_depth = max(
                        3,
                        min(
                            CLAIM_LANE_MAX_RESULTS_PER_QUERY,
                            max_sources // len(claim_lane_positions),
                        ),
                    )
                    per_query_sources = [
                        (
                            claim_lane_depth
                            if i in set(claim_lane_positions)
                            else ELEMENT_RESULTS_PER_QUERY
                        )
                        for i in range(len(queries))
                    ]

            for i, query in enumerate(queries):
                # Per-query freshness: use the freshness for this specific query's element
                this_freshness = (
                    query_freshness_list[i]
                    if i < len(query_freshness_list)
                    else default_freshness
                )
                task = self.evidence_extractor.search_service.search_for_evidence(
                    query,
                    max_results=per_query_sources[i],
                    freshness=this_freshness,
                    country=search_country,
                )
                query_tasks.append(task)

            # Gather all search results
            all_results = await asyncio.gather(*query_tasks, return_exceptions=True)

            # Merge and deduplicate search results by URL
            # Track element associations so cross-element URL dedup preserves all element_ids
            query_element_ids = query_plan.get("query_element_ids", [])
            seen_urls = {}  # URL -> search result reference
            unique_search_results = []

            for i, results in enumerate(all_results):
                if isinstance(results, Exception):
                    logger.warning(f"Query {i+1} failed: {results}")
                    continue

                element_id = (
                    query_element_ids[i] if i < len(query_element_ids) else None
                )

                for result in results:
                    # Skip excluded domain
                    if (
                        excluded_domain
                        and extract_domain(result.url) == excluded_domain
                    ):
                        continue

                    # Deduplicate by URL, but accumulate element associations
                    if result.url in seen_urls:
                        if element_id:
                            seen_urls[result.url]._element_ids.add(element_id)
                        continue

                    # Attach query metadata to result for later preservation
                    result._query_index = i
                    result._query_used = queries[i]
                    result._claim_type = claim_type
                    result._freshness = default_freshness  # For staleness check
                    result._element_ids = {element_id} if element_id else set()
                    seen_urls[result.url] = result
                    unique_search_results.append(result)

            # BALANCED FRESHNESS FALLBACK when 0 results
            if not unique_search_results:
                fallback_progression = ["pw", "pm", "py"]
                current_idx = (
                    fallback_progression.index(default_freshness)
                    if default_freshness in fallback_progression
                    else -1
                )

                # FALLBACK: Progressively relax freshness (pw->pm->py, never 2y)
                if (
                    not unique_search_results
                    and current_idx >= 0
                    and current_idx < len(fallback_progression) - 1
                ):
                    for fallback_freshness in fallback_progression[current_idx + 1 :]:
                        logger.info(
                            f"[FRESHNESS FALLBACK] Relaxing: {default_freshness} -> {fallback_freshness}"
                        )
                        for fb_i, query in enumerate(queries):
                            try:
                                results = await self.evidence_extractor.search_service.search_for_evidence(
                                    query,
                                    # Per-lane depth, not the uniform
                                    # pre-Phase-2 share: relaxing freshness
                                    # must not quietly flatten the claim lane
                                    # back to an element lane's slice.
                                    max_results=per_query_sources[fb_i],
                                    freshness=fallback_freshness,
                                    country=search_country,
                                )
                                # Same lane bookkeeping as the main loop above.
                                # This branch was DEAD 2026-02-12 → 2026-08-17:
                                # PR-B03 converted `seen_urls` from set to dict
                                # and missed this `.add()`, so the first result
                                # of every fallback query raised AttributeError
                                # into the except below and the path could
                                # never return an item. Its test asserted only
                                # the max_results argument against an empty
                                # stub, so it stayed green throughout.
                                fb_element_id = (
                                    query_element_ids[fb_i]
                                    if fb_i < len(query_element_ids)
                                    else None
                                )
                                for result in results:
                                    if (
                                        excluded_domain
                                        and extract_domain(result.url)
                                        == excluded_domain
                                    ):
                                        continue
                                    if result.url in seen_urls:
                                        if fb_element_id:
                                            seen_urls[result.url]._element_ids.add(
                                                fb_element_id
                                            )
                                        continue
                                    result._query_index = fb_i
                                    result._query_used = query
                                    result._claim_type = claim_type
                                    result._freshness = (
                                        fallback_freshness  # Use fallback freshness
                                    )
                                    result._freshness_fallback = fallback_freshness
                                    result._element_ids = (
                                        {fb_element_id} if fb_element_id else set()
                                    )
                                    seen_urls[result.url] = result
                                    unique_search_results.append(result)
                            except Exception as e:
                                logger.warning(f"Fallback query failed: {e}")
                        if unique_search_results:
                            logger.info(
                                f"[FRESHNESS FALLBACK] Found {len(unique_search_results)} with {fallback_freshness}"
                            )
                            break

                if not unique_search_results:
                    logger.warning(
                        f"[FRESHNESS FALLBACK] No results after all attempts"
                    )
                    return []

            # ============================================================
            # CRITICAL FIX: Extract actual page content (like standard path)
            # ============================================================
            # Use shared pool if provided (work-stealing across claims),
            # otherwise fall back to per-claim pool for standalone use.
            fetch_sem = url_fetch_semaphore or asyncio.Semaphore(
                self.evidence_extractor.max_concurrent
            )

            # Phase 2: allocate the fetch budget across lanes, not down the
            # list. unique_search_results is in query order, so a plain
            # [:max_sources] slice funds the first queries and starves the
            # last — with one lane that never bit, with a dozen it drops whole
            # elements before a single URL is fetched. Weighted round-robin
            # (claim lane 2 : element lane 1) gives every lane a share, in the
            # spirit of invariant #2. Unwired plans keep the original slice.
            fetch_candidates = unique_search_results
            if element_wired:
                fetch_candidates = _allocate_fetch_budget(
                    unique_search_results, plan_element_ids
                )
            fetch_set = fetch_candidates[:max_sources]

            budget_dropped = len(unique_search_results) - len(fetch_set)
            if budget_dropped > 0:
                logger.info(
                    f"[RETRIEVE] Fetch budget | candidates="
                    f"{len(unique_search_results)} fetched={len(fetch_set)} "
                    f"dropped_by_budget={budget_dropped} "
                    f"per_lane={_lane_histogram(fetch_set, plan_element_ids)}"
                )
            else:
                logger.info(
                    f"[RETRIEVE] Fetch budget | candidates="
                    f"{len(unique_search_results)} fetched={len(fetch_set)} "
                    f"per_lane={_lane_histogram(fetch_set, plan_element_ids)}"
                )

            extraction_tasks = [
                self._extract_with_fallback(result, claim_text, fetch_sem)
                for result in fetch_set
            ]

            extracted_results = await asyncio.gather(
                *extraction_tasks, return_exceptions=True
            )

            # Filter successful extractions and track fallback stats
            evidence_snippets = []
            fallback_count = 0
            dropped_count = 0

            for result in extracted_results:
                if isinstance(result, Exception):
                    logger.warning(f"Content extraction exception: {result}")
                    dropped_count += 1
                    continue
                if result is None:
                    dropped_count += 1
                    continue
                if result.metadata and result.metadata.get("is_snippet_fallback"):
                    fallback_count += 1
                evidence_snippets.append(result)

            # Log extraction stats
            total = len(fetch_set)
            total_found = len(unique_search_results)
            success_count = len(evidence_snippets) - fallback_count
            logger.info(
                f"[RETRIEVE] Query Planning extraction: "
                f"{success_count}/{total} content, {fallback_count} fallback, {dropped_count} dropped | "
                f"claim_type={claim_type} | total_search_hits={total_found}"
            )

            return evidence_snippets, total_found

        except Exception as e:
            logger.error(f"Planned query execution failed: {e}")
            # Fallback to standard search with claim text
            fallback = await self.evidence_extractor.extract_evidence_for_claim(
                claim_text, max_sources=max_sources
            )
            return fallback, len(fallback) if isinstance(fallback, list) else 0

    async def _extract_with_fallback(
        self, search_result, claim_text: str, semaphore: asyncio.Semaphore
    ) -> Optional[EvidenceSnippet]:
        """
        Extract content from a search result with nuanced fallback policy.

        Fallback Policy:
        - 403/429 blocked: Keep snippet if ALLOW_SNIPPET_FALLBACK=True, mark as fallback
        - Timeout: Keep snippet if ALLOW_SNIPPET_FALLBACK=True, mark as fallback
        - Empty/JS-only: Drop entirely (return None)
        - Success: Return extracted content

        Args:
            search_result: SearchResult with attached query metadata
            claim_text: Claim text for relevance matching
            semaphore: Concurrency limiter

        Returns:
            EvidenceSnippet with extracted content, or None if dropped
        """
        # Preserve query planning metadata
        query_index = getattr(search_result, "_query_index", None)
        query_used = getattr(search_result, "_query_used", None)
        claim_type = getattr(search_result, "_claim_type", "general")
        freshness = getattr(search_result, "_freshness", "py")  # For staleness check
        element_ids = list(getattr(search_result, "_element_ids", set()))

        try:
            # Attempt full content extraction
            snippet = await self.evidence_extractor._extract_from_page(
                search_result, claim_text, semaphore
            )

            if snippet is not None:
                # Success: Enrich with query planning metadata
                snippet.metadata = snippet.metadata or {}
                snippet.metadata["query_index"] = query_index
                snippet.metadata["query_used"] = query_used
                snippet.metadata["claim_type"] = claim_type
                snippet.metadata["source_path"] = "query_planning"
                snippet.metadata["extraction_status"] = "success"
                snippet.metadata["is_snippet_fallback"] = False
                snippet.metadata["element_ids"] = element_ids

                # Add staleness check for time-sensitive claims (using dynamic freshness)
                from app.utils.query_planner import check_evidence_staleness

                staleness = check_evidence_staleness(
                    evidence_date=snippet.published_date,
                    freshness=freshness,  # Use LLM-decided freshness from query plan
                )
                snippet.metadata["staleness_check"] = staleness
                if staleness["is_stale"]:
                    logger.warning(
                        f"[STALE EVIDENCE] {staleness['message']} - URL: {snippet.url}"
                    )

                return snippet

            # Content extraction returned None
            # This means HTML was fetched but yielded no substantive content (JS-only/empty)
            # Policy: Drop entirely - don't pollute with low-signal meta descriptions
            logger.debug(f"Dropping empty extraction for {search_result.url}")
            return None

        except Exception as e:
            # Extraction failed - check if we should use snippet fallback
            error_str = str(e).lower()
            is_blocked = (
                "403" in error_str or "429" in error_str or "forbidden" in error_str
            )
            is_timeout = "timeout" in error_str

            if (is_blocked or is_timeout) and settings.ALLOW_SNIPPET_FALLBACK:
                # Transient failure: Use snippet as fallback with lower score
                extraction_status = (
                    "fallback_blocked" if is_blocked else "fallback_timeout"
                )
                logger.debug(
                    f"Using snippet fallback ({extraction_status}) for {search_result.url}"
                )

                return EvidenceSnippet(
                    text=search_result.snippet or "",
                    source=extract_domain(search_result.url),
                    url=search_result.url,
                    title=search_result.title or "",
                    published_date=search_result.published_date,
                    relevance_score=0.0,  # No hardcoded score, status tracked via metadata
                    metadata={
                        "query_index": query_index,
                        "query_used": query_used,
                        "claim_type": claim_type,
                        "source_path": "query_planning",
                        "extraction_status": extraction_status,
                        "is_snippet_fallback": True,
                        "fallback_reason": str(e)[:100],
                        "element_ids": element_ids,
                    },
                    # Page fetch failed — engine date, unconfirmed
                    date_basis=derive_date_basis(
                        search_result.url, search_result.published_date
                    ),
                )
            else:
                # Other failure or fallback disabled: Drop
                logger.debug(f"Dropping failed extraction for {search_result.url}: {e}")
                return None

    def _apply_evidence_filters(
        self,
        evidence_list: List[Dict[str, Any]],
        claim: Dict[str, Any] = None,
        track_raw_evidence: bool = False,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]] | List[Dict[str, Any]]:
        """Apply minimal filtering to evidence.

        Two stages:
        1. Satire exclusion — remove known satire domains
        2. Content dedup — remove identical/syndicated content
        Plus corroboration boost (annotation, not a filter).

        Args:
            evidence_list: List of evidence items
            claim: Claim dict for context-aware filtering
            track_raw_evidence: If True, returns tuple (filtered, raw_evidence_metadata)

        Returns:
            If track_raw_evidence=False: List of filtered evidence
            If track_raw_evidence=True: Tuple of (filtered_evidence, raw_evidence_metadata)
        """
        try:
            original_evidence_count = len(evidence_list)

            # --- RAW EVIDENCE TRACKING: snapshot before any filtering ---
            raw_evidence_tracking = []
            if track_raw_evidence:
                for ev in evidence_list:
                    raw_evidence_tracking.append(
                        {
                            "source": ev.get("source", ""),
                            "url": ev.get("url", ""),
                            "title": ev.get("title", ""),
                            "snippet": ev.get("snippet", ""),
                            "published_date": ev.get("published_date"),
                            "is_included": True,
                            "filter_stage": None,
                            "filter_reason": None,
                            "tier": ev.get("tier"),
                            "is_factcheck": ev.get("is_factcheck", False),
                            "external_source_provider": ev.get(
                                "external_source_provider"
                            ),
                            "relevance_score": ev.get("combined_score", 0.0),
                        }
                    )
            url_to_raw = (
                {item["url"]: item for item in raw_evidence_tracking}
                if track_raw_evidence
                else {}
            )

            # --- STAGE 1: Satire exclusion ---
            before_satire = len(evidence_list)
            satire_excluded = []
            kept = []
            for ev in evidence_list:
                domain = extract_domain(ev.get("url", ""), fallback="")
                if domain in SATIRE_DOMAINS:
                    satire_excluded.append(ev)
                else:
                    kept.append(ev)
            evidence_list = kept
            if track_raw_evidence:
                for e in satire_excluded:
                    url = e.get("url", "")
                    if url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "satire"
                        url_to_raw[url]["filter_reason"] = "Excluded: satire source"
            logger.info(
                f"[FILTER] Satire exclusion: {before_satire} -> {len(evidence_list)}"
            )

            # --- STAGE 2: Content dedup ---
            before_dedup = len(evidence_list)
            from app.utils.deduplication import EvidenceDeduplicator

            deduplicator = EvidenceDeduplicator()
            before_dedup_list = list(evidence_list) if track_raw_evidence else []
            evidence_list, dedup_stats = deduplicator.deduplicate(evidence_list)
            if track_raw_evidence:
                after_urls = {e.get("url") for e in evidence_list}
                for e in before_dedup_list:
                    url = e.get("url", "")
                    if url not in after_urls and url in url_to_raw:
                        url_to_raw[url]["is_included"] = False
                        url_to_raw[url]["filter_stage"] = "dedup"
                        url_to_raw[url]["filter_reason"] = "Duplicate content"
            logger.info(f"[FILTER] Dedup: {before_dedup} -> {len(evidence_list)}")

            # --- Corroboration boost (annotation only) ---
            if len(evidence_list) >= 2:
                from app.utils.corroboration import apply_corroboration_boost

                evidence_list, corroboration_stats = apply_corroboration_boost(
                    evidence_list
                )
                if corroboration_stats.get("items_annotated", 0) > 0:
                    logger.info(
                        f"[FILTER] Corroboration: {corroboration_stats['items_annotated']} items annotated "
                        f"({corroboration_stats['corroboration_pairs']} pairs, "
                        f"{corroboration_stats.get('groups', 0)} groups)"
                    )

            # Sort by combined_score
            evidence_list.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

            # Safety check
            if len(evidence_list) == 0 and original_evidence_count > 0:
                logger.warning(
                    f"All {original_evidence_count} evidence items eliminated by filters"
                )

            if track_raw_evidence:
                return evidence_list, raw_evidence_tracking
            return evidence_list

        except Exception as e:
            logger.error(f"Evidence filtering error: {e}")
            if track_raw_evidence:
                return evidence_list, []
            return evidence_list

    async def _retrieve_from_government_apis(
        self, claim_text: str, claim: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve evidence from government APIs based on claim domain/jurisdiction.

        Phase 5: Government API Integration

        Args:
            claim_text: The claim text to search for
            claim: Full claim dictionary (may include domain info)

        Returns:
            Dictionary with:
                - evidence: List of evidence items
                - api_stats: API usage statistics
        """
        from app.core.config import settings

        # Check feature flag
        api_flag = getattr(settings, "ENABLE_API_RETRIEVAL", False)
        logger.info(
            f"[API DEBUG] ENABLE_API_RETRIEVAL={api_flag}, self.enable_api_retrieval={self.enable_api_retrieval}"
        )
        logger.info(
            f"[API DEBUG] Registry adapter count: {len(self.api_registry.adapters)}"
        )

        if not api_flag or not self.enable_api_retrieval:
            logger.warning("[API DEBUG] API retrieval DISABLED by feature flag")
            return {"evidence": [], "api_stats": {}}

        # Safety check: if registry is empty, adapters weren't initialized
        if len(self.api_registry.adapters) == 0:
            logger.error(
                "[API DEBUG] CRITICAL: Registry has 0 adapters! Initializing now..."
            )
            from app.services.api_adapters import initialize_adapters

            initialize_adapters()
            logger.info(
                f"[API DEBUG] After emergency init: {len(self.api_registry.adapters)} adapters"
            )

        keyword_routed_names = set()
        try:
            # PRIORITY 1: Check if claim was classified as legal during extraction
            # If legal, use legal_metadata for targeted routing to statute APIs
            claim_type = claim.get("claim_type")
            legal_metadata = claim.get("legal_metadata", {})

            # NF-15: extract LLM emits typed entities {text, type}; map type
            # to label for the existing adapter contract. The legacy heuristic
            # _label_entities_for_api is gone — types are LLM-typed at extract.
            key_entities = claim.get("key_entities") or []
            entities = [
                {"text": e["text"], "label": e["type"]}
                for e in key_entities
                if isinstance(e, dict) and e.get("text") and e.get("type")
            ]

            # NF-09: ensure secondary_domains is always defined so the cap
            # logic (and the secondary-merge block) can rely on it in both
            # the legal-override and article-classification branches.
            secondary_domains: List[str] = []

            if claim_type == "legal" and legal_metadata:
                # Use legal classification for routing (override domain/jurisdiction)
                domain = "Law"
                jurisdiction = legal_metadata.get("jurisdiction", "US")
                confidence = claim.get("classification", {}).get("confidence", 0.9)

            else:
                # PRIORITY 2: Use article-level classification (once per check, not per claim)
                # This is set during extraction and attached to all claims
                article_classification = claim.get("article_classification", {})

                if article_classification:
                    # Use article-level classification
                    domain = article_classification.get("primary_domain", "General")
                    jurisdiction = article_classification.get("jurisdiction", "Global")
                    # Coerce None → 0.0: the key may be present with a None value
                    # (degraded classification), so the .get default never applies.
                    confidence = article_classification.get("confidence") or 0.0
                    secondary_domains = article_classification.get(
                        "secondary_domains", []
                    )

                    # Warn if classification failed (using fallback "General")
                    if article_classification.get("classification_failed"):
                        logger.warning(
                            f"[API ROUTING] Classification failed - using General domain, "
                            f"API evidence may be less targeted"
                        )

                    logger.debug(
                        f"[API ROUTING] Using article classification: "
                        f"domain={domain}, jurisdiction={jurisdiction}, "
                        f"confidence={confidence:.2f}, source={article_classification.get('source', 'unknown')}"
                    )
                else:
                    # Fallback: No article classification available
                    # This happens when ENABLE_ARTICLE_CLASSIFICATION is disabled
                    # or classification failed during extraction
                    domain = "General"
                    jurisdiction = "Global"
                    confidence = 0.0
                    secondary_domains = []
                    logger.warning(
                        "[API ROUTING] No article classification, defaulting to General"
                    )

            # Get relevant API adapters for primary domain
            relevant_adapters = self.api_registry.get_adapters_for_domain(
                domain, jurisdiction
            )

            # Also query secondary domain adapters (for cross-domain articles)
            if secondary_domains:
                for sec_domain in secondary_domains:
                    sec_adapters = self.api_registry.get_adapters_for_domain(
                        sec_domain, jurisdiction
                    )
                    # Add unique adapters (avoid duplicates)
                    for adapter in sec_adapters:
                        if adapter not in relevant_adapters:
                            relevant_adapters.append(adapter)
                            logger.debug(
                                f"[API ROUTING] Added secondary domain adapter: {adapter.api_name} ({sec_domain})"
                            )

            # Claim-level keyword routing: add adapters based on claim text keywords
            # This catches cross-domain claims (e.g., oil prices in Politics articles)
            from app.utils.claim_keyword_router import get_keyword_router

            keyword_router = get_keyword_router()
            keyword_adapters = keyword_router.get_additional_adapters(
                claim_text,
                relevant_adapters,
                self.api_registry,
                domain=domain,
                jurisdiction=jurisdiction,
            )
            keyword_routed_names = set()
            for adapter in keyword_adapters:
                relevant_adapters.append(adapter)
                keyword_routed_names.add(adapter.api_name)
                logger.info(
                    f"[KEYWORD ROUTING] Added {adapter.api_name} for claim: {claim_text[:50]}..."
                )

            # M-05: Jurisdiction filter — remove adapters that don't belong.
            # Keyword-routed adapters are now pre-filtered for jurisdiction
            # in the router itself, so they no longer need a bypass here.
            allowed_names = get_adapters_for_jurisdiction(jurisdiction)
            if allowed_names is not None:
                pre_filter = len(relevant_adapters)
                relevant_adapters = [
                    a for a in relevant_adapters if a.api_name in allowed_names
                ]
                if pre_filter != len(relevant_adapters):
                    logger.info(
                        f"[JURISDICTION] {jurisdiction}: {pre_filter} -> {len(relevant_adapters)} adapters"
                    )

            # PQ-06 + B1 + NF-09: Tier-aware, domain-aware adapter cap.
            # Specialists first, generalists fill gaps. Cap varies by article
            # domain so Health/Science claims don't silently lose OpenAlex/S2.
            # NF-09 widens the cap when secondary_domains are present so
            # cross-domain claims (e.g. Climate+Law for "Climate Change Act
            # 2008") keep their cross-specialists.
            max_adapters = get_effective_adapter_cap(domain, secondary_domains)
            if len(relevant_adapters) > max_adapters:
                allowed = allowed_names or []

                def _sort_key(adapter):
                    tier = getattr(adapter, "priority_tier", 1)
                    try:
                        pref = allowed.index(adapter.api_name)
                    except ValueError:
                        pref = len(allowed) + 1
                    return (tier, pref, adapter.api_name)

                relevant_adapters.sort(key=_sort_key)
                logger.info(
                    f"[TIER CAP] domain={domain} cap={max_adapters} | "
                    f"{len(relevant_adapters)} adapters → {max_adapters}: "
                    f"selected {[a.api_name for a in relevant_adapters[:max_adapters]]}, "
                    f"cap victims {[a.api_name for a in relevant_adapters[max_adapters:]]}"
                )
                relevant_adapters = relevant_adapters[:max_adapters]

            # Log final adapter list
            adapter_names = [a.api_name for a in relevant_adapters]
            logger.info(f"[API DEBUG] Final adapters to query: {adapter_names}")

            if not relevant_adapters:
                logger.warning(
                    f"[API] No adapters found for domain={domain}, jurisdiction={jurisdiction}"
                )
                return {"evidence": [], "api_stats": {}}

            # Query all relevant APIs concurrently with timing
            import time as _time

            async def _timed_adapter_call(
                adapter, claim_text, domain, jurisdiction, entities
            ):
                """Wrap adapter call with latency measurement."""
                t0 = _time.monotonic()
                result = await asyncio.to_thread(
                    adapter.search_with_cache,
                    claim_text,
                    domain,
                    jurisdiction,
                    entities,
                )
                latency_ms = round((_time.monotonic() - t0) * 1000)
                return result, latency_ms

            from app.services.government_api_client import GovernmentAPIClient

            api_tasks = []
            for adapter in relevant_adapters:
                # Keyword-routed adapters bypass domain guard — the keyword
                # router already decided this adapter is relevant for the claim.
                adapter_domain = (
                    GovernmentAPIClient.KEYWORD_ROUTED
                    if adapter.api_name in keyword_routed_names
                    else domain
                )
                task = _timed_adapter_call(
                    adapter, claim_text, adapter_domain, jurisdiction, entities
                )
                api_tasks.append((adapter.api_name, task))

            # Gather all API results
            api_results = await asyncio.gather(
                *[task for _, task in api_tasks], return_exceptions=True
            )

            # Collect evidence and statistics
            all_api_evidence = []
            api_stats = {
                "apis_queried": [],
                "total_api_calls": 0,
                "total_api_results": 0,
            }

            for i, (api_name, _) in enumerate(api_tasks):
                result = api_results[i]

                if isinstance(result, Exception):
                    logger.error(f"{api_name} API call failed: {result}")
                    api_stats["apis_queried"].append(
                        {"name": api_name, "results": 0, "error": str(result)}
                    )
                    continue

                evidence_items, latency_ms = result

                if evidence_items:
                    all_api_evidence.extend(evidence_items)
                    api_stats["apis_queried"].append(
                        {
                            "name": api_name,
                            "results": len(evidence_items),
                            "latency_ms": latency_ms,
                        }
                    )
                    api_stats["total_api_results"] += len(evidence_items)
                else:
                    api_stats["apis_queried"].append(
                        {"name": api_name, "results": 0, "latency_ms": latency_ms}
                    )

            api_stats["total_api_calls"] = len(api_tasks)

            # Log API results summary
            logger.info(
                f"[API DEBUG] Results: {api_stats['total_api_calls']} APIs queried, {api_stats['total_api_results']} total results"
            )
            for api_stat in api_stats["apis_queried"]:
                logger.info(
                    f"[API DEBUG]   - {api_stat['name']}: {api_stat.get('results', 0)} results"
                    + (
                        f" (ERROR: {api_stat.get('error', '')})"
                        if api_stat.get("error")
                        else ""
                    )
                )

            # Fix 0b: Cap total API evidence per claim
            MAX_API_EVIDENCE_PER_CLAIM = 12
            if len(all_api_evidence) > MAX_API_EVIDENCE_PER_CLAIM:
                logger.info(
                    f"[API CAP] Reducing {len(all_api_evidence)} API items to {MAX_API_EVIDENCE_PER_CLAIM}"
                )
                # Round-robin across API providers for source diversity
                from collections import defaultdict

                by_provider = defaultdict(list)
                for item in all_api_evidence:
                    by_provider[item.get("external_source_provider", "unknown")].append(
                        item
                    )
                providers = list(by_provider.values())
                interleaved = []
                idx = 0
                while len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM:
                    added = False
                    for group in providers:
                        if (
                            idx < len(group)
                            and len(interleaved) < MAX_API_EVIDENCE_PER_CLAIM
                        ):
                            interleaved.append(group[idx])
                            added = True
                    if not added:
                        break
                    idx += 1
                all_api_evidence = interleaved

            # A8b: diagnostic instrumentation, demoted from CRITICAL → INFO.
            logger.info(
                f"[API RETRIEVAL] Returning {len(all_api_evidence)} evidence items from {api_stats['total_api_calls']} API calls"
            )
            if all_api_evidence:
                logger.info(
                    f"[API RETRIEVAL] First item: {all_api_evidence[0].get('source', 'N/A')} - {all_api_evidence[0].get('title', 'N/A')[:50]}"
                )

            return {"evidence": all_api_evidence, "api_stats": api_stats}

        except Exception as e:
            logger.error(f"Government API retrieval error: {e}", exc_info=True)
            return {"evidence": [], "api_stats": {}}

    def _convert_api_evidence_to_snippets(
        self, api_evidence: List[Dict[str, Any]]
    ) -> List[EvidenceSnippet]:
        """
        Convert API evidence dictionaries to EvidenceSnippet objects.

        Args:
            api_evidence: List of evidence dictionaries from APIs

        Returns:
            List of EvidenceSnippet objects
        """
        snippets = []
        conversion_failures = 0

        for i, evidence in enumerate(api_evidence):
            try:
                text = evidence.get("snippet", "")
                if not text:
                    logger.warning(
                        f"[API CONVERT] Item {i}: Empty snippet, source={evidence.get('source', 'N/A')}"
                    )
                    conversion_failures += 1
                    continue

                snippet = EvidenceSnippet(
                    text=text,
                    source=evidence.get("source", "Unknown API"),
                    url=evidence.get("url", ""),
                    title=evidence.get("title", ""),
                    published_date=evidence.get("source_date"),
                    relevance_score=0.0,  # No hardcoded score, LLM scorer decides
                    # word_count is calculated automatically in EvidenceSnippet.__init__
                    metadata={
                        **evidence.get("metadata", {}),
                        "external_source_provider": evidence.get(
                            "external_source_provider"
                        ),
                    },
                    content_basis="api",
                    # F2: adapter source_date is authoritative for that source
                    date_basis=(
                        DATE_BASIS_API if evidence.get("source_date") else None
                    ),
                )
                snippets.append(snippet)
            except Exception as e:
                logger.warning(f"[API CONVERT] Item {i}: Failed to convert - {e}")
                conversion_failures += 1
                continue

        if conversion_failures > 0:
            logger.warning(
                f"[API CONVERT] {conversion_failures}/{len(api_evidence)} items failed conversion"
            )

        return snippets
