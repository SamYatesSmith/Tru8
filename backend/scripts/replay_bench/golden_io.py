"""Read/write golden.json files.

When --update-golden is passed, the harness writes a derived golden.json from
the current observation. Tolerances and similarity floors get sensible
defaults; the user is expected to tune them by hand for each corpus claim.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


GOLDEN_FILENAME = "golden.json"


def golden_path(corpus_dir: Path, claim_id: str) -> Path:
    return corpus_dir / claim_id / GOLDEN_FILENAME


def load_golden(corpus_dir: Path, claim_id: str) -> Optional[Dict[str, Any]]:
    p = golden_path(corpus_dir, claim_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def write_observation_dump(
    corpus_dir: Path, claim_id: str, observation: Dict[str, Any]
) -> Path:
    """Write the raw observation to observation.json — useful for debugging
    and for manually constructing/updating goldens."""
    p = corpus_dir / claim_id / "observation.json"
    p.write_text(
        json.dumps(observation, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return p


def derive_default_golden(
    claim_id: str, observation: Dict[str, Any], git_sha: str = "unknown"
) -> Dict[str, Any]:
    """Produce a starter golden.json from an observation. Tune by hand after."""
    metrics = observation.get("pipeline_metrics") or {}
    tiers = observation.get("tier_distribution") or {}
    classifier_inject = observation.get("classifier_inject") or {}
    fresh = observation.get("freshness_inject_per_claim") or {}
    fired_claims = sorted(
        int(k) for k, v in fresh.items() if isinstance(v, dict) and v.get("fired")
    )

    hard_invariants: Dict[str, Any] = {}
    if classifier_inject:
        hard_invariants["classifier_inject"] = {
            "primary": classifier_inject.get("primary"),
            "secondaries_must_include": list(
                classifier_inject.get("final_secondaries", [])
            ),
            "jurisdiction_to": classifier_inject.get("jurisdiction_to"),
        }
    if fired_claims:
        hard_invariants["freshness_inject_must_fire_on_claims"] = fired_claims
    hard_invariants["must_have_url_substrings"] = []
    # Auto-derived goldens leave must_not_have empty: aspirational rules belong
    # in user-tuned goldens, not in the captured baseline of current behaviour.
    hard_invariants["must_not_have_url_substrings"] = []
    if observation.get("final_adapter_set"):
        hard_invariants["expected_adapters_subset"] = []
    # max() so a stochastic-bug run with N>0 doesn't pin future runs at zero.
    # Cap is generous: NF-21 fires once per unresolved element on cov-recovery
    # claims, and that count drifts run-to-run with mapping outcomes.
    obs_cov_failures = int(observation.get("coverage_recovery_failures", 0))
    hard_invariants["coverage_recovery_failures_max"] = max(6, obs_cov_failures + 2)

    # Counter tolerances are intentionally loose by default; tighten by hand
    # once you know the natural drift for each claim.
    tolerant_counters: Dict[str, Dict[str, int]] = {}
    for name, value in [
        ("sources_included", metrics.get("sources_included")),
        ("claims", metrics.get("claims")),
        ("elements", metrics.get("elements")),
        ("web_search", metrics.get("web_search")),
        ("api_adapters", metrics.get("api_adapters")),
    ]:
        if value is not None:
            # claims tolerance=1 absorbs the LLM occasionally splitting an
            # article into N+/-1 claims for the same input. Tighten to 0 by
            # hand once you've confirmed the extraction is stable for the claim.
            tol = 1 if name == "claims" else (3 if name == "elements" else 8)
            tolerant_counters[name] = {"value": int(value), "tolerance": tol}
    for tier, count in tiers.items():
        # Tier counts are LLM-driven and the noisiest signal in the suite.
        tolerant_counters[f"tier_{tier}"] = {
            "value": int(count),
            "tolerance": max(4, int(count) // 2),
        }

    # Jaccard floors are size-aware: small pools naturally produce noisier
    # set-overlap because a single different URL is a bigger fraction. Tune
    # higher by hand once you trust the noise floor for each claim.
    url_pool = observation.get("url_ledger_flat", []) or []
    dom_pool = observation.get("domain_set", []) or []

    def _floor(
        n: int, very_small: float, small: float, mid: float, large: float
    ) -> float:
        if n < 8:
            return very_small
        if n < 15:
            return small
        if n < 30:
            return mid
        return large

    url_floor = _floor(len(url_pool), 0.15, 0.25, 0.35, 0.40)
    dom_floor = _floor(len(dom_pool), 0.20, 0.30, 0.45, 0.55)
    set_jaccard: Dict[str, Dict[str, Any]] = {
        "url_ledger_flat": {
            "golden": list(url_pool),
            "min_similarity": url_floor,
        },
        "domain_set": {
            "golden": list(dom_pool),
            "min_similarity": dom_floor,
        },
    }

    return {
        "claim_id": claim_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "captured_with": git_sha,
        "captured_with_known_bugs": [],
        "notes": "Auto-derived golden — review and tune tolerances/must-haves by hand.",
        "hard_invariants": hard_invariants,
        "tolerant_counters": tolerant_counters,
        "set_jaccard": set_jaccard,
    }


def write_golden(corpus_dir: Path, claim_id: str, golden: Dict[str, Any]) -> Path:
    p = golden_path(corpus_dir, claim_id)
    p.write_text(json.dumps(golden, indent=2, sort_keys=False), encoding="utf-8")
    return p
