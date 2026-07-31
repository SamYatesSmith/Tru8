# Phase 3 — mapper answeredness: MEASURED, headline DECLINED; P3-A built

**Date:** 2026-07-31
**Status:** measurement complete · headline item **declined on evidence** · **P3-A BUILT**
**SOT row:** `audit/DECOUPLING_STATE.md` · register: `audit/OPEN_WORK.md`
**Precedent this follows:** factual-path atomicity, measured at 0.8% on 2026-07-30 and
**declined rather than built**. Measuring first is what made Phase 3a credible; measuring
first is also what stops Phase 3 shipping a mechanism nothing needs.

---

## 1. What Phase 3 was for

Phase 1 (`007cf5c`) stated its own limits, in writing, so they could not be quietly claimed
later:

> `TRU-4B9D-65EA` e01/e02 will probably still read `supported`, because 4 and 3 sources clear
> the floor even though the evidence did not answer the question. **The headline verdict line
> dies; two element badges remain wrong.** Those are Phase 3, and they need the Phase 2 pool
> to tune against.

The witness is damning because **the mapper contradicted itself**. On *"The UK COVID vaccine
rollout was a triumph"* all four grounds came back `+SUPPORTED` while every one of the
mapper's own `reasoning` strings said the evidence did not answer — *"not fully detailed"*,
*"not provided, nor is a direct comparison"*, *"does not specify"*, *"not explicitly
provided"*. An element badged `supported` off prose that says nothing was established is
invariant #7 in the sycophantic direction, on a positive-valence claim.

Two things were owed:

* **P3-HEADLINE — answeredness.** Stop the mapper filing non-answering sources as `supports`.
* **P3-A — the grounds predicate.** Carried from Phase 1 §4b: `_grounds_applied` tests whether
  the grounds STAGE RAN, not whether its elements are questions.

---

## 2. P3-HEADLINE — measured on the post-Phase-2 pool, and declined

### 2.1 Method

`backend/scripts/mapper_answeredness_census.py`. Six real, networked checks through the live
pipeline — **both valences deliberately** (a positive head over-supporting is sycophancy; a
negative head over-supporting is the same defect pointed the other way, and measuring only
negative claims would report half the problem). For every grounds element it records each
`supports` ref's `relationship` and the mapper's own `reasoning`, then counts elements badged
`supported` whose supporting refs are, in the mapper's own prose, non-answering.

**The first battery entry is the witness claim itself**, so this is a re-test of the original
failure and not merely a survey of adjacent ones.

The phrase list is tuned for **recall, and is not proposed as a fix** — a blocklist cannot
close an open set (the evaluative-head lesson). Every flagged ref, and on inspection every
ref, is printed verbatim so the number can be checked by eye rather than trusted.

### 2.2 Result

| measure | value |
|---|---|
| grounds elements | 23 |
| ... badged `supported` | 15 |
| **... HOLLOW (supported, every support non-answering)** | **0** |
| ... partly hollow | 0 |
| supporting refs | 72 |
| **... non-answering by the mapper's own prose** | **0** |

**The witnessed defect did not reproduce.** The supporting reasonings now cite concrete
answering content — *"over 90% of those aged 12 and over"*, *"87.4%"*, *"£92,412 in 2016"*,
*"£87.7bn to £102.7bn (2025 prices)"*, *"no increased rate of sudden death"*. Nothing
resembling *"does not specify"* survives anywhere in the sample.

**Blindness check, because 0.0% earns scepticism rather than a tick.** A deliberately weaker,
broader hedge scan (`implies|suggests|indirect|partial|not |no |without|unclear|however…`)
was run over all 72 reasonings. It returned 10, and on inspection 8 are ordinary evidential
hedging wrapped around hard figures. The census is not under-powered; the defect is absent.

### 2.3 Why it vanished — and why that was predictable

`DECOUPLING_STATE.md` already said it: *"the root cause of all three is that the questions
were never searched."* Phase 2 wired element-level retrieval, so the sub-questions are now
searched and answering evidence is actually **in the pool**. The mapper was never mainly
guessing; it was labelling a pool that contained no answers. Fix the pool and the labels
follow. The F7 re-gold measured the same change from the other side — primary-tier evidence
rose on every corpus claim.

**This is the second time in two days that a defect was found already closed by an upstream
structural fix** (factual-path atomicity was the first). That is a pattern worth naming: on
this pipeline, tuning a downstream judgement is usually the wrong instinct.

### 2.4 Recommendation — DECLINE, do not build

Building an answeredness mechanism against a **0/15 and 0/72** rate would add a prompt
contract and a mechanical gate to the one path currently working, and would need tuning
against examples that no longer occur. **Closed as measured-and-declined, not as done.**

### 2.5 Honest limits of this measurement

* **n is small** — 6 claims, 23 elements, 72 refs. This rules out a HIGH rate. It does not
  prove zero.
* It only sees claims that took the grounds path.
* Nondeterminism is real: an earlier 2-claim run flagged 1 of 29 where the 6-claim run flagged
  0 of 72. The signal is "rare", not "never".

### 2.6 One residual, logged for monitoring rather than fixed

A softer, different defect appears twice in 72 (~2.8%): **a quantitative question answered by
qualitative evidence, filed as a full support.**

* *"What proportion of claimants experienced significant difficulties navigating…?"* supported
  by *"claimants were 'scared' of Universal Credit, suggesting apprehension"*.
* *"What was the estimated impact of the furlough scheme on unemployment rates?"* supported by
  *"the CJRS's purpose was to avoid redundancies"* — purpose, not estimated impact.

The evidence genuinely bears on the question; it just does not reach the precision the
question asked. This is **materially milder than the witness** and does not justify a build on
this evidence. **Monitor; re-measure if a live report shows it compounding.**

---

## 3. P3-A — the grounds predicate now means what its callers assume

### 3.1 The defect, code-confirmed

`apply_grounds_stage` has a lock-collapse path: when the value-predicate lock rejects every
candidate ground, the rebuilt set is empty, so the **BASELINE ASSERTION elements are restored**
— and the map is still marked `applied: True`.

`_grounds_applied` read only `applied`, and it is the single gate for three behaviours. So on
that path, assertion-shaped elements were:

1. given `GROUNDS_MAPPING_ADDENDUM`, which instructs the mapper to grade whether/extent
   **questions**;
2. judged against `GROUNDS_MIN_WEIGHTED_SUPPORT` (3), a bar designed for *"did we find out?"*;
3. **stripped of orientation**, on the reasoning that summing question elements reads as a
   verdict on an opinion — which is not true of assertions.

### 3.2 The fix, and the trap Phase 1 nearly set

Phase 1 §4b tentatively proposed `applied and converged`. **That would have been a worse bug.**
`converged` is False for *two* different reasons:

```python
converged = not lock_collapsed and len(final) >= min(BREADTH_FLOOR, MAX_ELEMENTS)
```

— the collapse, **and** a set that is genuinely question-shaped but thinner than the breadth
floor (pinned by the pre-existing `test_thin_set_discloses_not_fails`). Keying on `converged`
would have stripped the addendum, the floor and the suppression from **real questions**.

`converged` cannot carry two meanings, so the collapse is disclosed on its own key:

* `opinion_symmetry.py` — grounds metadata gains `"collapsed": bool(lock_collapsed)`.
* `claim_map_analyzer.py::_grounds_applied` — returns False when `collapsed is True`.

**Single point of change.** All consumers (addendum selection, `_grounds_floor`, orientation
suppression, batch partition, completion and recovery passes) already funnel through this one
predicate, which is why Phase 1 named it the place to fix once.

**Back-compatible by construction:** a claim_map persisted before the key existed has no
`collapsed`, reads as not-collapsed, and keeps exactly its current behaviour.

**`is True`, not truthiness** — this runs on every mapping call and must degrade to
"not collapsed" on corrupt metadata rather than silently disabling grounds handling.

### 3.3 Bench exposure: none, and this is why it could ship now

Phase 1 deferred this partly because changing `_grounds_applied` alters which prompt is built,
which invalidates cassettes. **It does not, for this corpus.** All 8 replay claims are factual,
never take the grounds path, and carry no `metadata.grounds` at all — so the predicate returns
False before and after and every corpus prompt is byte-identical.

### 3.4 Evidence

* Suite **2,986 passed / 0 failed / 69 skipped** (was 2,981 — the 5 new tests).
* **Mutation matrix 5/5 FIRE** (`scripts/p3a_mutation_matrix.py`), files restored and
  SHA-verified after each. A green test file is not evidence it pins anything.

| mutation | test that must fail | result |
|---|---|---|
| drop the `collapsed` check | `test_lock_collapsed_map_is_not_treated_as_grounds` | FIRES |
| use `applied and converged` (the §4b trap) | `test_thin_but_genuine_question_set_is_still_grounds` | FIRES |
| stop disclosing collapse | `test_lock_collapse_restores_baseline_but_discloses` | FIRES |
| always disclose `collapsed: True` | `test_collapsed_is_false_when_the_rebuild_actually_produced_questions` | FIRES |
| truthiness instead of `is True` | `test_collapsed_only_disables_on_exact_true` | FIRES |

**The mutation harness found its own bug first:** the initial version restored files with
`write_text`, which on Windows rewrites `\n` as `\r\n`, so two anchors silently stopped
matching and two mutations reported as unrunnable. The SHA guard caught it. Byte-mode restore
now. A harness that cannot restore its tree cannot be trusted to have tested it.

### 3.5 What P3-A does NOT do

It does not change behaviour on any claim that does not hit lock-collapse — which is the
overwhelming majority. This is a correctness fix on a **rare** path, justified because the
path's behaviour was **known-wrong and code-confirmed**, not because it was measured as
frequent. That is a different and weaker justification than Phase 3a's 21.2%, and is recorded
as such rather than dressed up.

---

## 4. Verification status — stated plainly

**This build was verified by the pass that wrote it.** Phase 3a carries the same caveat and it
is recorded here for the same reason: it is a real weakness, not a formality. An independent
pass re-deriving §3.4 from the frozen criteria is owed before this is treated as proven.

## 5. Rollback

P3-A has no flag. It is two small edits; revert `_grounds_applied`'s `collapsed` branch and
the metadata key. No migration, no stored-data change, no prompt change on the factual path.
