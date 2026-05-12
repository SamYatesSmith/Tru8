"""Date-anchor query augmentation (2026-05-12).

Surfaced by live-test of Prompt 1 (November 2023 Autumn Statement):
the claim explicitly named "November 2023" but search providers
returned 2025 Autumn Budget content because the LLM Query Planner
produced queries like "Autumn Statement National Insurance OBR" with
no year — and Google ranks recent content higher for recurring
topics.

This is a different failure mode than NF-20-B (DATE entity missing
on a claim) and different from B4 freshness inject (which lifts the
time filter). Here the DATE entity IS present, freshness IS "none",
the providers DO return broader temporal range — but their RANKING
favours recency. Without an explicit year in the query string, the
2025 budget cycle outranks the 2023 one.

Fix: mechanical augmentation. After the LLM Query Planner returns
queries, if the claim has a clear single year in its DATE entities
and the year isn't already in the query string, append it. NF-11-
safe (mechanical, not prompt-only).

Scope:
  * Multiple years in DATE entities → no-op (ambiguous; LLM may
    have already handled the comparison case).
  * Year already in query → no-op (LLM did the right thing).
  * No DATE entity → no-op (covered by other paths).
  * Current year → still anchors. Lower stakes since recent content
    is what Google wants to return anyway.

Runs BEFORE class augmentation so class-targeted queries inherit the
date anchor in their base.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Match 4-digit years 19xx or 20xx as standalone tokens (word-boundary
# anchored so 2024-01 inside an ISO date matches, but parts of larger
# numbers like the "20" in "2024" don't trigger spurious hits).
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _extract_years_from_entities(
    entities: Optional[List[Dict[str, Any]]],
) -> List[int]:
    """Return unique years referenced by DATE entities in the bag.

    Reads ``{text, type}`` shape (NF-15 typed). Includes inherited
    DATEs that NF-20-B's propagation added — they carry the same
    ``type: "DATE"`` so this function is agnostic to source.
    """
    if not entities:
        return []
    found: List[int] = []
    seen = set()
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        if (ent.get("type") or "").upper().strip() != "DATE":
            continue
        text = ent.get("text") or ""
        if not isinstance(text, str):
            continue
        for match in _YEAR_RE.finditer(text):
            year = int(match.group(0))
            if year not in seen:
                seen.add(year)
                found.append(year)
    return found


def augment_plans_with_date_anchor(
    plans: List[Dict[str, Any]],
    claims_with_elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Append the claim's DATE year to queries that don't carry it.

    Mutates each plan's ``queries`` list in place. Returns the same
    list for caller chaining.

    No-op when:
      * No plans / no claims_with_elements.
      * A plan's claim has zero or 2+ unique years in DATE entities
        (single-year ambiguity is what this addresses).
      * The query already contains the year as a 4-digit token.
    """
    if not plans or not claims_with_elements:
        return plans

    # Index claim_index → unique years (sorted for determinism).
    years_by_claim: Dict[int, List[int]] = {}
    for claim in claims_with_elements:
        idx = claim.get("claim_index")
        if idx is None:
            continue
        years = sorted(_extract_years_from_entities(claim.get("key_entities")))
        years_by_claim[idx] = years

    augmented_count = 0
    anchors_by_year: Dict[int, int] = {}
    for plan in plans:
        claim_idx = plan.get("claim_index")
        years = years_by_claim.get(claim_idx, [])
        # Only anchor when there is ONE clear year. Multi-year claims
        # are ambiguous; let the LLM's query stand.
        if len(years) != 1:
            continue

        year_str = str(years[0])
        queries = plan.get("queries") or []
        new_queries: List[str] = []
        for q in queries:
            if not isinstance(q, str):
                new_queries.append(q)
                continue
            if year_str in q:
                # Year already embedded by the LLM.
                new_queries.append(q)
                continue
            new_queries.append(f"{q} {year_str}")
            augmented_count += 1
            anchors_by_year[years[0]] = anchors_by_year.get(years[0], 0) + 1
        plan["queries"] = new_queries

    if augmented_count:
        logger.info(
            f"[QUERY AUGMENT] Date anchor appended {augmented_count} time(s) "
            f"across plans (years: {dict(sorted(anchors_by_year.items()))})"
        )

    return plans
