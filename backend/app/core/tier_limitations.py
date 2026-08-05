"""What a tier withheld, derived from the pipeline config rather than declared by hand.

WHY THIS MODULE EXISTS
----------------------
`QUICK_LIMITATIONS` was a hand-maintained list in `app/api/v1/agent.py`, copied
verbatim into `app/api/v1/agent_x402.py`. Measured 2026-08-05, it declared six
omissions while `QUICK_CONFIG` disabled ten — the four it missed were evidence
distillation, post-filter recovery, and the two caps that shrink breadth
(sources 20 -> 8, queries per element 3 -> 1). A caller paying for the reduced
tier was told less had been withheld than actually was.

Two failure modes produced that, and a hand-maintained list is open to both:

  1. A stage gets disabled in QUICK_CONFIG and nobody updates the list.
  2. The list is duplicated, so one copy is updated and the other is not.

So the list is computed from the config objects themselves. Adding a new
reduction to QUICK_CONFIG without naming it here fails
`tests/unit/test_tier_limitations.py::test_every_config_reduction_is_declared`,
which is the only way this stays true.

Invariant #5: no hidden curation — every exclusion has a receipt.
"""

from typing import Dict, List, Optional

# Field name on PipelineConfig -> the slug we publish in _meta.limitations.
#
# Slugs are part of the public agent API. The first six are the original
# hand-written values and MUST NOT be renamed — callers may branch on them.
# The rest were added 2026-08-05 when the list was found to be incomplete.
_FIELD_SLUGS: Dict[str, str] = {
    "enable_llm_classifier": "heuristic_classification",
    "enable_factcheck_lookup": "no_factcheck_lookup",
    "enable_api_adapters": "no_api_sources",
    "enable_llm_relevance_scorer": "no_llm_relevance_scoring",
    "enable_coverage_recovery": "no_coverage_recovery",
    "enable_query_answering": "no_query_answering",
    # Added 2026-08-05 — real reductions that were never declared.
    "enable_evidence_distillation": "no_evidence_distillation",
    "enable_post_filter_recovery": "no_post_filter_recovery",
    "max_sources_per_claim": "reduced_source_cap",
    "max_queries_per_element": "reduced_query_breadth",
    "max_wall_time_seconds": "reduced_time_budget",
}


def _configs():
    """Imported lazily — the API layer must not pull in the pipeline at import time."""
    from app.pipeline.runner import DEFAULT_CONFIG, QUICK_CONFIG

    return DEFAULT_CONFIG, QUICK_CONFIG


def undeclared_reductions() -> List[str]:
    """Config fields where quick differs from full but no slug is mapped.

    Empty is the healthy state. The drift guard asserts exactly that, so a new
    reduction cannot ship silently.
    """
    default, quick = _configs()
    return sorted(
        field
        for field in vars(default)
        if getattr(quick, field) != getattr(default, field)
        and field != "mode"
        and field not in _FIELD_SLUGS
    )


def limitations_for_tier(tier: Optional[str]) -> List[str]:
    """What the given tier withheld, as published in ``_meta.limitations``.

    ``tier`` is the tier that ACTUALLY produced the analysis — for a cached or
    retrieved result that is ``Check.executed_tier``, never the tier the caller
    asked for. Serving a quick-produced result to a caller who requested full
    and reporting no limitations is the defect this signature exists to stop.

    Unknown or missing tiers return [] rather than guessing: a wrong receipt is
    worse than an absent one, and pre-2026-08 rows predate the column.
    """
    if tier != "quick":
        return []

    default, quick = _configs()
    return sorted(
        slug
        for field, slug in _FIELD_SLUGS.items()
        if hasattr(default, field) and getattr(quick, field) != getattr(default, field)
    )
