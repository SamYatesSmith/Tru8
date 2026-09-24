# Recital-gate misfires: independent review of the design

**Date:** 2026-09-24. **Reviews:** `audit/2026-09-24_a_minus_recital_design.md`.
**Method:** read-only. I read `recital_scope.py` in full, `interested_party.released_subjects` (cd4e340), the wiring at `claim_map_analyzer.py:2891-3001`, the three recital test files, and the 018F golden, observation and cassette. I pulled the four public payloads (curl) and replayed `recital_match` offline against the stored title+snippet. I ran no checks, no bench and no model calls.

**Overall: APPROVE WITH CHANGES. R3 needs rework before any build.** The diagnosis in §2 is right. Two things in the design are wrong: which rule clears which misfire, and the 018F safety argument. R3 as written reopens the 018F hole through a different wording.

---

## 1. Is §2 right? Yes, and all nine misfires replay exactly

Replaying today's `recital_match` on the stored title+snippet reproduces all 9 misfires. The markers match byte for byte and every one has `found_in: "evidence"`. None of the nine reasonings has an attribution verb anchored to a subject, and none has a veto word, so every one of them falls through to step 2. The public payload is therefore a faithful input for the state replay in §5, with one caveat: the three correct fires on 75ef (the restatement path) **do not** replay. The public metadata carries no `claim_text`, and those fires match the submitted wording only. A replay has to supply `metadata.claim_text`. Otherwise the three correct fires look "released" and the result reads 12/12 for the wrong reason.

How `_assess` anchors, and why it misfires:
- It scans the **whole text**. `_VETO` is checked across the whole text, then each pattern takes its first `search()` hit anywhere in it. Nothing ties the hit to the sentence the relationship rests on. That is the whole defect.
- The windows use `re.DOTALL`: `.{0,40}?` after the token, `.{0,30}?` after `according to`. They **cross sentence and bullet boundaries.** #6 is `according to the article.\n- Delo`: the "according to" phrase ends one bullet, and the token begins the next.
- `according to .{0,30}? <token>` was written for "according to Trump". It also matches "According to abcnews.com, **Reform** UK received…", where the token is the subject of the *reported fact* and not the speaker (#4, #5).
- The token only has to sit before the verb. It does not have to be the verb's subject. "Harborne's donation **was announced**" (#9) is a passive, and "donations … from Harborne and Ben **Delo, announced** within 24 hours" (#7's text) is a reduced relative. In neither is the subject the speaker.

**The design misattributes which rule clears which misfire.** Several texts contain more than one anchored match, so excusing the first match is not enough:

| # | Other anchored matches in the same text | Actually cleared by |
|---|---|---|
| 4 | "Christopher Harborne announced he was matching the donation", "Delo said his donation was calculated…" | R1 **and** R4 |
| 7 | "…Ben Delo, announced within 24 hours" | R2 **and** R4 |
| 5, 6 | none (once #6 is sentence-bounded) | R1 (or sentence bounds, for #6) |

R4 is load-bearing for 6 of the 9 misfires, not 4. Mutation checks have to be read with that in mind: disabling R4 should re-break #4 and #7 as well.

**The implementation must use `finditer` and skip per match.** `_assess` calls `pattern.search`, which returns only the first hit. If a rule "excuses" that hit and the loop moves on to the next pattern, a real recital later in the same text is never examined. That fails in the over-releasing direction. Each rule must excuse one match and keep scanning.

**The rules must be evidence-path only.** `_assess` is shared by the reasoning path and the evidence path. Put the rules inside `_assess` unparameterised and they also release reasoning strings such as "Reports Harborne announced his £36m donation". The design promises the reasoning path is untouched; that needs an explicit `mode="evidence"` argument or a separate function, plus a pin.

## 2. 018F safety: the bench cannot verify it on this recording

What the committed 018F recording actually contains:
- The main mapping (gemini-3.7-flash) returned **9 refs, all `challenges`, and zero supports**. The completion census added 5 challenges and 4 context refs.
- `recital_scope_events` = `[e1:1, e1:3]`: **4 scoped refs, all challenges** (the golden pins 3 at tolerance 0; that is the known off-by-one).
- At least one fire is on the reasoning path: `ev-b507541111b9`, "Identifies **Trump's claims** of having ended seven wars as false and misleading". The mapper calls it a refutation, but `false|misleading` is not in `_VETO`.
- At least one is on the evidence path: `ev-1da14489eb62`, the AP story "FACT FOCUS: **Trump says** he's ended eight wars. His numbers are off". The silent-reasoning challenges that go to the evidence path are 1da1, 0ad6, 89ec, 7bf6, 30f2 and 5114.

So on this recording **the 018F recital pin counts fact-checks being demoted to context.** These are misfires of exactly the §2 shape (the attribution sentence is the claim under check, not the basis of the challenge), running in the challenge direction. The trap the gate exists for, recital *supports*, is absent. It follows that:
- "R1–R4 must not move 018F's counts" is the wrong acceptance test. A drop could be an improvement, and a hold proves nothing about supports.
- Compare **per ref** (evidence_id, direction, marker) between the arms, not counts.
- 018F-safety for supports rests entirely on the unit fixtures, which are the verbatim 2026-08-13 strings. Add the negative pins listed in §5 below.
- The design's line that "every misfire is on a support" holds for the 19 graded records but not for the corpus claim. Record challenge-direction misfires (and the `false|misleading|incorrect|exaggerat*|overstat*` veto gap) as a separate open item. Do not fix them in this build.

**Existing fixtures R1–R4 would change: none.** In `test_recital_scope.py`, every production fixture is on the reasoning path, or is `claimed` (R4-vetoed), or has no stem ("announced he negotiated a truce"). The wiring tests (`ev-cbs`, `ev-wh-solved`, Thirlwall, Cook, the White House "published" map) either use reasoning-path fires, or disarm through attribution-shaped elements, or are owned by interested-party. The Cook claim *would* release `cook political report` under R3, but `ev-cook` has no anchored match today, so its outcome does not change. The original-wording, no-subjects and reported-result tests are all restatement path. **This is a gap as much as a comfort:** no existing test exercises the evidence path with a speech verb next to a transactional stem, so nothing pins R4's boundary today.

## 3. R4: the list is too broad, and the open question

The shared-stem test only checks that the sentence and the claim share an act stem. It does not check what the element asserts about that act. Constructed cases that R4-as-written releases but should keep gated:

| Probe (claim / evidence sentence) | R4 as written | Should |
|---|---|---|
| "Trump contributed to ending six wars" / "Trump said he contributed to the ceasefire" | release (`contribut`) | **gate**: this is 018F again |
| "The government launched 40 new hospitals" / "Johnson announced he had launched 40 new hospitals" | release (`launch`) | **gate**: a classic contested self-report |
| "Company X donated £1bn to charity" / "Company X announced it donated £1bn" (no other statement in the text) | release | **gate**: an interested account of a completed act |
| "Delo made the biggest donation in British history" / "Delo said his donation was the biggest ever" | release (`donat`; "said" is not a veto) | **gate**: the element is the self-assessment, not the act |
| "Musk acquired Twitter to save free speech" / "Musk said he acquired Twitter to save free speech" | release (`acqui`) | **gate**: the element is the motive |
| "Minister announced the hospital was launched" | release | gate |

**Answer to the open question: take performative-or-co-stated, not performative-only.** R4 releases a match only when all of the following hold:
1. The stem list is cut to what was observed: `donat|gift|pledg`, plus `match(ed|ing)` only within ~6 words of `donation|gift|pledge`. Drop `contribut`, `launch`, `acqui`, `purchas`. Add `resign` and `appoint` only when a case is observed, following the rule the interested-party map already applies to itself.
2. The element carries no qualifier beyond who, what, how much and when: no `record|biggest|largest|most|first|ever|history|because|to <verb>` motive or comparison. Those are self-assessments, which is the one thing a recital must never support.
3. Either (a) the claim's own verb for that subject is **performative**, so the announcement *is* the act (`pledged|promised|announced|appointed|resigned`), or (b) the same text carries an **own-voice co-statement**: a sentence stating the element's figure with no anchored attribution match, no `according to` (other than the self-reference R1 excuses) and no distancing adverb. The support then rests on the reporter's statement, not the announcement.
4. The self-assessment veto list stays, and gains `credit` ("claimed credit").

Checked against the 12 by hand (not executed): the 1ca0 claim says "pledged", so (a) clears #4, #7 and #12. cb93 is completed ("came … from"), but its texts state the figure in their own voice ("received 72 million pounds … this weekend"; "On Friday Ben Delo gave Reform UK £36 million"), so (b) clears #10 and #11. #9 is cleared by (b), or by the passive rule below. All six adversarial probes above stay gated. Pure performative-only would keep #10 and #11 firing, and cb93 e1 would lose AP, which is the record M1 needs.

**Add a passive-voice rule (R5).** `was|were|been|being` directly before the speech verb, or a reduced relative (`<token>, announced`), never anchors a fire, because the token is not the speaker. It clears #9 and #7's second match independently of R4, is general, and cannot release a recital, since in a passive the subject is not doing the saying.

## 4. R3: reusing `released_subjects` is wrong for this gate

`released_subjects` was built for a domain gate that keeps a backstop: executive-comms domains are never released. The recital gate has no equivalent backstop. Verified against the committed function:
- **The saying branch reopens 018F.** "Donald Trump stopped six wars, as he said he would" → releases `donald trump`, because `said` falls inside the 80-char window, and the element "Donald Trump took actions that … ended six wars" names the subject. The same happens for "Donald Trump, who says he is the president of peace, stopped six wars" and "Trump stopped six wars, the White House said". In each case "Trump claimed he ended six wars" in the evidence text would then stop anchoring.
- **The element restriction is close to vacuous here.** The recital gate only fires on a subject token, and elements usually name the subject, so `names_subject` nearly always holds. #8 releases only because the element happens to say "**Ireland**'s", and `ireland` is a token of "central bank of ireland". Written as "Multinational activity has driven economic outperformance", it would not release.
- **The 80-char window crosses clauses.** "Reform UK received £72m this weekend, according to figures published by the Electoral Commission" releases `reform uk`, because another subject's `published` falls inside the window.
- Stored payloads carry no `subject_kinds`, so the ORG branch will not fire in the §5 state replay unless the replay supplies kinds.

**Required rework for R3:** write a recital-specific release, `publication_subjects`:
- measurement/publication frame only, ORG only, and **no saying branch**. Saying claims already disarm the whole gate through attribution-shaped elements, and the saying branch is where the hole is;
- the frame must be the claim's **main predicate**: the subject NP opens the claim, followed by `research|study|survey|poll|data|analysis|bulletin`, then optionally `published|released …`, then `shows|finds|found|estimates`, all in the same clause (no comma, semicolon or dash between them);
- no `names_subject` test. The frame itself is the licence, since every element of such a claim is a proposition inside the published finding;
- for a released subject, drop only the `according to <token>` and `<token> … says/said` anchors. Distancing (`purportedly…`) and the restatement path stay live.

Probes: #8 releases. "Pfizer's study shows its vaccine is 95% effective" releases, which is correct because the claim is the study's result. "Donald Trump stopped six wars, as he said he would" does not release.

## 5. Is there a simpler, more general rule?

**Candidate A: fire only on a sentence that itself carries the element's content** (at least one shared content word or figure). I evaluated it on the stored texts, with sentence-bounded matching and figures normalised. It clears 4 of 9 (#6, #9, #10, #11). It keeps #4, #5 and #12, whose sentences carry £72m/£36m, #7, where "Delo, announced" carries £36m, and #8. It is also **unsafe**: lexical overlap misses paraphrase. CBS's "Trump says he's ended 6 or 7 wars" against an element "Six distinct conflicts existed" shares nothing ("6" vs "Six"), so a real recital would be released. **Rejected as a replacement.**

**Candidate B: sentence-bounded matching (call it R0).** Split on `(?<=[.!?])\s+(?=[A-Z"'“])` and on newlines/bullets, and never let an anchor window cross a boundary. It is general, it only tightens locality, and no verbatim 018F fixture spans a boundary. It clears #6 on its own. **Adopt it, alongside R1–R5.**

**Candidate C: pick the sentence using the mapper's reasoning** (fire only when the sentence the reasoning overlaps most is the attribution sentence). It clears #9–11 elegantly and is the most direct encoding of §2. But it trusts model-shaped reasoning, which the module docstring names as its known limit. Keep it as a later option, not the floor.

**Required pins, beyond #1–12:** "Trump said he contributed to the ceasefire"; "Johnson announced he had launched 40 new hospitals"; "Company X announced it donated £1bn" (no own voice); "Delo said his donation was the biggest ever" on a "biggest" element; "Donald Trump stopped six wars, as he said he would" together with an evidence-path "Trump claimed he ended six wars" (R3); "According to whitehouse.gov, Trump ended eight wars" on a non-whitehouse item (R1 must not excuse it); "Trump has not stopped saying he ended six wars" (R2 must not excuse it); a text where the excused match comes first and a real recital second (`finditer`); a reasoning string carrying "announced his £36m donation" (evidence-path only).

## Verdicts

| Rule | Verdict | Required changes |
|---|---|---|
| **R0** (new) sentence bounds | APPROVE (add) | Anchor windows never cross a sentence or bullet boundary. |
| **R1** self-reference | APPROVE WITH CHANGES | Excuse only `according to` + `the (article|report|piece|story|post)` placed immediately, or the **evidence item's own host**. A bare domain other than the item's own (`according to whitehouse.gov, Trump…`) still anchors. Per-match skip with `finditer`. Say that it clears #5 and #6 alone and #4 only with R4. Optional later work: stop the distiller writing "According to <domain>" (this re-keys cassettes). |
| **R2** declined speech | APPROVE WITH CHANGES | Adjacent form only: `(declin|refus)\w* to (say|comment|confirm|disclose)`, or `(would|did|will|could) ?(not|n't) (say|comment|confirm)`. Never `denied` (a self-serving denial must still scope). "has not stopped saying" must still fire. It clears #7 only together with R4 or R5. |
| **R3** publication subject | **REWORK** | Do not reuse `released_subjects`. Use a recital-specific, ORG-only publication frame that is the claim's main predicate, with no saying branch and no `names_subject`. Release only the according-to and says anchors. Pin "as he said he would". |
| **R4** own transactional act | APPROVE WITH CHANGES | Stems `donat|gift|pledg|match+donation` only. The element carries no qualifier or self-assessment. Release only if the claim verb is performative **or** the text co-states the element's figure in its own voice. Add `credit` to the veto list. Evidence path only. |
| **R5** (new) passive or reduced relative | APPROVE (add) | `was/were/been/being <verb>` or `<token>, <verb>` never anchors. |

**Acceptance:** compare the 018F arms per ref, not by count. The current recording has no recital supports, so 018F-safety for supports rests on the unit pins. Record separately, without building: challenge-direction misfires on 018F (the AP "His numbers are off" story; the `false|misleading` veto gap).
