# Review: recital direction release (R6)

**Date:** 2026-09-25. **Reviews:** `audit/2026-09-25_recital_direction_release_design.md`.
**Method:** read-only. Read `recital_scope.py`, the wiring at `claim_map_analyzer.py:2991-3059`, the 018F golden, the 2026-09-24 review, and the prototype (`proto_recital.py:551-712`). Re-ran `run_proto.py` / `run_payloads.py` (the design's numbers reproduce: 4 of 4 018F fires released, 0 of 12 stored fires change). Wrote adversarial probes (`rev_probe.py`, `rev_probe2.py` in the scratchpad). No model calls, no bench.

**Overall: the diagnosis is right, but the classifier REWORKS before build.** Three probes reopen the 2026-08-13 support trap, and four release genuinely recital-based challenges.

| Part | Verdict |
|---|---|
| §1 diagnosis (the 4 fires are fact-checks restating the claim to rebut it) | APPROVE |
| §2 principle ("a ref rests only on a recital pointing its own way") | APPROVE |
| §3 self-report / polarity classifier | **REWORK** (F1, F3, F4, F6) |
| §3 text-level stance | **REWORK** (F2, F5, F7) |
| §6.4 supports mirror | APPROVE WITH CHANGES: drop it for this build |
| Wiring / `finditer` / cache | APPROVE WITH CHANGES |
| §6.1 018F re-pin | APPROVE WITH CHANGES |
| §7 verification plan | APPROVE WITH CHANGES |

## Findings (probe results are OLD → NEW gate fire)

**F1. Contractions lose negation (blocker, challenge side).** In `_classify` the word regex `[A-Za-z0-9]+|n['’]t` tokenises "didn't" as `didn`, `t`, so `_NEGATION` never sees it. As a result a denial reads as a restatement:
- "Trump said he didn't end six wars." challenges: True → **False** (stance: proponent)
- "Trump says he hasn't ended six wars, only helped." challenges: True → **False**

This releases the exact case §4 says stays gated (a denial filed as a challenge). The §4 probe only passes because it uses "did not".

**F2. The anchor is not the speaker (blocker, support side).** `\btrump\b.{0,40}?\bsay` matches "Critics **of Trump say** he did not end six wars". That line classifies as a denial, and the text's stance becomes opponent.
- "Trump has repeatedly claimed credit for ending six wars. Critics of Trump say he did not end six wars." supports: True → **False**

The first sentence is a §4 "stays gated" probe word for word. Over-anchoring was harmless while the anchor could only cause a fire. It is unsafe once the anchor can cause a release. The same fault affects "Supporters of Trump said…" on the challenge side.

**F3. Claim polarity is computed from any negation token anywhere in the claim (blocker).** `claim_negated = _is_negated(texts[0])` flips on "without", "no" or "never" in any position. Negation words also count as content stems (`never` is not in `_STOP`).
- Claim "Donald Trump ended the Gaza war without a single US casualty"; "Trump says he's ended the war in Gaza, calling it a historic peace." supports: True → **False**. This is a plain recital support, released.
- "Biden says he never raised taxes…" against the claim "Biden never raised taxes…" is classified `denies`, because `never` is the first shared stem. The subject-free path happens to catch it.

**F4. "Negation before the first shared stem" is not predicate scope.** "Trump said he did what no president could: end six wars." supports: True → **False**. A claim of credit is read as a denial.

**F5. Stance is pooled across subjects.** `_stance` mixes all subject tokens together, so one subject's restatement releases another subject's recital.
- Reform-style claim: "Harborne said he had given Reform UK donations of £72m. Delo said it has not donated anything to Reform." challenges: True → **False**. Delo's denial is released.
- Accuser-type claim ("Amber Heard physically abused Johnny Depp…"): "Heard says she was the one physically abused during the marriage." challenges: True → **False**. The subject's contrary account shares the stems `abus`, `physic` and `marria`, so it is read as restating the claim.

**F6. Contrary figures count as restatement.** "Trump said he has only ended two wars." challenges: True → **False**. "In 2019 Trump said he had ended just one war." gives the same result. A challenge that rests on the subject's own lower count is a recital challenge. The mirror support ("Trump said he ended six wars") stays gated, so the gate becomes asymmetric in effect. All four 018F texts carry a figure ≥ 6 (six, eight, seven, seven), so a figure rule does not cost the fix.

**F7. The stance scan ignores R0–R5.** `_stance` uses the untagged `(t,t)` patterns with `finditer` and never calls `EvidenceNarrowing.skip`. Two probes show the effect:
- "Trump did not say he ended six wars; Trump said the deals were signed by others." is read as proponent (R2 negated speech counted), and the challenge is released.
- "Trump said they had ended six wars between them, referring to Qatar and Egypt." is read as proponent, and the challenge is released (§6.5 confirmed).

**F8. Implementation details (fine as built):**
- `(t,t)` vs tagged patterns: `_subject_patterns` ignores the subject argument, so the regexes are identical.
- The reasoning-path switch from `search` to `finditer` does not change behaviour when `release` is None, because the first `finditer` match is the leftmost `search` match.
- The cache keyed by text is safe per instance, because stance does not depend on direction.

Still needed at wiring time:
- Build one `DirectionRelease` over **both** `recital_texts` (`claim_map_analyzer.py:3000-3003`).
- Compute `claim_negated` from the normalised claim, not `texts[0]` alone.
- Read the ref's relationship at gate time.

**F9. The free measurement cannot see the risk.** Of the 12 stored fires, 8 are already silent under R0–R5 and 4 are supports that stay gated. The 0/12 figure therefore says nothing about challenge releases. The only challenge-direction evidence is 4 refs from one claim. Every hole above came from the kind of text the design names as its target (interviews and profiles, multi-subject claims).

**F10. A cheaper complement exists.** The 2026-09-24 review recorded a rebuttal-veto gap: `false|misleading|incorrect|exaggerat*|overstat*`. On the 018F texts, the AP reasoning ("incorrect") and the Guardian reasoning and text ("false and misleading") would be vetoed symmetrically, with no stance model. USA Today and CNN still need R6. Consider shipping that veto alongside R6, so R6 carries less.

## §6 open questions
1. **Re-pin.** All 21 directional refs in the 018F recording are `challenges`. The pin has therefore been counting misfires since at least 2026-09-10, although the golden's notes call them "the trap still fires". Re-pin to 0 and correct those notes. `recital_scope` is also in `scope_gates_must_fire`, and the existing precondition mechanism is a URL substring, which cannot express "the pool has a recital support". Two options:
   - add a precondition kind (for example, "≥1 `supports` ref whose reasoning carries a subject-anchored attribution verb");
   - or remove `recital_scope` from must-fire, with a dated note.

   Then add a **positive** tolerance-0 pin: the AP, USA Today, Guardian and CNN evidence ids stay `challenges`. A recital-support fixture does not need a paid re-record. Build a `_parse_mapping_response` wiring test from the stored 1c90a8bb / 75ef5e70 payload texts, which contain supports that restate the claim.
2. **Mirror.** Drop it in this build. Every support-side hole (F2, F3, F4) reaches the gate through the `opponent` branch, and the design expects its true-positive rate to be near zero. The principle stays symmetric as stated. Re-add the mirror, with its own flag, once the polarity detector passes the F1–F4 probes. Record this in the design as a deliberate, dated asymmetry of implementation, not of principle.
3. **Not in §6, but should be:** the multi-subject rule (F5) and the contrary-figure rule (F6).

## Required changes, in priority order
1. **Polarity (F1, F3, F4):**
   - Match `n't` on the raw text: `\b\w+n['’]t\b`.
   - Exclude negation words from stems.
   - Derive claim negation from predicate scope: a negator immediately before the main verb or auxiliary, not anywhere in the claim.
   - Treat `denies` as valid only when the negator sits between the self-report pronoun or auxiliary and the first shared stem, with no other clause in between. Anything else is `None`, never `denies`.
2. **Speaker (F2):** for release, count only matches whose token is the grammatical head, meaning no `of|by|against|for|about|to|with` and no possessive between the token and the verb. Firing keeps the loose anchor.
3. **Per-subject stance (F5):**
   - Compute stance per claim subject.
   - Release only matches anchored on that subject, and only when they classify as `restates` or `None`.
   - Never release a match classified `denies` or anchored on another subject.
4. **Figures (F6):** when the claim carries a figure, content with a lower figure, or a downtoner (`only|just|merely|a few`) before the first shared stem, is not `restates`.
5. **Stance ignores what the gate ignores (F7):**
   - Apply `EvidenceNarrowing.skip` (R0, R2, R5) and R0 sentence locality to stance matches as well.
   - Require the pronoun head to be `he|she|I|we` for a single-person subject. Allow `they|it` only for an ORG subject (`subject_kinds`).
6. **Drop the supports mirror** in this build (§6.2 above).
7. **Consider the rebuttal veto** (F10) as a separate, symmetric, one-line change.

## Additions to §7 verification
- Pin every probe in this review in both directions, beside the §4 set. They are the regression set for the classifier.
- Mutation-check each new rule (contraction negation, speaker head, per-subject stance, figure floor), not only the three the design lists.
- Build a challenge-direction population: replay `recital_match` with the gate on over **every directional ref** in the 19 stored payloads plus the corpus observations, not just the 12 stored fires. Read each released challenge by hand and list them in the design.
- Run the existing recital wiring tests with the flag on and off. Check for any parametrized `challenges` case whose expectation silently flips.
- Bench: compare arms per ref (evidence_id, direction, marker), as the 2026-09-24 review required, against a HEAD control.
