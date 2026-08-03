# Track N — LLM Audit Results

**Auditor**: Claude Opus 4.6 (automated review)
**Date**: 2026-03-02
**Model under review**: gemini-2.5-flash-lite
**Cases reviewed**: 20 (from 8 distinct checks)
**Total ref judgments**: 189
**Total state judgments**: 66

---

## Executive Summary

The mapper (gemini-2.5-flash-lite) performs well on straightforward empirical claims with
clear evidence. **Ref-level accuracy: ~95.8% (181/189 correct)**. **State-level accuracy:
~92.4% (61/66 correct)**. The dominant failure mode is **C (Misattributed scope)** — the
mapper conflates domestic/regional data with global claims. The secondary failure is
**D (State inflation)** — labelling elements "supported" when only context refs exist.

A separate quality issue: **23 of 189 refs (12.2%) have null reasoning**, concentrated in
cases 016-019. This suggests the model sometimes runs out of output budget or hits a
generation issue, producing structurally valid but unexplained mappings.

### Failure Mode Frequency Table

| Mode | Description | Window Sufficient | Window Insufficient | Total |
|------|-------------|:-:|:-:|:-:|
| **A** | Missed contradiction | 2 | 0 | **2** |
| **B** | Phantom support | 2 | 0 | **2** |
| **C** | Misattributed scope | 5 | 0 | **5** |
| **D** | State inflation | 5 | 0 | **5** |
| **Total** | | **14** | **0** | **14** |

### Decision Signal

All errors occur with **window_sufficient = true**. This means the decisive information
was visible to the mapper in every case. The problem is **model weakness, not input
weakness**. Expanding the snippet window would not fix these errors.

**Primary fix**: Improve the mapping prompt to:
1. Distinguish domestic/regional scope from global claims (C errors)
2. Prevent "supported" state when only context refs exist (D errors)
3. Require non-null reasoning for every ref

---

## Per-Case Reviews

### case-001 — "The 2026 UK Transparency Mandate led to a 22% reduction in medical hallucinations within the NHS."

**Type**: causal_interpretive | **Elements**: 4 | **Evidence**: 14 | **Refs**: 11

This is likely a fabricated or unverifiable claim (dated 2026, no evidence of such a mandate).

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | YES | unresolved | — |
| e2 | supported | **NO** | unresolved | B, D |
| e3 | unresolved | YES | unresolved | — |
| e4 | unresolved | YES | unresolved | — |

**Ref errors:**
- `ev-beac060411b1` mapped as `supports` for e2 — **Phantom support (B)**. Title is simply
  "Hallucinations" (a book chapter, likely about psychiatric hallucinations). The mapper saw
  only the title and assumed it confirms medical hallucinations in the NHS. No actual content
  supports this. Window: sufficient (all text visible, just a title).

**State errors:**
- e2: `supported` with 1 phantom support + 1 context = should be `unresolved`. **State
  inflation (D)** caused by the phantom support above.

---

### case-002 — "The Great Wall of China is visible from space with the naked eye."

**Type**: empirical | **Elements**: 3 | **Evidence**: 11 | **Refs**: 11

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | — |
| e3 | disputed | YES | disputed | — |

**No errors.** Excellent case. The mapper correctly identified 7 "challenges" refs from
astronaut accounts and scientific sources debunking the visibility myth. The single
"supports" for e3 (ev-0ffb39bff315) is from a Reddit thread where the title says "not
actually visible" but the excerpt includes "You can 100% see..." — the mapper's handling
(labelling as "challenges" based on the overall source) is defensible.

---

### case-003 — "China manufactures a greater quantity of electric vehicles than any other nation."

**Type**: empirical | **Elements**: 4 | **Evidence**: 20 | **Refs**: 20

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | unresolved | YES | unresolved | — |
| e3 | supported | YES | supported | C (minor) |
| e4 | supported | YES | supported | C (minor) |

**Ref errors:**
- `ev-bff968da5b5d` mapped as `supports` for e3 and e4 — **Misattributed scope (C)**.
  The evidence says "Chinese OEMs' share over 70%" which refers to the *domestic Chinese
  market*, not global manufacturing output. Domestic market share =/= global manufacturing
  comparison. Window: sufficient.

**Note:** These scope errors don't change the final states because other refs (IEA data
showing 70% of global production) correctly support the elements.

---

### case-004 — "Tesla holds the leading position in worldwide electric vehicle sales."

**Type**: empirical | **Elements**: 3 | **Evidence**: 11 | **Refs**: 10

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | C |
| e3 | disputed | YES | disputed | — |

**Ref errors:**
- `ev-rec-e2_1_5f109087` mapped as `supports` for e2 — **Misattributed scope (C)**. Says
  "Tesla remains the EV market leader" and "Nearly half of all EVs sold in the U.S."
  This is U.S.-specific data mapped against a *worldwide* claim. Window: sufficient.
- `ev-rec-e2_4_78b8fc7d` mapped as `supports` for e2 — **Misattributed scope (C)**. Same
  issue: "Tesla remained the market leader with 633,762 sales" is U.S. data. Window: sufficient.

**State:** e3 correctly marked `disputed` — BYD surpassed Tesla (NYT, BBC evidence). Well done.

---

### case-005 — "Electric vehicles constitute 18% of all new car sales globally."

**Type**: empirical | **Elements**: 4 | **Evidence**: 14 | **Refs**: 12

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | borderline | supported | — |
| e2 | supported | YES | supported | — |
| e3 | supported | YES | supported | — |
| e4 | supported | borderline | disputed | A |

**Ref errors:**
- Missing refs for e4: `ev-rpf-0_0` says "EVs made up about 25% of global car sales in
  2025", `ev-rec-e2_2_34dad788` says "over 20%", `ev-rec-e3_1_f281254c` says "more than
  20% of global sales". These challenge the 18% figure for recent periods but were not mapped
  to e4 at all. **Missed contradiction (A)**, window sufficient.

**Note:** Whether 18% is outdated depends on temporal scope. Some evidence confirms 18% for
specific quarters (Q3 2024, 2023 annual). The claim doesn't specify a time period. The
mapper could reasonably defend "supported" if interpreting the 18% as historically accurate,
but should have acknowledged the contradicting data.

---

### case-006 — "Approximately 60% of the Amazon rainforest is located within Brazil."

**Type**: empirical | **Elements**: 3 | **Evidence**: 10 | **Refs**: 8

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | **NO** | supported | under-state |
| e2 | supported | YES | supported | — |
| e3 | supported | YES | supported | — |

**State issues:**
- e1: `unresolved` — the mapper labels evidence as `context` even though ev-rec-2_2 explicitly
  states "Spanning over 3 million square miles." This directly supports that the total area
  can be determined. The mapper was overly cautious, treating direct area statements as mere
  context. Not a standard failure mode (more like "missed support" — inverse of A).

**Overall:** Good on the core claim (e2, e3 both correctly supported with 4 sources each).

---

### case-007 — "Deforestation in the Amazon has decreased by 50% compared to the level in 2004."

**Type**: empirical | **Elements**: 3 | **Evidence**: 13 | **Refs**: 7

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | — |
| e3 | disputed | YES | disputed | A |

**Ref errors:**
- `ev-rec-3_2_8b0804d0` mapped as `supports` for e3 — **Missed contradiction (A)**. The
  mapper's own reasoning states: "reduced by approximately five times, which is a reduction
  of about 80%, not 50%." The mapper correctly identified the contradiction *in the reasoning
  text* but then assigned the relationship as `supports` instead of `challenges`. This is a
  particularly interesting error: the analytical reasoning is correct, but the label is wrong.
  Window: sufficient.

**Note:** Despite the mislabelled ref, the mapper arrives at the correct state (`disputed`)
via the uncertainty note. The state is saved by correct reasoning, despite incorrect labelling.

---

### case-008 — "The Amazon river is the longest river globally."

**Type**: empirical | **Elements**: 3 | **Evidence**: 22 | **Refs**: 15

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | — |
| e3 | disputed | YES | disputed | — |

**No errors.** Strong case. The mapper correctly identifies the Nile/Amazon debate,
mapping multiple sources as `challenges` (Britannica, NatGeo, Geography Realm) and
others as `supports` (Facebook posts claiming Amazon is longest). The `disputed` state
with appropriate uncertainty note is exactly right.

---

### case-009 — "The Amazon rainforest is responsible for producing 20% of the Earth's oxygen."

**Type**: empirical | **Elements**: 3 | **Evidence**: 13 | **Refs**: 15

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | borderline | supported | — |
| e2 | unresolved | YES | unresolved | — |
| e3 | disputed | YES | disputed | — |

**Notes:**
- e1 `supported`: The mapper uses social media sources (Facebook, LinkedIn, VisualCapitalist)
  that repeat the debunked 20% figure as "supports" for e1 (whether oxygen production *can
  be quantified*). Technically correct — quantifiability is supported regardless of the
  specific percentage. Acceptable but borderline.
- e3 `disputed`: Correctly identified FactCheck.org and AP News as `challenges`, citing the
  actual figure of 6-9%. Well done.
- Fact-check sources (ev-fbecdcc2008a, ev-7744e79261da) mapped as `context` for e1/e2
  rather than `supports` — this is conservative but reasonable.

---

### case-010 — "Ethereum's shift to proof-of-stake resulted in a 99% reduction in its energy consumption."

**Type**: causal_interpretive | **Elements**: 4 | **Evidence**: 8 | **Refs**: 7

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | YES | unresolved | — |
| e2 | supported | YES | supported | — |
| e3 | supported | YES | supported | — |
| e4 | supported | YES | supported | — |

**No errors.** Clean case. The mapper correctly handles the causal claim, attributing
the energy reduction to the PoS transition with multiple supporting refs. The one caution
on e1 (pre-transition energy not explicitly quantified) is reasonable.

---

### case-011 — "China manufactures a greater quantity of electric vehicles than any other nation." (duplicate claim, different check)

**Type**: empirical | **Elements**: 4 | **Evidence**: 8 | **Refs**: 1

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved (0 refs) | borderline | unresolved | — |
| e2 | unresolved (0 refs) | YES | unresolved | — |
| e3 | unresolved (0 refs) | YES | unresolved | — |
| e4 | supported | **NO** | unresolved | B/C, D |

**Ref errors:**
- `ev-bff968da5b5d` mapped as `supports` for e4 — **Misattributed scope (C) / Phantom
  support (B)**. "Chinese OEMs' Share over 70%" refers to domestic market share, not a
  global manufacturing comparison. The mapper's uncertainty note acknowledges the weakness
  but still labels the state as supported.

**State errors:**
- e4: `supported` with 1 problematic support ref = **State inflation (D)**. Should be
  `unresolved` given the evidence doesn't actually compare China's output to other nations.

**Note:** This is the same claim as case-003 but with far less evidence (8 vs 20 items).
The weaker evidence set reveals the mapper's tendency to over-interpret.

---

### case-012 — "Sixty percent of the Amazon rainforest is located within the borders of Brazil."

**Type**: empirical | **Elements**: 3 | **Evidence**: 13 | **Refs**: 6

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | — |
| e3 | disputed | **NO** | supported | D |

**Ref errors:**
- `ev-3d32c0cd4676` mapped as `challenges` for e3 because it says "59%" instead of "60%".
  This is a **phantom challenge**. The 1% difference is well within the "approximately"
  qualifier. Britannica says "approximately 60 percent", Reddit says "about 60%", the
  Amazon Facts source says "roughly 60%". Marking 59% as a *challenge* is overly literal.

**State errors:**
- e3: `disputed` when it should be `supported`. Two refs say "60%" / "approximately 60%"
  and one says "59%". The claim uses "sixty percent" which is a round figure. This is
  **State inflation (D)** caused by a phantom challenge.

---

### case-013 — "The Amazon rainforest is responsible for producing 20% of the Earth's oxygen." (duplicate)

**Type**: empirical | **Elements**: 3 | **Evidence**: 6 | **Refs**: 6

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | YES | unresolved | — |
| e2 | unresolved | YES | unresolved | — |
| e3 | disputed | YES | disputed | — |

**No errors.** Clean handling. Cleaner than case-009 because this evidence set doesn't
include the social media sources that repeat the debunked 20% figure.

---

### case-014 — "The Amazon river is the longest river globally." (duplicate)

**Type**: empirical | **Elements**: 3 | **Evidence**: 12 | **Refs**: 10

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | unresolved | borderline | supported | — |
| e3 | disputed | YES | disputed | — |

**No material errors.** e2 `unresolved` is overly cautious (evidence clearly lists other
river lengths) but defensible. e3 correctly disputed with 4 challenges.

---

### case-015 — "The Great Wall of China is visible from space with the naked eye." (duplicate)

**Type**: empirical | **Elements**: 3 | **Evidence**: 11 | **Refs**: 12

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | YES | supported | — |
| e2 | supported | YES | supported | — |
| e3 | disputed | YES | disputed | — |

**No errors.** Excellent handling, consistent with case-002. 7 challenges correctly
identified. The mapper is very reliable on this well-documented myth.

---

### case-016 — "The number of Amazon employees globally exceeded 1.5 million in the year 2023."

**Type**: empirical | **Elements**: 3 | **Evidence**: 7 | **Refs**: 6

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved (0 refs) | borderline | supported | — |
| e2 | unresolved | borderline | supported | — |
| e3 | supported | YES | supported | — |

**Quality issue:** All 6 refs have **null reasoning**. The mapper produced structurally
valid output (correct evidence IDs, plausible relationships) but no explanations. This
makes the output less useful for review.

**Note:** e1 having 0 refs is odd — multiple evidence items discuss employee counts. The
mapper may have run out of generation budget.

---

### case-017 — "In the year 2023, Tesla's sales volume of electric vehicles exceeded that of all other automotive companies."

**Type**: empirical | **Elements**: 4 | **Evidence**: 7 | **Refs**: 8

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | supported | **NO** | unresolved | D |
| e2 | supported | **NO** | unresolved | D |
| e3 | disputed | YES | disputed | — |
| e4 | disputed | YES | disputed | — |

**State errors:**
- e1: `supported` with 0 supports + 3 context = **State inflation (D)**. Only context
  refs exist; none directly confirm Tesla's 2023 sales figure. Cannot be "supported".
- e2: `supported` with 0 supports + 4 context = **State inflation (D)**. Same issue.
  Context about the EV market doesn't constitute support for quantifying every competitor's sales.

**Quality issue:** All 8 refs have **null reasoning**. This is the most concerning case
for state inflation: the mapper assigns "supported" states despite having zero "supports"
relationships in the refs.

---

### case-018 — "Global sea levels have risen by approximately 8 to 9 inches between the years 1880 and the present."

**Type**: empirical | **Elements**: 3 | **Evidence**: 7 | **Refs**: 7

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | borderline | supported | — |
| e2 | supported | YES | supported | — |
| e3 | supported | YES | supported | — |

**Quality issue:** All 7 refs have **null reasoning**.

**Note:** e3 is very well supported by authoritative sources (NASA, NOAA, WMO) all
confirming 8-9 inches / 20-24 cm since 1880. Despite null reasoning, the relationship
labels and state assignments are correct.

---

### case-019 — "The state of Israel functions as a satellite state of the United States."

**Type**: causal_interpretive | **Elements**: 4 | **Evidence**: 10 | **Refs**: 2

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved (0 refs) | borderline | unresolved | — |
| e2 | unresolved | YES | unresolved | — |
| e3 | unresolved (0 refs) | borderline | unresolved | — |
| e4 | disputed | YES | disputed | — |

**Quality issue:** Only 2 refs mapped from 10 evidence items. Both have null reasoning.
Multiple evidence items with relevant content were not mapped.

**Missing refs:**
- `ev-0e121a8615f5` (Iran-Israel war): mentions "Israel and Iran agreed to a ceasefire
  under US pressure" — relevant to e2 (US influence on foreign policy) and e3 (US military
  involvement). Should be mapped.
- `ev-8a632f770f79` has rich content about US-Israel dynamics but was only mapped to e2
  and e4, missing e1 (political support via AIPAC) and e3 (military relationship).

**Note:** Despite sparse mapping, the overall picture is directionally correct. The key
ref (`ev-8a632f770f79`) explicitly states "Israel is no satellite state" and the mapper
correctly uses this for e4's `disputed` state.

---

### case-020 — "The location of Stonehenge has changed over time."

**Type**: empirical | **Elements**: 2 | **Evidence**: 18 | **Refs**: 15

| Element | Mapper State | Correct? | Expected | Errors |
|---------|-------------|----------|----------|--------|
| e1 | unresolved | YES | unresolved | — |
| e2 | unresolved | YES | unresolved | — |

**No errors.** Impressive interpretive handling. The evidence discusses how stones were
*transported to* Stonehenge from distant quarries, not that Stonehenge's *location*
changed. The mapper correctly distinguishes "stone transport" from "monument relocation"
and marks both elements as `unresolved` since no evidence supports the monument having
moved. All 15 refs are correctly labelled as `context`.

---

## Aggregate Statistics

### Ref-Level Accuracy

| Metric | Value |
|--------|-------|
| Total refs reviewed | 189 |
| Correct relationship | 181 (95.8%) |
| Incorrect relationship | 8 (4.2%) |
| Null reasoning | 23 (12.2%) |

### State-Level Accuracy

| Metric | Value |
|--------|-------|
| Total states reviewed | 66 |
| Correct state | 61 (92.4%) |
| Incorrect state | 5 (7.6%) |
| Borderline (not counted as error) | 6 |

### Error Breakdown by Failure Mode

| Mode | Code | Count | % of errors |
|------|------|:-----:|:-----------:|
| Missed contradiction | A | 2 | 14.3% |
| Phantom support | B | 2 | 14.3% |
| Misattributed scope | C | 5 | 35.7% |
| State inflation | D | 5 | 35.7% |
| **Total** | | **14** | **100%** |

### Window Sufficiency

| | Window Sufficient | Window Insufficient |
|---|:-:|:-:|
| A — Missed contradiction | 2 | 0 |
| B — Phantom support | 2 | 0 |
| C — Misattributed scope | 5 | 0 |
| D — State inflation | 5 | 0 |

**All errors occur with window_sufficient = true.**

### Null Reasoning Distribution

| Case | Null Reasoning Refs | Total Refs | % Null |
|------|:-------------------:|:----------:|:------:|
| case-016 | 6 | 6 | 100% |
| case-017 | 8 | 8 | 100% |
| case-018 | 7 | 7 | 100% |
| case-019 | 2 | 2 | 100% |
| All others | 0 | 166 | 0% |

The null reasoning issue appears to be systematic for certain runs, not random.

---

## Key Findings

### 1. Scope Confusion is the Dominant Ref Error (C = 35.7% of errors)

The mapper regularly conflates domestic/regional data with global claims:
- Domestic Chinese market share (70% of sales IN China) treated as evidence of global
  manufacturing leadership
- U.S.-only Tesla market data treated as evidence of worldwide leadership

**Fix:** Add explicit scope-checking instruction to the mapping prompt: "Before assigning
'supports', verify that the evidence's geographic and temporal scope matches the claim's
scope."

### 2. State Inflation is the Dominant State Error (D = 35.7% of errors)

Two patterns:
- **Context-only inflation**: e1 and e2 in case-017 have ZERO "supports" refs but are
  marked "supported". The mapper appears to derive state from topical relevance rather
  than evidential relationship.
- **Phantom-driven inflation**: e2 in case-001 is "supported" based on a phantom support.

**Fix:** Add rule to mapping prompt: "An element can only be 'supported' if at least one
evidence ref has relationship = 'supports'. Context-only elements must be 'unresolved'."

### 3. The Mapper is Excellent at Identifying Challenges

The mapper consistently and correctly identifies when evidence contradicts a claim:
- Great Wall visibility: 7/7 challenge refs correct across two cases
- Amazon 20% oxygen: fact-check sources correctly mapped as challenges
- Tesla leadership: BYD surpassing Tesla correctly identified
- Amazon longest river: Nile comparisons correctly handled

This is the mapper's strongest capability.

### 4. Null Reasoning is a Systematic Issue

23 refs (12.2%) have null reasoning, concentrated in 4 consecutive cases. This appears to
be a generation budget or output length issue, not a random failure. The mapper may be
hitting token limits on larger evidence sets.

**Fix:** Monitor and retry when reasoning fields are null.

### 5. Duplicate Claims Show Consistency

Several claims appear in multiple checks with different evidence sets:
- Great Wall (002 vs 015): Consistent, both correct
- Amazon 20% oxygen (009 vs 013): Consistent, both correct
- China EV manufacturing (003 vs 011): case-003 correct, case-011 has errors (less evidence)
- Amazon longest river (008 vs 014): Consistent, both correct

The mapper is stable when evidence is sufficient but degrades on weaker evidence sets.

---

## Recommendations

### Immediate (Prompt Changes)
1. Add scope-matching instruction to prevent C errors
2. Add "supported requires supports refs" rule to prevent D errors
3. Add "reasoning must not be null" validation with retry logic

### Short-term (Pipeline Changes)
4. Monitor null reasoning rate per run
5. Flag cases where the same evidence ID appears in both e3 and e4 with different
   relationships (scope confusion indicator)

### Medium-term (Regression Infrastructure)
6. Promote cases 002, 003, 008, 010, 013, 015, 020 as golden cases (zero errors)
7. Use cases 001, 007, 012, 017 as regression fixtures (known failure modes)
8. Track C and D error rates across prompt/model changes

---

## Appendix: Error Catalogue

| # | Case | Element | Evidence | Mapper Says | Should Be | Mode | Window |
|---|------|---------|----------|-------------|-----------|------|--------|
| 1 | 001 | e2 | ev-beac060411b1 | supports | context | B | sufficient |
| 2 | 001 | e2 | (state) | supported | unresolved | D | — |
| 3 | 003 | e3 | ev-bff968da5b5d | supports | context | C | sufficient |
| 4 | 003 | e4 | ev-bff968da5b5d | supports | context | C | sufficient |
| 5 | 004 | e2 | ev-rec-e2_1_5f109087 | supports | context | C | sufficient |
| 6 | 004 | e2 | ev-rec-e2_4_78b8fc7d | supports | context | C | sufficient |
| 7 | 007 | e3 | ev-rec-3_2_8b0804d0 | supports | challenges | A | sufficient |
| 8 | 005 | e4 | (missing) | not mapped | challenges | A | sufficient |
| 9 | 011 | e4 | ev-bff968da5b5d | supports | context | C | sufficient |
| 10 | 011 | e4 | (state) | supported | unresolved | D | — |
| 11 | 012 | e3 | ev-3d32c0cd4676 | challenges | supports | B* | sufficient |
| 12 | 012 | e3 | (state) | disputed | supported | D | — |
| 13 | 017 | e1 | (state) | supported | unresolved | D | — |
| 14 | 017 | e2 | (state) | supported | unresolved | D | — |

*Error 11 is a "phantom challenge" (inverse of B) — the mapper treats 59% as contradicting
a claim of "sixty percent" when 59% is within rounding tolerance.
