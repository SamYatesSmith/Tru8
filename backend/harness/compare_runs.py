#!/usr/bin/env python3
"""
Compare two golden dataset runs and output a pass/fail report + markdown diff.

Usage:
    python compare_runs.py runs/20260206T120000_baseline-v1 runs/20260206T130000_after-PR-1A

Outputs:
    - Terminal: Claim Map divergences, evidence URL Jaccard, ledger diffs
    - File: <after_dir>/_diff_report.md (PR-reviewable markdown)
    - Pass/Fail against two-gate system (evidence determinism + Claim Map stability)
"""
import argparse
import json
import sys
from pathlib import Path


# --- Gate 1: Evidence determinism (Jaccard thresholds) ---
MIN_EVIDENCE_JACCARD = 0.80  # 80% URL overlap (normal runs)
MIN_FIXTURES_FOR_HARD_GATE = 12

# Frozen URL replay (tighter — search variance eliminated)
FROZEN_MIN_EVIDENCE_JACCARD = 0.90

# Frozen EVIDENCE replay (strictest — zero network)
FROZEN_EVIDENCE_MIN_JACCARD_OVERALL = 0.90
FROZEN_EVIDENCE_MIN_JACCARD_CORE = 0.95

# --- Gate 2: Claim Map stability (classification-based) ---
# No numeric threshold — uses compare_claim_maps() to categorize each divergence:
#   hard_fail:     element count mismatch (structural divergence)
#   pipeline_fail: orientation differs but element states are identical (mechanical bug)
#   llm_noise:     element state flip, evidence mapping change, or claim type change


def compare_claim_maps(baseline_cm, current_cm):
    """Compare two ClaimMap dicts for determinism testing.

    Returns (status, reason, details) where status is one of:
        'pass', 'hard_fail', 'pipeline_fail', 'llm_noise'
    """
    if not baseline_cm or not current_cm:
        if not baseline_cm and not current_cm:
            return ("pass", "both_empty", {})
        return ("hard_fail", "missing_claim_map", {})

    b_elements = baseline_cm.get("elements", [])
    c_elements = current_cm.get("elements", [])

    # 1. Element count mismatch → hard_fail
    if len(b_elements) != len(c_elements):
        return (
            "hard_fail",
            "element_count_mismatch",
            {"baseline": len(b_elements), "current": len(c_elements)},
        )

    # 2. Per-element state comparison
    state_flips = []
    for b_elem, c_elem in zip(b_elements, c_elements):
        if b_elem.get("state") != c_elem.get("state"):
            state_flips.append(
                {
                    "element_id": b_elem.get("element_id", "?"),
                    "baseline_state": b_elem.get("state"),
                    "current_state": c_elem.get("state"),
                }
            )

    # 3. Evidence mapping comparison (informational)
    mapping_diffs = []
    for b_elem, c_elem in zip(b_elements, c_elements):
        b_refs = {r.get("evidence_id") for r in b_elem.get("evidence_refs", [])}
        c_refs = {r.get("evidence_id") for r in c_elem.get("evidence_refs", [])}
        if b_refs != c_refs:
            mapping_diffs.append(
                {
                    "element_id": b_elem.get("element_id", "?"),
                    "only_baseline": sorted(b_refs - c_refs),
                    "only_current": sorted(c_refs - b_refs),
                }
            )

    # 4. Claim type comparison
    claim_type_diff = None
    b_ct = baseline_cm.get("claim_type")
    c_ct = current_cm.get("claim_type")
    if b_ct != c_ct:
        claim_type_diff = {"baseline": b_ct, "current": c_ct}

    # 5. Orientation comparison
    b_orient = baseline_cm.get("orientation")
    c_orient = current_cm.get("orientation")
    orientation_diff = b_orient != c_orient

    details = {
        "state_flips": state_flips,
        "mapping_diffs": mapping_diffs,
        "claim_type_diff": claim_type_diff,
        "orientation_diff": orientation_diff,
    }

    # Classification rules:
    # - Element state flip → llm_noise
    if state_flips:
        return ("llm_noise", "element_state_flip", details)

    # - Orientation differs but states match → pipeline_fail (mechanical bug)
    if orientation_diff and not state_flips:
        return ("pipeline_fail", "orientation_mismatch_with_same_states", details)

    # - Evidence mapping differs → llm_noise
    if mapping_diffs:
        return ("llm_noise", "evidence_mapping_diff", details)

    # - Claim type differs → llm_noise
    if claim_type_diff:
        return ("llm_noise", "claim_type_diff", details)

    return ("pass", "all_match", details)


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def load_run(run_dir: Path):
    """Load all slug artifacts from a run directory."""
    artifacts = {}
    for p in sorted(run_dir.glob("*.json")):
        if p.name.startswith("_"):
            continue
        with open(p) as f:
            data = json.load(f)
        slug = data.get("slug", p.stem)
        artifacts[slug] = data
    return artifacts


def load_summary(run_dir: Path):
    """Load run summary if it exists."""
    summary_path = run_dir / "_summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            return json.load(f)
    return {}


def compare(before_dir: Path, after_dir: Path):
    before = load_run(before_dir)
    after = load_run(after_dir)
    before_summary = load_summary(before_dir)
    after_summary = load_summary(after_dir)

    common_slugs = sorted(set(before) & set(after))
    if not common_slugs:
        print("ERROR: No matching slugs between runs.")
        sys.exit(1)

    # Determine fixture count for adaptive thresholds
    fixture_count = len(common_slugs)
    is_small_dataset = fixture_count < MIN_FIXTURES_FOR_HARD_GATE

    # Detect frozen replay via summary metadata
    is_frozen_evidence = after_summary.get("freeze_version", 0) >= 2
    is_frozen = bool(after_summary.get("freeze_from")) and not is_frozen_evidence

    # Warn on freeze_stage mismatch
    before_stage = before_summary.get("freeze_stage")
    after_stage = after_summary.get("freeze_stage")
    freeze_stage_mismatch = before_stage and after_stage and before_stage != after_stage
    if freeze_stage_mismatch:
        print(
            f"  WARNING: freeze_stage mismatch: before={before_stage}, after={after_stage}"
        )
        print(
            f"           Results may not be comparable — re-run baseline with current code."
        )

    # Check if hash data is available (enables two-gate system)
    has_hash_data = False

    total_claims = 0
    divergent_claims = 0
    all_jaccards = []
    rows = []
    divergence_details = []  # For markdown report

    # Gate 2 classification counters
    hard_fail_count = 0
    pipeline_fail_count = 0
    llm_noise_count = 0

    # Per-tag tracking
    tag_stats = {}  # tag -> {"claims": 0, "divergences": 0, "jaccards": []}

    for slug in common_slugs:
        b = before[slug]
        a = after[slug]
        tag = a.get("tag", b.get("tag", "untagged"))

        if tag not in tag_stats:
            tag_stats[tag] = {"claims": 0, "divergences": 0, "jaccards": []}

        # Skip errored runs
        if b.get("status") != "completed" or a.get("status") != "completed":
            rows.append(
                f"  {slug} [{tag}]: SKIPPED (status: {b.get('status')}/{a.get('status')})"
            )
            continue

        b_claim_maps = b.get("claim_maps", {})
        a_claim_maps = a.get("claim_maps", {})
        b_urls = b.get("evidence_urls", {})
        a_urls = a.get("evidence_urls", {})
        b_hashes = b.get("claim_map_input_hashes", {})
        a_hashes = a.get("claim_map_input_hashes", {})

        if b_hashes or a_hashes:
            has_hash_data = True

        claim_positions = sorted(set(b_claim_maps) | set(a_claim_maps))
        slug_divergences = 0

        for pos in claim_positions:
            total_claims += 1
            tag_stats[tag]["claims"] += 1

            b_cm = b_claim_maps.get(pos)
            a_cm = a_claim_maps.get(pos)

            status, reason, details = compare_claim_maps(b_cm, a_cm)

            if status != "pass":
                divergent_claims += 1
                slug_divergences += 1
                tag_stats[tag]["divergences"] += 1

                if status == "hard_fail":
                    hard_fail_count += 1
                elif status == "pipeline_fail":
                    pipeline_fail_count += 1
                else:
                    llm_noise_count += 1

                divergence_details.append(
                    {
                        "slug": slug,
                        "tag": tag,
                        "claim": pos,
                        "status": status,
                        "reason": reason,
                        "state_flips": details.get("state_flips", []),
                        "hash_before": (b_hashes.get(pos, "") or "")[:8],
                        "hash_after": (a_hashes.get(pos, "") or "")[:8],
                    }
                )

            bu = set(b_urls.get(pos, []))
            au = set(a_urls.get(pos, []))
            j = jaccard(bu, au)
            all_jaccards.append(j)
            tag_stats[tag]["jaccards"].append(j)

        divergence_indicator = (
            f" DIVERGENCES={slug_divergences}" if slug_divergences else ""
        )
        rows.append(
            f"  {slug} [{tag}]: {len(claim_positions)} claims{divergence_indicator}"
        )

    # --- Ledger comparison ---
    ledger_rows = []
    ledger_details = []  # For markdown

    for slug in common_slugs:
        bl = before[slug].get("evidence_ledger", {})
        al = after[slug].get("evidence_ledger", {})
        if not bl and not al:
            continue

        bs = bl.get("summary", {})
        as_ = al.get("summary", {})

        def delta(key):
            return (as_.get(key, 0) or 0) - (bs.get(key, 0) or 0)

        d_entered = delta("evidence_entered_pipeline")
        d_analyzer = delta("evidence_reached_analyzer")
        d_snippets = delta("snippet_fallbacks_at_analyzer")

        # Stage diffs
        stage_diffs = []
        for stage_name in [
            "url_dedup",
            "llm_scoring",
            "global_domain_cap",
            "credibility_filtering",
            "frozen_replay",
            "frozen_evidence_replay",
        ]:
            b_stage = bl.get("stages", {}).get(stage_name, {})
            a_stage = al.get("stages", {}).get(stage_name, {})
            b_rem = b_stage.get("removed", 0) or 0
            a_rem = a_stage.get("removed", 0) or 0
            if b_rem != a_rem:
                stage_diffs.append(f"{stage_name}: {b_rem}->{a_rem}")
            # Track frozen replay mismatches specifically
            if stage_name == "frozen_replay":
                b_mm = b_stage.get("mismatches", 0) or 0
                a_mm = a_stage.get("mismatches", 0) or 0
                if b_mm or a_mm:
                    stage_diffs.append(f"frozen_mismatches: {b_mm}/{a_mm}")

        parts = [
            f"entered:{d_entered:+d}",
            f"analyzer:{d_analyzer:+d}",
            f"snippets:{d_snippets:+d}",
        ]
        if stage_diffs:
            parts.append("stages=[" + ", ".join(stage_diffs) + "]")
        ledger_rows.append(f"  {slug}: {' | '.join(parts)}")
        ledger_details.append(
            {
                "slug": slug,
                "entered": d_entered,
                "analyzer": d_analyzer,
                "snippets": d_snippets,
                "stages": stage_diffs,
            }
        )

    # --- Fingerprint comparison ---
    b_fp = before_summary.get("fingerprint", {})
    a_fp = after_summary.get("fingerprint", {})
    fingerprint_diff = {}
    if b_fp and a_fp:
        if b_fp.get("git_commit") != a_fp.get("git_commit"):
            fingerprint_diff["git"] = (
                f"{b_fp.get('git_commit', '?')[:10]} -> {a_fp.get('git_commit', '?')[:10]}"
            )
        # Flag differences
        b_flags = b_fp.get("flags", {})
        a_flags = a_fp.get("flags", {})
        changed_flags = {
            k: f"{b_flags.get(k, 'unset')} -> {v}"
            for k, v in a_flags.items()
            if b_flags.get(k) != v
        }
        changed_flags.update(
            {k: f"{v} -> unset" for k, v in b_flags.items() if k not in a_flags}
        )
        if changed_flags:
            fingerprint_diff["flags"] = changed_flags

    # --- Metrics ---
    divergence_rate = divergent_claims / total_claims if total_claims else 0
    avg_jaccard = sum(all_jaccards) / len(all_jaccards) if all_jaccards else 1.0

    # --- Terminal Report ---
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("=" * 60)
    out("CLAIM MAP COMPARISON — RUN COMPARISON")
    out("=" * 60)
    out(f"Before: {before_dir.name}")
    out(f"After:  {after_dir.name}")
    out(f"Slugs compared: {fixture_count}")
    if is_small_dataset:
        out(
            f"NOTE: Small dataset ({fixture_count} < {MIN_FIXTURES_FOR_HARD_GATE}) — divergence rate is INFORMATIONAL"
        )
    out()

    if fingerprint_diff:
        out("Fingerprint changes:")
        for k, v in fingerprint_diff.items():
            if isinstance(v, dict):
                for fk, fv in v.items():
                    out(f"  {fk}: {fv}")
            else:
                out(f"  {k}: {v}")
        out()

    out("Per-slug:")
    for r in rows:
        out(r)
    out()

    out("Claim Maps:")
    out(f"  Total claims:    {total_claims}")
    out(f"  Divergences:     {divergent_claims}")
    out(f"  Divergence rate: {divergence_rate:.1%}")
    if divergent_claims > 0:
        out(f"  Hard fails:      {hard_fail_count} (element count mismatch)")
        out(f"  Pipeline fails:  {pipeline_fail_count} (orientation bug)")
        out(f"  LLM noise:       {llm_noise_count} (state/mapping/type changes)")
    out()

    # Per-tag breakdown
    if len(tag_stats) > 1:
        out("Per-tag:")
        for tag, stats in sorted(tag_stats.items()):
            tag_div_rate = (
                stats["divergences"] / stats["claims"] if stats["claims"] else 0
            )
            tag_jaccard = (
                sum(stats["jaccards"]) / len(stats["jaccards"])
                if stats["jaccards"]
                else 1.0
            )
            out(
                f"  {tag}: {stats['claims']} claims, {stats['divergences']} divergences ({tag_div_rate:.0%}), Jaccard={tag_jaccard:.3f}"
            )
        out()

    out("Evidence:")
    out(f"  Avg URL Jaccard: {avg_jaccard:.3f}")
    out()

    if ledger_rows:
        out("Ledger deltas:")
        for r in ledger_rows:
            out(r)
        out()

    # --- Two-Gate System ---
    # Gate 1: Evidence determinism (Jaccard)
    if is_frozen_evidence:
        jaccard_threshold = FROZEN_EVIDENCE_MIN_JACCARD_OVERALL
    elif is_frozen:
        jaccard_threshold = FROZEN_MIN_EVIDENCE_JACCARD
    else:
        jaccard_threshold = MIN_EVIDENCE_JACCARD

    gate1_passed = avg_jaccard >= jaccard_threshold

    # Gate 2: Claim Map stability — hard_fail and pipeline_fail must be 0
    gate2_passed = hard_fail_count == 0 and pipeline_fail_count == 0

    out("Guardrails:")
    if freeze_stage_mismatch:
        out(f"  [WARNING] freeze_stage mismatch: {before_stage} vs {after_stage}")
        out(
            f"            Results may not be comparable — re-run baseline with current code."
        )
    if is_frozen_evidence:
        out(f"  [FROZEN EVIDENCE REPLAY] Zero-network deterministic")
        if after_stage:
            out(
                f"  [FREEZE STAGE] {after_stage} (v{after_summary.get('freeze_version', '?')})"
            )
    elif is_frozen:
        out(f"  [FROZEN REPLAY] Search variance eliminated")

    # Gate 1 output
    gate1_status = "PASS" if gate1_passed else "FAIL"
    out(f"  Gate 1 — Evidence Determinism:")
    out(
        f"    [{gate1_status}] Avg URL Jaccard: {avg_jaccard:.3f} >= {jaccard_threshold}"
    )

    # Gate 2 output
    gate2_status = "PASS" if gate2_passed else "FAIL"
    out(f"  Gate 2 — Claim Map Stability:")
    out(
        f"    [{gate2_status}] Hard fails: {hard_fail_count}, Pipeline fails: {pipeline_fail_count} (must be 0)"
    )
    if llm_noise_count > 0:
        out(f"    [INFO] LLM noise divergences: {llm_noise_count} (not gated)")
    out()

    all_pass = gate1_passed and gate2_passed
    if all_pass:
        out("RESULT: ALL GATES PASSED")
    else:
        failed_gates = []
        if not gate1_passed:
            failed_gates.append("Gate 1 (Evidence)")
        if not gate2_passed:
            failed_gates.append("Gate 2 (Claim Map)")
        out(f"RESULT: FAILED — {', '.join(failed_gates)} — review before merging")

    # --- Markdown Report ---
    md = _build_markdown_report(
        before_dir,
        after_dir,
        fixture_count,
        is_small_dataset,
        fingerprint_diff,
        total_claims,
        divergent_claims,
        divergence_rate,
        avg_jaccard,
        divergence_details,
        tag_stats,
        ledger_details,
        gate1_passed,
        gate2_passed,
        all_pass,
        b_fp,
        a_fp,
        jaccard_threshold=jaccard_threshold,
        is_frozen=is_frozen,
        is_frozen_evidence=is_frozen_evidence,
        hard_fail_count=hard_fail_count,
        pipeline_fail_count=pipeline_fail_count,
        llm_noise_count=llm_noise_count,
        freeze_stage=after_stage,
        freeze_stage_mismatch=freeze_stage_mismatch,
    )
    report_path = after_dir / "_diff_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    out(f"Diff report: {report_path}")

    return 0 if all_pass else 1


def _build_markdown_report(
    before_dir,
    after_dir,
    fixture_count,
    is_small_dataset,
    fingerprint_diff,
    total_claims,
    divergent_claims,
    divergence_rate,
    avg_jaccard,
    divergence_details,
    tag_stats,
    ledger_details,
    gate1_passed,
    gate2_passed,
    all_pass,
    b_fp,
    a_fp,
    jaccard_threshold=MIN_EVIDENCE_JACCARD,
    is_frozen=False,
    is_frozen_evidence=False,
    hard_fail_count=0,
    pipeline_fail_count=0,
    llm_noise_count=0,
    freeze_stage=None,
    freeze_stage_mismatch=False,
):
    """Build PR-reviewable markdown diff report."""
    md = []
    md.append(f"# Run Comparison: {before_dir.name} vs {after_dir.name}\n")

    # Fingerprint
    if b_fp or a_fp:
        md.append("## Environment\n")
        md.append("| | Before | After |")
        md.append("|---|---|---|")
        b_git = b_fp.get("git_commit", "?")[:10]
        a_git = a_fp.get("git_commit", "?")[:10]
        b_dirty = " (dirty)" if b_fp.get("git_dirty") else ""
        a_dirty = " (dirty)" if a_fp.get("git_dirty") else ""
        md.append(f"| Git | `{b_git}{b_dirty}` | `{a_git}{a_dirty}` |")
        md.append("")

        if fingerprint_diff.get("flags"):
            md.append("**Changed flags:**\n")
            for k, v in fingerprint_diff["flags"].items():
                md.append(f"- `{k}`: {v}")
            md.append("")

    # Summary
    md.append("## Summary\n")
    result_label = "PASS" if all_pass else "FAIL"
    md.append(
        f"**Result: {result_label}** | {fixture_count} fixtures | {total_claims} claims\n"
    )

    if freeze_stage_mismatch:
        md.append(
            "> **WARNING:** freeze_stage mismatch — results may not be comparable.\n"
        )
    if is_frozen_evidence:
        stage_label = f" (`{freeze_stage}`)" if freeze_stage else ""
        md.append(
            f"> **Frozen Evidence Replay{stage_label}** — zero network, fully deterministic.\n"
        )
    elif is_frozen:
        md.append("> **Frozen URL Replay** — search variance eliminated.\n")

    # Gate results table
    md.append("| Gate | Check | Status |")
    md.append("|------|-------|--------|")
    md.append(
        f"| Gate 1: Evidence | Jaccard {avg_jaccard:.3f} >= {jaccard_threshold} | {'PASS' if gate1_passed else 'FAIL'} |"
    )
    md.append(
        f"| Gate 2: Claim Map | Hard fails: {hard_fail_count}, Pipeline fails: {pipeline_fail_count} | {'PASS' if gate2_passed else 'FAIL'} |"
    )
    if llm_noise_count > 0:
        md.append(f"| | LLM noise divergences: {llm_noise_count} | INFO |")
    md.append("")

    # Per-tag breakdown
    if len(tag_stats) > 1:
        md.append("## Per-Tag Breakdown\n")
        md.append("| Tag | Claims | Divergences | Divergence Rate | Avg Jaccard |")
        md.append("|-----|--------|-------------|-----------------|-------------|")
        for tag, stats in sorted(tag_stats.items()):
            tdr = stats["divergences"] / stats["claims"] if stats["claims"] else 0
            tj = (
                sum(stats["jaccards"]) / len(stats["jaccards"])
                if stats["jaccards"]
                else 1.0
            )
            md.append(
                f"| {tag} | {stats['claims']} | {stats['divergences']} | {tdr:.0%} | {tj:.3f} |"
            )
        md.append("")

    # Claim Map divergences detail
    if divergence_details:
        md.append("## Claim Map Divergences\n")
        md.append(
            "| Fixture | Tag | Claim | Status | Reason | Hash Before | Hash After | State Flips |"
        )
        md.append(
            "|---------|-----|-------|--------|--------|-------------|------------|-------------|"
        )
        for dd in divergence_details:
            flips_str = ""
            if dd["state_flips"]:
                flips_str = "; ".join(
                    f"{f['element_id']}: {f['baseline_state']}->{f['current_state']}"
                    for f in dd["state_flips"]
                )
            md.append(
                f"| {dd['slug']} | {dd['tag']} | {dd['claim']} "
                f"| {dd['status']} | {dd['reason']} "
                f"| {dd['hash_before']} | {dd['hash_after']} | {flips_str} |"
            )
        md.append("")

    # Ledger deltas
    if ledger_details:
        md.append("## Evidence Pipeline Deltas\n")
        md.append("| Fixture | Entered | Analyzer | Snippets | Stage Changes |")
        md.append("|---------|---------|----------|----------|---------------|")
        for ld in ledger_details:
            stages_str = ", ".join(ld["stages"]) if ld["stages"] else "--"
            md.append(
                f"| {ld['slug']} | {ld['entered']:+d} | {ld['analyzer']:+d} | {ld['snippets']:+d} | {stages_str} |"
            )
        md.append("")

    md.append("---\n*Generated by `compare_runs.py`*\n")
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Compare two golden dataset runs")
    parser.add_argument("before", help="Path to baseline run directory")
    parser.add_argument("after", help="Path to comparison run directory")
    args = parser.parse_args()

    before_dir = Path(args.before)
    after_dir = Path(args.after)

    if not before_dir.exists():
        print(f"ERROR: {before_dir} not found", file=sys.stderr)
        sys.exit(1)
    if not after_dir.exists():
        print(f"ERROR: {after_dir} not found", file=sys.stderr)
        sys.exit(1)

    sys.exit(compare(before_dir, after_dir))


if __name__ == "__main__":
    main()
