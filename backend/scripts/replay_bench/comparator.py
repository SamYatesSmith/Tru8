"""Compare an Observation dict against a golden dict.

Three categories — hard invariants (exact), tolerant counters (numeric ±tol),
set Jaccard (similarity floor + must-have / must-not-have subsets).

Each comparator yields zero-or-more Diff records with one of three levels:
- ok: signal matches as expected
- warning: signal drifted within an acceptable band
- failure: signal violates a hard invariant or breaks a tolerant range
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass
class Diff:
    level: str  # "ok" | "warning" | "failure"
    signal: str
    expected: Any
    observed: Any
    message: str

    def is_failure(self) -> bool:
        return self.level == "failure"

    def is_warning(self) -> bool:
        return self.level == "warning"


def _get(obs: Dict[str, Any], path: str) -> Any:
    """Dotted-path lookup with int-keyed dict support: 'freshness_inject_per_claim.0.fired'."""
    cur: Any = obs
    for part in path.split("."):
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
            elif part.isdigit() and part in cur:
                cur = cur[part]
            else:
                return None
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return None
    return cur


# ---------- hard invariants ----------


def compare_hard_invariants(obs: Dict[str, Any], hard: Dict[str, Any]) -> List[Diff]:
    out: List[Diff] = []
    if not hard:
        return out

    ci_expected = hard.get("classifier_inject")
    ci_obs = obs.get("classifier_inject")
    if ci_expected is not None:
        out.extend(_check_classifier_inject(ci_obs, ci_expected))

    fresh_must_fire = hard.get("freshness_inject_must_fire_on_claims")
    if fresh_must_fire is not None:
        out.extend(_check_freshness(obs, fresh_must_fire))

    if "factchecks_min" in hard or "factchecks_max" in hard:
        out.append(
            _check_factcheck_range(
                obs, hard.get("factchecks_min", 0), hard.get("factchecks_max", 999)
            )
        )

    must_have = hard.get("must_have_url_substrings", [])
    must_not = hard.get("must_not_have_url_substrings", [])
    if must_have or must_not:
        out.extend(_check_url_substrings(obs, must_have, must_not))

    expected_subset = hard.get("expected_adapters_subset")
    if expected_subset is not None:
        out.append(_check_adapter_subset(obs, expected_subset))

    expected_recovery_failures_max = hard.get("coverage_recovery_failures_max")
    if expected_recovery_failures_max is not None:
        out.append(_check_coverage_recovery(obs, expected_recovery_failures_max))

    if hard.get("coverage_recovery_must_not_timeout"):
        out.append(_check_coverage_recovery_timeout(obs))

    v3_floors = hard.get("v3_quality_floors")
    v3_warn = hard.get("v3_quality_warn_band")
    if v3_floors:
        out.extend(_check_v3_quality_per_claim(obs, v3_floors, v3_warn or {}))

    temporal_periods = hard.get("temporal_scope_must_fire_on_periods")
    if temporal_periods is not None:
        out.extend(_check_temporal_scope(obs, temporal_periods))

    return out


def _check_temporal_scope(
    obs: Dict[str, Any], expected_periods: Sequence[str]
) -> List[Diff]:
    """The F1 gate must still fire, on the periods it fired on when golden.

    A boolean structural signal, so it belongs in hard invariants rather than in
    tolerant counters: the gate either acted on a month-pinned element or it did
    not, and that cannot drift without code changing. This exists because the gate
    shipped, passed the bench and had fired zero times — a corpus with no
    month-pinned claim cannot notice a gate that stops working.
    """
    events = obs.get("temporal_scope_events") or []
    observed_periods = sorted({e.get("period") for e in events if e.get("period")})
    scoped_refs = sum(int(e.get("scoped", 0)) for e in events)
    out: List[Diff] = []

    for period in expected_periods:
        fired = period in observed_periods
        out.append(
            Diff(
                level="ok" if fired else "failure",
                signal=f"temporal_scope:{period}",
                expected=f"gate fires on an element pinned to {period}",
                observed=(
                    f"{scoped_refs} ref(s) scoped on {observed_periods}"
                    if events
                    else "never fired"
                ),
                message=(
                    f"temporal scope gate fired on {period}"
                    if fired
                    else (
                        "the F1 temporal scope gate stopped scoping off-period "
                        "evidence — settled facts can read as disputed again"
                    )
                ),
            )
        )
    return out


def _check_classifier_inject(obs_inject: Any, expected: Dict[str, Any]) -> List[Diff]:
    out: List[Diff] = []
    if not isinstance(obs_inject, dict):
        return [
            Diff(
                level="failure",
                signal="classifier_inject",
                expected=expected,
                observed=obs_inject,
                message="No [CLASSIFICATION INJECT] line was emitted by this run",
            )
        ]
    for key in ("primary", "jurisdiction_to", "jurisdiction_from"):
        if key in expected and expected[key] != obs_inject.get(key):
            out.append(
                Diff(
                    level="failure",
                    signal=f"classifier_inject.{key}",
                    expected=expected[key],
                    observed=obs_inject.get(key),
                    message=f"classifier_inject.{key} mismatch",
                )
            )
    if "secondaries_must_include" in expected:
        obs_sec = set(obs_inject.get("final_secondaries", []))
        missing = [s for s in expected["secondaries_must_include"] if s not in obs_sec]
        if missing:
            out.append(
                Diff(
                    level="failure",
                    signal="classifier_inject.secondaries",
                    expected=expected["secondaries_must_include"],
                    observed=sorted(obs_sec),
                    message=f"missing required secondaries: {missing}",
                )
            )
        else:
            out.append(
                Diff(
                    level="ok",
                    signal="classifier_inject.secondaries",
                    expected=expected["secondaries_must_include"],
                    observed=sorted(obs_sec),
                    message="all required secondaries present",
                )
            )
    if "secondaries_must_not_include" in expected:
        obs_sec = set(obs_inject.get("final_secondaries", []))
        unwanted = [s for s in expected["secondaries_must_not_include"] if s in obs_sec]
        if unwanted:
            out.append(
                Diff(
                    level="failure",
                    signal="classifier_inject.secondaries_unwanted",
                    expected=f"none of {expected['secondaries_must_not_include']}",
                    observed=sorted(obs_sec),
                    message=f"unwanted secondaries present: {unwanted}",
                )
            )
    return out


def _check_freshness(obs: Dict[str, Any], must_fire_on: Sequence[int]) -> List[Diff]:
    out: List[Diff] = []
    fresh = obs.get("freshness_inject_per_claim", {}) or {}
    for claim_idx in must_fire_on:
        rec = fresh.get(str(claim_idx))
        if not (isinstance(rec, dict) and rec.get("fired")):
            out.append(
                Diff(
                    level="failure",
                    signal=f"freshness_inject.claim={claim_idx}",
                    expected="fired",
                    observed=rec,
                    message=f"[FRESHNESS INJECT] did not fire on claim {claim_idx}",
                )
            )
        else:
            out.append(
                Diff(
                    level="ok",
                    signal=f"freshness_inject.claim={claim_idx}",
                    expected="fired",
                    observed=f"py->{rec.get('to')}",
                    message="freshness inject fired as expected",
                )
            )
    return out


def _check_factcheck_range(obs: Dict[str, Any], lo: int, hi: int) -> Diff:
    fc = obs.get("factchecks_per_claim", {}) or {}
    total = sum(int(v) for v in fc.values())
    if lo <= total <= hi:
        return Diff(
            level="ok",
            signal="factchecks_total",
            expected=f"[{lo}, {hi}]",
            observed=total,
            message="factcheck count within band",
        )
    return Diff(
        level="warning",
        signal="factchecks_total",
        expected=f"[{lo}, {hi}]",
        observed=total,
        message="factcheck count outside band (Google Fact-Check returns drift)",
    )


def _check_url_substrings(
    obs: Dict[str, Any],
    must_have: Sequence[str],
    must_not: Sequence[str],
) -> List[Diff]:
    out: List[Diff] = []
    flat = obs.get("url_ledger_flat", []) or []
    for needle in must_have:
        if any(needle in u for u in flat):
            out.append(
                Diff(
                    level="ok",
                    signal=f"must_have_url:{needle}",
                    expected=needle,
                    observed="present",
                    message=f"required URL substring present: {needle}",
                )
            )
        else:
            out.append(
                Diff(
                    level="failure",
                    signal=f"must_have_url:{needle}",
                    expected=needle,
                    observed="absent",
                    message=f"required URL substring missing: {needle}",
                )
            )
    for needle in must_not:
        hits = [u for u in flat if needle in u]
        if hits:
            out.append(
                Diff(
                    level="failure",
                    signal=f"must_not_have_url:{needle}",
                    expected="absent",
                    observed=hits[:3],
                    message=f"banned URL substring present: {needle}",
                )
            )
        else:
            out.append(
                Diff(
                    level="ok",
                    signal=f"must_not_have_url:{needle}",
                    expected="absent",
                    observed="absent",
                    message=f"banned URL substring correctly absent: {needle}",
                )
            )
    return out


def _check_adapter_subset(obs: Dict[str, Any], expected_subset: Sequence[str]) -> Diff:
    obs_set = set(obs.get("final_adapter_set", []))
    missing = [a for a in expected_subset if a not in obs_set]
    if missing:
        return Diff(
            level="failure",
            signal="expected_adapters_subset",
            expected=list(expected_subset),
            observed=sorted(obs_set),
            message=f"required adapters absent from final set: {missing}",
        )
    return Diff(
        level="ok",
        signal="expected_adapters_subset",
        expected=list(expected_subset),
        observed=sorted(obs_set),
        message="all required adapters present",
    )


def _check_coverage_recovery(obs: Dict[str, Any], max_failures: int) -> Diff:
    fails = int(obs.get("coverage_recovery_failures", 0))
    if fails > max_failures:
        return Diff(
            level="failure",
            signal="coverage_recovery_failures",
            expected=f"<={max_failures}",
            observed=fails,
            message=f"coverage recovery failed {fails} times (cap {max_failures})",
        )
    return Diff(
        level="ok",
        signal="coverage_recovery_failures",
        expected=f"<={max_failures}",
        observed=fails,
        message="coverage recovery within tolerance",
    )


def _check_coverage_recovery_timeout(obs: Dict[str, Any]) -> Diff:
    """Hard invariant: [COVERAGE RECOVERY] Timed out must not appear.

    Bug B (V1 plan Step 2, commit c132704) scales the recovery budget per
    claim. If the line fires post-fix, something regressed — either the
    per-claim scaling broke or the candidate count is wildly higher than
    expected for this corpus case.
    """
    timed_out = bool(obs.get("coverage_recovery_timed_out", False))
    seconds = obs.get("coverage_recovery_timeout_seconds")
    if timed_out:
        return Diff(
            level="failure",
            signal="coverage_recovery_timed_out",
            expected=False,
            observed=f"after {seconds}s",
            message="[COVERAGE RECOVERY] Timed out — Bug B regression suspect",
        )
    return Diff(
        level="ok",
        signal="coverage_recovery_timed_out",
        expected=False,
        observed=False,
        message="coverage recovery did not time out",
    )


# V3 signals — see audit/pipeline-issues/2026-05-06_v1_quality_plan.md.
# Each signal is either *_min (higher is better — FAIL below Poor floor,
# WARN between Poor floor and Mediocre floor) or *_max (lower is better —
# FAIL above Poor cap, WARN between Mediocre cap and Poor cap). Quality
# verdict is judged on MAPPED items only; mapping rate itself is diagnostic.
_V3_MIN_SIGNALS = ("unique_domains", "factual_weight_share", "element_resolution")
_V3_MAX_SIGNALS = ("top_domain_share", "wikipedia_share")


def _check_v3_quality_per_claim(
    obs: Dict[str, Any],
    floors: Dict[str, Any],
    warn_band: Dict[str, Any],
) -> List[Diff]:
    """Per-claim V3 quality floor check.

    `floors` carries Poor thresholds (FAIL crosses these); `warn_band` carries
    Mediocre thresholds (WARN inside [Poor, Mediocre], OK beyond Mediocre).

    Claims absent from `b3_quality_per_claim` are skipped silently — no log
    line means no mapped evidence, which is its own observable elsewhere.
    """
    out: List[Diff] = []
    b3_quality = obs.get("b3_quality_per_claim") or {}
    if not b3_quality:
        return out

    for claim_key, signals in b3_quality.items():
        if not isinstance(signals, dict):
            continue
        for name in _V3_MIN_SIGNALS:
            out.append(
                _check_v3_min(
                    claim_key,
                    name,
                    signals.get(name),
                    floors.get(f"{name}_min"),
                    warn_band.get(f"{name}_min"),
                )
            )
        for name in _V3_MAX_SIGNALS:
            out.append(
                _check_v3_max(
                    claim_key,
                    name,
                    signals.get(name),
                    floors.get(f"{name}_max"),
                    warn_band.get(f"{name}_max"),
                )
            )
    return [d for d in out if d is not None]


def _check_v3_min(
    claim_key: str,
    name: str,
    observed: Any,
    poor_floor: Any,
    mediocre_floor: Any,
) -> Diff:
    if poor_floor is None or observed is None:
        return None  # type: ignore[return-value]
    signal = f"v3:{name}.claim={claim_key}"
    obs_f = float(observed)
    poor_f = float(poor_floor)
    if obs_f < poor_f:
        return Diff(
            level="failure",
            signal=signal,
            expected=f">={poor_f}",
            observed=obs_f,
            message=f"{name}={obs_f} below Poor floor {poor_f} on claim {claim_key}",
        )
    if mediocre_floor is not None and obs_f < float(mediocre_floor):
        return Diff(
            level="warning",
            signal=signal,
            expected=f">={mediocre_floor}",
            observed=obs_f,
            message=(
                f"{name}={obs_f} in Mediocre band [{poor_f}, {mediocre_floor}) "
                f"on claim {claim_key} — drifting toward Poor"
            ),
        )
    return Diff(
        level="ok",
        signal=signal,
        expected=f">={mediocre_floor or poor_f}",
        observed=obs_f,
        message=f"{name} OK on claim {claim_key}",
    )


def _check_v3_max(
    claim_key: str,
    name: str,
    observed: Any,
    poor_cap: Any,
    mediocre_cap: Any,
) -> Diff:
    if poor_cap is None or observed is None:
        return None  # type: ignore[return-value]
    signal = f"v3:{name}.claim={claim_key}"
    obs_f = float(observed)
    poor_f = float(poor_cap)
    if obs_f > poor_f:
        return Diff(
            level="failure",
            signal=signal,
            expected=f"<={poor_f}",
            observed=obs_f,
            message=f"{name}={obs_f} above Poor cap {poor_f} on claim {claim_key}",
        )
    if mediocre_cap is not None and obs_f > float(mediocre_cap):
        return Diff(
            level="warning",
            signal=signal,
            expected=f"<={mediocre_cap}",
            observed=obs_f,
            message=(
                f"{name}={obs_f} in Mediocre band ({mediocre_cap}, {poor_f}] "
                f"on claim {claim_key} — drifting toward Poor"
            ),
        )
    return Diff(
        level="ok",
        signal=signal,
        expected=f"<={mediocre_cap or poor_f}",
        observed=obs_f,
        message=f"{name} OK on claim {claim_key}",
    )


# ---------- tolerant counters ----------


# Map each counter signal to its location in the observation dict.
_COUNTER_PATHS = {
    "sources_included": ("pipeline_metrics", "sources_included"),
    "sources_considered": ("pipeline_metrics", "sources_considered"),
    "claims": ("pipeline_metrics", "claims"),
    "elements": ("pipeline_metrics", "elements"),
    "web_search": ("pipeline_metrics", "web_search"),
    "api_adapters": ("pipeline_metrics", "api_adapters"),
    "llm_calls": ("pipeline_metrics", "llm_calls"),
    "tier_primary": ("tier_distribution", "primary"),
    "tier_reporting": ("tier_distribution", "reporting"),
    "tier_commentary": ("tier_distribution", "commentary"),
    "scorer_kept": ("scorer_summary", "keeping"),
    "scorer_excluded": ("scorer_summary", "excluded"),
    "b3_shown": ("b3_receipts", "shown"),
    "b3_unmapped": ("b3_receipts", "unmapped"),
    "b3_excluded": ("b3_receipts", "excluded"),
    # F1 temporal scope gate (2026-08-06)
    "temporal_scoped_refs": ("temporal_scope_summary", "scoped_refs"),
    "temporal_scoped_elements": ("temporal_scope_summary", "elements"),
}


def compare_tolerant_counters(
    obs: Dict[str, Any], counters: Dict[str, Dict[str, int]]
) -> List[Diff]:
    out: List[Diff] = []
    if not counters:
        return out
    for name, spec in counters.items():
        path = _COUNTER_PATHS.get(name)
        if path is None:
            out.append(
                Diff(
                    level="warning",
                    signal=f"counter:{name}",
                    expected=spec,
                    observed="N/A",
                    message=f"unknown counter name {name!r}",
                )
            )
            continue
        section = obs.get(path[0]) or {}
        observed = section.get(path[1]) if isinstance(section, dict) else None
        target = spec.get("value")
        tol = spec.get("tolerance", 0)
        # If the parent section emitted but the specific key is absent, treat
        # as zero rather than missing — this happens routinely for tier/type
        # buckets that drop to 0 between runs.
        if observed is None and isinstance(section, dict) and section:
            observed = 0
        if observed is None:
            out.append(
                Diff(
                    level="failure",
                    signal=f"counter:{name}",
                    expected=target,
                    observed=None,
                    message="signal absent from observation (parent section never emitted)",
                )
            )
            continue
        delta = abs(int(observed) - int(target))
        if delta <= tol:
            out.append(
                Diff(
                    level="ok",
                    signal=f"counter:{name}",
                    expected=f"{target}+-{tol}",
                    observed=observed,
                    message="within tolerance",
                )
            )
        elif delta <= tol * 2:
            out.append(
                Diff(
                    level="warning",
                    signal=f"counter:{name}",
                    expected=f"{target}+-{tol}",
                    observed=observed,
                    message=f"drift delta={delta} exceeds tolerance but within 2x -- review",
                )
            )
        else:
            out.append(
                Diff(
                    level="failure",
                    signal=f"counter:{name}",
                    expected=f"{target}+-{tol}",
                    observed=observed,
                    message=f"drift delta={delta} exceeds 2x tolerance -- likely regression",
                )
            )
    return out


# ---------- set Jaccard ----------


def jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def compare_set_jaccard(
    obs: Dict[str, Any], jaccard_specs: Dict[str, Dict[str, Any]]
) -> List[Diff]:
    out: List[Diff] = []
    if not jaccard_specs:
        return out
    for name, spec in jaccard_specs.items():
        observed_set = obs.get(name)
        if observed_set is None:
            out.append(
                Diff(
                    level="warning",
                    signal=f"jaccard:{name}",
                    expected=spec,
                    observed=None,
                    message=f"signal {name!r} absent from observation",
                )
            )
            continue
        if not isinstance(observed_set, (list, set)):
            observed_set = list(observed_set or [])
        golden = spec.get("golden", [])
        floor = float(spec.get("min_similarity", 0.6))
        sim = jaccard(observed_set, golden)
        if sim >= floor:
            out.append(
                Diff(
                    level="ok",
                    signal=f"jaccard:{name}",
                    expected=f">={floor:.2f}",
                    observed=f"{sim:.2f}",
                    message=f"set similarity {sim:.2f} above floor",
                )
            )
        elif sim >= floor - 0.20:
            out.append(
                Diff(
                    level="warning",
                    signal=f"jaccard:{name}",
                    expected=f">={floor:.2f}",
                    observed=f"{sim:.2f}",
                    message=f"set similarity {sim:.2f} below floor (within noise band) -- review",
                )
            )
        else:
            out.append(
                Diff(
                    level="failure",
                    signal=f"jaccard:{name}",
                    expected=f">={floor:.2f}",
                    observed=f"{sim:.2f}",
                    message=f"set similarity {sim:.2f} far below floor -- likely regression",
                )
            )
    return out


# ---------- top-level entry ----------


def compare(obs: Dict[str, Any], golden: Dict[str, Any]) -> List[Diff]:
    diffs: List[Diff] = []
    diffs.extend(compare_hard_invariants(obs, golden.get("hard_invariants", {})))
    diffs.extend(compare_tolerant_counters(obs, golden.get("tolerant_counters", {})))
    diffs.extend(compare_set_jaccard(obs, golden.get("set_jaccard", {})))
    return diffs
