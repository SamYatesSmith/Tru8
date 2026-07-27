# Evaluative-head detector — F-VERDICT + P13

**Date:** 2026-07-26 · **Status:** BUILT + VERIFIED (6 verification rounds) · **Flag:** `ENABLE_EVALUATIVE_HEAD_SIGNAL` (default `True`)
**Code:** `backend/app/utils/evaluative_heads.py` · `extract.py::apply_evaluative_head_signal` · `runner.py` seam
**SOT:** `audit/DECOUPLING_STATE.md` — where this file and that one disagree, that one wins.

---

## 1. The two defects

**`F-VERDICT` (HIGH — a live invariant breach).** Check `TRU-52FB-DDC3` emitted
**"The learning-styles theory is indefensible."** as a claim-map ELEMENT and returned it
`+SUPPORTED` with 11 supporting sources. Tru8 rendered a **verdict on a value judgement** —
Invariant #7 and the product lock ("We organise; you decide") both breached.

**`P13`.** The LLM `normative` hint under-fires on two shapes:
- **(a) idea/proposition as subject** — "indefensible" about a *theory* reads as epistemic.
- **(b) extraposition** — "It is ADJ for X to Y" has no contentful subject, so Rule 6's
  "incidental subjective adjectives are still cleaned" licence **deletes the judgement from
  the claim text**. This voided live-verification attempt 1 (`TRU-7EF2-087A`) — an
  already-paid cost, not a hypothetical.

## 2. Mechanism, as verified in code before any design

- The hint is born in exactly one place, by LLM judgement: `_OPINION_REFRAME_RULE`
  (`extract.py:118-135`), spliced at `:433-437`. Both worked examples use a contentful
  subject + copula, which is why both miss shapes follow directly.
- `should_apply_grounds` (`runner.py:691-698`) is the **only** gate:
  `ENABLE_OPINION_REFRAME and type_hint == "normative"`. **One hint miss silently reverts
  the entire grounds chain to the baseline decompose path, with no later checkpoint.**
- **There is no downstream guard.** The only value-predicate lock in the codebase,
  `opinion_symmetry._is_restatement`, lives *inside* the grounds stage and never runs when
  the hint misses.
- **New fact found during verification:** `extract.py:70` claims decompose's classification
  "remains the authority downstream". Nothing reads `claim_type == "normative_flagged"` for
  routing. It is persisted and echoed in API schemas, full stop.

## 3. What was built

A mechanical detector wired as a **SECOND signal**, OR-ed with the LLM hint, never unsetting it.

| Piece | Where | Note |
|---|---|---|
| `find_evaluative_head()` | `app/utils/evaluative_heads.py` | Pure tagger. Precedent: `scope_sensitivity.py`, `temporal_markers.py` |
| Second signal | `extract.py::apply_evaluative_head_signal` | Hints unhinted claims whose text carries a main-predicate judgement |
| Restoration | same | Extraposed shape only: replaces claims with the user's exact sentence when the judgement survives nowhere |
| Seam | `runner.py`, post-cache beside `recombine_single_thesis` | Heals cached extractions; **no extraction-cache key bump needed** |
| Residual-miss telemetry | `runner.py` claim-save loop | `normative_flagged` + unhinted → `logger.warning`. The measurement that justifies a narrow lexicon |

**Bias (founder-approved):** recall via structure, precision via lexicon. The detector's
**misses are exactly today's behaviour**; only its **false fires** are new. Proved
byte-for-byte, not asserted: across 27 probe strings, seam output with the flag ON and OFF
was identical in 26 — the exception being the one case that legitimately fired.

**Restoration rationale.** It edits user-visible claim text, but the status quo *already*
edits it — by silently deleting the judgement. Restoration puts the user's own sentence back.

## 4. Verification — 6 rounds, 6 findings, all fixed

Independent Opus verifier, adversarial, re-deriving pass/fail from the frozen criteria.

| Round | Verdict | What it found |
|---|---|---|
| 1 | **FAIL** | 15/15 false fires on empirical prose — noun modifiers ("is the **disaster** response body", "was a **catastrophe** that killed 3,787 people") + impact adjectives. Would have routed Grenfell/Bhopal/Post Office off the empirical path |
| 2 | PASS | Recall-cost reasoning proved empirically (26/27). Found a **regression I introduced**: the terminal guard pushed "It is a disgrace that…" out of both branches |
| 3 | **FAIL** | Fixing `for` left its `to` twin open one line away — 6/6, reaching **restoration** |
| 4 | **FAIL** | Third hole: `to` + determiner-less NP, 16/16. Diagnosis: `_DET` blocklists an **open set** — "to *the* farmers" blocked, "to farmers" fired |
| 5 | **FAIL** | Experiencer PPs ("It is outrageous **to me**") disproved the premise the head-class split rested on — 7/7 |
| 6 | **PASS** | **0/83** accumulated negatives, 12/12 must-fires |

**Final structure.** The bare-`to` complement arm — which asks *"is the word after `to` a
verb?"*, undecidable by regex — is **removed for both head classes**. Nominal frame takes
`that` **only** and contains **no word-list dependency at all**. Adjectival frame keeps
`for … to` because P13 witness (b) is that shape.

## 5. Why this converged rather than treadmilled

The two branches have **structurally different exposure**, and only one was ever dangerous:

- **Predicative** *can* match empirical prose (a noun modifier can occupy the head position).
  Every genuinely harmful finding lived here. Guarded by `_TERMINAL` — a **closed, decidable**
  question. Has not leaked since round 2.
- **Extraposed** *cannot*. A match requires `It is <evaluative head>` **before** any complement
  is parsed, so the sentence is already a judgement by the time the complement matters. A
  misparse changes *which* judgement is caught, never *whether* a fact is. Tested: 9/9 blocked
  on the exact noun-modifier shapes that broke the predicative branch in round 1.

So the one remaining open-set guard (`_DET` in the adjectival `for … to`, which leaks 8/8)
sits in the branch where an open-set failure is **inert**. Lengthening it would buy parse
accuracy that changes no outcome while re-introducing the dependency four rounds removed.

Severity declined monotonically **and changed kind**: round 1 was empirical claims being
routed off the honest path; round 6 was *"It was a catastrophe for staff senior to middle
management."*

## 6. Documented limitations — deliberately not fixed

| Limitation | Class | Disposition |
|---|---|---|
| `_DET` misparse in adjectival `for … to` (8/8) | Undecidable by regex | **Bounded by construction** (§5). Documented in-module |
| Cross-sentence attribution — `He said. "The thing is a disaster."` fires | Discourse | Pinned as KNOWN LIMITATION. Fixing it would suppress any article quoting anyone |
| `_TERMINAL` admits `,` `;` `:` — "was a catastrophe, killing 3,787 people" | Product judgement | **FOUNDER CALL** — open |
| Attribution word list simultaneously over-suppresses (13/14) and leaks (11/15) | Needs syntax, not more words | **FOUNDER CALL** — open |
| Accepted recall costs: bare-`to` infinitives, nominal `for … to`, trailing modifiers | — | Pinned with reasoning; miss = today's behaviour |

**Is regex the wrong tool?** No — *here*. The design makes misses free, so only precision
matters, and precision is bought by narrowing. It would be wrong if this were the primary
signal, had to handle attribution properly, or needed an aggressively growing lexicon.

## 7. NOT closed — needs a networked environment

1. **No live check.** `TRU-52FB-DDC3` has never been re-run end-to-end. The detector is
   verified; **the outcome it exists to change is not.** Paraphrase the input — identical
   text replays the 1h/6h/24h caches.
2. **Replay bench, 6 rounds stale.** `_EXTRAPOSED_*` changed in 5 consecutive rounds with no
   corpus measurement. Zero prompt bytes changed, so cassettes *should* be unaffected — that
   is an argument, not a measurement.
3. **Residual-miss telemetry unexecuted** — needs a real decompose result.

Both the builder and the verifier judge these worth more than a seventh adversarial round.

## 8. Durable lessons

- **A blocklist cannot close an open set.** Three rounds were spent lengthening `_DET` before
  the fix turned out to be structural — split by head class, then delete the arm entirely.
- **Fixing half a defect class ships the other half.** `for` was guarded and `to` was not, one
  line away; the pin test covered only the half just fixed, so it passed.
- **A verifier that only checks what it recommended is not verifying.** Two deviations from
  its advice were flagged explicitly *as* deviations; one was better, one was a defect.
- **Do not edit a file while it is being verified.** Two transient `NameError` states landed
  on the pipeline path (`runner.py`, no `try/except`) — committing either would have failed
  every check at extract. Fix: freeze and hash-pin.
- **Measure before conceding.** One reported regression (B2) turned out never to have passed;
  the verifier had inferred a measurement it never took, and conceded when challenged.
