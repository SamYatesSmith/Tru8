"""
Corroboration Detection

Detects when multiple independent sources report similar information.
Annotates evidence with corroboration metadata (group IDs, corroborating
evidence IDs) for use by the Cartographer convergence zones.

No score mutation. No editorial judgment. Pure structural detection.

Philosophy (locked 2026-02-16): Classify, don't score.
"""

import logging
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)

# Minimum text similarity to consider evidence as corroborating
MIN_CORROBORATION_SIMILARITY = 0.35

# Minimum fact overlap ratio for corroboration
MIN_FACT_OVERLAP = 0.3


def _get_ownership_group(source: str, url: str) -> str:
    """
    Get ownership group for a source to determine independence.

    Sources in the same ownership group are not considered independent
    for corroboration purposes.
    """
    # Known media ownership groups (simplified - could be expanded)
    ownership_groups = {
        # News Corp
        "wsj.com": "newscorp",
        "nypost.com": "newscorp",
        "thesun.co.uk": "newscorp",
        "thetimes.co.uk": "newscorp",
        "news.com.au": "newscorp",
        # BBC Group
        "bbc.com": "bbc",
        "bbc.co.uk": "bbc",
        # Guardian Media Group
        "theguardian.com": "guardian",
        "guardian.co.uk": "guardian",
        # Reuters/Thomson
        "reuters.com": "thomson_reuters",
        # AP
        "apnews.com": "ap",
        "ap.org": "ap",
        # Wire services (each independent)
        "afp.com": "afp",
        "ritzau.dk": "ritzau",
        # Government (each independent by country)
        ".gov": "us_gov",
        ".gov.uk": "uk_gov",
        # Academic (each institution independent)
        ".edu": f"edu_{source}",
        ".ac.uk": f"ac_uk_{source}",
    }

    source_lower = source.lower()
    url_lower = url.lower()

    for pattern, group in ownership_groups.items():
        if pattern in source_lower or pattern in url_lower:
            return group

    # Default: each domain is its own group (independent)
    return source_lower


def _text_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity between two evidence snippets.

    Uses SequenceMatcher for reasonable speed/accuracy tradeoff.
    """
    if not text1 or not text2:
        return 0.0

    # Normalize texts
    t1 = text1.lower()[:500]  # Limit to first 500 chars for speed
    t2 = text2.lower()[:500]

    return SequenceMatcher(None, t1, t2).ratio()


def _extract_key_facts(text: str) -> Set[str]:
    """
    Extract key facts/numbers from text for matching.

    Looks for numbers, percentages, dates, and quoted phrases.
    """
    import re

    facts = set()

    # Extract numbers (including decimals and percentages)
    numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", text)
    facts.update(numbers)

    # Extract quoted phrases
    quotes = re.findall(r'"([^"]{10,50})"', text)
    facts.update(q.lower() for q in quotes)

    # Extract dates (various formats)
    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4})\b",
        text,
        re.IGNORECASE,
    )
    facts.update(d.lower() for d in dates)

    return facts


def _check_fact_overlap(facts1: Set[str], facts2: Set[str]) -> float:
    """Calculate overlap between two sets of facts. Returns 0.0-1.0."""
    if not facts1 or not facts2:
        return 0.0

    intersection = facts1 & facts2
    union = facts1 | facts2

    return len(intersection) / len(union) if union else 0.0


def find_corroborating_sources(
    evidence_list: List[Dict[str, Any]]
) -> Dict[int, List[int]]:
    """
    Find evidence items that corroborate each other.

    Two items corroborate if:
    1. They come from independent ownership groups
    2. Their text content is sufficiently similar OR
    3. They share key facts (numbers, quotes, dates)

    Returns:
        Dict mapping evidence index to list of corroborating indices.
    """
    n = len(evidence_list)
    if n < 2:
        return {}

    # Pre-compute ownership groups and facts for each item
    ownership = []
    facts = []
    for ev in evidence_list:
        source = ev.get("source", "")
        url = ev.get("url", "")
        text = ev.get("text", ev.get("snippet", ""))

        ownership.append(_get_ownership_group(source, url))
        facts.append(_extract_key_facts(text))

    # Find corroborating pairs
    corroboration_map = defaultdict(list)

    for i in range(n):
        for j in range(i + 1, n):
            # Skip same ownership group (not independent)
            if ownership[i] == ownership[j]:
                continue

            # Check text similarity
            text_i = evidence_list[i].get("text", evidence_list[i].get("snippet", ""))
            text_j = evidence_list[j].get("text", evidence_list[j].get("snippet", ""))
            text_sim = _text_similarity(text_i, text_j)

            # Check fact overlap
            fact_overlap = _check_fact_overlap(facts[i], facts[j])

            # Combine: either strong text similarity or shared facts
            if (
                text_sim >= MIN_CORROBORATION_SIMILARITY
                or fact_overlap >= MIN_FACT_OVERLAP
            ):
                corroboration_map[i].append(j)
                corroboration_map[j].append(i)
                logger.debug(
                    f"[CORROBORATION] Items {i} and {j} corroborate "
                    f"(text_sim={text_sim:.2f}, fact_overlap={fact_overlap:.2f})"
                )

    return dict(corroboration_map)


def _assign_corroboration_groups(
    corroboration_map: Dict[int, List[int]]
) -> Dict[int, int]:
    """
    Assign group IDs to corroborated evidence using union-find.

    All items that transitively corroborate each other get the same group ID.
    Returns dict mapping index to group_id.
    """
    if not corroboration_map:
        return {}

    # Union-find
    parent: Dict[int, int] = {}

    def find(x: int) -> int:
        if x not in parent:
            parent[x] = x
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Union all corroboration pairs
    for idx, corroborators in corroboration_map.items():
        for other in corroborators:
            union(idx, other)

    # Map each index to its group root, then normalize to sequential IDs
    roots = {}
    next_group = 1
    result: Dict[int, int] = {}

    for idx in sorted(parent.keys()):
        root = find(idx)
        if root not in roots:
            roots[root] = next_group
            next_group += 1
        result[idx] = roots[root]

    return result


def _detect_derivation_chains(
    evidence_list: List[Dict[str, Any]],
    corroboration_map: Dict[int, List[int]],
) -> Dict[int, List[str]]:
    """
    Detect derivation chains: when multiple reporting/commentary sources
    cite the same primary source.

    A derivation chain exists when:
    - Item A is tier=primary
    - Items B, C are tier=reporting or commentary
    - B and C both corroborate with A

    Returns dict mapping primary item index to list of evidence_ids
    of the items that derive from it.
    """
    chains: Dict[int, List[str]] = {}

    for idx, corroborators in corroboration_map.items():
        ev = evidence_list[idx]
        if ev.get("tier") != "primary":
            continue

        # Find reporting/commentary items that corroborate with this primary
        derived = []
        for other_idx in corroborators:
            other_ev = evidence_list[other_idx]
            other_tier = other_ev.get("tier", "")
            if other_tier in ("reporting", "commentary"):
                other_id = other_ev.get("evidence_id", "")
                if other_id:
                    derived.append(other_id)

        if len(derived) >= 2:
            chains[idx] = derived
            logger.debug(
                f"[CORROBORATION] Derivation chain: primary {ev.get('evidence_id', idx)} "
                f"→ {len(derived)} derived sources"
            )

    return chains


def apply_corroboration_boost(
    evidence_list: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Detect and annotate corroborated evidence.

    Sets on each corroborated item:
    - corroboration_group_id: int group identifier (items in same group corroborate)
    - corroborating_evidence_ids: comma-separated evidence_ids of corroborating items
    - corroborating_sources: count of corroborating sources
    - derivation_chain: list of evidence_ids that derive from this primary source

    No score mutation. Pure metadata annotation.
    """
    if len(evidence_list) < 2:
        return evidence_list, {"enabled": True, "items_annotated": 0}

    # Find corroborating sources
    corroboration_map = find_corroborating_sources(evidence_list)

    if not corroboration_map:
        return evidence_list, {
            "enabled": True,
            "items_annotated": 0,
            "reason": "no_corroboration_found",
        }

    # Assign group IDs
    group_assignments = _assign_corroboration_groups(corroboration_map)

    # Detect derivation chains
    derivation_chains = _detect_derivation_chains(evidence_list, corroboration_map)

    # Annotate corroborated items
    annotated_count = 0

    for idx, corroborators in corroboration_map.items():
        if idx >= len(evidence_list):
            continue

        ev = evidence_list[idx]

        # Resolve corroborating evidence_ids (stable references, not indices)
        corroborating_ids = []
        for other_idx in corroborators:
            if other_idx < len(evidence_list):
                other_id = evidence_list[other_idx].get("evidence_id", "")
                if other_id:
                    corroborating_ids.append(other_id)

        ev["corroboration_group_id"] = group_assignments.get(idx)
        ev["corroborating_evidence_ids"] = ",".join(corroborating_ids)
        ev["corroborating_sources"] = len(corroborators)

        # Add derivation chain if this is a primary source
        if idx in derivation_chains:
            ev["derivation_chain"] = derivation_chains[idx]

        annotated_count += 1

        logger.debug(
            f"[CORROBORATION] {ev.get('source', 'unknown')} (group {group_assignments.get(idx)}): "
            f"corroborated by {len(corroborators)} independent sources"
        )

    stats = {
        "enabled": True,
        "items_annotated": annotated_count,
        "corroboration_pairs": len(corroboration_map),
        "groups": len(set(group_assignments.values())) if group_assignments else 0,
        "derivation_chains": len(derivation_chains),
    }

    if annotated_count > 0:
        logger.info(
            f"[CORROBORATION] Annotated {annotated_count} items in "
            f"{stats['groups']} groups "
            f"({stats['corroboration_pairs']} corroborating pairs, "
            f"{stats['derivation_chains']} derivation chains)"
        )

    return evidence_list, stats
