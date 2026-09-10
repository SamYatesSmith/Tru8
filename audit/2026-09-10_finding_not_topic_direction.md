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

## 7. Measurement

| run | labels | justified (primary) | rejected | both reject | topic-without-finding | Sweden misreads | direction repair fired |
|---|---:|---:|---:|---:|---:|---:|---:|
| before (3-run mean, specificity build) | 363 | 87.5% | 45 | — | 17 | 5 | — |
| **b2 run 1** (`audit/review_sheets/2026-09-10-b2run1`) | 123 | **91.1%** | 11 | 6 | 4 | **0** | 0 (prompt held) |
| **b2 run 2** (`audit/review_sheets/2026-09-10-b2run2`) | 122 | **88.5%** | 14 | 4 | 5 | **0** | 0 (prompt held) |
| **b2 run 3** (`audit/review_sheets/2026-09-10-b2run3b`) | 115 | **88.7%** | 13 | 5 | 5 | **0** | 0 (prompt held) |
| **build-2 three-run** | 360 | **89.4%** | 38 | — | 14 | **0** | 0 |

### b2 run 1 — the 11 rejections, by kind

- **The claim's own wording: 5** — t07 ×3 ("directly causes SQLITE_BUSY errors not to occur"; passages about WAL locking that the reviewer wants to see name the mechanism), t14 ×2 (a 3.75% passage without "7 September 2026").
- **Topic without the finding: 4** (was ~6 a run) — t02 a semaglutide meta-analysis for "the SELECT trial demonstrated"; t03 older-adults/dementia population for "healthy adults"; t03 a 20 g protocol for "5g daily"; t08 EPA tailpipe page for a particulate-matter question. Venus ×0 (was 1–3 a run), rating-only ×0 (was 1 a run), trial-design ×0 (was 2).
- **Arguable: 2** — t08 techoble ("individual statistics, not a comprehensive lifecycle analysis" — the grounds question asked for *"what lifecycle analyses show regarding the total carbon footprint"*, a quantity-shaped head the detector's list does not cover: "What do … show regarding the total …"); t13 scienceinsights (Sweden 4.4% vs Norway 5.0% read as making "lower than every other country" MORE likely).
- **Sweden direction: both causal elements kept "lower"** ("…caused it to have lower excess mortality in 2020-22"; "…was the cause of its having lower excess mortality…") — the prompt rule alone did it; `direction_restored` absent on every record (the repair call was not needed). **Zero misreads on those elements** (were 2–3 a run).

### ⚠️ Watch on runs 2–3: Sweden causation now UNRESOLVED on both records

Both causal elements carry **no evidence refs at all** this run, and the pool (12 sources per record) contains neither the Nature counterfactual paper nor the UVA report that disputed causation on every morning run. Two possible causes, not separable from one run: pool churn (62% between identical runs), or the reworded causal element changed its element-lane queries and stopped retrieving those studies. If it is unresolved on all three runs, the direction fix will have cost the record its causal challenge — a structure regression the label gain does not pay for — and the remedy is on the retrieval side (the element lane query), not the decomposition.

### b2 run 2 — the 14 rejections, by kind

- **The claim's own wording: 4** — t13 + t06 "every other European country" vs passages saying "lowest in the EU and Nordic countries" / "lowest in all of Europe according to some data sets"; t02 "everyone who is overweight"; t14 "expected to hold at 3.75% next week" for "is 3.75% as of 7 September".
- **Topic without the finding: 5** — t09 ×2 (HN / GitHub threads about journal modes that never state the DEFAULT), t08 an assessment "undertaken" with no findings, t12 a Venus temperature with no comparison (back once, was 0 on run 1), t13 healthdata per-country figures for the "every other country" ranking.
- **Reviewer error: 2** — t07 "WAL stops readers from blocking the writer" read as the *inverse* of "readers never block writers" (it is the same statement).
- **⚠️ Unstated specificity, back in a NEW grammatical head: 3** — the EV grounds question *"How does the **proportion** of renewable energy versus fossil fuels used to charge electric cars compare across different regions?"* demands proportions the claim never stated; three region-specific passages were then graded "neither". The morning's detector covers `what proportion` but not `how does the proportion … compare`, and the prompt rule did not hold on this draw. Same family as b2 run 1's *"what do lifecycle analyses show regarding the **total** carbon footprint"*. **Widen the detector to these two heads after run 3** (measure the build as built; change the instrument between series, not inside one).
- **Sweden direction:** both causal elements kept "lower" again (repair never fired). **t06 causation now DISPUTED** with the counterfactual sources back in the pool — run 1's UNRESOLVED was pool churn, as the query-plan comparison suggested; **watch item cleared**. t13 unresolved this draw (its causal element drew no directional refs on the same cached pool — mapper variance).
- **Thin records, network again:** t03 creatine retrieved ZERO web sources (`provider_status.web_search = timeout`, PubMed/WHO/Wikipedia/Semantic Scholar all 0 results in the same window — connectivity, recorded honestly by provider status); t01 and t02 five sources each. Costs the run ~10 labels it would otherwise have had; changes no kind.

### b2 run 3 — the 13 rejections, by kind

(The first attempt at run 3 died after one input — the regrade process exited 127 with no Python error while the session's MCP servers dropped at the same moment; an environment event. Its partial outputs sit untracked in `tmp/astra-regrade-2026-09-10-b2run3/` and `audit/review_sheets/2026-09-10-b2run3/` (6 labels, meaningless) and are NOT the run. The run is `b2run3b`. Cost of the aborted attempt ≈ 5p over the approved 52p.)

- **The claim's own wording: 4** — t06 + t13 "lowest in the EU and Nordic countries" against "every other European country"; t02 "everyone who is overweight" (the trial's restricted cohort IS the challenge); t14 a 3.75% passage with no date.
- **Topic without the finding: 5** — t02 the NEJM "2%" fragment; t08 carbone4 (manufacturing higher, nothing on offset); **t08 IEA — the retained window is a bibliographic chart citation, no data at all** (a passage-selection fault of the rating-only kind); t11 an inflation-rate definition; t07 a single-writer queue architecture for the SQLITE_BUSY element.
- **Reviewer error: 2** — t07 "WAL stops readers blocking the writer" read as the inverse of "readers never block writers" (third time); t02 acc.org, the reviewer's own arithmetic mid-sentence ("but wait, let me re-calculate").
- **Arguable: 2** — t08 earth.org on a "to what extent" question; t02 news-medical "no heterogeneity across body habitus" read as support for "everyone".
- **Unstated specificity: 0. Sweden misreads: 0.** t06's causal element kept "lower" and read DISPUTED; t13's kept "lower" and drew no directional refs (unresolved) on its own pool.

## 8. Build-2 three-run reading (2026-09-10, ~£1.61 for the three incl. the aborted attempt)

| | labels | justified | rejected | Sweden-direction misreads | topic-without-finding |
|---|---:|---:|---:|---:|---:|
| build 1 (morning, 3 runs) | 362 | 87.6% | 45 | 5 | 17 |
| **build 2 (afternoon, 3 runs)** | 360 | **89.4%** | 38 | **0** | 14 |

**What build 2 did:** the direction fault is gone (0 misreads on the Sweden causal elements over three runs, was 5; the prompt rule alone held on all six records — the repair call never fired). The "topic without finding" kind fell 17 → 14 and its measured shapes went to zero or near it (Venus 4 → 1, rating-only 2 → 0, trial-design 2 → 0); what remains is new shapes each run — a bibliographic citation window, a definition, a wrong-architecture passage. **The rate: 87.6% → 89.4%, p = 0.43 — not distinguishable from pool noise.** The kind-level results are the evidence; the rate is consistent with them and proves nothing on its own.

**Where the product stands on the label axis, honestly:** blind 89.4% (three-run mean; best single run 91.1%). Of the 38 remaining rejections: **13 are the user's own wording** ("cannot occur", "everyone", "every other European country", "as of 7 September") — the reviewer being strict on words the claim itself uses, which we must not soften; **4 are reviewer errors**; **14 are passage-level** (the mapper reading a subject-matched passage as the finding, or a retained window that is a citation / definition / rating); **3 are one grounds question in a head the quantity detector did not cover** (widened after run 3: `how does the proportion … compare`, `what do … show regarding the total …`); 4 arguable. **Adjudicated (removing reviewer errors and the claim's-own-wording class): ≈ 21 / 360 ≈ 94.2%.**

**Reading against the founder's gate (internal 8/10 on both axes):** structure has held on every headline outcome across all six runs today (Bank Rate ×2, JWST orbit, SELECT population and absolute risk, SQLite, Sweden ranking and causation, the invented trial). The blind label rate is 89–91%, adjudicated ≈94%, against a 95% bar. **The gap that is ours is the passage-level class (~14/360 ≈ 4 points): a retained window that carries no finding (citation, definition, rating badge) and a mapper reading a same-subject passage as the finding.** The class that is not ours (~13/360 ≈ 3.6 points) will not move without softening the user's words, and it should not.

**What the measurement names next, if the founder wants the last four points:** (1) passage selection — do not retain a window that is a bibliographic citation, a definition or a badge (mechanical: the IEA "Cite chart" window, the AFP rating, the calculatorlib definition all have lexical signatures); (2) the mapper's same-subject reading — already prompted; the residual is model reading, measurable only. Neither touches decomposition or retrieval.

