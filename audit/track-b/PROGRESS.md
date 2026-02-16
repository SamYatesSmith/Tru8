# Track B Progress — Claim Map System

**Started:** 2026-02-12
**Baseline:** Track A complete at commit `041b55f` (~2,100 lines removed)
**Canonical contract:** `audit/track-b/2026-02-12_claim-map-contract.md`
**Codebase analysis:** `audit/track-b/2026-02-12_track-b-deep-dive.md`

---

## Strategy: Direct Replacement

Pipeline is offline during Track B. No feature gate, no dual paths, no fallback.

1. **Add new infrastructure** (B01–B02) — types, schema, new modules
2. **Replace retrieval + orchestration** (B03–B04) — element-level retrieval, new stages replace old
3. **Validate** (B05) — harness confirms new path
4. **Rewrite externals** (B06) — API + services serve new shapes
5. **Delete old artefacts** (B07) — judge files, verdict columns, dead flags
6. **Clean up tests** (B08) — test suite overhaul

---

## PR Sequence

| PR | Title | Est. Lines | Status | Depends On |
|----|-------|-----------|--------|------------|
| B01 | [Foundation — types, migration, config](PR-B01-foundation.md) | +160 | **DONE** `1f04f7b` | Track A complete |
| B02 | [Claim Map analyzer + selector](PR-B02-claim-map-analyzer.md) | +1,528 | **DONE** `79708ed` | B01 |
| B03 | [Evidence ID + element retrieval](PR-B03-element-retrieval.md) | +540/−200 | **DONE** | B01, B02 |
| B04 | [Pipeline wiring](PR-B04-pipeline-wiring.md) | +330/−380 | **DONE** `9306ddd` | B02, B03 |
| B05 | [Harness adaptation](PR-B05-harness-adaptation.md) | +250/−100 | **DONE** `81e06e0` | B04 |
| B06 | [API + services](PR-B06-api-services.md) | +585 | **DONE** `24fcb0d` | B04 |
| B07 | [Verdict deletion](PR-B07-verdict-deletion.md) | −2,510 | **DONE** `3aa8fb0` | B05, B06 |
| B08 | [Test suite overhaul](PR-B08-test-suite-overhaul.md) | −4,877 | **DONE** `d40668b` | B07 |

**Estimated net change: ~-2,500 lines** (Track B reduces codebase while adding the Claim Map system)

---

## Dependency Graph

```
B01 ──→ B02 ──→ B03 ──→ B04 ──→ B05 ──→ B07 ──→ B08
                              └──→ B06 ──┘
```

B05 (harness) and B06 (API) can run in parallel after B04. Both must complete before B07 (deletion).

---

## Key Decision Log

All 6 architectural decisions resolved on 2026-02-12. See deep-dive Section 12.

1. Elements: 1–5 (floor 1, cap 5)
2. Evidence keying: `element_ids` on evidence (convenience), `evidence_refs` in ClaimMap (source of truth)
3. Seed retrieve: NOT in v1
4. Evidence mapping: structured output only (supports/challenges/context)
5. Orientation: mechanical templates from state counts
6. Claim type: at decomposition (authority)

---

## Scope Boundaries

- **Track B covers:** Backend pipeline, API, DB schema, harness, tests, email, shared types
- **Track C (separate):** Frontend web (18 files), mobile (21 files) — full UI redesign
- **No feature gate.** Pipeline is offline during Track B — no `ENABLE_CLAIM_MAP` toggle
- **Track B does NOT:** Remove VerdictType from shared/types (frontend needs it until Track C), touch mobile code, redesign frontend components

---

## Track B: COMPLETE

**Completed:** 2026-02-13
**Final commit:** `d40668b` (B08)
**Net change:** ~7,000 lines removed across all 8 PRs

All 8 PRs landed on `main` in sequence: B01 → B02 → B03 → B04 → B05+B06 (parallel) → B07 → B08.

**Next step:** Track C — frontend UI redesign (39 files across web + mobile).
