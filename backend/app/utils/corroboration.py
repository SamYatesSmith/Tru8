"""
Corroboration-Based Credibility Weighting

Boosts credibility for evidence items when multiple independent sources
report similar information. This helps surface legitimate but lesser-known
sources that are corroborated by established outlets.

Phase 6: Source Diversity Enhancement
"""

import logging
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
from collections import defaultdict

from app.core.config import settings

logger = logging.getLogger(__name__)

# Corroboration boost amounts
CORROBORATION_BOOST_2_SOURCES = 0.08  # 2 independent sources agree
CORROBORATION_BOOST_3_PLUS = 0.12    # 3+ independent sources agree

# Minimum text similarity to consider evidence as corroborating
MIN_CORROBORATION_SIMILARITY = 0.35

# Maximum boost from corroboration (prevents scores > 1.0)
MAX_CORROBORATION_BOOST = 0.15


def _get_ownership_group(source: str, url: str) -> str:
    """
    Get ownership group for a source to determine independence.

    Sources in the same ownership group are not considered independent
    for corroboration purposes.

    Args:
        source: Source name/domain
        url: Full URL

    Returns:
        Ownership group identifier
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

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score 0.0-1.0
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

    Args:
        text: Evidence text

    Returns:
        Set of extracted facts
    """
    import re

    facts = set()

    # Extract numbers (including decimals and percentages)
    numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', text)
    facts.update(numbers)

    # Extract quoted phrases
    quotes = re.findall(r'"([^"]{10,50})"', text)
    facts.update(q.lower() for q in quotes)

    # Extract dates (various formats)
    dates = re.findall(
        r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|'
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+\d{1,2},?\s+\d{4})\b',
        text, re.IGNORECASE
    )
    facts.update(d.lower() for d in dates)

    return facts


def _check_fact_overlap(facts1: Set[str], facts2: Set[str]) -> float:
    """
    Calculate overlap between two sets of facts.

    Args:
        facts1: First fact set
        facts2: Second fact set

    Returns:
        Overlap ratio 0.0-1.0
    """
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

    Args:
        evidence_list: List of evidence items

    Returns:
        Dict mapping evidence index to list of corroborating indices
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
            if text_sim >= MIN_CORROBORATION_SIMILARITY or fact_overlap >= 0.3:
                corroboration_map[i].append(j)
                corroboration_map[j].append(i)
                logger.debug(
                    f"[CORROBORATION] Items {i} and {j} corroborate "
                    f"(text_sim={text_sim:.2f}, fact_overlap={fact_overlap:.2f})"
                )

    return dict(corroboration_map)


def apply_corroboration_boost(
    evidence_list: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Apply credibility boosts for corroborated evidence.

    Evidence items that are corroborated by independent sources
    receive a credibility boost. This is especially valuable for
    lesser-known sources that are reporting the same facts as
    established outlets.

    Args:
        evidence_list: List of evidence items with credibility_score

    Returns:
        Tuple of:
        - Updated evidence list with boosted scores
        - Stats about corroboration boosts applied
    """
    if len(evidence_list) < 2:
        return evidence_list, {"enabled": True, "items_boosted": 0}

    # Find corroborating sources
    corroboration_map = find_corroborating_sources(evidence_list)

    if not corroboration_map:
        return evidence_list, {
            "enabled": True,
            "items_boosted": 0,
            "reason": "no_corroboration_found"
        }

    # Apply boosts
    boosted_count = 0
    total_boost = 0.0

    for idx, corroborators in corroboration_map.items():
        if idx >= len(evidence_list):
            continue

        ev = evidence_list[idx]
        current_cred = ev.get("credibility_score", 0.6)

        # Determine boost based on number of corroborating sources
        num_corroborators = len(corroborators)
        if num_corroborators >= 3:
            boost = CORROBORATION_BOOST_3_PLUS
        elif num_corroborators >= 2:
            boost = CORROBORATION_BOOST_2_SOURCES
        else:
            boost = CORROBORATION_BOOST_2_SOURCES * 0.7  # Single corroborator

        # Cap the boost
        boost = min(boost, MAX_CORROBORATION_BOOST)

        # Apply boost (cap at 1.0)
        new_cred = min(1.0, current_cred + boost)

        if new_cred > current_cred:
            ev["credibility_score"] = new_cred
            ev["corroboration_boost"] = boost
            ev["corroborating_sources"] = num_corroborators
            ev["corroboration_indices"] = corroborators

            boosted_count += 1
            total_boost += boost

            logger.debug(
                f"[CORROBORATION BOOST] {ev.get('source', 'unknown')}: "
                f"{current_cred:.2f} -> {new_cred:.2f} "
                f"(corroborated by {num_corroborators} independent sources)"
            )

    stats = {
        "enabled": True,
        "items_boosted": boosted_count,
        "total_boost": total_boost,
        "corroboration_pairs": len(corroboration_map)
    }

    if boosted_count > 0:
        logger.info(
            f"[CORROBORATION] Applied boosts to {boosted_count} items "
            f"({stats['corroboration_pairs']} corroborating pairs found)"
        )

    return evidence_list, stats
