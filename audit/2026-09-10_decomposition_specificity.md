# Decomposition specificity — elements and grounds questions at the claim's own level

**Status:** BUILT 2026-09-10, suite green, **corpus RE-RECORDED** (`170/5/8/3 + 82CF drift`, 9/10 zero misses — `backend/tests/replay_corpus/README.md` header), **NOT yet measured** (three paid regrade + blind-review runs owed, each asked for separately).
**Date:** 2026-09-10
**SOT chain:** `audit/OPEN_WORK.md` → `audit/2026-09-09_astra_regrade.md` (the measurement that named this build) → this doc.
**Flags:** `ENABLE_UNSTATED_QUANTITY_REPAIR` (default True, requires `ENABLE_ELEMENT_ATOMICITY`). The prompt rules have no flag — they are the prompt.

---

## 1. The defect, measured

Two blind AI label reviews on Astra's 14 inputs (`backend/scripts/review_labels.py`, element + passage only, never the label):

| run | labels | justified | rejected |
|---|---|---:|---:|
| `audit/review_sheets/2026-09-09` | 137 | 86.1% | 19 |
| `audit/review_sheets/2026-09-09-postfix` | 147 | 81.6% | 27 |

The rate moves ±5 points with the retrieval pool alone; the **kinds** are stable. Of the 27 post-fix rejections, 18 are one disease: the decomposition demanded specificity the claim never stated, and a source that answers the claim then cannot answer the element.

- **11 on one record, in question form** (`t08_ev`, "Electric cars are cleaner than petrol cars"): the grounds path asked *"What is the total lifecycle greenhouse gas emission volume associated with the manufacturing and operation of electric cars compared to petrol cars?"* (8 rejections) and *"What proportion of the electricity used to charge electric cars is generated from fossil fuels across major vehicle markets?"* (3). Sources saying EVs emit less over their life were graded "neither".
- **7 in assertion form**: "consistently consume", "quantified average temperature", "verified maximum", "completely prevents", "under all operational circumstances", "no other conditions" — and, from the first run, "exactly 5g" (4 rejections on one element) and "strictly of healthy adults".
- Also on the assertion path: an intervention turned into a population behaviour ("Healthy adults consistently consume 5g of creatine daily" for "Taking 5g of creatine daily prevents dementia in healthy adults") and a mechanism element the claim never asserted ("initiates a biological mechanism that alters neurological pathways relevant to dementia").

The assertion-form adverbs already had a mechanical backstop (`app/utils/invented_precision.py`, 2026-09-09). The question form had nothing, and the prompts said nothing about specificity in either path.

## 2. What was built

Three pieces, one bounded change.

### 2.1 Prompt rule on both decomposition prompts (`claim_map_analyzer.py`)

Added to `DECOMPOSITION_PROMPT` and `BATCH_DECOMPOSITION_PROMPT`:

> **MATCH THE CLAIM'S OWN SPECIFICITY.** An element must never be stricter or more specific than the claim: do not add figures, thresholds, dates, ranges, absolutes ("all", "every", "no other", "under all circumstances"), qualifiers ("exactly", "consistently", "completely", "quantified"), mechanisms, populations or behaviours the claim does not state. A comparative claim with no figure ("X is cleaner than Y") decomposes into comparative elements with no figure. An intervention ("taking 5g daily") is not a behaviour of a population ("adults consume 5g daily"). Evidence is judged against the element AS WRITTEN, so every word you add that the claim lacks is a test the claim never set.

And the contestable-parts list now reads *"mechanism (only where the claim asserts one)"* — the previous wording was an open invitation to invent one.

### 2.2 Prompt rule on the grounds question-builder (`opinion_symmetry.py`)

Added to `NORMATIVE_DECOMPOSE_PROMPT`:

> Ask at the claim's OWN level of specificity. Where the claim states no figure, proportion, total or threshold, do not ask for one — ask how the subject compares, what the evidence shows, or to what extent something holds. [worked example: the EV volume question → "How do the lifecycle emissions of electric cars compare with petrol cars?"] Ask for a quantity only when the claim itself states one.

The §20.6(1) direction-free constraint still holds (pinned twice: `test_opinion_symmetry.py` and the new file).

### 2.3 Mechanical backstop for questions (`app/utils/unstated_quantity.py` + repair routing)

NF-11: a prompt rule is a first line of defence, never a guarantee. The detector `demands_unstated_quantity(question, claim)` fires when a question opens with a quantity-demanding head AND the claim states no quantity.

- **Heads, deliberately narrow** — the measured forms and close kin: `what proportion / percentage / share / fraction / volume / quantity / magnitude`, `what is/was the total / exact / precise / quantified / overall / aggregate / absolute / net …`, `by what proportion / percentage / share / fraction / margin / factor`. **Left out on purpose:** `how much`, `how many`, `what is the average` — "How much did the furlough scheme cost?" is a legitimate ground for "the scheme was a waste of money". The prompt covers the open set; the detector covers what was measured.
- **Claim guard:** a claim carrying a digit, `%`, or a quantity word (per cent, proportion, share, fraction, total, majority, half, third, quarter, double, twice, -fold, volume, amount, "number of", how much/many, magnitude) may be asked for a quantity. `most` is not a quantity word ("most people think").
- **Routing:** flagged questions ride the **same repair call as compounds** — `_repair_compounds` became `_repair_questions`; each item is tagged `[two questions]`, `[unstated quantity]` or both; one model call per claim regardless of mix. `COMPOUND_REPAIR_PROMPT` became `QUESTION_REPAIR_PROMPT` (alias kept; the `"repairing research questions"` marker the tests key on is unchanged).
- **Fail-safe, same contract as atomicity:** any exception, malformation or wrong-length reply keeps every original; a rewrite is accepted only if it clears **both** defects (a rewrite that still demands the figure, or that introduces a compound, is discarded). Repair runs **before** the value-predicate lock, same load-bearing order as compounds.
- **Disclosure:** `metadata.grounds.specificity = {detected, repaired, surviving}` beside `atomicity`. Quantity survivors have **no** mapper backstop (compounds have the `[COMPOUND]` tag); a survivor is disclosed, that is all.
- **Rollback:** `ENABLE_UNSTATED_QUANTITY_REPAIR=False` restores compound-only behaviour byte-for-byte (no tag, no key, no call for a lone quantity question). `ENABLE_ELEMENT_ATOMICITY=False` disables both.

## 3. What was NOT built, and why

- **No mechanical backstop for the assertion-path shapes** beyond the existing adverb strip. "Healthy adults consume 5g daily" (behaviour for intervention) and the invented mechanism element have no lexical signature; they are the prompt's job. If the three measurement runs still show them, the next lever is a bounded rewrite call on the assertion path shaped like this one.
- **No absolutes strip** ("under all operational circumstances", "no other conditions"). Both came from a claim that is itself absolute ("SQLITE_BUSY errors cannot occur"), so a strip guarded by the claim's own absolutes would not have fired on the measured cases. Not worth a mechanism that fires on nothing measured.
- **No rewrite of `how much` / `how many`** — see 2.3.

## 4. Verification

- New: `tests/unit/pipeline/test_decomposition_specificity.py` — 37 tests: prompt pins (4 prompts), detector (measured questions detected; close kin detected; ordinary/`how much`/`average` questions left alone; quantity-stating claims license the question), routing (one call, tags, both-defect items, no call when clean, still-demanding rewrite rejected, compound-introducing rewrite rejected, exception fail-safe, flag off ×2, atomicity off disables both, repair-before-lock order).
- Existing pins unchanged and green: `test_element_atomicity.py`, `test_opinion_symmetry.py`, `test_invented_precision.py`, `test_mapping_applicability.py`, `test_grounds_mapping.py`.
- Full suite: see `audit/OPEN_WORK.md` for the count at commit.
- **Verification is NOT independent** — the same pass built and verified it. The measurement (§5) is the independent check.

## 5. What is owed (paid, ask before each)

1. ✅ **Corpus re-recorded** (~£1.45). What the recording showed about the change: every one of the ten decompositions read faithfully to its claim — no invented figures, qualifiers or absolutes; the prerequisite-element rule from 2026-09-09 is draw-dependent (018F: 2 elements yesterday, 3 today). Two first-pass pools collapsed on network, not code (0001: 30 connection timeouts; 82CF: fetch-deadline cancellations round a 15 MB filing) — both re-recorded singly; 82CF drifts cross-process as before and its 18 MB re-record was reverted.
2. **Three measured runs** — see §7 below for each run as it lands. (`tmp/astra-regrade.py --arm default` + `backend/scripts/review_labels.py`, ~50p each): one run is noise (86.1 → 81.6 on identical inputs). Read the **kinds** of rejection before the rate. Target: the "unstated specificity" kind gone or near it; the rate above 95% would be the first time.
3. ~~Then STOP pipeline work and go get strangers.~~ **Struck 2026-09-10 — founder: "I want an 8/10 output BEFORE any sends go out."** The next build is what the three runs name.

## 6. Durable lessons

- **A question can invent precision as readily as an assertion.** The adverb strip watched one grammatical form; the same disease moved to the other. When a mechanical guard is built for one shape of a defect, ask which other shapes the model has available.
- **Route a new defect through the existing repair call, not a new one.** One tagged call per claim keeps cost, latency and the fail-safe contract identical.
- **Leave the legitimate cases out of the detector and say so.** "How much did it cost?" is a real ground; a detector that fires on it would trade one kind of wrong label for another.

## 7. Measurement (paid, one run at a time, founder-approved each)

Method per run: `tmp/astra-regrade.py --arm default` (Astra's 14 inputs, live retrieval, local DB; the Redis evidence-pool cache is cleared first so element lanes are searched from the NEW elements) then `backend/scripts/review_labels.py --reviewers gemini,gemini_flash` (blind: element + passage only). `gemini_flash` errors on ~40% of labels both days, so the **primary reviewer (`gemini`, gemini-3.5-flash-lite) is the rate**; the second is a check on the overlap.

| run | labels | justified (primary) | rejected | both reviewers reject | "unstated specificity" kind |
|---|---:|---:|---:|---:|---:|
| 2026-09-09 first | 137 | 86.1% | 19 | — | ~5 (exactly/strictly) |
| 2026-09-09 post-fix | 147 | 81.6% | 27 | 13 | **18** |
| **2026-09-10 run 1** (`audit/review_sheets/2026-09-10-run1`) | 138 | **87.6%** | 17 | **4** | **0** |
| **2026-09-10 run 2** (`audit/review_sheets/2026-09-10-run2`) | 107 | **86.0%** | 15 | 11 | **0** |

### Run 1 — the 17 rejections, by kind

- **Unstated specificity: 0.** The EV record's grounds questions came out comparative ("How do the lifecycle greenhouse gas emissions of electric cars compare with those of petrol cars?", "To what extent do the environmental impacts … differ"); no "exactly", "consistently", "quantified", "completely", "under all circumstances" anywhere in the 14 decompositions. `metadata.grounds.specificity` on t08: the prompt produced clean questions, so the repair call was not needed (detected 0).
- **Reviewer direction error: 2** (t06 Nature paper + UVA report read as *supporting* "no lockdown was the primary driver" when both say no-lockdown caused MORE deaths — Tru8's `challenges` is right; the same two sources were misread yesterday).
  - ⚠️ A real, smaller decomposition fault sits underneath: the t06 element reads *"the primary driver of its mortality outcome"* — the claim's direction ("LOWER excess mortality") was dropped, so the element is readable either way. t13 (same claim, no focus text) kept it: "the primary cause of it having lower excess mortality". Lost specificity, the mirror of the disease this build fixed. Watch on runs 2–3.
- **Strictness on wording the CLAIM itself carries: 6** — t07 ×3 ("directly prevents SQLITE_BUSY" — sources showing SQLITE_BUSY still fires in WAL are a fair challenge to "cannot occur"); t02 "everyone who is overweight" (the trial's restricted cohort IS the challenge); t06 "lowest in the EU" vs "every other European country"; t03 "3–5 g" vs "5g".
- **Genuine mislabels: 5** — t11 "fell below 10%" supporting "falls from 10% to 3%"; t12 a Venus temperature passage with no planetary comparison badged `supports`; t09 a passage with no release date supporting a dated element; t08 a rating-only AFP fact-check passage badged `supports` (yesterday's USA Today twin — a **passage-selection** fault: the retained window is the verdict badge, not the finding); t08 carbone4 manufacturing-only passage as `challenges`.
- **Arguable / question-shape: 4** — t06 uvahealth per-capita deaths as `challenges` to the causal element; t08 kgm-motors, mdpi, azom on the particulate and mineral-extraction questions.

Reading: the kind this build targeted is gone on run 1; what remains is reviewer error (2), the claim's own absolutes (6), and passage-level mislabels (5) — the latter is the next measurable disease if runs 2–3 agree (rating-only passages; a passage that names the topic but not the finding).

### Run 2 — the 15 rejections, by kind

- **Unstated specificity: 0.** A scan of all 41 elements for the measured words (exactly / strictly / consistently / completely / quantified / verified / "under all" / "no other" / "what proportion" / "total … volume") finds none. EV questions comparative again; `grounds.specificity` detected 0 (the prompt did the work, the repair call was not needed on either run).
- **The claim's own absolutes / causal wording: 5** — t07 ×3 ("directly prevents … SQLITE_BUSY" — sources showing SQLITE_BUSY under concurrent writers are fair challenges to "cannot occur"), t02 "everyone who is overweight", t14 "as of 7 September 2026" (a passage stating 3.75% with no date).
- **Reviewer direction error: 2** — t07 reddit ("writers only conflict with writers" read as support), t13 BBC (a spike in Swedish excess deaths read as support for "no lockdown drove the outcome").
- **Passage-level mislabels: 6** — t12 ×3 (a Venus temperature with no planetary comparison badged `supports` on reddit, PMC and astronoo — the "topic without the finding" shape; 1 on run 1, 3 here), t08 AFP rating-only fact-check window (**both runs**), t04 a pre-launch "set to launch on 18 December" article supporting "was launched", t03 alzdiscovery's 20 g/day protocol supporting 5 g.
- **Decomposition shape, 1 element / 2 labels** — t03 *"Healthy adults take 5g of creatine daily"*: the intervention-as-behaviour shape the prompt rule names came out anyway on this draw (run 1 had "The intervention consists of taking 5g of creatine daily"). Prompt-only, no mechanical form; recorded, not actioned.
- **Absence vocabulary, 1** — t03 brainhealth "evidence is inconclusive" mapped `challenges`; the absence-of-evidence gate (2026-09-09) did not recognise "inconclusive". A vocabulary gap in that gate, one label.

**Seen on both runs, small, not this build's disease:** the causal element drops the claim's direction on one Sweden record per run (run 1 t06 "primary driver of its mortality outcome"; run 2 t13 "primary driver of its relative mortality outcomes") while the sibling record keeps "lower". Two reviewer misreads came from exactly that ambiguity.

