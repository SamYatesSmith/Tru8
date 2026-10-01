# Echo link detector: measured precision (2026-10-01)

**Question:** how often is a pair that `corroboration.find_corroborating_sources` links (primary A ↔ reporting/commentary B) a real relay? Free: local DB pools, no model calls. Labels were blind (fresh agent, excerpts + URLs only, no code).

## Data
- 317 distinct claims (latest per claim text) from the local DB, all tiered. The detector links 741 primary↔derivative pairs in 137 pools; 582 sit in a derivation chain (the echo gate's input). Rules: 299 by text similarity (≥0.35, SequenceMatcher on 500 chars), 442 by fact overlap (≥0.3 Jaccard).
- Fact-rule links are weak by construction: 177 of 442 rest on ONE shared token ("1", "2020", "31"); 116 share only years.
- Echo gate firings in stored claim maps: 65 claims, 195 refs scoped to context (21 distinct claims after dedup).

## Results
| Sample | relay | independent | unclear | precision |
|---|---|---|---|---|
| A: 80 chain pairs (40 text-rule, 40 fact-rule, ≤2 per pool, 44 pools) | 19 | 61 | 0 | **24%** (15% if the labeller's 7 well-known-fact relays are excluded) |
| B: 41 pairs the echo gate actually scoped (21 pools) | 12 | 26 | 3 | **32%** of decided |

By rule (A): text 7/40, facts 12/40. **The gate removes about two independent sources for every copy it removes.** Invariant #7 is not breached in a direction (the gate is symmetric), but invariant #5's spirit is: independent support and challenge are hidden as "echo".

## Can a mechanical threshold fix it?
"Strong" facts = shared tokens excluding bare years and single digits.

| Rule | A: relay / independent | B: relay / independent |
|---|---|---|
| ≥2 strong facts | 5 / 6 (recall 5/19) | 8 / 4 (recall 8/12) |
| ≥3 strong facts | 3 / 4 (recall 3/19) | 6 / 0 (recall 6/12) |
| adding text sim ≥0.6 | no change | no change |

No threshold gets both: ≥3 is clean on B but 3/7 on A. Text similarity carries no signal at any cut seen.

## Options (founder decision)
1. **Echo gate off** (`ENABLE_ECHO_SCOPE_GATE=False`) until a better link exists. Restores the hidden independent sources. Copies count twice again (the S4 status quo before 17 Aug).
2. **Tighten to ≥3 strong shared facts.** Cheap, free to test; precision unproven on A (small n), recall ~half.
3. **Model-judged link:** keep the cheap detector as a candidate filter, and confirm each scoped pair with one model call (same pattern as the relationship review, about 1p per check). Needs design + held-out eval (difficulty 3).

The derivation-chain NOTE (grey "echo" sourcing note) reads the same chains and inherits the same error.

Files: `audit/echo_precision/` (extract script, blind inputs, keys, labels).
