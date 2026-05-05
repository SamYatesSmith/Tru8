# Replay Bench Corpus

Frozen 5-claim regression corpus. Run `python scripts/replay_bench.py --all` before
every commit on Phase B / B5 / Phase C work. Catches regressions of the
"changed-stage-X-broke-stage-Y" class (e.g. NF-21, where Session B's Pydantic
conversion broke coverage recovery silently for 2 weeks).

## Coverage

| Claim ID | Mode | Tests |
|---|---|---|
| TRU-B4A3-C42D | article (3 claims) | B1a inject, B4 freshness inject, NF-11 Growth Plan exclusion, SC-11 `.co.uk` gap, NF-21 coverage recovery |
| TRU-82CF-2F81 | article (2 claims) | B1a LAW→Law, cap widening, Finance/UK routing |
| TRU-93DD-F4B7 | focused (1 claim) | NF-18 wired `prepare_query` path, NOAA CDO end-to-end |
| TRU-A3E8-3199 | focused (1 claim) | NF-07 hardening, GBIF species extraction |
| TRU-5647-FA4F | article (2 claims) | NF-11 baseline UK coverage, Climate routing, B4 (2022) |

## Schema — `input.json`

```json
{
  "claim_id": "TRU-XXXX-XXXX",
  "description": "One-line purpose",
  "tests": ["short list of what this claim regresses"],
  "input_type": "text",
  "content": "The exact claim text that was originally submitted",
  "url": null,
  "user_query": null,
  "entry_mode": "article" | "focused",
  "selected_positions": [0, 1, 2]
}
```

`selected_positions` is the user's claim selection (article mode only). For
focused mode the pipeline runs Phase 2 directly; `selected_positions: [0]` is
written for symmetry.

## Schema — `golden.json`

Three categories of assertion. All optional — omit a category to skip it.

```json
{
  "claim_id": "TRU-XXXX-XXXX",
  "captured_at": "2026-05-05T10:30:00Z",
  "captured_with": "git SHA short form",
  "captured_with_known_bugs": ["NF-21", "B4-inheritance-gap"],
  "notes": "Free text — what's expected, what's a known wart",

  "hard_invariants": {
    "classifier_inject": {
      "primary": "Finance",
      "secondaries_must_include": ["Politics"],
      "jurisdiction_to": "UK"
    },
    "freshness_inject_must_fire_on_claims": [0],
    "factchecks_min": 0,
    "factchecks_max": 3,
    "must_have_url_substrings": ["bbc.com/news/business-62920969"],
    "must_not_have_url_substrings": ["facebook.com", "kids.kiddle.co"],
    "expected_adapters_subset": ["GOV.UK Content API", "UK Parliament Hansard"]
  },

  "tolerant_counters": {
    "sources_included": {"value": 32, "tolerance": 3},
    "claims": {"value": 3, "tolerance": 0},
    "elements": {"value": 8, "tolerance": 2},
    "tier_primary": {"value": 11, "tolerance": 4}
  },

  "set_jaccard": {
    "url_ledger_flat": {
      "golden": ["https://...", "https://..."],
      "min_similarity": 0.6
    },
    "domain_set": {
      "golden": ["bbc.com", "gov.uk", "..."],
      "min_similarity": 0.7
    }
  }
}
```

### Why three categories

LLM and live-search non-determinism means *exact* equality on full output is
useless (everything looks red even when nothing's wrong). The bench discriminates:

- **Hard invariants** — boolean/structural signals that should *not* drift
  between runs unless code changed (a classifier inject either fired or it
  didn't; a URL is either in the ledger or it isn't). Exact match required.
- **Tolerant counters** — quantitative signals that *do* drift slightly between
  runs because of LLM noise and external API variation. Compared with explicit
  `±tolerance`. Tolerances should be set tight enough to catch real
  regressions, loose enough to absorb day-to-day variation. ~2-4 typically.
- **Set Jaccard** — URL ledgers and domain sets that drift more substantially
  (Serper returns different results day to day). Compared by overlap ratio
  with a floor (0.6-0.8). Combined with `must_have_url_substrings` for the
  specific known-good URLs that *must* survive any drift.

## Capturing or updating goldens

```bash
# Capture initial golden (or update after a deliberate behaviour change)
python scripts/replay_bench.py --claim TRU-B4A3-C42D --update-golden

# Review the diff before committing
git diff backend/tests/replay_corpus/TRU-B4A3-C42D/golden.json

# Commit the golden update IN THE SAME COMMIT as the code change that caused it
git add backend/tests/replay_corpus/TRU-B4A3-C42D/golden.json backend/app/...
git commit -m "..."
```

When goldens change in a fix commit, the diff is the *evidence* that the fix
did what was intended. Reviewing this diff is the regression-prevention
discipline that compensates for trunk-based-with-no-PR.

## Running the bench

```bash
# Full bench — all 5 claims
python scripts/replay_bench.py --all

# Single claim
python scripts/replay_bench.py --claim TRU-B4A3-C42D

# Fast mode — skip retrieve, replay from cached pool (deterministic)
# Useful when iterating on classify / score / map
python scripts/replay_bench.py --all --fast

# Verbose — print full captured observation alongside diff
python scripts/replay_bench.py --claim TRU-B4A3-C42D --verbose
```

## What this bench does NOT catch

- New failure modes from claim shapes outside the corpus → still need
  iterative live test.
- LLM model upgrades → goldens invalidated, expected, update them.
- External API outages → bench fails for the wrong reason; document in the
  diff and don't commit.
- Bugs in the bench itself → reviewed at build time only.
