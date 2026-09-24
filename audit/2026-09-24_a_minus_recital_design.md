# Recital-gate misfires: design, for review before any build

**Date:** 2026-09-24.
**Status:** DRAFT for independent review.
**Rule:** difficulty 3; this gate guards TRU-018F-44AA.
**Why now:** the mapping review's #1 net-effect trap. The relationship review (M1) would demote Sky/YouTube on record cb939365 e1. The only sources stating "one weekend" (Guardian, AP) were already demoted by this gate, so e1 falls to unresolved. M1 cannot ship until this is fixed.

## 1. Every recital fire on the 19 graded records (12)

| # | Record/el | Marker (as stored) | Right? | Kind |
|---|---|---|---|---|
| 1 | 75ef e1 | restates the claim (energyflux) | ✅ correct | the claimant's own newsletter, verbatim |
| 2 | 75ef e2 | same | ✅ correct | " |
| 3 | 75ef e3 | same | ✅ correct | " |
| 4 | 1ca0 e1 | "According to abcnews.com, Reform…" | ❌ | **self-reference**: the distiller names the source itself |
| 5 | 1ca0 e2 | "According to theguardian.com, Reform…" | ❌ | self-reference |
| 6 | 1ca0 e3 | "…according to the article. — Delo…" | ❌ | self-reference |
| 7 | 1ca0 e2 | "Reform declines to say if…" | ❌ | **negated speech**: declining to say asserts nothing |
| 8 | 1c90 e2 | "…according to the Central Bank of Ireland" | ❌ | **the claim reports S's own research**: "S says" is the thing claimed |
| 9 | cb93 e1 | "Harborne's donation was announced on Saturday" | ❌ | **actor announces own act**: the timing IS the evidence for "one weekend" |
| 10 | cb93 e1 | "Harborne on Saturday announced he was matching the donation" | ❌ | actor announces own act |
| 11 | cb93 e2 | "Delo announced his gift on 11 September" | ❌ | actor announces own act |
| 12 | 1ca0 e2 | "Harborne has said he has matched the record £36m donation" | ❌ | actor announces own act |

**Result: 3 correct fires, 9 misfires.** Every misfire is on a support; the gate is symmetric but these happened to be supports.

## 2. How the gate decides today
`recital_scope.recital_match` (`app/utils/recital_scope.py`):
1. The mapper's `reasoning` is authoritative when it speaks either way (veto words, or attribution anchored to a subject token).
2. Otherwise the **evidence text** is scanned for `<subject token> … <attribution verb>` or `according to … <subject>`.
3. Otherwise the subject-free restatement check runs.

Misfires 4–12 all come through step 2, on a sentence in the evidence text that is not the sentence the support rests on.

## 3. Proposed rules. All narrow the evidence-text path (step 2); none touches the restatement path or the reasoning path.

- **R1: self-reference is not attribution.** `according to` followed by `the article|report|piece|story|source|post`, `this article|report`, or a bare domain (`abcnews.com`) never anchors a fire. Clears #4–6.
- **R2: negated or declined speech is not attribution.** `declin*/refus*/would not/did not/won't … (to) say|comment|confirm` never anchors a fire. Clears #7.
- **R3: a claim reporting S's own saying or publication.** Reuse `interested_party.released_subjects` (built today). For a released subject S, "S said / according to S" is the claimed fact, not a recital of it. It is per subject, and 018F-safe for the same reasons as the interested-party release: a closed verb list, an ORG-only measurement act, and the element restriction. Clears #8.
- **R4: an actor announcing their own TRANSACTIONAL act.** A speech verb (`announced|said|says|stated`) in the matched sentence does not fire when:
  - that sentence and the claim share a transactional-act stem from a closed list (donat, gift, pledg, match, contribut, resign, appoint, acqui, purchas, launch), with money-from phrasing ("£36m from X") in the claim mapped to the transfer stems; and
  - the sentence carries none of the contested self-assessment verbs (`claim*|tout*|boast*|insist*`).

  Rationale: announcing a donation, resignation or appointment is how the act becomes public record, and its date is often exactly the evidence (#9–11 give the weekend). "Trump stopped/ended/solved wars" shares no stem with the list, so it stays gated.

  Clears #9–12.

**Prototype (free, the 12 stored fires plus 018F-style probes):**
- **12/12 classified right:** the 3 correct fires kept, the 9 misfires released.
- Probes kept firing: "Trump has repeatedly claimed credit for ending six wars", "Trump announced he had ended the war between Israel and Iran", "Trump said he has solved six wars", "Trump claimed he had … donated his salary" (the `claim` verb vetoes the release), "The CEO said the company invested £2bn" (`invest` is not in the list).

## 4. Risks
- **R4 releases self-reports of transactions.** A pledge announced and never paid would count. For "X pledged £36m" the announcement IS the pledge; for "X donated £36m" it is an interested account. **Open question for review:** restrict R4 to claims whose own verb is performative (pledged, announced, appointed, resigned) rather than completed (donated, paid)?
- **A closed list is an open set (the lesson of the evaluative-head detector).** R4 is deliberately narrow, and a missed act keeps firing, which is the conservative direction.
- **018F bench pins:** `recital_scoped_refs` on 018F is already off by 1 in both arms (pre-existing). R1–R4 must not move 018F's recital or interested-party counts further. Check with the bench plus a control arm.
- **Symmetry:** the rules release supports and challenges alike (a released source keeps its direction).

## 5. Verification plan
- Unit tests pinning #1–12 and the probes, both ways; each rule mutation-checked.
- Bench vs the current HEAD control, focusing on 018F.
- State replay on the 19 payloads: which element states change. cb939365 e1 should keep its supports once M1 lands.

---

## Review outcome: 2026-09-24 (`audit/2026-09-24_a_minus_recital_review.md`)

**Verdict: APPROVE WITH CHANGES; R3 REWORK.**

**§2 holds.** All 9 misfires replay on the stored title and snippet through the evidence-text path. However:
- #4 and #7 each carry a SECOND anchored match, so they need R4 too.
- R4 therefore carries 6 of the 9, not 4.
- **Build requirement:** use `finditer` with a per-match skip, and apply the rules to evidence text only.

**018F cannot vouch for this change.** Its committed recording has no recital SUPPORTS; its 4 scoped refs are fact-check challenges. Compare runs ref by ref, not by count; support safety rests on the unit tests.

**R3 REWORK.**
- Reusing `released_subjects` released Trump for "Donald Trump stopped six wars, as he said he would". That exposed the same hole in the interested-party release shipped earlier today (`cd4e340`), and the old 2026-09-22 whole-gate disarm had it too, only wider.
- **Fixed immediately in `interested_party.released_subjects`:** ORG-only for both branches, and the verb must sit in the subject's own clause (a clause break — comma, "as", "which"… — blocks it; a coordinated name list does not).
- Tests: that sentence with subject typed person AND org, plus a plain person saying; mutation-checked. Unit suite green.
- For the recital gate, R3 becomes an ORG-only publication frame as the claim's main verb, with no saying branch.

**R4, with changes:**
- Cut `contribut` and `launch` from the stem list.
- Block self-assessing elements ("biggest ever").
- Answer to the open question: release when the claim's verb is performative, OR the same text states the figure in its own voice.

**New rules:**
- **R0:** matches cannot cross sentence boundaries.
- **R5:** passive voice ("X's donation was announced") never anchors.

**Rejected:** "the sentence must carry the element's content". It clears only 4/9 and would release paraphrased recitals.

---

## Build log: 2026-09-24 (uncommitted at time of writing)

**Built:** R0, R1, R2, R3, R4 and R5 in `recital_scope.EvidenceNarrowing` / `_assess_evidence`, applied to the EVIDENCE-text path only. Rollback: `ENABLE_RECITAL_EVIDENCE_NARROWING`.

**Changes from the review, all applied:**
- **Overlapping search:** each match restarts one character after the previous match start. A match skipped by R0 from an earlier token occurrence must not hide the real one. Found by a failing test.
- **R3:** `released_subjects(include_saying=False)`, ORG only.
- **R4:** stems cut to donat / gift / pledg / match / resign / appoint / acqui / purchas; a self-assessing element blocks it; it releases only when the claim is performative OR the text states a claim figure in its own voice.

**Replay** of the 12 stored fires through the real code: **12/12 right** (9 released, 3 energyflux restatements still fire). All 4 018F probes still fire, including "Trump has said he donated his salary and ended six wars".

**Tests:**
- 21 in `test_recital_narrowing.py`, including 2 wiring tests through the real parser (the weekend source keeps its support; flag-off restores the old behaviour).
- **All 9 mutants caught** (R0, R1, R2, R3, R4, R5 and R4's three guards). R5 and the claim-verb guard first SURVIVED; isolating tests were added.

**Unit suite:** 4,004 pass / 44 skipped.

**Bench:** identical to the previous run, check for check (147/9/11/5, known 82CF + 93DD drift).

**018F:** narrowing on vs off gives identical recital blocks (e1: 1 + 3 scoped). The bench records per-element counts, not per-ref ids, so this is the finest comparison available. Support-side safety rests on the unit tests, as the review said.
