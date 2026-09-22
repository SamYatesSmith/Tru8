# The mapper is starved, not wrong — evidence-supply defect, measured

**Date:** 2026-09-22
**Status:** DIAGNOSED AND MEASURED against two stored production records. Not built.
**Trigger:** the founder asked whether the flaws named in the four wave-1 send notes are
pipeline errors or inefficiencies (they are errors), then asked for the proposed fix to be
reviewed for accuracy, quality and efficiency. **That review overturned the first draft of
this document.** The corrections are in §6.
**Blocks:** the 2026-09-22 batch of four emails — HELD.

---

## 0. One paragraph

Four records prepared for send on 2026-09-21 each contain at least one correctness error.
The first draft of this document blamed the mapping stage — "the mapper reads framing, not
sentences". **That was wrong.** The mapper reasoned correctly from what it was given; it
was given almost nothing. On the Katz record the mapper saw **4,282 characters of evidence
text while the public page displays 63,953** — a 14.9× gap. The deciding sentence in each
failure was captured, stored, persisted, and printed to the reader, and never reached the
stage whose job was to read it. The defect is the evidence-text supply between CLASSIFY
and MAP, and it has three separate causes.

---

## 1. The measurement

`GET /api/v1/checks/public/{id}?detailed=true` carries `textProvenance` per row. Comparing
the `snippet` the mapper is serialised against the `retained_characters` the page prints:

| Record | Rows | Mapper saw | Page shows | Ratio |
|---|---|---|---|---|
| Katz `b1954873` | 14 | **4,282 chars** | 63,953 chars | **14.9×** |
| Tidman `8d66d41a` | 21 | **6,008 chars** | 51,419 chars | **8.6×** |

By `content_basis`:

| Record | basis | n | mapper text (median) | article (median) | page shows (median) |
|---|---|---|---|---|---|
| Katz | distilled | 9 | **334** | 7,102 | 6,663 |
| Katz | full | 1 | 379 | 7,363 | 7,175 |
| Katz | snippet | 4 | 225 | — | — |
| Tidman | distilled | 5 | **163** | 4,461 | 4,461 |
| Tidman | full | 6 | **521** | **16,392** | 6,975 |
| Tidman | pdf | 1 | 282 | — | — |
| Tidman | snippet | 9 | 163 | — | — |

`EVIDENCE_SNIPPET_LENGTH` is 1,000. **The median item uses a third of it.** The mapper is
not truncation-bound; it is supply-bound.

Reproduce: `scratchpad/measure.py` (session scratchpad), or re-fetch the two payloads.

---

## 2. Cause 1 — the distiller discards counter-evidence (Katz)

The BBC row `ev-6b984c76f2a4` (`bbc.com/news/articles/cy4zejgz3z9o`):

- `extraction_characters = 6663` — **entirely inside** the distiller's 8,000-char window.
- The Thuringia sentence sits in passage 6, offsets **4,481–5,381**. The distiller read it.
- The text handed to the mapper is **483 characters, six facts**:

```
- The Alternative for Germany (AfD) won a decisive victory in Germany's eastern state of Saxony-Anhalt.
- Preliminary results show the AfD gained 43.8% of the vote compared to the conservative CDU's 17.2%.
- No far-right party has controlled a German state since World War Two.
- The AfD is heading for 39 seats in the 83-seat state parliament, which is three short of an outright majority.
- The left-wing populist BSW is set to win five seats.
- Turnout in Saxony-Anhalt was 77.8%.
```

- `"Thuringia" not in snippet` → **False**. It is absent.
- The mapper's stored interpretation — *"States that no far-right party has controlled a
  German state since World War Two, which addresses controlling a state rather than winning
  the most seats"* — **is fact 3, verbatim, correctly reasoned about.**

The mapper did not read past the sentence. The sentence was not there.

**Why the distiller dropped it.** `DISTIL_PROMPT` (`evidence_distiller.py:23`) asks for
"the atomic facts … relevant to evaluating the claim" and is given **the claim only** — the
elements are appended solely when `ENABLE_PASSAGE_MAPPING` is on (`:106`), and it is off.
The model behaved as a summariser: it wrote down what the article is about. Nothing in the
prompt says that a fact **contradicting** the claim is the most valuable fact in the
article. Neither bound was reached — 6 facts of a permitted 8, 483 chars of a permitted
1,000 — so this is a selection failure, not a capacity failure.

## 3. Cause 2 — the decisive document was never distilled (Tidman)

The inquiry's own summary report `ev-1d6962cf81e7`
(`thirlwall.public-inquiry.uk/summary-chapter/summary-report/part…`):

- `extraction_characters = 23788` — full text was fetched successfully.
- `content_basis = "full"`, **not `"distilled"`**. `content_basis` is set to `"distilled"`
  only on distiller success (`evidence_distiller.py:166`); `"full"` is what the fetcher set
  (`services/evidence.py:558`). **So distillation did not replace this item's text.**
- The mapper therefore received the item's **original snippet: 605 characters, for a
  23,788-character document.**
  ⚠️ **CORRECTED 2026-09-22 after review** — that fallback is NOT a search-engine snippet,
  as this document first said. It is `_find_relevant_snippet` (`services/evidence.py:522`,
  `:858-944`; semantic extraction default-on, `config.py:371`): the page's top ~3
  claim-similar sentences, ≤200 words, stored as `text_provenance.original_snippet`
  (`text_provenance.py:109`). It is page-derived and genuinely relevant — but selected
  against the **claim**, not the **elements**, which is exactly why an element-specific
  sentence at offset 11,676 loses. The mechanism stands; the characterisation was wrong.
- `"should be introduced"` sits in passage 8 at offsets **11,676–12,565** — and is printed
  on the page as retained excerpt 8.

So the record's conclusion that the inquiry's own report does not support the barring-system
element was reached from a Google snippet, while the page shows the reader the sentence that
settles it.

**This is the larger of the two causes.** Six of Tidman's 21 rows are `content_basis:
"full"` with a **median article length of 16,392 characters** — reaching the mapper as
~500-character search snippets. The pattern is adverse: **the longest and most
authoritative documents are the ones that arrive undistilled.**

⚠️ **Not yet established:** *why* they were not distilled. Candidates: the 15-second
`DISTIL_TIMEOUT` on a batch of five articles at up to 8,000 chars each (a failed batch
"keeps snippets for ITS items only", `:148-150`); `_full_text` absent by the time the
distiller ran; or items joining the pool after distillation. **This needs a log check
before any fix is chosen** — the three have different fixes. Whatever the cause, the
*silence* is a defect on its own: nothing warns that the mapper is judging a 24,000-char
document from 605 characters.

## 4. Cause 3 — an 8,000-character leading slice on a 23,788-character document

`evidence_distiller.py:184` — `full_text = (item.get("_full_text") or "")[:MAX_ARTICLE_CHARS]`,
`MAX_ARTICLE_CHARS = 8000`.

`select_passages` (`text_provenance.py:29`) windows **all** text; the distiller reads the
leading slice. For Tidman's inquiry report the deciding sentence is at 11,676 — **so even
had distillation run, it would not have seen it.** Causes 2 and 3 compound on the single
most important document in that record.

The code to fix this already exists and is gated behind the wrong flag (`:185-192`): under
`ENABLE_PASSAGE_MAPPING`, the distiller reads the retained passages instead of the leading
slice.

## 5. What the mapper does with numbers (Kennedy, Legum) — a separate defect

Cause 1–3 do not explain Kennedy's 88%-filed-as-supporting-83%, or Legum's part-period
figures summed into a full-period range. There the deciding numbers **were** present and
were accepted as matching. `MAPPING_PROMPT` already forbids this in three rules
(TOPIC vs FIGURE `:401`, FINDING NOT TOPIC `:407`, CONTEXT DISCIPLINE) — all of which
address evidence that **omits** the figure. **None addresses evidence stating a different
value of the same measure.** That gap is real and is not a supply problem. See F2.

---

## 6. Corrections to the first draft of this document

Recorded because the founder's review request is what produced them, and because three of
them would have wasted a build.

| # | First draft said | The records show |
|---|---|---|
| 1 | "The mapper reads framing, not sentences" — the mapping stage is the defect. | **Wrong.** The mapper's interpretation is distilled fact 3 verbatim. It reasoned correctly from a 483-char input. The defect is upstream, in supply. |
| 2 | Cause is the 8,000-char leading slice (N1) plus claim-not-elements (N2). | **Half wrong.** Katz's article is 6,663 chars — wholly inside the window. N1 is innocent there. N1 *is* implicated on Tidman (deciding sentence at 11,676). Different records, different causes. |
| 3 | **F1a**: "feed the distiller the retained passages instead of the leading slice — free, may close most of it." | **Near-useless as stated.** For a typical article the passages *are* the article (Katz: retained 6,663 of 6,663; Tidman distilled rows: 4,461 of 4,461). Feeding passages changes nothing below ~7,200 chars. It is an **overflow strategy for long documents only** — worth doing for that, not as the main fix. |
| 4 | **F1 efficiency**: route per element using `matched_element_ids` to cut tokens. | **Dead.** `matched_element_ids` is `['e1','e2','e3']` on essentially every window, because it counts **any** term overlap with no normalisation (`text_provenance.py:78`). It is not selective and yields no saving. |
| 5 | F1 costs "~7× the mapping input". | **Understated.** Measured 8.6× (Tidman) and 14.9× (Katz) — 4k–6k chars today against 51k–64k. |
| 6 | Cause is a single defect across all four records. | **Wrong.** At least three distinct causes, plus a fourth (numeric tolerance) that is not a supply problem at all. |

**The method that produced the corrections is the reusable part:** the stored public payload
carries `textProvenance` with character offsets and the exact `snippet` the mapper was given.
Any claim about what a stage saw can be settled from a finished record, for free, in one
fetch. It should not have been asserted from code-reading alone.

---

## 6A. VERIFIED by local reproduction — cause found, fix proven

Run 2026-09-22 against the four documents the Tidman record skipped, using the real
`EvidenceDistiller`, the real model (`gemini-3.5-flash-lite`), the real batch composition
and the real 8,000-char cap. **Extraction lengths matched production to the digit**
(19,623 / 9,230 / 13,162 / 23,788), so the reproduction is faithful.
Scripts: `scratchpad/repro_distil.py`, `repro_fix.py`, `repro_passages.py`.
Total spend: ~18k input tokens on Flash-Lite, well under 1p.

### The cause, confirmed

**The distiller returns empty fact lists for substantive, on-topic documents.**

| Document | chars | facts returned |
|---|---|---|
| inquirytracker.uk | 19,623 | **0** |
| mamaacademy.org.uk | 9,230 | 1 |
| independent.co.uk | 20,353 | **0** |
| madeformums.com | 13,162 | **0** |
| thirlwall.public-inquiry.uk (the inquiry's own report) | 23,788 | **0** |

Exactly the production pattern. Ruled out on the way: **batch failure** (the skipped items
interleave with successes inside one batch) and **front-matter** (all five open with
substantive, on-topic prose). Two further "full" rows — 491 and 337 chars — are correct
behaviour, below `DISTIL_MIN_TEXT_LENGTH = 500`.

`DISTIL_PROMPT` asks for facts "relevant to evaluating the claim" and says "If an article
contains NO relevant facts, return an empty list." Given the fused claim sentence, the
model applies a very high relevance bar and returns nothing for a document about the
inquiry's 17 recommendations. The pipeline then **silently** substitutes the Google search
snippet — `_parse_response` treats "no facts" and "call failed" identically, and neither is
logged per item.

### The fix, tested

**B — elements appended + a rule that counter-evidence is the most valuable fact:**

| Document | A (current) | B (candidate) |
|---|---|---|
| inquirytracker.uk | 0 | 1 |
| mamaacademy.org.uk | 1 | 3 |
| independent.co.uk | 0 | 0 (residual) |
| madeformums.com | 0 | 1 |
| thirlwall.public-inquiry.uk | 0 | 2 |
| **total** | **1** | **7** |

Cost: +106 input tokens for the batch. Negligible.

**B still did not recover the deciding sentence**, because *"A statutory barring system for
managers should be introduced"* sits at offset **11,676 — past the 8,000-char cap**.
Measured directly: `decisive sentence present in leading 8000: False`.

**B + passages as input (D3):** feeding the *stored* retained passages (7,190 chars, inside
the same cap) instead of the leading slice returns, verbatim:

> "A statutory barring system for managers should be introduced but, having been introduced
> and operated, it should be reviewed with a view to moving to…"

**That is the sentence the record got wrong, recovered from the document the record
misfiled, at 1,723 input tokens.**

### What this establishes

1. D2 (elements + counter-evidence rule) and D3 (passages for long documents) are **both
   required**; neither alone recovers the Tidman failure.
2. D1 (never fall back silently to a search snippet) is the safety net — `independent.co.uk`
   still returned 0 under B, so the fallback path will keep being taken.
3. The fix is cheap: one prompt change, one input-selection change, one guard. **No
   architectural change and no meaningful token cost.** D4 (handing the mapper all passages,
   9–15×) stays deferred and may never be needed.

---

## 6B. Independent review (Fable 5.1, 2026-09-22) — NOT SAFE TO BUILD AS WRITTEN

Read-only verification against the codebase, commissioned by the founder to check scope and
placement. **Core diagnosis upheld** — C1, C2, C3, C4 all VERIFIED (C3 "stronger than the
doc says"). The *plan* required eight changes, applied above and below.

**Where the provenance capture actually happens (for whoever builds this):**
`runner.py:2067`, before the classify/distil block, **with the claim-map elements and under
no flag** — which is why the stored passages are element-matched even with
`ENABLE_PASSAGE_MAPPING` off. The call at `evidence_distiller.py:104` is a no-op repeat
(`text_provenance.py:91` early-returns when a receipt exists). Also note the scope gates
read the **same** text the mapper does: `_index_evidence` builds gate text from title +
snippet (`claim_map_analyzer.py:1584`).

**Errors in this document that the review refuted:**

| Claim here | Finding |
|---|---|
| "Elements are already passed into the function" (D2.1) | **False.** `runner.py:2158-2166` and `re_search.py:117` gate them too. Deleting `:106` alone is a no-op. |
| "search-engine snippet" (§3, D1.3) | **False.** `_find_relevant_snippet` — page-derived, claim-selected, ≤200 words. |
| "prefer contradicting facts" (D2.2) | **Invariant 7 breach.** Directional supply bias. §6A arm B used it, so that measurement is not clean. |
| "Raise `DISTIL_MAX_FACTS_PER_ITEM`" (D2.3) | **Inert** — cap never reached (0–6 of 8). |
| §8 Tidman expected answer | **Unreachable without F3** — see below. |
| §3/§9 step 2 "read the distil logs first" | **Stale** — superseded by §6A, which found the cause by reproduction. Delete. |

**Hard blocker found — §8's Tidman target cannot pass under D1–D3 alone.** The
interested-party gate fires on **URL alone** (`claim_map_analyzer.py:2770`;
`interested_party.py:262-270`, label-START match). If the claim's subject set contains
"Thirlwall Inquiry", the token `thirlwall` matches the label of
`thirlwall.public-inquiry.uk`, so **the inquiry's own report is scoped to `context`
whatever the mapper decides.** F3 must land before or with D1–D3. (Unconfirmed without the
record's `metadata.subjects`.)

**Blast radius the document missed:**
- **Bench re-record owed in the SAME COMMIT as D2** — all 10 corpus cassettes contain
  flash-lite `generateContent` calls and the signature is `sha256(body)`
  (`scripts/replay_bench/cassette.py:156-172`). Any distil-prompt change drifts every claim,
  and changed evidence text re-keys every mapping cassette.
- **Scope gates read the same text** the mapper does — `_index_evidence` builds gate text
  from title + snippet (`claim_map_analyzer.py:1584`). Changing supply changes the lexical
  input to the temporal, date_scope, measure, jurisdiction and recital gates. The tolerance-0
  corpus pins (`temporal_scoped_refs` on 0005; recital / interested-party on 018F) may move.
  **Run the control arm before reading any pin movement as a regression.**
- Manifest signing is safe: `content_basis` is signed at sign time (`manifest_signer.py:112`,
  `:179`), after these stages; a new value is handled (`comparison.py:195/203` only
  special-cases "full").

**Flags (review recommendation, adopted):** D2 **default-on, no flag** — it is the input the
stage was designed for, and a flag adds a third branch. D3 behind its own rollback flag; add
it to `compute_pipeline_fingerprint` since it changes model input. Confirmed a new D3 flag
enables **none** of the 13 other things `ENABLE_PASSAGE_MAPPING` switches on.

**A simpler complement the document missed.** A mechanical, no-prompt top-up: after
distillation, append the top element-ranked retained passage to any item whose mapper text
is under `EVIDENCE_SNIPPET_LENGTH`. Deterministic, unit-testable **without paid runs**, uses
data already stored, and attacks the measured "median item uses a third of its budget"
directly. Weigh against D1.3.

**Tests.** Breaks: `test_evidence_distiller.py:104-120` and `:124-138` (assert the fallback
keeps original text); `test_re_search_payload_integration.py:84` — its mock is
`async def distil(text, items)`, so an `elements=` kwarg raises `TypeError`. Pins owed: the
prompt contains "Research elements:" with the flag **False**; a runner-level test that
`_distil_one_claim` passes elements with the flag False; a 9,000-char `_full_text` with a
marker at ~8,500 inside a retained window, present in the prompt with D3 on and absent off;
`caplog` WARNING naming the `evidence_id` on empty facts and on batch failure.
**Nothing in the suite would have caught this defect** — no test asserts that an item with
`text_provenance` never reaches the mapper as `content_basis == "full"`, and no corpus
golden pins `content_basis_breakdown`. A runner-level invariant test with a mocked distiller
returning `[]` fails today and should be the first thing written.

---

## 7. The fix, re-derived — cheapest and most certain first

### D1 — Make undistilled full-text items impossible (targets Cause 2)

**Invariant:** *no item whose full text was fetched may reach the mapper as a search snippet.*

1. Log a warning naming the item whenever distillation fails or is skipped for an item
   holding `_full_text`. Today this is silent.
2. Retry the item singly on batch failure (batch failure is the prime suspect and a single
   item is a small prompt).
3. ⚠️ **REVISED after review.** The original step 3 — "hand the mapper the leading passages
   rather than the search snippet" — rested on the false "search snippet" premise and on
   "leading" being a relevance order. It is not: passages are **offset-sorted**
   (`text_provenance.py:82`). Either drop this step, or implement it as:
   rank with `rank_passages(valid_passages(item), element_terms)` (`passage_mapping.py:15`);
   write to `item["text"]` and **never** to `item["snippet"]` — the classifier reads
   `snippet` concurrently and the two stages are documented as writing disjoint fields
   (`runner.py:2208-2210`); let `finalize_distilled_payload` do the copy
   (`text_provenance.py:117`, which acts only when `_distilled`); and set
   `provenance["derivation"]` (`:169`) or the receipt shows text that is neither
   `original_snippet` nor `derived_text`.

   **Scope gap (review):** coverage-recovery items (`retrieve.py:1225-1247`) are built with
   **no `_full_text`** — never distilled, no `text_provenance`, `content_basis` inherited
   from the fetcher. D1's invariant as written does not cover them, and §8's
   "`content_basis: full` count → 0" metric **cannot reach zero** while they exist. Either
   bring them into scope or state them out and drop that metric.

Cost: no extra model calls in the normal path; one retry on failure. **First step is the log
check** — it decides between retry, timeout raise, and ordering fix.

### D2 — Distil against the elements, and keep contradicting facts (targets Cause 1)

1. **THREE call sites, not one** (corrected after review — the original claim that "they
   are already passed into the function" was **false**): the elements never reach the
   distiller in production because the *callers* gate them too.
   - `evidence_distiller.py:106` — the prompt-append gate.
   - `runner.py:2158-2166` — the runner passes `elements` **only** under
     `ENABLE_PASSAGE_MAPPING`.
   - `re_search.py:117` — same, for Seeker re-search. Must change together or re-search
     distils differently from the main run.
   Deleting `:106` alone changes nothing.
2. Add to `DISTIL_PROMPT` a requirement to extract facts that **bear directly on any
   element** — ⚠️ **written SYMMETRICALLY.** The wording first proposed here ("prefer facts
   that contradict…") is directional supply bias and breaches invariant 7. Correct shape:
   *facts bearing directly on any element, confirming OR contradicting it, outrank facts
   about the article's general subject.*
   ⚠️ **§6A's arm B used the biased wording**, so its 1→7 result is not a clean measurement
   of the symmetric rule. **Re-measure before building.**
3. ~~Raise `DISTIL_MAX_FACTS_PER_ITEM`~~ — **dropped.** Inert for this defect: the measured
   returns were 0–6 facts of a permitted 8, so the cap was never reached.

⚠️ This is a prompt change, and `feedback_nf11_prompt_only_failed` warns that fragile fixes
need a mechanical rule. The distinction that makes it askable here: in NF-11 the information
was **absent from the payload**, so no prompt could comply. Here the sentence is in the
input and is being discarded by a summariser given no instruction to keep it. That is a
prompt-shaped defect. **It still needs measuring, not assuming** (§8).

### D3 — Read long documents by passage, not by prefix (targets Cause 3)

Use the retained passages as the distiller's input **when `len(full_text) > MAX_ARTICLE_CHARS`**,
keeping the leading slice below that. The code exists at `:185-192`; it needs the size
condition and its own flag, not `ENABLE_PASSAGE_MAPPING`.

⚠️ **Do not ship this by enabling `ENABLE_PASSAGE_MAPPING`.** That flag also switches on
`fact_applicability` and `relationship_scope_review`, which the 2026-09-09 regrade found
**not ready** (over-scopes day-scoped values; binds quotes to the wrong element).

### D4 — Give the mapper the passages directly (deferred)

The first draft's F1. Now measured at **8.6–14.9×** the mapping input. Defer until D1–D3 are
measured; if they close the gap, this is never needed. If built: its own flag, a per-item
character budget chosen from measurement, and a bench re-record in the same commit.

### F2 — A numeric-mismatch gate (targets §5, independent of all the above)

Where an element states a figure and a reference is directional, require a matching figure
within a stated tolerance or the element's own qualifier; otherwise re-label `context` with
a receipt naming both figures. Build as a scope gate alongside the existing eight.
⚠️ Gate **order** is behaviour; **one gate owns a reference** (the `break`); a new gate
**must** join `_SCOPE_RECEIPT_KEYS` or both merge paths drop its receipts. Must be
**symmetric** — scoping `supports` exactly as `challenges`, or it is a sycophancy mechanism
(invariant 7). Design owed.

### F3 — Attribution-claim gate mis-fires (unchanged, and now more urgent)

Recital and interested-party gates strip directionality when the claim's **subject** is an
institution's own statement (Tidman ×3, Legum ×1). On Tidman these mis-fires **accidentally
corrected** a mapper error: raw weights were supports 12 vs challenges 6, an exact 2× tie →
`close_split` → **DISPUTED**. **Fixing supply without fixing F3 could make that element read
DISPUTED on a live NHS-policy claim.** D1–D3 and F3 must be measured together.

---

## 8. How to verify — and what cannot verify it

**Cannot:** the replay bench. Two recordings of one claim an hour apart with identical
settings differed by 25 of 40 URLs; a change of this kind is invisible in that noise. The
bench confirms **no drift**, never **improvement**. A single before/after pair is not
evidence — run a control arm.

**Can, for free:** the supply metric itself. `measure.py` reports mapper-chars vs
page-chars per record from the public payload. D1 should drive the `content_basis: "full"`
count to zero; D2 should raise the distilled median well above 334 chars. Neither needs a
paid run to check on **existing** records — but confirming the *new* behaviour needs new
checks.

**The real test — a known-truth set.** These four records have documented right answers:

| Record | Element | Correct answer |
|---|---|---|
| Katz `b1954873` | 03 "first since 1933" | **challenged** (BBC: AfD won Thuringia 2024) |
| Legum `5c443ac3` | 02 "$898m–$2.87bn" | **context-only** (no source states the range) |
| Kennedy `60d43292` | 02 "83% seasonal norm" | not supportable on 85%/88% |
| Tidman `8d66d41a` | 02 barring system | **supported**, with the inquiry's own report as `supports` — and it must **stay** supported (F3) |

Re-run all four after any build and score against those answers. ~£0.60 at 15p.
**Ask before running — founder rule, any amount.**

This set did not exist before 2026-09-22. It is the founder's own proposal — *where the
truth is known, grade the output against it* — and it should be extended and kept.

---

## 9. Recommended order

1. **Hold the batch.** (Done.)
2. ~~Read the distil logs~~ — **deleted.** §6A found the cause by reproduction; the logs are
   aggregate-only and cannot identify a per-item outcome.
3. **Write the failing test first** — runner-level, mocked distiller returning `[]`, assert
   no item with `text_provenance` reaches the mapper as `content_basis == "full"`. It fails
   today. Nothing in the suite currently catches this class.
4. **F3 / interested-party first or alongside** — §8's Tidman answer is unreachable without
   it (§6B).
5. **D2** (three call sites, symmetric wording) → **D1** → **D3**. Re-measure the symmetric
   prompt before building; arm B's 1→7 used biased wording.
6. **Bench re-record in the same commit** as D2. Control arm before attributing any pin
   movement.
7. Re-run the four-record set. Score against §8 (with the Tidman row corrected for F3).
8. **F2** design.
9. **D4** only if the set still fails.

## 10. What this changes about the send process

§4C–§4E of `audit/2026-09-11_outreach_operating_procedure.md` check that a record is
*presentable* and that a note is *accurate about the record*. Neither asks **"is the record
right?"**, and a fresh fact-check agent comparing note to record cannot catch an error both
share. All four notes then named their record's error as "the seam" — so the B+ grades
graded **disclosure**, not correctness, and the sales pitch disclosed the bug.

**Procedure change owed:** a correctness gate before the note is written — for each element,
does the pool's own retained text justify the badge? Hold on failure; log the flaw as a
product observation. That would have caught all four before any note was drafted.

## 11. Open questions for the founder

1. **Does "name the seam" survive?** Defensible for a *coverage gap* ("no primary source
   states this" — the product working). Not defensible for a *correctness error*.
   Suggested: keep for gaps, never for errors; hold the record instead.
2. **Does this breach "no pipeline work until strangers exist"** (`OUTREACH.md`)? Strictly
   yes. The counter-argument: the rule exists to stop the machine being polished instead of
   sold, and this is the one defect class that makes sends counterproductive.
3. **D1's log check** needs a Railway look (`railway ssh` — `railway run` cannot reach the
   prod DB). Founder access.
