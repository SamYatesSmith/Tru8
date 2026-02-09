#!/usr/bin/env python3
"""
Compare two golden dataset runs and output a pass/fail report + markdown diff.

Usage:
    python compare_runs.py runs/20260206T120000_baseline-v1 runs/20260206T130000_after-PR-1A

Outputs:
    - Terminal: verdict flip rate, confidence deltas, evidence URL Jaccard, ledger diffs
    - File: <after_dir>/_diff_report.md (PR-reviewable markdown)
    - Pass/Fail against two-gate system (evidence determinism + verdict stability)
"""
import argparse
import json
import sys
from pathlib import Path


# --- Gate 1: Evidence determinism (Jaccard thresholds) ---
MIN_EVIDENCE_JACCARD = 0.80         # 80% URL overlap (normal runs)
MIN_FIXTURES_FOR_HARD_GATE = 12

# Frozen URL replay (tighter — search variance eliminated)
FROZEN_MIN_EVIDENCE_JACCARD = 0.90

# Frozen EVIDENCE replay (strictest — zero network)
FROZEN_EVIDENCE_MIN_JACCARD_OVERALL = 0.90
FROZEN_EVIDENCE_MIN_JACCARD_CORE = 0.95

# --- Gate 2: Verdict stability (classification-based) ---
# No numeric threshold — uses classify_flip() to categorize each flip:
#   hard_fail:     supported <-> contradicted (directional reversal, always fails)
#   pipeline_fail: uncertain <-> {supported,contradicted} with DIFFERENT judge input hash
#   llm_noise:     uncertain <-> {supported,contradicted} with SAME hash (LLM nondeterminism)

# Legacy thresholds kept for non-frozen runs (no hash data available)
MAX_VERDICT_FLIP_RATE = 0.05        # 5% for mature datasets (>= 12 fixtures)
MAX_VERDICT_FLIP_RATE_SMALL = 0.15  # 15% for small datasets (< 12 fixtures)
FROZEN_MAX_VERDICT_FLIP_RATE = 0.05


def classify_flip(before_verdict, after_verdict, before_hash, after_hash):
    """Classify a verdict flip into hard_fail, pipeline_fail, or llm_noise.

    Returns (flip_type, reason) tuple.
    """
    # Directional reversal: supported <-> contradicted is always a hard fail
    if {before_verdict, after_verdict} == {"supported", "contradicted"}:
        return ("hard_fail", "directional reversal")

    # Same judge input hash = LLM nondeterminism (not a pipeline bug)
    if before_hash and after_hash and before_hash == after_hash:
        return ("llm_noise", f"same judge input ({before_hash[:8]})")

    # Different hash = pipeline changed what went into the judge
    if before_hash and after_hash and before_hash != after_hash:
        return ("pipeline_fail", f"hash {before_hash[:8]}->{after_hash[:8]}")

    # No hash data (legacy runs) — assume LLM noise
    return ("llm_noise", "no hash data (legacy)")


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

    # Warn on freeze_stage mismatch (e.g. pre_weighting vs judge_input_evidence)
    before_stage = before_summary.get("freeze_stage")
    after_stage = after_summary.get("freeze_stage")
    freeze_stage_mismatch = (
        before_stage and after_stage and before_stage != after_stage
    )
    if freeze_stage_mismatch:
        print(f"  WARNING: freeze_stage mismatch: before={before_stage}, after={after_stage}")
        print(f"           Results may not be comparable — re-run baseline with current code.")

    # Check if hash data is available (enables two-gate system)
    has_hash_data = False

    total_claims = 0
    flipped_claims = 0
    all_jaccards = []
    confidence_deltas = []
    rows = []
    flip_details = []  # For markdown report

    # Gate 2 classification counters
    hard_fail_count = 0
    pipeline_fail_count = 0
    llm_noise_count = 0

    # Per-tag tracking
    tag_stats = {}  # tag -> {"claims": 0, "flips": 0, "jaccards": []}

    for slug in common_slugs:
        b = before[slug]
        a = after[slug]
        tag = a.get("tag", b.get("tag", "untagged"))

        if tag not in tag_stats:
            tag_stats[tag] = {"claims": 0, "flips": 0, "jaccards": []}

        # Skip errored runs
        if b.get("status") != "completed" or a.get("status") != "completed":
            rows.append(f"  {slug} [{tag}]: SKIPPED (status: {b.get('status')}/{a.get('status')})")
            continue

        b_verdicts = b.get("verdicts", {})
        a_verdicts = a.get("verdicts", {})
        b_confs = b.get("confidences", {})
        a_confs = a.get("confidences", {})
        b_urls = b.get("evidence_urls", {})
        a_urls = a.get("evidence_urls", {})
        b_hashes = b.get("judge_input_hashes", {})
        a_hashes = a.get("judge_input_hashes", {})

        if b_hashes or a_hashes:
            has_hash_data = True

        claim_positions = sorted(set(b_verdicts) | set(a_verdicts))
        slug_flips = 0

        for pos in claim_positions:
            total_claims += 1
            tag_stats[tag]["claims"] += 1
            bv = b_verdicts.get(pos, "?")
            av = a_verdicts.get(pos, "?")

            if bv != av:
                flipped_claims += 1
                slug_flips += 1
                tag_stats[tag]["flips"] += 1
                bc_val = b_confs.get(pos, 0) or 0
                ac_val = a_confs.get(pos, 0) or 0

                # Classify the flip using judge input hashes
                b_hash = b_hashes.get(pos, "")
                a_hash = a_hashes.get(pos, "")
                flip_type, flip_reason = classify_flip(bv, av, b_hash, a_hash)

                if flip_type == "hard_fail":
                    hard_fail_count += 1
                elif flip_type == "pipeline_fail":
                    pipeline_fail_count += 1
                else:
                    llm_noise_count += 1

                flip_details.append({
                    "slug": slug, "tag": tag, "claim": pos,
                    "before": bv, "after": av,
                    "conf_before": bc_val, "conf_after": ac_val,
                    "flip_type": flip_type, "flip_reason": flip_reason,
                    "hash_before": b_hash[:8] if b_hash else "",
                    "hash_after": a_hash[:8] if a_hash else "",
                })

            bc = b_confs.get(pos, 0) or 0
            ac = a_confs.get(pos, 0) or 0
            confidence_deltas.append(ac - bc)

            bu = set(b_urls.get(pos, []))
            au = set(a_urls.get(pos, []))
            j = jaccard(bu, au)
            all_jaccards.append(j)
            tag_stats[tag]["jaccards"].append(j)

        flip_indicator = f" FLIPS={slug_flips}" if slug_flips else ""
        rows.append(f"  {slug} [{tag}]: {len(claim_positions)} claims{flip_indicator}")

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
        d_judge = delta("evidence_reached_judge")
        d_snippets = delta("snippet_fallbacks_at_judge")

        # Stage diffs
        stage_diffs = []
        for stage_name in ["url_dedup", "llm_scoring", "global_domain_cap", "credibility_filtering", "frozen_replay", "frozen_evidence_replay"]:
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

        parts = [f"entered:{d_entered:+d}", f"judge:{d_judge:+d}", f"snippets:{d_snippets:+d}"]
        if stage_diffs:
            parts.append("stages=[" + ", ".join(stage_diffs) + "]")
        ledger_rows.append(f"  {slug}: {' | '.join(parts)}")
        ledger_details.append({"slug": slug, "entered": d_entered, "judge": d_judge,
                               "snippets": d_snippets, "stages": stage_diffs})

    # --- Fingerprint comparison ---
    b_fp = before_summary.get("fingerprint", {})
    a_fp = after_summary.get("fingerprint", {})
    fingerprint_diff = {}
    if b_fp and a_fp:
        if b_fp.get("git_commit") != a_fp.get("git_commit"):
            fingerprint_diff["git"] = f"{b_fp.get('git_commit', '?')[:10]} -> {a_fp.get('git_commit', '?')[:10]}"
        # Flag differences
        b_flags = b_fp.get("flags", {})
        a_flags = a_fp.get("flags", {})
        changed_flags = {k: f"{b_flags.get(k, 'unset')} -> {v}" for k, v in a_flags.items() if b_flags.get(k) != v}
        changed_flags.update({k: f"{v} -> unset" for k, v in b_flags.items() if k not in a_flags})
        if changed_flags:
            fingerprint_diff["flags"] = changed_flags

    # --- Metrics ---
    flip_rate = flipped_claims / total_claims if total_claims else 0
    avg_jaccard = sum(all_jaccards) / len(all_jaccards) if all_jaccards else 1.0
    avg_conf_delta = sum(confidence_deltas) / len(confidence_deltas) if confidence_deltas else 0

    # --- Terminal Report ---
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("=" * 60)
    out("EVIDENCE LOSS LEDGER — RUN COMPARISON")
    out("=" * 60)
    out(f"Before: {before_dir.name}")
    out(f"After:  {after_dir.name}")
    out(f"Slugs compared: {fixture_count}")
    if is_small_dataset:
        out(f"NOTE: Small dataset ({fixture_count} < {MIN_FIXTURES_FOR_HARD_GATE}) — flip-rate is INFORMATIONAL")
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

    out("Verdicts:")
    out(f"  Total claims:    {total_claims}")
    out(f"  Flipped:         {flipped_claims}")
    out(f"  Flip rate:       {flip_rate:.1%}")
    if has_hash_data and flipped_claims > 0:
        out(f"  Hard fails:      {hard_fail_count} (directional reversals)")
        out(f"  Pipeline fails:  {pipeline_fail_count} (different judge input)")
        out(f"  LLM noise:       {llm_noise_count} (same judge input)")
    out()

    # Per-tag breakdown
    if len(tag_stats) > 1:
        out("Per-tag:")
        for tag, stats in sorted(tag_stats.items()):
            tag_flip_rate = stats["flips"] / stats["claims"] if stats["claims"] else 0
            tag_jaccard = sum(stats["jaccards"]) / len(stats["jaccards"]) if stats["jaccards"] else 1.0
            out(f"  {tag}: {stats['claims']} claims, {stats['flips']} flips ({tag_flip_rate:.0%}), Jaccard={tag_jaccard:.3f}")
        out()

    out("Evidence:")
    out(f"  Avg URL Jaccard: {avg_jaccard:.3f}")
    out(f"  Avg conf delta:  {avg_conf_delta:+.1f}")
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

    # Gate 2: Verdict stability
    use_two_gate = has_hash_data and (is_frozen or is_frozen_evidence)

    if use_two_gate:
        # Two-gate mode: classify flips, only hard_fail and pipeline_fail block
        gate2_passed = hard_fail_count == 0 and pipeline_fail_count == 0
    else:
        # Legacy mode: use flip rate thresholds
        if is_frozen_evidence:
            flip_threshold = 0.0
        elif is_frozen:
            flip_threshold = FROZEN_MAX_VERDICT_FLIP_RATE
        elif is_small_dataset:
            flip_threshold = MAX_VERDICT_FLIP_RATE_SMALL
        else:
            flip_threshold = MAX_VERDICT_FLIP_RATE
        gate2_passed = flip_rate <= flip_threshold

    out("Guardrails:")
    if freeze_stage_mismatch:
        out(f"  [WARNING] freeze_stage mismatch: {before_stage} vs {after_stage}")
        out(f"            Results may not be comparable — re-run baseline with current code.")
    if is_frozen_evidence:
        out(f"  [FROZEN EVIDENCE REPLAY] Zero-network deterministic")
        if after_stage:
            out(f"  [FREEZE STAGE] {after_stage} (v{after_summary.get('freeze_version', '?')})")
    elif is_frozen:
        out(f"  [FROZEN REPLAY] Search variance eliminated")

    # Gate 1 output
    gate1_status = "PASS" if gate1_passed else "FAIL"
    out(f"  Gate 1 — Evidence Determinism:")
    out(f"    [{gate1_status}] Avg URL Jaccard: {avg_jaccard:.3f} >= {jaccard_threshold}")

    # Gate 2 output
    out(f"  Gate 2 — Verdict Stability:")
    if use_two_gate:
        gate2_status = "PASS" if gate2_passed else "FAIL"
        out(f"    [{gate2_status}] Hard fails: {hard_fail_count}, Pipeline fails: {pipeline_fail_count} (must be 0)")
        if llm_noise_count > 0:
            out(f"    [INFO] LLM noise flips: {llm_noise_count} (not gated)")
    elif is_small_dataset and not is_frozen and not is_frozen_evidence:
        out(f"    [INFO] Verdict flip rate: {flip_rate:.1%} (threshold {flip_threshold:.0%}, informational until {MIN_FIXTURES_FOR_HARD_GATE}+ fixtures)")
        gate2_passed = True  # Informational only
    else:
        gate2_status = "PASS" if gate2_passed else "FAIL"
        out(f"    [{gate2_status}] Verdict flip rate: {flip_rate:.1%} <= {flip_threshold:.0%}")
    out()

    all_pass = gate1_passed and gate2_passed
    if all_pass:
        out("RESULT: ALL GATES PASSED")
    else:
        failed_gates = []
        if not gate1_passed:
            failed_gates.append("Gate 1 (Evidence)")
        if not gate2_passed:
            failed_gates.append("Gate 2 (Verdict)")
        out(f"RESULT: FAILED — {', '.join(failed_gates)} — review before merging")

    # --- Markdown Report ---
    md = _build_markdown_report(
        before_dir, after_dir, fixture_count, is_small_dataset,
        fingerprint_diff, total_claims, flipped_claims, flip_rate,
        avg_jaccard, avg_conf_delta, flip_details, tag_stats,
        ledger_details, gate1_passed, gate2_passed, all_pass,
        b_fp, a_fp, jaccard_threshold=jaccard_threshold, is_frozen=is_frozen,
        is_frozen_evidence=is_frozen_evidence, use_two_gate=use_two_gate,
        hard_fail_count=hard_fail_count, pipeline_fail_count=pipeline_fail_count,
        llm_noise_count=llm_noise_count,
        freeze_stage=after_stage, freeze_stage_mismatch=freeze_stage_mismatch,
    )
    report_path = after_dir / "_diff_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    out(f"Diff report: {report_path}")

    return 0 if all_pass else 1


def _build_markdown_report(
    before_dir, after_dir, fixture_count, is_small_dataset,
    fingerprint_diff, total_claims, flipped_claims, flip_rate,
    avg_jaccard, avg_conf_delta, flip_details, tag_stats,
    ledger_details, gate1_passed, gate2_passed, all_pass,
    b_fp, a_fp, jaccard_threshold=MIN_EVIDENCE_JACCARD, is_frozen=False,
    is_frozen_evidence=False, use_two_gate=False,
    hard_fail_count=0, pipeline_fail_count=0, llm_noise_count=0,
    freeze_stage=None, freeze_stage_mismatch=False,
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
    md.append(f"**Result: {result_label}** | {fixture_count} fixtures | {total_claims} claims\n")

    if freeze_stage_mismatch:
        md.append("> **WARNING:** freeze_stage mismatch — results may not be comparable.\n")
    if is_frozen_evidence:
        stage_label = f" (`{freeze_stage}`)" if freeze_stage else ""
        md.append(f"> **Frozen Evidence Replay{stage_label}** — zero network, fully deterministic.\n")
    elif is_frozen:
        md.append("> **Frozen URL Replay** — search variance eliminated.\n")

    # Gate results table
    md.append("| Gate | Check | Status |")
    md.append("|------|-------|--------|")
    md.append(f"| Gate 1: Evidence | Jaccard {avg_jaccard:.3f} >= {jaccard_threshold} | {'PASS' if gate1_passed else 'FAIL'} |")
    if use_two_gate:
        md.append(f"| Gate 2: Verdict | Hard fails: {hard_fail_count}, Pipeline fails: {pipeline_fail_count} | {'PASS' if gate2_passed else 'FAIL'} |")
        if llm_noise_count > 0:
            md.append(f"| | LLM noise flips: {llm_noise_count} | INFO |")
    else:
        md.append(f"| Gate 2: Verdict | Flip rate: {flip_rate:.1%} | {'PASS' if gate2_passed else 'FAIL'} |")
    md.append(f"| | Avg confidence delta: {avg_conf_delta:+.1f} | -- |")
    md.append("")

    # Per-tag breakdown
    if len(tag_stats) > 1:
        md.append("## Per-Tag Breakdown\n")
        md.append("| Tag | Claims | Flips | Flip Rate | Avg Jaccard |")
        md.append("|-----|--------|-------|-----------|-------------|")
        for tag, stats in sorted(tag_stats.items()):
            tfr = stats["flips"] / stats["claims"] if stats["claims"] else 0
            tj = sum(stats["jaccards"]) / len(stats["jaccards"]) if stats["jaccards"] else 1.0
            md.append(f"| {tag} | {stats['claims']} | {stats['flips']} | {tfr:.0%} | {tj:.3f} |")
        md.append("")

    # Verdict flips detail
    if flip_details:
        md.append("## Verdict Flips\n")
        if use_two_gate:
            md.append("| Fixture | Tag | Claim | Before | After | Type | Hash Before | Hash After | Reason |")
            md.append("|---------|-----|-------|--------|-------|------|-------------|------------|--------|")
            for fd in flip_details:
                md.append(
                    f"| {fd['slug']} | {fd['tag']} | {fd['claim']} "
                    f"| {fd['before']} | {fd['after']} | {fd['flip_type']} "
                    f"| {fd['hash_before']} | {fd['hash_after']} | {fd['flip_reason']} |"
                )
        else:
            md.append("| Fixture | Tag | Claim | Before | After | Conf Before | Conf After |")
            md.append("|---------|-----|-------|--------|-------|-------------|------------|")
            for fd in flip_details:
                md.append(f"| {fd['slug']} | {fd['tag']} | {fd['claim']} | {fd['before']} | {fd['after']} | {fd['conf_before']} | {fd['conf_after']} |")
        md.append("")

    # Ledger deltas
    if ledger_details:
        md.append("## Evidence Pipeline Deltas\n")
        md.append("| Fixture | Entered | Judge | Snippets | Stage Changes |")
        md.append("|---------|---------|-------|----------|---------------|")
        for ld in ledger_details:
            stages_str = ", ".join(ld["stages"]) if ld["stages"] else "--"
            md.append(f"| {ld['slug']} | {ld['entered']:+d} | {ld['judge']:+d} | {ld['snippets']:+d} | {stages_str} |")
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
