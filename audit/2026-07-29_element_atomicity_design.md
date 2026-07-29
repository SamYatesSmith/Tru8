# Element atomicity — Phase 3a design

**Status:** ✅ **BUILT 2026-07-29** — committed, NOT pushed. Acceptance GREEN (§7: 21.2% →
0.0%, mixed-shape → 0.0%). 36 tests, 13/13 mutations caught, zero regressions.
**Verification is NOT independent** — the same pass built and verified it.
**Date:** 2026-07-29
**SOT chain:** `audit/OPEN_WORK.md` → `audit/DECOUPLING_STATE.md` → this doc.

---

## 1. The defect, measured

A Claim Map element is supposed to be one question. It often is not.

**Battery, live decompose+grounds path, 20 evaluative claims → 80 elements**
(`backend/scripts/compound_question_battery.py`, log
`backend/scripts/.compound_question_battery.log`):

| | count | share |
|---|---|---|
| Elements asking two questions at once | 17 | **21.2%** |
| ...of which the two halves take **different grading rules** | 11 | **13.8%** |
| Claims with ≥1 compound element | 8 | **40%** |

Two independent runs produced ~the same rate over a **different set of claims** — this is
the prompt, not particular topics. The splitter under-counts by design (it splits only on a
coordinator followed by an interrogative head), so 21.2% is a **floor**.

### Why it breaks grading

`GROUNDS_MAPPING_ADDENDUM` (`claim_map_analyzer.py:302-334`) opens with *"Decide which kind
a question is BEFORE mapping evidence to it"* — **one shape per element**. A mixed-shape
compound has two:

> *"What are the projected passenger numbers and revenue forecasts for the HS2 line,
> **and how do these compare to initial estimates?**"*

- Half 1 is enumerative — any document listing forecasts is `supports`. **Trivially satisfiable.**
- Half 2 is directional — this is the half that bears on *"catastrophic waste of money"*.

Whichever shape the mapper picks, the other half is graded by the wrong standard. In
practice the easy half accumulates `supports`, state derivation is mechanical on per-element
counts, and the element badges `supported` while the judgement-bearing half was never
assessed.

**This is `TRU-4B9D-65EA` by construction** — all 4 grounds `+SUPPORTED` while every summary
said the evidence supplied nothing. It also explains why that check survived Phase 1: the
`GROUNDS_MIN_WEIGHTED_SUPPORT=3` floor is cleared by three sources answering the trivial half.

### Same-shape compounds are a separate failure

The other 6 (`"What were the costs, and what were the recoveries?"`) don't break the shape
rule — they break **answeredness**. One half answered badges the whole element. Phase 3's
threshold cannot fix this either, because there is no sub-element unit to threshold.

### Root cause

**No atomicity rule exists anywhere.** Verified by grep over `opinion_symmetry.py` for
`atomic|one question|conjunction` — no matches. `NORMATIVE_DECOMPOSE_PROMPT`
(`opinion_symmetry.py:51-70`) asks for open questions and says nothing about how many
questions each may contain. `extract.py` Rule 3 enforces atomicity for *claims*; nothing
does for *elements*.

---

## 2. Scope — every consumer of element text

Widened deliberately; the defect is not confined to the mapper.

| Consumer | Code | Effect of a compound element |
|---|---|---|
| **Retrieval lanes** | `retrieve.py:250-257` — `description` **is** the lane query | A two-part question is a poor search string. **Post-D3 this is the *only* search surface.** |
| **Re-search / Seeker** | `re_search.py:126,141,190` | Targeted re-query inherits the compound question |
| **Mapper (grounds)** | `claim_map_analyzer.py:302-334` | The found defect — one rule, two shapes |
| **State derivation** | `_derive_element_state_with_authority:699` | Mechanical, per element. The element is the atom; there is no half-element |
| **Scope tagger** | `scope_sensitivity.apply_scope_flags` | Two halves can carry different geographic reach; flags collapse to one |
| **Support structure / F4** | `support_structure.py` | Echo/thin/repetition annotated per element |
| **Frontend** | element cards, `/r/` | Users read the compound question and the single badge |
| **Manifest** | canonical payload | Descriptions are signed — new checks only, no back-compat issue |

**The finding that changes priority:** D3 (founder-decided 2026-07-28) makes element text the
**sole retrieval surface** — the claim text stops being a query. Atomicity therefore stops
being a mapping-quality question and becomes a **retrieval-quality** one. Landing D3 on
compound elements would ship a known-degraded search surface.

→ **Atomicity must land before D3, not after.**

### Factual path — real, unmeasured, deliberately deferred

`DECOMPOSITION_PROMPT:187` says *"Each element description must be a single clear
sentence"* — a single sentence is freely compound (*"Expenditure exceeded £37bn and delays
reached five years"*). The two-shape rule does not apply to assertions, so the failure mode
differs (partial support badges the whole), but the **retrieval** consequence is identical.

`compound_element_census.py` measures this path and **could not run** — local Postgres is
down (Docker Desktop: *"Virtualization Enabled In Firmware: No"*). Not built here. Stated as
a known gap rather than silently omitted.

---

## 3. Design principles

1. **Mechanical guarantee, not a prompt rule.** [NF-11's lesson](../.claude/CLAUDE.md):
   fragile fixes need a mechanical post-processing rule. A prompt line is the first line of
   defence, never the guarantee.
2. **Honesty before capability.** The backstop (§4E) closes the mis-grading even if every
   LLM step fails. It ships regardless of how well repair performs.
3. **Never fail a live check.** Matches `apply_grounds_stage`'s existing discipline — any
   exception preserves the originals.
4. **Change nothing that is locked.** The Claim Map contract (1 map/claim, 1-5 elements) and
   the retrieval budget stay exactly as they are.

---

## 4. The design

### A. Prompt rule (first line, cheap)

Add to `NORMATIVE_DECOMPOSE_PROMPT`:

> Each question must ask **exactly one thing**. Never join two questions with "and" or "or".
> If a question has two parts, ask the part that bears most directly on the judgement.

Costs nothing, catches most cases, guarantees nothing.

### B. Mechanical detector (shared, testable)

Promote `conjuncts()` / `is_compound()` from the two scripts into `app/utils/atomicity.py`.
Conservative rule, already validated across 40 real elements: split only where a coordinator
is followed by an **interrogative head** (wh-word, "to what extent", or auxiliary+subject
inversion).

**Must not split conjoined noun phrases** — *"efficacy and evidence base"* is one question.
The interrogative-head requirement is what prevents this, and it gets a dedicated pin.

Shape classifier (also from the battery): directional (`whether` / `to what extent` /
aux-initial) vs enumerative (`what` / `which` / `how many`).

### C. Repair pass — rewrite, do not split

When any candidate is compound, **one** LLM call rewrites only the flagged items into a
single standalone question, preferring the judgement-bearing half.

**Rewriting rather than splitting is the load-bearing choice.** Splitting would take 4
elements to 7, blow `MAX_ELEMENTS = 5`, force a drop rule, and — because the trailing
conjunct is usually the directional, judgement-bearing half — a naive cap would drop
precisely the half worth keeping. It would also inflate the retrieval budget (element lanes
are ≤2 queries each; 5 elements is exactly the current 13-query design) and touch a LOCKED
contract. Rewriting keeps element count, cap, budget and contract **byte-identical in
shape**.

Little is lost: *"What were the stated objectives, and to what extent were they met?"* →
*"To what extent were the stated objectives of privatising British Rail met?"* — answering
the survivor entails the enumerative half.

Fail-safe: malformed response, wrong length, or exception → **keep the originals**.

### D. Ordering inside `apply_grounds_stage`

```
_decompose  →  [detect + repair]  →  _on_subject  →  value-predicate lock
            →  structural coverage  →  cap  →  _write_elements
```

**Repair must precede the lock.** A rewritten question can collapse into the value judgement
(*"To what extent was HS2 a waste of money?"*), and `_is_restatement` must see the final
text, not the pre-repair text. Placing repair after the lock would open a laundering route
through the exact door slice-2 was built to shut.

Telemetry into `metadata.grounds`: `compound_detected`, `compound_repaired`,
`compound_surviving`.

### E. Mapper backstop — the honesty guarantee

For any element that is **still** compound with **mixed** shapes after A–D, compute the
shape mechanically and inject a per-element directive into the mapping prompt: grade this
element by the **whether/extent** rule (the stricter one).

Under the directional rule, a document merely listing targets no longer shows "the ground IS
the case" — so the easy-half-badges-the-whole failure is closed **whether or not repair
succeeded**. Mechanical: we compute the shape and tell the mapper, rather than asking it to
notice.

Scope: mixed-shape compounds only. Same-shape compounds are an answeredness problem (Phase 3
proper) and are addressed by A–D, not by E.

### F. Flag

`ENABLE_ELEMENT_ATOMICITY`, default `True`, rollback `=False` without redeploy — same shape
as `ENABLE_OPINION_REFRAME` and `ENABLE_ELEMENT_RETRIEVAL`.

---

## 5. Freeze criteria — what must NOT change

Per the Phase 2 lesson (frozen criteria earn their keep by catching the builder):

1. **Flag off → byte-identical output.** Reproduces today exactly.
2. **Factual/declarative path untouched.** `DECOMPOSITION_PROMPT` unchanged in this phase.
3. **Element count never exceeds `MAX_ELEMENTS`, and never falls below today's count for the
   same input.** Repair rewrites 1→1.
4. **Conjoined noun phrases are never split.** *"efficacy and evidence base"* stays one.
5. **Repair failure preserves originals; a live check never fails here.**
6. **The value-predicate lock still sees final text** — a repaired restatement is still dropped.
7. **Retrieval query budget unchanged** — still 13/claim full, 6 quick, ≤65/check.
8. **`re_search.py` unaffected** — it supplies its own single element.

Pin the **crossings**, not just the axes: flag-on × repair-fails, flag-on × repair-produces-a-
restatement, flag-off × compound-present.

---

## 6. Tests

Unit, in `tests/unit/pipeline/test_element_atomicity.py`:

- detector: 17 real compounds from the battery split; conjoined noun phrases do not
- shape classifier: directional / enumerative / mixed
- repair fail-safe: malformed JSON, wrong array length, exception → originals preserved
- repair → lock ordering: a repaired restatement is dropped
- backstop injection fires on mixed-shape survivors and only on those
- flag-off byte-identity

**Every guard gets a mutation.** A green file that pins nothing is decoration — assert the
mutation string applied before running, restore in `finally`, hash-verify after.

## 7. Acceptance

Re-run `compound_question_battery.py` on the same 20 claims.

- **Gate:** compound rate 21.2% → **≤5%**, mixed-shape → **0%**
- **Must not regress:** elements produced (80), `converged` rate, breadth floor of 3
- Record the log as the artefact, as with the baseline

## 8. Sequencing

1. **Phase 3a — this doc** (atomicity)
2. **D3** — retrieval searches element lines only *(needs 3a first: element text becomes the
   sole search surface)*
3. **F7 re-gold — once, after both.** Both changes invalidate cassettes (query strings are
   keys); re-golding between them wastes the run
4. **Phase 3 proper** — mapper answeredness threshold, tuned on the resulting pool
5. Push

## 9. Out of scope

Factual-path atomicity (§2, blocked on the census) · `_grounds_applied` precision · floored
elements losing "N sources disagree" · `P1` · `F-MMR-POOL` · pool balance/MMR. All Phase 3
or later.
