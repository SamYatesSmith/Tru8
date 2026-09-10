# Decomposition specificity — elements and grounds questions at the claim's own level

**Status:** BUILT 2026-09-10, suite green, **NOT yet measured** (three paid regrade + blind-review runs owed, each asked for separately) and **corpus re-record owed** (the prompt change re-keys every cassette).
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

1. **Corpus `--record`** (~£1.20): the prompt change re-keys every cassette (request signatures are cassette keys); 018F was already owed from the "specifically" strip. Record once, `--record-missing`, then `--update-golden` **and restore the curated invariants from git** — `--update-golden` drops every hard_invariant and tolerance-0 pin. Re-read the 018F recital pin against the new observation.
2. **Three measured runs** (`tmp/astra-regrade.py --arm default` + `backend/scripts/review_labels.py`, ~50p each): one run is noise (86.1 → 81.6 on identical inputs). Read the **kinds** of rejection before the rate. Target: the "unstated specificity" kind gone or near it; the rate above 95% would be the first time.
3. Then **STOP pipeline work and go get strangers** (`audit/OUTREACH.md`).

## 6. Durable lessons

- **A question can invent precision as readily as an assertion.** The adverb strip watched one grammatical form; the same disease moved to the other. When a mechanical guard is built for one shape of a defect, ask which other shapes the model has available.
- **Route a new defect through the existing repair call, not a new one.** One tagged call per claim keeps cost, latency and the fail-safe contract identical.
- **Leave the legitimate cases out of the detector and say so.** "How much did it cost?" is a real ground; a detector that fires on it would trade one kind of wrong label for another.
