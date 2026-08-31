# Replay Bench Corpus

> ## ⚠️ A clean `--all` run reports **1 fail**, and that is EXPECTED (2026-07-30)
>
> **`TRU-82CF-2F81` is KNOWN-FLAKY and accepted as such (founder call).** The gate is
> the other **8** claims. It reports `cassette_drift` (~12–20 misses, all ordinary
> evidence page fetches) and **cannot be re-golded**: replay has no network latency, so
> the pipeline gets further through its fetch queue inside `CLAIM_TIMEOUT=45s` than any
> live run does, and requests pages the recording never reached. The request set depends
> on wall-clock timing rather than on the cassette, so re-recording never converges — it
> was tried, and misses went 9 → 8 → 12 across passes.
>
> **Do NOT "fix" this by making missed evidence fetches non-fatal.** That would weaken the
> drift guard across the whole corpus to buy a green tick. Its golden is still the
> 2026-07-21 `fdf3509` capture and is **not** comparable to post-Phase-2 behaviour.
>
> So: **`121 ok / 5 warn / 11 fail / 5 unexercised` is the current PASS state**
> (2026-08-28 re-record: the `ENABLE_FACTCHECK_SIGNAL` flip changed the classifier
> prompt, re-keying EVERY cassette; whole corpus re-recorded and replay-verified
> same day). Every fail is attributed, none is an unexplained regression:
> - **3 × cassette_drift — the timing-flaky set is now THREE claims and its
>   membership WANDERS between replay passes:** 82CF (19 misses, the original),
>   B4A3 (10–11 misses, consistent across 3 passes this recording), 5647
>   (0 misses in one pass, 43 in another — intermittent). All carry the
>   documented signature (ordinary evidence fetches; replay has no network
>   latency so it outruns the recording's fetch queue). Their goldens were NOT
>   overwritten (`--update-golden` skips drifted claims). Do not chase them.
> - **2 × 018F recital pins + 1 × 0005 `gianlucabenigno` must-have — the KEPT
>   DEBT, failing visibly by design** (pins at 2026-08-17 capture values; pay by
>   re-recording until the pool carries the traps — see each golden's notes).
> - **5 × thin-pool v3 metrics** (`factual_weight_share` 018F/93DD/A3E8,
>   `unique_domains` 93DD, `top_domain_share` 0003) — record-time pool drift,
>   same class as the accepted 2026-08-11/08-27 fails.
> History: 135/2/1 → 158/2/1 → RETIRED 2026-08-11 → 143/13/5 (2026-08-13; true
> post-re-pin state 144/13/4) → 166/14/4 (018F joined) → 171/10/3 (Phase B; 5647
> re-recorded — the factual floor sends thin-support elements to recovery, which
> issues queries old recordings never made, attributed by matched-pair replay) →
> 175/10/2 (2026-08-17) → 178/5/9/5 (2026-08-27 model-migration re-record) →
> 121/5/11/5 (2026-08-28; the ok-count drop is the flaky set zeroing three
> claims' assertions in the scoring pass, not lost coverage — a pass where they
> replay clean scores higher). Anything worse is a real regression.
> `audit/OPEN_WORK.md` item 7.

## UNEXERCISED — a guard that was never given the chance (2026-08-27)

A must-fire gate assertion (`scope_gates_must_fire`,
`temporal_scope_must_fire_on_periods`) can only mean *"the gate broke"* if the
pool actually contained something the gate could fire on. Live pools churn ~62%
between identical runs, so a draw routinely arrives without the trap — and a
check reporting that as FAILED cannot be told apart from a real break. That is
how a red bench stops being read.

Goldens may therefore declare, per gate, the domains whose presence is the
precondition for firing:

```json
"hard_invariants": {
  "must_fire_preconditions": {"interested_party": ["whitehouse.gov"]}
}
```

| precondition | gate fired | verdict |
|---|---|---|
| absent  | no  | **UNEXERCISED** — not a failure, and **not a pass** |
| present | no  | **FAILURE** — the trap was there and nothing caught it |
| either  | yes | OK |
| *not declared* | no | **FAILURE** — silence never softens a guard |

`UNEXERCISED` is counted and printed separately, never folded into `ok`, and
never changes the exit code. Its counters (`*_scoped_refs` / `*_scoped_elements`)
follow their gate.

⚠️ **The precondition reads the FINAL POOL (`domain_set`), never
`url_ledger_flat`** — and this distinction is load-bearing. On the 2026-08-27
recording of `TRU-018F-44AA`, whitehouse.gov *was* fetched (a National Security
Strategy PDF) but was dropped before mapping, so the gate never saw it. Reading
the URL ledger calls that trap "present" and reports a hard failure for a gate
that was given nothing. Pinned by
`tests/unit/replay_bench/test_unexercised_gates.py`.

⚠️ **UNEXERCISED is not evidence the gate works.** The deterministic guards are
`test_assertion_evidence_wiring.py` (recital + interested-party) and
`test_temporal_scope_wiring.py` (F1), which run the gates through the real
mapping parser on fixed evidence. The bench anchor only adds "does this also
happen on a live pool".

**Frozen 9-claim regression corpus** (it was 5 when this file was written; the C1A0
series was added later). Run `python scripts/replay_bench.py --all` before every
pipeline-quality commit. Catches regressions of the
"changed-stage-X-broke-stage-Y" class (e.g. NF-21, where Session B's Pydantic
conversion broke coverage recovery silently for 2 weeks).

⚠️ **The bench runs against the WORKING TREE.** Any uncommitted prompt change makes
every claim fail on `cassette_drift` — request signatures are cassette keys — so an
in-progress prompt edit must be taken out of the tree before the bench can measure
anything else. This cost a full 11-minute run to notice on 2026-08-06.

## Coverage

| Claim ID | Mode | Tests |
|---|---|---|
| TRU-B4A3-C42D | article (3 claims) | B1a inject, B4 freshness inject, NF-11 Growth Plan exclusion, SC-11 `.co.uk` gap, NF-21 coverage recovery |
| TRU-82CF-2F81 | article (2 claims) | B1a LAW→Law, cap widening, Finance/UK routing |
| TRU-93DD-F4B7 | focused (1 claim) | NF-18 wired `prepare_query` path, NOAA CDO end-to-end, DATE-driven date window |
| TRU-A3E8-3199 | focused (1 claim) | NF-07 hardening, GBIF species extraction, biodiversity routing |
| TRU-5647-FA4F | article (2 claims) | NF-11 baseline UK coverage, Climate routing, B4 (2022) |
| TRU-C1A0-0001 | article (1 claim) | ONS routing + yield, Finance/UK jurisdiction, `ONS_DATASET_MAPPING` concept match |
| TRU-C1A0-0003 | focused (1 claim) | PubMed routing + yield, Health domain, Semantic Scholar keyless 429 |
| TRU-C1A0-0004 | article (2 claims) | GovInfo routing + yield (Politics/US), GET→POST 400 fix, US jurisdiction |
| TRU-C1A0-0005 | focused (1 claim) | **F1 temporal scope gate fires** — the only month-pinned claim, so the only one that can exercise the gate at all. See the caveat below. |
| TRU-018F-44AA | focused (1 claim) | **Recital gate fires** (2 elements / 3 refs, tolerance 0, mutation-checked) — the 2026-08-13 incident claim. ⚠️ Interested-party does NOT fire in this recording (no whitehouse.gov in its pool — run-variance); its must-fire assertion is owed at the first re-record whose pool carries the claimant's organ. |

### TRU-C1A0-0005 guards the GATE, not the 2026-08-06 extension

Added because F1 shipped, passed the bench at 135/2/1 and had fired **zero times** — a
corpus with no month-pinned claim cannot see the gate. Two things were needed beyond
the fixture: `capture.py` observes `[TEMPORAL SCOPE]` (`RE_TEMPORAL_SCOPE`), and
`comparator.py` gained the `temporal_scope_must_fire_on_periods` hard invariant.
Without the matcher the fixture would still have gone green while the gate died.

**Verified by mutation, not assumed:** the claim fails under
`ENABLE_TEMPORAL_SCOPE_GATE=False`, so it pins real behaviour — but it still passes
with the two-digit year parsing disabled, with the month/year separator reverted, and
with `ENABLE_TEMPORAL_PUBLICATION_RESOLUTION=False`. Its firing comes from the
**original** stated-period rule. A second fixture whose off-period evidence carries a
two-digit year (`September-25`) or a bare month is owed to guard the extension.

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

Historically, LLM and live-search non-determinism meant *exact* equality on full
output was useless (everything looked red even when nothing was wrong). With
cassette replay that non-determinism is now frozen, so tighter comparison is
viable — but the three categories are retained: they still document intent
(what *must* hold vs what may vary) and they keep `--live`/`--record` runs
interpretable. The bench discriminates:

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

## Deterministic replay (cassettes)

Each claim has a `cassette.json.gz` — a gzipped record of **every** HTTP
interaction the pipeline made (web search, all API adapters, Gemini, OpenAI;
they all ride `httpx`, so one mechanism captures the lot). By default the bench
**replays** from the cassette, so no network is touched and the run is
byte-for-byte reproducible. This removes the provider-side drift (Serper/Brave
re-ranking + cache rotation) and LLM variance that previously swamped the
signal: a red result now means *your code changed behaviour*, not that the
internet shifted under you.

```bash
python scripts/replay_bench.py --all              # default: deterministic replay
python scripts/replay_bench.py --all --record     # live + capture new cassettes
python scripts/replay_bench.py --all --live       # live, no cassette (legacy/drift)
```

Cassettes scrub credentials (secret query params + auth headers) before they
touch disk, and exclude them from the match key, so a rotated API key never
invalidates a cassette and no secret is ever committed.

**When to re-record:** after a deliberate pipeline change that alters the
requests made (new adapter, changed prompt, different query shaping), or to
refresh against the live world. A replay **miss** (an unrecorded request) is a
hard error naming the request — that's the signal the pipeline's behaviour
moved and the cassette needs a `--record`.

**Caveat — wall-clock in prompts:** if a prompt/query embeds today's date, its
body hash shifts daily and will miss on replay. Re-record, or normalise the date
in `cassette._canonical_signature`.

## Running the bench

```bash
# Full bench — all 5 claims (deterministic replay)
python scripts/replay_bench.py --all

# Single claim
python scripts/replay_bench.py --claim TRU-B4A3-C42D

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
