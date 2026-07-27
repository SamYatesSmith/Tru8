# Phase 1 design — mechanical honesty for question-shaped elements

**Date:** 2026-07-27 · **Status:** DESIGN, awaiting approval · **No code written**
**Parent:** `audit/2026-07-27_element_retrieval_design.md` (Phase 2) · SOT `audit/DECOUPLING_STATE.md`
**Process:** phased-build-loop — acceptance criteria frozen here, before any code.

---

## 1. What this phase fixes

On a grounds-routed (opinion) claim, Tru8 currently states a verdict it has not earned:

- `TRU-4B9D-65EA` — *"retrieved evidence predominantly supports all 4"* on **"The UK COVID
  vaccine rollout was a triumph"**, where all four element summaries say the evidence did
  not supply the figures. Two of the four are marked `supported` off **one source each**.
- `TRU-171A-9EF9` — *"evidence is mixed"* where 12–13 sources agree with the claim.

Two mechanical causes, both fixable with **zero prompt bytes**:

1. `derive_orientation` aggregates question elements as though they were assertions.
2. `_derive_element_state_with_authority` rule `all_supports`: `n_challenges == 0 AND
   n_supports > 0 → supported`. Sound for an assertion; near-zero bar for *"did we find
   out?"*.

**Explicitly NOT fixed here** (needs the real pool — Phase 3): the mapper filing
partially-answering sources as `supports`. This phase does not attempt it, so
`TRU-4B9D-65EA` e01/e02 (4 and 3 supports) will likely still read `supported`. That is
expected, stated now, and is not a criterion of success for this phase.

---

## 2. Design

### 2.1 Backend — orientation suppression (removes existing duplication)

`derive_orientation(elements)` + `compute_orientation_basis(elements)` are called as an
identical **pair at 5 sites** (`claim_map_analyzer.py:1271, 1352, 1471, 1610, 2393`).
That duplication is pre-existing and is the natural place to make this change once.

**Add one helper** — `apply_orientation(claim_map)` — that:
- computes `orientation_basis` exactly as today, **always** (see §2.3)
- sets `orientation = None` when `_grounds_applied(claim_map)` is true
- otherwise sets the prose exactly as today

Replace all 5 duplicated pairs with a call to it. **Net: five duplications removed, one
grounds-aware decision point added.**

Reuses the existing `_grounds_applied(claim_map)` predicate (`claim_map_analyzer.py:353`) —
the canonical "did the grounds stage rebuild this map" test. **No new predicate.**

### 2.2 Backend — evidential floor for grounds elements

Extend `_derive_element_state_with_authority` with one optional parameter,
`min_weighted_support: int = 0`. Default `0` reproduces today's behaviour byte-for-byte, so
the factual path is untouched by construction.

When the parameter is > 0 and the computed state is `supported` but
`weighted_supports < min_weighted_support`, downgrade to `unresolved` and record
`rule = "grounds_support_floor"` in the existing `state_basis` dict.

**Reuses the existing tier weights** (`primary=3, reporting=2, commentary=1`) and the
existing basis/transparency mechanism. No new weighting, no parallel derivation function.

**Threshold: `GROUNDS_MIN_WEIGHTED_SUPPORT = 3`** (new setting) — satisfied by one primary
source, two reporting, or three commentary. Principled rather than arbitrary: a single blog
post does not answer a research question; one official statistic does.

**Downgrade target is `unresolved`, not `contextual` — a deliberate divergence from the
2026-05-12 rule.** That decision (`SeekerView.tsx:57-60`) excludes `contextual` from gaps
because context-tier evidence "is not absent". Correct for an **assertion**. For a
**question**, "we have topical material but no answer" is precisely an unknown worth
re-searching, so it must reach the Seeker. Different element kind, different rule — recorded
here so it is not read later as an oversight.

### 2.3 `orientation_basis` is NOT touched

It is part of the manifest canonical payload (`manifest_signer.py:76`), whereas the prose
`orientation` is explicitly **excluded** as free-text narrative (`:7`). Leaving the basis
intact means **signed manifests are unaffected** and the mechanical audit trail survives
even where the prose is suppressed. This is why suppression is prose-only.

### 2.4 Frontend — suppression must render NOTHING

A null orientation today produces *more* text, not less:

| Component | Line | Current null behaviour |
|---|---|---|
| `ClaimOverviewCard.tsx` | 121 | `'No orientation available.'` |
| `ClaimSectionCard.tsx` | 133 | `'No orientation available.'` |
| `ClaimSummaryPanel.tsx` | 203-209 | **"The gathered evidence doesn't clearly lean either way — elements remain unresolved."** |

The third is the serious one: on a suppressed opinion claim it replaces a false verdict with
a **false-balancing statement** — the Version B breach, in the same slot. Shipping backend
suppression alone would make the page worse.

Two nulls must be distinguished:
- **suppressed** (claim is an opinion; we deliberately do not summarise) → render nothing
- **absent** (derivation failed / no elements) → today's fallback text is right

**One shared helper** — `web/lib/orientation.ts` → `isOrientationSuppressed(claimMap)`,
reading `claimMap.metadata?.grounds?.applied` (already exposed: `ClaimMapSchema.metadata`,
`schemas.py:279`). Consumed by the three components above. **No per-component logic.**

`orientation-line.tsx` already returns `null` for null and needs no change.
`ProjectionistView` / `ClaimSummary` pass through — verify only.

### 2.5 Not in scope (later phases, deliberately)

Mapper `supports` threshold · compound-question atomicity · element-retrieval seam ·
per-element label wording (answered/partly/not answered) · grounds-aware re-search offers.

---

## 3. Acceptance criteria (frozen — verified independently)

| # | Criterion | Evidence required |
|---|---|---|
| 1 | Grounds-routed claim → `claim_map["orientation"] is None` | unit test on a grounds fixture |
| 2 | Non-grounds claim → orientation prose **byte-identical** to today | regression test, factual fixture |
| 3 | `orientation_basis` unchanged in **both** cases | unit test asserting dict equality |
| 4 | Grounds element, would-be `supported`, weighted supports < 3 → `unresolved`, `rule == "grounds_support_floor"` | unit test |
| 5 | Grounds element with weighted supports ≥ 3 → unchanged | unit test |
| 6 | Non-grounds element states **byte-identical** (default param 0) | regression test |
| 7 | No call site computes orientation directly; all 5 use the helper | grep shows 0 direct `derive_orientation(` calls outside the helper |
| 8 | Suppressed orientation renders **nothing** in all 3 components — no fallback string, no "doesn't clearly lean either way" | component tests / rendered output |
| 9 | Absent-but-not-suppressed orientation still shows today's fallback | component test |
| 10 | PDF omits the orientation block when suppressed | template already `{% if %}` — assert via render |
| 11 | `unresolved` grounds elements increment the Seeker's unknown count | existing `SeekerView` logic + test |
| 12 | Full backend suite passes, no new failures | `pytest tests/ -v` output captured |
| 13 | `tsc --noEmit` clean; no `npm run build` against the working tree | captured output |
| 14 | **Zero prompt bytes changed** → mapping cassettes unaffected; replay bench not required this phase | `git diff` shows no prompt-string edits |

---

## 4. Risks + reversibility

| Risk | Mitigation | Reversible? |
|---|---|---|
| Threshold too aggressive → Seeker noisy, re-search upsell pressure | measure on T1/T2/T4 before/after; tune the setting | **Yes** — `GROUNDS_MIN_WEIGHTED_SUPPORT=0` restores today exactly |
| Consolidating 5 call sites changes behaviour at a site I misread | verifier diffs each site individually | Yes — single commit |
| A frontend surface renders orientation that I have not found | criterion 8 + repo-wide grep in verification | Yes |
| Suppression reads as "Tru8 has nothing to say" | intended: the elements below carry the content | Yes |

**Rollback unit:** one commit. Setting `GROUNDS_MIN_WEIGHTED_SUPPORT=0` disables the floor
without a deploy; orientation suppression reverts with the commit.

---

## 4a. Mutation matrix — the pin is proven, not asserted (2026-07-27)

Independent verification caught the first version of `orientation-suppression.test.tsx`
being **vacuous on two of four surfaces**: the `ClaimSummaryPanel` fixture used
`evidence: []` / `elements: []`, so the render short-circuited at `evidenceCount > 0`
*before* reaching the guarded branch, and `ClarityResponseCard` was never rendered at all.
Both passed for the wrong reason — including the false-balance string, the highest-value
assertion in the phase.

Fixture now carries 2 mapped sources + an element with `evidenceRefs` (so `barTotal > 0`),
and a `ClarityResponseCard` case was added. Each guard was then disabled in turn and the
pin re-run:

| Surface | Guard disabled → | Verdict |
|---|---|---|
| `ClaimOverviewCard` | 2 failed / 8 passed | FIRES |
| `ClaimSectionCard` | 1 failed / 9 passed | FIRES |
| `ClaimSummaryPanel` | 2 failed / 8 passed | FIRES |
| `ClarityResponseCard` | 1 failed / 9 passed | FIRES |

All four files md5-verified byte-identical after restore. Frontend suite: **87/87 across 10
files**, confirmed on three consecutive clean runs.

**Lesson worth keeping:** a green test file is not evidence that it pins anything. Mutate
every guard it claims to protect, or the file is decoration.

**Fixture-realism guard.** Every suppression assertion is NEGATIVE (`not.toContain`), so an
emptied fixture satisfies them all by rendering nothing — reintroducing the vacuous failure
silently. The ClaimSummaryPanel case therefore also asserts `toContain('Sources mapped')`,
which only renders when `barTotal > 0`, i.e. when the fixture's `evidenceRefs` genuinely
resolve. Trim the fixture and it fails loudly.

**Mutation-harness rules (learned the hard way here).** The first scripted matrix died on a
Python encoding error *before* its restore line, leaving a component mutated on disk. So:
(1) assert the mutation string actually applied (`src.count(old) == 1`) before running —
a mutation that silently fails to apply produces a **false green**, which reads as "the pin
fires"; (2) put every restore in `finally`; (3) verify by hash after; (4) never chain a
full-suite run into the same command as a mutation script. An intermediate full run during
this work reported 2 failures that neither five clean runs nor three direct replications
could reproduce — cause unproven, but the harness weakness is real either way and cuts
toward false greens as easily as false reds.

## 4b. Carried to Phase 3 — a behaviour difference, not a naming tidy-up

`_grounds_applied` tests whether the grounds STAGE ran, which is not the same as "these
elements are questions". On the lock-collapse path (`opinion_symmetry.py:280-286`) the
value-predicate lock empties the grounds set, the BASELINE assertion-shaped elements are
restored, and the map is still marked `applied: True, converged: False` — the collapse is
disclosed via `converged`, not `applied`.

**Consequence today: the support floor applies a question-shaped bar to assertion-shaped
elements on normative-hinted claims, and orientation is suppressed for them.** Rare, but a
real behaviour difference — record it as such so Phase 3 does not file it as "tidy up the
predicate".

Deliberately NOT fixed in Phase 1: `applied && converged` would make the floor disagree with
the pre-existing `_grounds_applied` that selects `GROUNDS_MAPPING_ADDENDUM` (`:1367`,
`:2370`), leaving the two with different definitions of a grounds claim — worse than uniform
imprecision. Changing `_grounds_applied` itself alters which prompt is built, breaking
criterion 14 and invalidating cassettes. Fix once, everywhere, in Phase 3.

## 5. What this does NOT achieve

Stated now so it cannot be claimed later: `TRU-4B9D-65EA` e01/e02 will probably still read
`supported`, because 4 and 3 sources clear the floor even though the evidence did not answer
the question. **The headline verdict line dies; two element badges remain wrong.** Those are
Phase 3, and they need the Phase 2 pool to tune against.
