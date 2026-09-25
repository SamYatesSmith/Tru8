# Recital gate: a reference cannot rest on a recital pointing the other way

**Date:** 2026-09-25.
**Status:** BUILT 2026-09-25 after review (`audit/2026-09-25_recital_direction_release_review.md`: principle approved, classifier REWORK). §8 is what was built and supersedes §3 where they differ.
**Rule:** difficulty 3 (it changes what a scope gate demotes on the tolerance-0 corpus claim TRU-018F-44AA). Founder chose "fix first" over re-pinning the off-by-one.

## 1. The fault
The 018F bench pin `recital_scoped_refs` reads 4 against a golden of 3. Reading the four refs one by one shows the count is not the problem. **All four are fact-check CHALLENGES that the recital gate demotes to context:**

| Source | Path | Matched attribution |
|---|---|---|
| USA Today "What six wars did Donald Trump end?" | evidence | "Donald Trump claims **to have settled six wars**" |
| AP "FACT FOCUS: Trump says he's ended eight wars. His numbers are off" | evidence | "Trump says **he's ended eight wars**" |
| Guardian "Fact-check: Donald Trump's false and misleading claims…" | reasoning | "Identifies Trump's claims **of having ended seven wars** as false and misleading" |
| CNN "Checking in on the 'seven un-endable wars' Trump did (not) end" | evidence | "Donald Trump claimed … **that he has 'ended seven un-endable wars'**" |

In each one, the attribution sentence is **the claim under check, restated so it can be rebutted.** The challenge rests on the rebuttal: "his numbers are off", "neither a war nor a peace agreement", "did (not) end". It does not rest on the saying.

So on a false claim made by a prominent person, which is the class users bring, the gate removes the fact-checks. That makes the claim look less challenged than it is, a sycophancy hazard (invariant 7). The 2026-09-24 recital review recorded this ("challenge-direction misfires on 018F") but did not build a fix.

## 2. Principle
The gate exists because **evidence that a claim was made is evidence of the making, not of the content.** A recital therefore points one way: the way of what it recites. A reference can only *rest on* a recital that points its own way:
- "Trump says he ended six wars" filed as **supports**: it rests on the recital. Gate it, as today (the 2026-08-13 trap).
- The same sentence inside a **challenge**: the challenge cannot rest on it, because the recital points the other way. Do not gate on it.
- The mirror: "Trump says he did not end the wars" (a denial) filed as **challenges** rests on it. Gate it. Inside a **supports** ref, it cannot be the basis. Do not gate on it.

This is symmetric in its logic. It releases whichever direction the recital points *away* from. It never releases a ref whose recital points its own way.

## 3. Design (R6, `app/utils/recital_scope.py`)
**Self-report.** A subject-anchored attribution match is the subject's own report when its content (the rest of that sentence after the match) opens as a self-report:
- `to (have) <verb>` (or the match itself ends in "to have"),
- `of having`,
- `(that) he|she|they|we|I …`,
- or an auxiliaried pronoun (`he has`, `he's`, `I've`) within 120 chars.

It **restates** the claim when that content shares **≥2 content stems** with the claim texts plus the element description. Stems are stop-worded, suffix-stripped and truncated to 6 characters, number words map to digits, and subject tokens are excluded. Its **polarity** is negated when a negation (`not`, `never`, `n't`, `no`, `neither`, `nor`, `without`, `deny`) precedes the first shared stem. It *restates* when its polarity equals the claim's and *denies* otherwise.

**Stance of a text.** Scan every subject-anchored match in ONE text (the reasoning, or the evidence text, separately):
- only *restates* found → the text presents the subject as the claim's **proponent**;
- only *denies* → **opponent**;
- both or neither → no stance.

**Release.** A match is skipped (the scan continues to the next one, exactly as R0–R5 skip) when:
- the ref is `challenges` and the text's stance is **proponent**; or
- the ref is `supports` and the text's stance is **opponent**.

Why the whole text and not just the matched sentence: USA Today and CNN also report "Trump announced a treaty between DRC and Rwanda" as background. Once a text has shown the subject asserting the claim, the subject's other statements in it point the claim's way, so a challenge cannot rest on them either. A per-sentence rule left USA Today and CNN firing on those lines. The prototype showed this, and it is why the rule works at text level.

**Scope:**
- Both the reasoning path and the evidence-text path, all three pattern kinds (verb, quote, according).
- Not the distancing-adverb path.
- Not the subject-free restatement path. Its veto already protects fact-checks that quote a claim (Carbon Brief), and no misfire is observed there.

**Wiring.** `recital_match(..., release=DirectionRelease(direction, claim_texts, element_text, subject_tokens))`. The gate's `fires(item, ref)` already has the ref, so it passes `ref["relationship"]`. Rollback flag `ENABLE_RECITAL_DIRECTION_RELEASE`, default True.

## 4. What stays gated (probes, prototype-verified)
| Probe | Ref | Result |
|---|---|---|
| "Trump claimed to have 'settled six wars'" (reasoning, 2026-08-13 verbatim) | supports | fires |
| "quotes President Trump saying, 'I've solved six wars'" | supports | fires |
| "Trump has repeatedly claimed credit for ending six wars" | supports | fires |
| "Trump said he has solved six wars" | supports | fires |
| "Trump announced he had ended the war between Israel and Iran" | supports | fires |
| "Trump said he did not end six wars…" (a denial) | challenges | fires |
| "Trump said the wars were ended by Biden and not by him" | challenges | fires |
| "Biden says inflation was caused by Putin's war" (self-serving blame shift, claim "Biden caused inflation to rise") | challenges | fires. It is not a self-report of the claim |
| "Biden said he has cut inflation since taking office" | challenges | fires. It shares only 1 stem |
| "Biden said he did not cause inflation to rise" | challenges | fires. It is a denial |
| "Trump says he's ended eight wars. His numbers are off." | challenges | **released** |
| "President Trump claims to have settled six wars … no war between Egypt and Ethiopia" | challenges | **released** |
| "Biden says he caused inflation to rise, but economists disagree" | challenges | **released** |
| "Trump said he never ended six wars" | supports | **released** (the mirror) |

## 5. Measured (free)
- **018F, all 21 directional refs from the committed cassette:** the 4 fires above are released. No other ref changes, and releasing can never add a fire.
- **The 12 stored recital fires on the 19 graded A− records:** 0 of 12 change (all are supports that restate the claim, or fall to R0–R5 already).
- **Expected 018F effect:** `recital_scoped_refs` goes 4 → **0** on this recording. The corpus claim then no longer exercises the recital gate at all. See §6.

## 6. Risks and open questions for review
1. **018F stops exercising the recital gate.** On this recording it has no recital SUPPORTS, so the tolerance-0 pin would read 0, and a golden of 0 at tolerance 0 no longer proves the gate works.
   - Proposal: re-pin to 0 with a dated note, and mark `recital_scope` as a precondition-dependent assertion (UNEXERCISED when 0, like interested_party). Support-side safety then rests on the unit pins, which use the 2026-08-13 verbatim strings, as the recital review already concluded.
   - Question: should a recital-SUPPORT fixture join the corpus instead? That is a separate, paid item.
2. **Stem overlap is lexical.** "settled" ≠ "stopped"; USA Today matches on "six/6" + "wars". A self-report sharing only one stem is not released, which is the conservative direction (it fires as today).
3. **A text that restates the claim AND carries the subject's self-serving contrary line without negation** (a blame shift) is released on a challenge, because the stance is proponent. This is rare and, inside a text already presenting the subject as the claim's proponent, low-harm. Named rather than hidden.
4. **The supports mirror** releases a support whose text shows the subject only denying the claim. Such a ref is a mapper error, which the gate currently absorbs by accident. It is kept for symmetry, and its frequency is expected near zero. Should the mirror be dropped? (Dropping it makes the rule one-way.)
5. **Pronoun heuristics** (`he|she|they|we|I` opening the tail) can misread "Trump said they …" (another party) as a self-report. It still needs ≥2 claim stems and a proponent stance.

## 7. Verification plan
- Unit tests: the four 018F texts released as challenges; every §4 probe both ways; the 2026-08-13 verbatim support strings still fire; the flag off restores today's behaviour. Each rule is mutation-checked: drop the stance, the ≥2 floor, or the polarity check.
- Replay the 12 stored fires (0 change) and the 21 018F refs.
- Bench on 018F plus a full `--all`, against a HEAD control. Re-pin 018F per §6.1 with a dated note.


## 8. As built, after the review (2026-09-25)
The review's probes found 7 ways the draft classifier could release the wrong thing. Every one is fixed, and each is pinned by a test.

| Review finding | Fix |
|---|---|
| F1 "didn't" split into `didn` + `t`, so the negation was lost | Words keep `n't` attached; negation is read on the raw word |
| F2 "Critics of Trump say…" read as Trump speaking | **Speaker check.** Only verb-kind matches count. The bridge between name and verb may hold only auxiliaries, adverbs and the subject's own other name words, and no preposition may lead the name (`of|for|against|about|by|to|with|…`) |
| F3 the claim's polarity flipped by "without" | Polarity comes from the normalised claim only. `no` and `without` are not predicate negations |
| F4 "no president could" read as a denial | Negation counts only in the 4 words before the first shared stem; `no` is excluded |
| F5 stance pooled across subjects | Stance is kept **per subject**, and a match is released only when its own subject's stance is exactly `{restates}` |
| F6 "only ended two wars" read as a restatement | A downtoner (`only/just/merely/barely/fewer/less than`) or a figure below the claim's makes the self-report **contrary**. A year (1900–2100) is not a count |
| F7 negated speech fed the stance; "they" counted as the subject | The stance scan applies R0/R2/R5; pronouns are only `he/she/I` |
| (found in the build) Heard "she was the one abused", a role reversal | **Voice parity:** a be-verb before the first shared stem plus a participle among the first two shared words makes the self-report passive; it is contrary unless the claim is passive too |
| Mirror | **Dropped.** R6 releases `challenges` only, so it cannot release a recital support |

A redundant per-match denial check was removed after a mutation survived it. A subject's denial already puts `contrary` into the stance, so the check could never change the result.

**Measured (free):**
- **018F:** all 4 fires are released (USA Today, AP, CNN on the evidence path; Guardian on the reasoning path). The same texts filed as `supports` still fire.
- **Probes:** every §4 probe and every probe from the review behaves as intended. The one exception is "Trump admitted…": `admitted` was never a gate verb, so that probe is out of scope.
- **19 graded payloads:** all 156 current directional refs replayed, with 0 fires before and 0 after, so nothing changes. The 12 stored recital fires are also unchanged.
- **Tests:**
  - `tests/unit/pipeline/test_recital_direction_release.py`: 42 tests, including the wired seam through `_parse_mapping_response` and a check that the flag off restores the old behaviour.
  - 8 mutants, all killed: the ≥2 floor, negation, downtoner, lower figure, voice, speaker, stance-per-subject, and supports-never.
  - Recital, interested-party and wiring suites: 204 pass.
  - Full unit suite: 4,118 pass.
- **Rollback:** `ENABLE_RECITAL_DIRECTION_RELEASE=False`.

**018F golden:**
- `recital_scoped_refs` and `recital_scoped_elements` are re-pinned to **0 at tolerance 0**. That makes the counter the positive pin: if the gate ever demotes those fact-checks again, the bench fails.
- `recital_scope` comes out of `scope_gates_must_fire`, with a dated note. This recording holds no recital support, and the comparator's only precondition type is a URL substring.
- Support-side safety rests on the unit pins, which use the 2026-08-13 verbatim strings, and on the wiring test's CBS recital support, which still reads `context`.

**Not done (named):**
- Veto words (`false|misleading|incorrect`): a separate change (review F10).
- A corpus fixture carrying a genuine recital support: a separate item.
