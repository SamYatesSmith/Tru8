# Decoupling read-layer — design review

**Opened:** 2026-07-24, from the completed decoupling live battery
(`audit/2026-07-23_decoupling_live_test_plan.md`). Model: Fable 5.
**Status:** ~~DESIGN REVIEW — nothing built~~ → **P21 Bug A BUILT 2026-07-25** after a
second review pass against the live code. Decisions #1 and #2 answered by the founder
(see §8). **Three statements in this document were found WRONG at build time and are
corrected in place below — read §8 before acting on §2 or Appendix A.**
P20 (§3) and P13+P1 (§4) remain unbuilt; decisions #3/#4 still owed.
**Verification:** every location below was confirmed against the live backend by a
code-verification pass (2026-07-24). Two findings needed their mechanism corrected
before design — those corrections are baked in here. **Do not design against the
original P20/P21 framing in the battery log; design against this.**

---

## 1. The corrected picture

The decoupling *mechanism* is sound — every mechanism probe in the battery passed.
What the flag going live exposed is a set of **read-layer** distortions: the report's
most-read surfaces (element badge, orientation top-line, jurisdiction framing) can now
misrepresent an honest evidence set. Crucially, verification showed these are **not**
"the machinery was never redesigned":

- The element **state** derivation is mechanical and **correct** — it faithfully counts
  the mapper's per-ref relationships. **It is not in scope to change.**
- A neutral-question **mapper** redefinition **already ships** (`GROUNDS_MAPPING_ADDENDUM`).
  P21 is therefore *half-solved already*; the unpatched half is orientation, left out
  by an explicit prior scoping decision.
- P20's "silently resolved to US" was **wrong** — the code defaults to `gb`; the US pool
  is emergent. The real defect is the *absence* of detection and disclosure, not a bad
  resolution.

So this review targets three narrow, verified seams, not a re-architecture.

---

## 2. P21 — supports/challenges + orientation on neutral questions  *(centrepiece)*

### What's verified

- **State is mechanical and correct.** `_derive_element_state_with_authority`
  (`claim_map_analyzer.py:699-788`) overrides the LLM state with a tier-weighted count
  over `evidence_refs` (`supports`/`challenges`/`context`). **Do not touch.**
- **A grounds-aware mapper addendum already exists.** `GROUNDS_MAPPING_ADDENDUM`
  (`:291-315`) is appended to the mapper prompt when `_grounds_applied()` is true
  (`:318-330`, reads `metadata.grounds.applied`). It redefines the relationships for open
  questions and forbids inferring the parent claim's truth (`:307`).
- **Bug A — the addendum is ambiguous** (`:296-301`) between two readings of "support":
  *"the evidence ANSWERS the question"* (direction-agnostic) vs *"the asked-about ground
  is ESTABLISHED"* (directional). T8 split on exactly this: e01 (effectiveness → absent)
  was read directionally → `challenges`; e02 (cost-effectiveness → absent) was read as
  "answered" → `supports`. Same claim, opposite frames, from one ambiguous sentence.
- **Bug B — orientation is grounds-UNAWARE by explicit scoping.** `derive_orientation`
  (`:572-630`), `_orientation_prose_state` (`:550-569`) and the phrase maps
  `_SINGLE/_UNANIMOUS/_ITEM_PHRASE` (`:525-547`) use assertion-frame vocabulary
  ("predominantly supports **it**") and emit `"evidence is mixed: …"` (`:630`) whenever no
  single state holds a strict majority. The code comment at `:289-290` states the §20
  reframe deliberately changed *label semantics only, not orientation*. That is the
  unpatched half of P21. T8's 1-`challenged` + 1-`supported` → 2-way tie → "mixed",
  even though both grounds point the same way.
- ~~**Latent — batch path uncovered.**~~ **CORRECTED 2026-07-25 — this work item does not
  exist.** The addendum is indeed appended to `MAPPING_PROMPT` only, but grounds claims
  never reach `BATCH_MAPPING_PROMPT`: `map_evidence_batch` partitions them out at
  `:1444-1454` and routes each through the single-claim mapper that carries the addendum.
  Pinned by `test_batch_routes_grounds_claims_individually`
  (`tests/unit/pipeline/test_grounds_mapping.py:139-164`, asserting the addendum is
  absent from the batch prompt *because* no grounds claim is in it). Nothing to extend.

### The design question you asked: *what do supports/challenges MEAN against a neutral question?*

**Proposed answer — lock the directional-on-the-ground reading, drop the "answered" reading.**

Every neutral question has an implicit **affirmative ground** — the proposition it is
asking whether to establish. "What is the clinical effectiveness…?" implicitly asks
whether *"homeopathy is clinically effective"* holds. Define the relationships against
that implicit affirmative, consistently:

| Relationship | Meaning against a neutral question |
|---|---|
| **supports** | evidence establishes the affirmative ground (the asked-about thing IS the case) |
| **challenges** | evidence refutes the affirmative ground (it is absent / the opposite is documented) |
| **context** | relevant but does not settle the ground either way |

Under this single semantics, T8 resolves consistently: **both** elements → `challenges`
(effectiveness absent; cost-effectiveness absent). No split, no misleading `+SUPPORTED`
on the cost question. This keeps `:307` intact — it still never infers whether the
*parent claim* ("indefensible") is true; it only reports whether each *ground* holds.

**Fix:** rewrite `GROUNDS_MAPPING_ADDENDUM:296-301` to state the implicit-affirmative
framing and delete the "substantively ANSWERS the question" phrasing that licenses the
direction-agnostic reading. Add one worked example (a question whose evidence documents
the *negative* answer → `challenges`, not `supports`).

### The design question you asked: *how do we fix the "mixed" orientation?*

The word "mixed" assumes all elements bear on **one** proposition, so differing states =
genuine disagreement. For grounded claims that assumption is **false** — the elements are
**orthogonal questions**, not competing evidence on a single claim. Aggregating them into
"supports it / mixed" is a category error, and "mixed" manufactures false balance
(**invariant #7**: a well-evidenced grave claim must not be made to look contested).

**Fix — make orientation grounds-aware; switch from *aggregate verdict* to *per-question
digest* for grounded claims.** Branch `derive_orientation` on the existing
`_grounds_applied` marker:

- **Non-grounded (assertion elements):** unchanged — they *are* facets of one claim, so
  the current aggregate ("predominantly supports it", and yes "mixed" when truly split)
  stays correct.
- **Grounded (neutral-question elements):** emit a neutral per-question line, never an
  aggregate parent-direction verdict and never the word "mixed". E.g. *"On the 2 questions
  examined: clinical effectiveness — evidence challenges it; cost-effectiveness — evidence
  challenges it."* This reports each ground honestly, leaves the judgement to the reader
  ("We organise; you decide"), and — because it never rolls up — cannot false-balance in
  either direction.

This is *on-philosophy*: refusing to aggregate grounds into a parent verdict is the same
discipline as `:307`. It does **not** reintroduce the forced counter-slot (it changes
summary vocabulary, not retrieval or mapping balance).

### Scope of the P21 fix
- `GROUNDS_MAPPING_ADDENDUM` (`:291-315`) — disambiguate (Bug A).
- `derive_orientation` (`:572-630`), `_orientation_prose_state` (`:550-569`), phrase maps
  (`:525-547`) — grounds-aware branch (Bug B).
- Confirm + extend to `BATCH_MAPPING_PROMPT` (`:368`).
- **Do NOT touch** `_derive_element_state_with_authority` (`:699`).

### Test
- Replay/synthetic: a grounded claim with two same-direction grounds must NOT produce
  "mixed" and must NOT badge one ground `+SUPPORTED` when its evidence documents the
  negative answer. Re-run the T8 shape; assert both grounds → `challenges` and a
  per-question orientation line.
- Regression: a non-grounded multi-element assertion claim keeps the current aggregate
  orientation verbatim (parity guard).
- Batch-mode grounded claim gets the addendum semantics (new coverage).

---

## 3. P20 — undisclosed jurisdiction on unanchored claims  *(mechanism corrected)*

### What's verified (and what the battery log got wrong)
- **No "resolve to US" step exists.** `_resolve_search_country` (`retrieve.py:122-134`)
  defaults an unanchored claim to **`gb`** (`:132-133`). The all-US T7 pool is **emergent**:
  the query carries no jurisdiction anchor, Serper `country=` is a soft ranking bias, and
  US immigration content dominates the English web, swamping the weak `gb` hint.
- **Nothing detects the gap.** `scope_sensitivity.py` flags only geography words that are
  *present* (`_GEOGRAPHIC` `:39-56`; `detect_scope_flags` `:122-135`); "the government"
  has no geo token → empty. The scope-caveat channel is built for *present-but-broader*
  ("element says Britain, evidence covers England/Wales"), **not absent-but-assumed**.
- **Nothing discloses it.** `re_search.py` (Seeker) has zero jurisdiction handling.

### Design
The defect is **detection + disclosure**, not "correct a default." Three parts:

1. **Detect a jurisdiction-unanchored subject.** The existing tagger cannot (it keys on
   present tokens). This needs a new signal that a subject *implies* a national
   jurisdiction it does not *specify* ("the government", "the president", "the country").
   - **Option A (lexical):** a small set of jurisdiction-implying-but-unanchored subject
     heads. Cheap, fragile, English-quirk-prone.
   - **Option B (LLM at extract/classify):** one boolean + optional "assumed jurisdiction"
     — extraction already runs an LLM. More robust; a semantic judgement.
   - **Recommend B**, with the mechanical lexicon as a cheap pre-filter/second signal
     (same "mechanical + LLM" belt-and-braces the codebase already prefers).
2. **Disclose it.** Home it in the **Seeker** as a first-class unknown ("Which
   jurisdiction? The claim doesn't specify; the evidence pool was dominated by US
   sources") **and** a one-line neutral **orientation caveat** (reuse the existing neutral
   caveat channel). Disclosure is the priority deliverable.
3. **Revisit the silent `gb` default** (`retrieve.py:133`). At minimum, when jurisdiction
   is unanchored *and* the emergent pool skews to a country other than the default bias,
   record the mismatch for the caveat. Deeper retrieval changes (e.g. multi-jurisdiction
   fan-out) are **parked** — out of scope here.

### Lane note
P20 is **specificity-gap / Seeker**, adjacent to but *separable* from decoupling — it can
proceed on its own track. It is grouped here only because T7 surfaced it in the same run.

### Test
- A jurisdiction-unanchored claim ("the government has …") raises the unanchored signal,
  produces a Seeker unknown + orientation caveat, and the caveat names the emergent pool
  skew. An anchored claim ("the UK government …") raises neither.

---

## 4. P1 + P13 — value-predicate leak & hint boundary  *(shared mechanism)*

### What's verified
- **P1 confirmed exactly.** `_is_restatement` (`opinion_symmetry.py:141-151`) is a lexical
  subset test — `claim_words <= element_words and len(element_words - claim_words) < 2`
  over stopword-filtered `_content_words` (`:124-126`). `_as_question` (`:129-138`) guards
  structural re-adds only with this same lexical test (`:266`, `:273`). A **paraphrased**
  value predicate (drop/swap one content word) escapes and re-enters as an element.
- **P13 correctly located, but NOT tense-coded.** The `normative` hint is an **LLM
  judgement** via `_OPINION_REFRAME_RULE` (`extract.py:118-135`) — `:119-125` (evaluative
  main point on measurable grounds → hint) vs `:127-134` (factual assertion; incidental
  subjective adjectives cleaned → no hint). "…has been a catastrophe" plausibly reads as
  a factual-outcome-with-adjective (no hint, T7); "…is indefensible" as a pure value
  predicate (hint, T8). **There is no trigger to patch — it's prompt-semantic variance.**

### Design — one mechanical value-predicate detector, two consumers
Both bugs want the same missing capability: a **mechanical evaluative-head detector** (a
lexicon + light morphology: *disaster, catastrophe, indefensible, triumph, scandal,
failure, shambles, …*). Build it once; wire it into both sites:

- **P13 consumer:** use it as a **second signal** that arms the grounds stage even when the
  LLM under-fires. If the claim's main predicate is an evaluative head, treat as normative
  regardless of the LLM boolean. (Durable lesson, `feedback_nf11_prompt_only_failed` /
  `feedback-nf11`: fragile boundaries need a mechanical post-processing rule, **not**
  prompt-only.) Also sharpen `_OPINION_REFRAME_RULE:127-134` so perfect/past evaluative
  predicates ("has been a disaster") are explicitly *not* "incidental adjectives".
- **P1 consumer:** replace/augment `_is_restatement`'s lexical test with a **semantic**
  check — exclude a structurally re-added element whose *predicate* is the claim's
  evaluative head (even paraphrased), using the same detector.

### Constraint
Neither change reintroduces the forced counter-slot. The P13 second-signal only affects
*whether grounds run*, not what evidence is retrieved or how it's balanced.

### Test
- P13: "X has been a catastrophe/disaster/failure" (past/perfect evaluative) arms grounds
  via the mechanical signal even if the LLM would not. A genuine factual claim with an
  incidental adjective does not.
- P1: a paraphrased value-predicate element ("…whether the outcomes are severe enough to
  be a disaster") is excluded from structural re-add; a legitimate distinct empirical
  ground is retained.

---

## 5. What this review deliberately does NOT touch

- **Element state derivation** (`:699`) — mechanical and correct.
- **The forced counter-slot** — removed after the Gaza denialist brief; no fix here
  reintroduces it. Every proposal above changes *summary/label semantics or detection*,
  never *retrieval/mapping balance*.
- **D1 one-sided-pool hardening (P3)** — KEEP DEFERRED. T8 was its probe and it did not
  bite (strong pool, honest mapping).
- **Pool-quality families (P4/P12/P14/P15/P19)** — retrieval backlog, separate lift.

---

## 6. Priority & effort

| Finding | Why it ranks | Effort | Lane |
|---|---|---|---|
| **P21** | live top-line distortion on well-evidenced claims (invariant #7); half already built | M (prompt + orientation branch) | decoupling |
| **P13 + P1** | T7 proved P13 *harmful*; shared mechanical detector fixes both | M (new detector + 2 wirings) | decoupling |
| **P20** | integrity gap, but separable Seeker track; needs a new detector | M–L (detector + disclosure) | specificity/Seeker |

Recommended order: **P21 first** (it's mis-reporting honest evidence *right now*, and the
mapper half already exists so it's the shortest path to correctness) → **P13 + P1**
(shared detector, closes the sycophancy back-door T7 exposed) → **P20** (own track, can
run in parallel by a different pass since it doesn't touch decoupling code).

Method: `phased-build-loop`, one finding at a time, independent verify with evidence.

---

## 7. Founder decisions needed

1. **P21 mapper semantics** — confirm the *directional-on-the-ground* reading (supports =
   affirmative ground established) over the "answered = supported" reading. This is the
   load-bearing call; everything in §2 follows from it.
2. **P21 orientation for grounded claims** — confirm the *per-question digest* (no
   aggregate verdict, no "mixed") over keeping an aggregate. Recommended: per-question.
3. **P20 detector** — Option B (LLM signal + mechanical pre-filter) vs Option A (lexical
   only). Recommended: B.
4. **P20 `gb` default** — leave as-is with disclosure only, or open the deeper
   multi-jurisdiction retrieval question later? Recommended: disclosure now, retrieval
   change parked.

---

## Appendix A — concrete before/after for P21 (built on recommended decisions #1 + #2)

Reading the real code changed the risk picture: **T8's "mixed" symptom is downstream of
the mapper ambiguity (Bug A), not the orientation layer.** Fix the mapper and T8 self-
corrects through the *existing* orientation path — the orientation change (Bug B) becomes
a robustness refinement for genuinely-split grounded claims, not a T8 requirement. This
shrinks the blast radius: **Bug A is the star; Bug B is optional-but-recommended.**

### A.1 — Bug A: disambiguate `GROUNDS_MAPPING_ADDENDUM` (the primary fix)

The single defect is the "ANSWERS the question" clause at `claim_map_analyzer.py:296`,
which licenses "question got answered → supports" regardless of the answer's direction.

**BEFORE** (`:296-303`):
```
- "supports" = the evidence substantively ANSWERS the question, documenting \
that the ground it asks about is established or present (e.g. for "What are \
the documented casualties?", a casualty report is "supports").
- "challenges" = the evidence disputes the substance the question asks about — \
contradicting reported figures, showing the asked-about ground is absent, or \
documenting the opposite.
- "context" = background that helps interpret the answers (same discipline as \
above).
```

**AFTER** (proposed):
```
- "supports" = the evidence establishes the AFFIRMATIVE of what the question \
asks — it documents that the asked-about ground IS the case. For "What is the \
clinical effectiveness of X?", evidence that X works is "supports"; evidence \
that X does NOT work is "challenges", not "supports". Answering a question in \
the NEGATIVE is a challenge, never a support.
- "challenges" = the evidence refutes that affirmative — documenting the ground \
is absent, false, or that the opposite is the case (e.g. contradicting reported \
figures, or a study finding no effect).
- "context" = relevant to the question but does not settle it either way.
```

~~Everything below `:304` (state mapping, the `:307` "NEVER infer whether the parent claim
is true" lock, GROUND PRECISION census rule) is **unchanged** — those are correct.~~

**CORRECTED 2026-07-25 — the state gloss at `:304-306` was NOT correct and had to move
with the fix.** It read *`"supported"` = the ground is well-documented; `"disputed"` = the
documentation is contested*. "Well-documented" **is** the answered reading — evidence
documenting that a ground is *absent* also makes it well-documented — so it re-licensed
the exact ambiguity two sentences below the rewrite. And `disputed` is now routinely
produced by the uniform `all_challenges` rule (`:787-789`), where documentation is not
"contested" at all. Since the mapper's own `state` output is discarded by
`_derive_element_state_with_authority` at all three call sites (`:1905`, `:2162`,
`:2337`), this block's only live function is to shape *relationship* choice — the exact
channel Bug A runs through. The `:307` never-infer lock and GROUND PRECISION are
untouched, as stated.

**Why this fixes T8 with no orientation change — worked trace.** e02 asked "What is the
cost-effectiveness…?"; its evidence documents *not* cost-effective (the negative answer).
- *Before:* negative answer → "question answered" → **3 refs = `supports`** → state
  `supported` → `_orientation_prose_state` = `supported`. e01 = `challenged_only`. Two
  different states → no majority → line `:630` → **"evidence is mixed: …"**, and e02
  wears a backwards **+SUPPORTED** badge.
- *After:* negative answer → **3 refs = `challenges`** → state `disputed` with challenges
  and no supports → `_orientation_prose_state` = `challenged_only` (`:562-568`). Now
  *both* elements are `challenged_only` → `counts` has one key → **unanimous branch**
  (`:604-605`) → **"Of 2 elements examined, retrieved evidence challenges all 2, with
  none supporting."** The badge on e02 flips to **−CHALLENGED** (correct: it challenges
  that homeopathy is cost-effective). No orientation code touched.

That "challenges all 2, with none supporting" line is the SAME anti-false-balance
refinement the team already shipped for `challenged_only` (2026-07-09, comment `:521-524`)
— so this lands squarely in existing precedent.

~~**Also required for Bug A:** confirm/extend the addendum to `BATCH_MAPPING_PROMPT`.~~
**CORRECTED 2026-07-25 — not required; already covered by the `:1444-1454` routing
partition.** See the corrected bullet in §2.

### A.2 — Bug B: make orientation grounds-aware (robustness refinement)

Bug A fixes T8, but the orientation *vocabulary* is still assertion-framed
("predominantly supports **it**", "supported") and will mislead on a **genuinely split**
grounded claim (one ground established, one not) — there it implies a parent-claim
direction the reframe forbids. The fix branches on the existing `_grounds_applied` marker.

**Signature + call sites.** `derive_orientation(elements)` → `derive_orientation(elements,
grounds_applied=False)`; all five callers (`:1236, :1317, :1436, :1575, :2358`) already
hold the `claim_map`, so each passes `_grounds_applied(claim_map)`. Backwards-compatible
default keeps every non-grounded path byte-identical.

**Grounded branch (sketch)** — question-framed, parent-neutral, never the word "mixed",
never "…it":
```python
_GROUNDS_ITEM = {
    "supported":       "the ground is established",
    "challenged_only": "the ground is not established",
    "disputed":        "the ground is contested",
    "unresolved":      "the ground is unresolved",
    "contextual":      "only context is available",
}

def _derive_grounds_orientation(state_values, total):
    counts = Counter(state_values)
    if len(counts) == 1:                      # unanimous grounds
        phrase = _GROUNDS_ITEM[state_values[0]]
        return (f"Of {total} questions examined, for each {phrase} "
                f"(the evidence answers each on its own terms; the judgement is yours).")
    parts = [f"{c} where {_GROUNDS_ITEM[s]}" for s, c in counts.most_common()]
    return f"Of {total} questions examined: " + "; ".join(parts) + "."
```
So a split grounded claim reads *"Of 3 questions examined: 1 where the ground is
established; 1 where the ground is not established; 1 where the ground is unresolved."* —
each question reported on its own terms, no aggregate parent verdict, no false "mixed".

**Doc-comment debt:** the scoping note at `:289-290` ("state derivation/orientation are
untouched") becomes half-false once Bug B lands — update it to "orientation is grounds-
aware; state derivation remains untouched."

### A.3 — What stays untouched (guard rails)
- `_derive_element_state_with_authority` (`:699`) — mechanical, correct, no change.
- `compute_orientation_basis` (`:633`) — machine-readable distribution; unaffected by
  prose changes (verify its consumers don't assume assertion framing).
- No retrieval/mapping *balance* change anywhere → forced counter-slot not reintroduced.

### A.4 — Minimal-change recommendation
Ship **Bug A alone first** (one prompt block ~~+ batch-prompt parity~~) and re-run the T8
shape: expect both grounds `challenged_only` and the honest unanimous line, with no
orientation code touched. Add **Bug B** as a fast follow for split-ground robustness. This
is the smallest edit that removes the live distortion, and it's verifiable against a
single replay. *(Followed. See §8.)*

---

## 8. Build outcome — P21 Bug A, 2026-07-25

### 8.1 The flaw found before building

Appendix A's rewrite defined `supports` as *"the evidence establishes the AFFIRMATIVE of
what the question asks."* **That is undefined for the question shape this stage most often
produces.** `NORMATIVE_DECOMPOSE_PROMPT` (`opinion_symmetry.py:55-66`) explicitly
commissions questions that *"must NOT presuppose"* their own answer, over grounds like
*"stated targets, measured outcomes, documented problems, comparative context."* For
*"What were the stated targets?"* there is no affirmative to establish or refute — a
uniformly directional rule would have forced the mapper to invent one, manufacturing a
label the question cannot carry. Appendix A also **deleted the casualty example**, which
is precisely the enumerative case the original clause handled correctly.

So the defect was narrower than "the addendum is ambiguous": **the addendum applied one
rule to two question shapes.**

| Shape | Origin | Affirmative? | Old `:296` |
|---|---|---|---|
| Polar / degree — *"What is the clinical effectiveness of X?"*, `_as_question`'s *"…about whether X?"* (`opinion_symmetry.py:129-138`) | LLM decompose + structural re-add | yes | **wrong** — this is T8 |
| Enumerative — *"What are the documented casualties?"* | LLM decompose | no | **already correct** |

### 8.2 Founder decisions (answered 2026-07-25)

1. **Mapper semantics — TWO-SHAPE RULE.** Whether/extent questions take the directional
   reading (a negative answer is `challenges`, never `supports`); what/how-many/which
   questions keep "supplies the answer = `supports`", with `challenges` reserved for
   evidence contradicting that record. Supersedes decision #1 as posed in §7.
2. **Build scope — Bug A alone.** Bug B (grounds-aware orientation) stays a fast-follow.

### 8.3 What was built

- `GROUNDS_MAPPING_ADDENDUM` (`claim_map_analyzer.py:291+`) — two-shape relationship
  rules; state gloss rewritten (`well-documented` → `disputed` explicitly *includes* a
  ground the evidence uniformly shows is not the case).
- Rationale comment added at `:285` block.
- **Untouched, as designed:** `_derive_element_state_with_authority`, `derive_orientation`,
  the phrase maps, `BATCH_MAPPING_PROMPT`, the `:307` never-infer lock, GROUND PRECISION.

### 8.4 Verification

- `tests/unit/pipeline/test_grounds_mapping.py` — **10 passed** (6 existing + 4 new):
  both shapes present; the negative-answer rule stated; the `well-documented` gloss gone;
  the T8 mechanical trace end-to-end (3 `challenges` refs → `disputed` /
  `rule_applied == "all_challenges"` → *"Of 2 elements examined, retrieved evidence
  challenges all 2, with none supporting."*, asserting `"mixed"` absent); and a pin that
  a genuinely-split grounded claim **still** reaches "mixed", keeping the Bug B deferral
  honest.
- `pytest tests/unit/pipeline/` — **978 passed, 44 skipped, 0 failed** (skips are the
  pre-existing live-LLM gate).
- The `test_addendum_is_direction_free_and_never_infers_the_claim` tripwire (`:71-75`,
  forbids the substring `"direction"`) **passed unchanged** — the two-shape rule is
  phrased without it, so no guard had to be loosened to land this.

### 8.5 Live verification — **PASSED**, `TRU-69E2-51DC` (2026-07-25, 14:56 UTC)

Attempt 1 (`TRU-7EF2-087A`) was **void**: the test claim used an extraposed construction
("It is indefensible **for** X **to** Y"), Rule 6 under-fired, `indefensible` was dropped
and the claim typed EMPIRICAL — the grounds stage never ran, so the addendum was never
in play. See §8.6.

Attempt 2 re-ran the original T8 text and passed all four gates:

| Gate | Element | Result |
|---|---|---|
| 0 precondition | claim typed `NORMATIVE FLAGGED`, 3 question elements | **PASS** — grounds stage ran |
| **1 the fix** | e02 *"…documented outcomes … compared to conventional treatments?"* | **PASS** — `−CHALLENGED`, **6 challenging / 0 supporting**. The old rule scored this `+SUPPORTED` because a negative answer still "ANSWERED the question". T8's exact defect, gone. |
| 2 orientation | *"Of 3 elements examined, 2 predominantly supported; 1 challenged with none supporting."* | **PASS** — majority branch, **no "evidence is mixed"** |
| **3 over-correction** | e01 documented costs, e03 documented allocation decisions | **PASS** — both stayed `+SUPPORTED`. **The shape rule discriminated instead of flipping everything.** A uniformly-directional rule (Appendix A as originally written) would likely have mislabelled both — neither has an affirmative to establish. |

Pool: 4 primary / 7 reporting / 2 commentary. **Deploy confidence strong, not proof:** 17
minutes after `b8c3170`, and identical input produced the *opposite* e02 badge from the
documented T8 baseline — decisive because the mapping prompt itself changed, so any
mapping cache keyed on request body necessarily missed. Residual: the claim text was
identical to T8, so extract/decompose/retrieval may have replayed. A paraphrased
confirmation would close it; not blocking.

### 8.6 Standing caveats and next work

- **⚠️ The fix is PROMPT-ONLY.** e02's *surface* form is enumerative ("What are the
  documented outcomes…?") yet was correctly read as directional because it embeds
  "compared to conventional treatments". The two shapes are therefore **not separable by
  syntax** — the rule rides on a per-run semantic judgement. Project lesson NF-11: fragile
  boundaries need a mechanical backstop. **Hardening path if it proves noisy: a mechanical
  question-shape tag set at the grounds stage and passed to the mapper.** Do not build
  yet — one clean run is not evidence of noise.
- **Bug B now has a concrete live witness — this very report.** *"2 predominantly
  supported"* is assertion vocabulary over question elements; a reader can take it as
  "the claim is 2/3 supported" when it means "the cost question and the funding-decision
  question were answered". On a claim about whether the spending is *defensible*, that
  leans toward the claim on grounds carrying no such direction. Not a regression — the
  deferred fast-follow — but the strongest argument yet for doing it.
- **New P13 witness (from attempt 1):** the extraposed evaluative construction
  ("It is indefensible for X to Y") does not merely miss the hint — it **silently drops
  the judgement**, the defect class decoupling exists to kill (origin TRU-1928-D5F6).
  `_OPINION_REFRAME_RULE`'s worked examples (`extract.py:124-125`) both use a contentful
  grammatical subject, as did T8; `:133-134` then licenses cleaning "incidental subjective
  adjectives inside a factual claim". Attach to the **P13+P1 shared detector** as a
  reproducible case — this is a natural, common English phrasing, not an edge case.
