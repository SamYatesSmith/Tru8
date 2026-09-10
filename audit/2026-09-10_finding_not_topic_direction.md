# Build 2 of 2026-09-10 — "finding, not topic" at mapping; causal elements keep the claim's direction

**Status:** BUILT 2026-09-10 (afternoon), suite green, **NOT yet measured** (three paid regrade + blind-review runs owed, asked for one at a time) and **corpus re-record owed** (the mapping-prompt change re-keys every mapping cassette; record once, after measurement).
**Date:** 2026-09-10
**SOT chain:** `audit/OPEN_WORK.md` → `audit/2026-09-10_decomposition_specificity.md` §8 (the three-run measurement that named this build) → this doc.
**Flags:** `ENABLE_DIRECTION_REPAIR` (default True). The prompt rules and the adapter fix have no flag.
**Founder rule in force:** an internal 8/10 on both axes BEFORE any send (`feedback_eight_out_of_ten_before_sends`).

---

## 1. What the measurement named

After the specificity build, three blind reviews (363 labels, 45 rejections, mean 87.5% justified) left these kinds (§8 of the specificity doc):

| kind | count | this build |
|---|---:|---|
| Passage names the subject, supplies a related fact, NOT the finding | 17 | **item 1** |
| The claim's own absolutes ("cannot occur", "everyone") | 14 | not ours |
| Reviewer misreads — 5 of 7 on a causal element that dropped the claim's direction | 7 | **item 2** |
| Decomposition shape (intervention → behaviour; counterfactual premise) | 4 | watch |
| Arguable | 3 | — |

## 2. Item 1 — "FINDING, NOT TOPIC"

### 2.1 Mapping rule (`MAPPING_PROMPT` + `BATCH_MAPPING_PROMPT`)

Appended after `TOPIC vs FIGURE`, which it generalises (that rule covered figures only):

> **FINDING, NOT TOPIC:** An element asserts a FINDING — a comparison, a result, a date, a population, a rating of a specific claim. A passage that names the element's subject and supplies a RELATED fact is not that finding: a planet's temperature with no comparison to the other planets does not support "hotter than every other planet"; a trial's design and endpoints without its result does not support "the trial found X"; a fact-check RATING with no statement of what was rated supports nothing; an article saying a launch is SCHEDULED does not support "was launched"; a study in one population does not support an element about a different one. Map such passages "context" (per CONTEXT DISCIPLINE) or omit them. "supports" and "challenges" require the passage to state the finding itself, in the element's direction or against it.

Every example is a measured rejection from the three runs (t12 Venus ×4, t02 SELECT design ×2, t08 AFP rating ×2, t04 pre-launch, t03 Alzheimer's-vs-healthy). Prompt-only; the existing `NOT A SCEPTICISM DIAL` rule still applies, so this is a matching test, not a reason to withhold support where the passage does state the finding.

### 2.2 Fact-check adapter snippet (`app/services/factcheck_api.py`)

When the fact-check article's text cannot be fetched, the fallback snippet was literally `Fact-check rating: False` — the mapper saw that plus the title; the blind reviewer saw only that. Now, when the API returned the rated claim text, the snippet reads `Fact-check of the claim "<rated claim>" — rating: <rating>`. The legacy form is kept byte-identical when no claim text is present (fixtures in `test_retrieve.py` / `test_assertion_evidence_wiring.py` use it). Extracted article text still wins.

## 3. Item 2 — causal elements keep the claim's direction

### 3.1 The fault

Claim: *"Sweden's decision not to impose a general lockdown caused it to have **lower** excess mortality in 2020-22 than every other European country."* Decomposed, on one Sweden record per run, to *"Sweden's lack of a general lockdown was the primary driver of its mortality outcomes."* The direction is gone; a source saying no-lockdown produced MORE deaths reads to a blind reader as support. The sibling record that kept "lower" was never misread. Lost specificity — the mirror of the invented-specificity fault the morning's build removed.

### 3.2 Prompt rule (both decomposition prompts), beside the specificity rule

> **KEEP THE CLAIM'S DIRECTION.** When the claim asserts a cause and an outcome with a direction ("caused it to have LOWER mortality", "drove prices HIGHER"), the causal element must state the outcome WITH that direction, in the claim's own words. "X was the primary driver of Y's mortality outcome" loses the direction and can be read either way; "X was the primary driver of Y's LOWER mortality" cannot.

### 3.3 Mechanical detector + repair (`app/utils/direction_fidelity.py`, `ClaimMapAnalyzer._repair_lost_direction`)

- **Detector:** the claim carries a directional word (lower/higher/more/fewer/…/reduced/rose/fell/…, matched as stems: first four letters, whole word when shorter) AND the element is causal (`_is_causal_link`) AND the element carries none of the claim's directional stems → flagged. A claim with no direction never flags; a non-causal element never flags.
- **`_is_causal_link` gained `driver(s) of`** — "the primary driver of its mortality" was invisible to the verb-only regex, so those elements also carried no `[CAUSAL LINK]` tag at mapping (`test_claim_integrity` pins hold).
- **Repair:** one call per claim for all flagged elements (`DIRECTION_REPAIR_PROMPT`, 1→1, "change nothing else"), on BOTH decomposition paths (single and batch), after parse. A rewrite is accepted only if it is still causal, now carries a claim direction stem, and — after `strip_invented_precision` — smuggles no adverb the claim lacks. Anything else (exception, malformed reply, wrong length, unchanged defect) keeps the original. Accepted rewrites are re-tagged for scope (`apply_scope_flags`) and recorded at `metadata.direction_restored = [{element_id, was, now}]`.
- **Rollback:** `ENABLE_DIRECTION_REPAIR=False` → no call, no key, originals untouched.

## 4. What was NOT built

- No mechanical form for the "topic without finding" mapping fault beyond the adapter fix — it is a reading fault with no lexical signature; the prompt is the lever, the blind review is the measure.
- The behaviour-for-intervention decomposition shape (3 labels) — prompt-only, watched.
- The JWST tie anomaly (a lone "5 metres" source disputing a 6.5 m fact after the echo gate demoted three corroborating supports) — recorded in `audit/2026-09-10_measurement_verification.md` §6 as a candidate; separate decision.

## 5. Verification

- New: `tests/unit/pipeline/test_finding_not_topic_and_direction.py` — 26 tests: prompt pins (4 prompts, ordering), fact-check snippet (with / without claim text / extracted text wins), detector (stems, the two measured shapes, kept direction, non-causal, no-direction claim, inflections, indices), repair routing (single path, batch path, no call when clean, three rejected-rewrite shapes, smuggled adverb stripped, malformed / exception fail-safe, flag off, scope re-tag).
- Existing pins green: `test_claim_integrity` (causal tag), `test_element_atomicity`, `test_claim_map_analyzer{,_batch}`, `test_e05_intelligence` (legacy snippet), `test_mapping_applicability`, `test_grounds_mapping`, `test_eval_harness`, `test_decomposition_specificity`.
- **Verification is NOT independent** — the same pass built and verified it. The measurement (§6) is the independent check.

## 6. What is owed (paid, ask before each)

1. Three regrade + blind-review runs, same method as the morning (`tmp/astra-regrade.py --arm default`; flush `tru8:evidence_extract:*` first; `review_labels.py --reviewers gemini,gemini_flash`), ~52p each. Read the kinds first: expect the "topic without finding" count to fall from ~6/run and the Sweden misreads to go; the claim's-own-absolutes class (~5/run) will remain and is not ours.
2. Corpus `--record` once after measurement (~£1.20), `scripts/restore_curated_goldens.py`, re-pin from observations, README header.
