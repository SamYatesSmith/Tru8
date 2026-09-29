# Family A: gates that misread who is speaking — design, for review before any build

**Date:** 2026-09-28. **Status:** REVISION 2 (end of file) is the live design. §2–§6 are v1, superseded after review (`2026-09-28_family_a_speaker_review.md`: diagnosis approved, both fixes rework). Revision 2 → second review → founder approval. Difficulty 3 (touches both TRU-018F-guarding gates).
**Origin:** `audit/2026-09-28_mapping_failures_review.md` § A (records #7 Cook, #10 Central Bank). The goal is the general fault class, not those two records.

## 1. What is actually wrong (reproduced offline, 2026-09-28, no spend)

The review filed family A as "a gate demotes an organisation's own publication". Reproducing both fires against the current code shows two separate faults. Neither is really about publishers.

### A1. The recital gate never works out who is speaking
The subject-anchored patterns pair **any** claim-subject token with **any** nearby attribution wording. They treat that token as the speaker, even when it is the topic of the reported fact. Reproduced on the current code, with subjects `democrats`, `trump`, `cook political report`:

| Sentence | Fires today | Correct |
|---|---|---|
| According to the September 2026 toplines, **Democrats** hold a two-point advantage. (#7's marker, exactly) | yes | **no**: the toplines speak; Democrats are the topic |
| **Democrats** hold a two-point lead, the poll said. | yes | **no**: the poll speaks |
| According to **Trump**, six wars have ended. | yes | yes |
| According to a White House statement, **Trump** has ended six wars. | yes | yes (his own office) |
| According to his spokesman, **Trump** has ended six wars. | yes | yes |
| **Trump** ended six wars, he said. | yes | yes (pronoun refers back) |
| **Trump**, speaking at the UN, claimed to have ended six wars. | yes | yes (appositive) |

**General effect:** on any claim whose subject is a party, a person or a company that sources report *about*, a source reporting a measured fact loses its direction. Elections, polls, company results and court rulings are the obvious cases. The effect is symmetric, so it hides challenges exactly as often as supports. It is not limited to Cook.

**Existing machinery:** R6 (`DirectionRelease._speaker_is_subject`, 2026-09-25) already identifies the speaker, but only to *release* a challenge. The fire path never asks.

### A2. The interested-party release is withheld on content elements
`released_subjects` releases an ORG whose own measurement or publication the claim reports ("Central Bank of Ireland research … shows"). The element must then name the subject or the act, a guard added so decomposition cannot carry a release onto "six wars ended". But decomposition routinely writes the finding as its own element with no name in it ("MNE activity added 1.2 per cent to annual growth since 2022"). The release is withheld, and `centralbank.ie` is scoped out as an interested party on the one element that carries the claim's figure. The page then says no source contains the figure, which is false.
- Reproduced: with the element worded without "Central Bank" or "Ireland", release = ∅ and prong 1 fires. With "Ireland" in the element, the release holds, because the token `ireland` counts as naming the subject.
- So the guard is both **too strict** (content elements) and **too loose** (a place-name token counts as naming the org).
- ⚠️ Confirmed on the grader's wording, not the stored element text. Reading #10's stored `metadata.subject_kinds` and e2 description is owed (see § 5).

## 2. Design

### A1: speaker resolution before a recital fires
Applied inside `_subject_patterns` matching, on **both** the reasoning and evidence paths, and to supports and challenges alike (invariant #7). A subject-anchored match fires only if the speaker is the subject:
- **`according` kind:** the according-to phrase ends at the first clause break (`,` `;` `:` `—` or a sentence break). The subject token must fall **inside** that phrase, or the phrase must name:
  - the subject's own office, reusing the `_EXECUTIVE_COMMS` terms (e.g. "White House" → trump); or
  - a possessive plus an agent noun ("his/her/their spokesman | spokesperson | office | campaign | aides | lawyer | representative").

  Otherwise there is no fire.
- **`verb` kind:** fires when either:
  - the words between the token and the verb are a speaker bridge (R6's `_SPEAKER_BRIDGE`, after removing one comma-delimited appositive); or
  - the clause immediately before the verb is a bare personal pronoun (he/she/they/it) with the token earlier in the same sentence.

  A different noun phrase as the verb's subject ("the poll said", "officials say", "Cook reported") means **no fire**.
- **`quote` kind:** unchanged. "quotes … Trump" names the quoted party.
- **Unchanged:** distancing adverbs, the verification veto, R0–R6, and the subject-free restatement path. A near-verbatim restatement of the claim is still caught with no speaker at all, so a source that merely recites "Democrats lead 49–47" is still scoped.
- **Flag:** `ENABLE_RECITAL_SPEAKER_RESOLUTION` (default True after verification; rollback = False).
- **One module:** R6 and A1 will share one speaker function, so they cannot disagree about who is speaking.

### A2: a measuring organisation is released unless the finding is about itself
Replace the element restriction **for the measurement/publication branch only**:
- **Release** the ORG subject when the claim reports its measurement or publication (the existing closed verb and noun lists, same clause), **unless** the reported finding refers back to the organisation itself.
- **What counts as referring back:** after the claim's finding head (`shows | finds | found | that | :` following the act), the org's token appears, or `its | their | our | own` appears. Examples:
  - "Exxon study shows **its** emissions fell" stays gated.
  - "CBI research shows multinational activity…" is released.
  - "Cook poll finds Democrats lead" is released.
- **Why claim-level, not element-level:** decomposition drops names unpredictably, so the element is the wrong place to look. The claim is where the org's relation to its finding is stated.
- **Unchanged:**
  - the saying branch keeps the element restriction (the TRU-018F lineage);
  - PERSON and claimant subjects are never released;
  - executive-comms domains are never released;
  - the recital R3 path uses the same function, so the two gates stay consistent.
- **Also fixed:** a place-name token ("ireland", "england") no longer satisfies the saying branch's "element names the subject". The org's first distinctive token must appear.
- **Flag:** `ENABLE_MEASURER_RELEASE` (default True after verification).

## 3. Guards that must hold (tests, written before the change)
**TRU-018F-44AA, every form:**
- "Trump stopped 6 wars": whitehouse.gov stays interested-party.
- Its recital fires still fire, including the White House, spokesman, pronoun and appositive forms in § 1.
- "The White House published figures showing 6 wars ended" still does not disarm anything.
- R6 challenge releases are unchanged.

**Other must-hold cases:**
- "Exxon's own study shows its emissions fell 20%": exxonmobil.com stays gated on every element.
- A claimant's own newsletter stays recital-scoped (Kennedy `977b36b7`).
- Thirlwall (`8d66d41a`) keeps its release.

**Mutants:** each new rule removed, and the pronoun branch removed, must each fail a test.

## 4. Why this is general
- **A1 changes one question:** is the named subject the speaker? It applies to every claim with a named subject.
- **A2 changes one question:** is the organisation the measurer, or the subject of its own finding? It applies to every claim that reports an institution's research, poll, survey or statistics.
- **No host lists, no org lists, nothing keyed to Cook or the Central Bank.** The only list touched is the existing executive-comms map, reused rather than extended.

## 5. Verification (all free; no model calls)
1. Unit tests above, with mutation checks.
2. **Fire-diff over every stored directional ref available.** Run both gates old vs new and hand-read every changed fire, both directions:
   - the replay corpus: 10 claims, local;
   - the 19 re-measure payloads. Fetching these needs the founder: the owner payloads need an API key, which this session is not permitted to read.

   Report counts of fires lost and gained. Any lost fire that a reader would call a genuine recital is a defect.
3. Replay bench: the 018F recital and interested-party pins must hold, the known drift claims excepted.
4. State replay on the 19 payloads: report every element state change, both directions.

## 6. Risks
- **Pronoun coreference is a heuristic.** "Trump ended six wars, he said" fires, correctly. But "Trump ended six wars, Rubio said. He said…" could mis-attribute. Firing on the pronoun is the conservative direction for the 018F class.
- **A2 widens a release.** An organisation that measures something it has a stake in, without saying "its" ("Exxon study shows oil demand will keep rising"), is now released. That is the correct reading of *what the study says*, but it counts an interested measurer as support for the fact. Question for the reviewer and the founder: is that acceptable, given the tier and ownership labels stay visible, or does A2 also need an "industry body / company" exclusion, and if so, from what signal?
- **Cassettes:** gate outcomes are not cassette keys, so no re-record is expected. Confirm on the bench.

---

## Revision 2 — 2026-09-28 (after review; founder decision on A2)

**What changed and why.** The review showed v1's A1 changed the gate's purpose. The subject token was only how the gate finds attribution; the gate exists to catch a recital by the claim's subject **or anyone else**. v1 lost the subject's own boasts ("Trump on Tuesday claimed…") and third-party recitals ("his spokesman said…"). v1's A2 did not fix #10. It also released campaigns, parties and companies on their own claims, and opened R3 to third-party sayings. Both are replaced.

**Founder decision (2026-09-28):** an organisation's own publication is released only when that organisation is **not the claimant**. Vote Leave, Labour, Reform or Tesla asserting their own finding stay gated. The Central Bank is released when a journalist reports its research.

### A1′: skip instrument speakers only (replaces v1 A1)
A subject-anchored match is skipped **only** when the speaker is a document or instrument. Every person or agent speaker keeps firing, whoever it is.
- **Instrument nouns (closed list):** toplines, poll(s), survey(s), data, figures, results, study, research, report, bulletin, index, estimates, analysis, statistics, release, dataset.
- **`according` kind:** skip when two things hold. The according-phrase, up to the matched token, contains no subject token of its own. And its head noun (the last noun before a comma, or before the token) is an instrument noun. This works with or without a comma.
  - Skipped: "According to the September 2026 toplines, Democrats…"; "According to the poll Democrats…".
  - Fires: "According to administration officials, Trump…"; "According to his spokesman, Trump…"; "According to the company, Tesla…"; "According to a White House statement, Trump…" ("statement" is speech, not an instrument).
- **`verb` kind:** skip when the words immediately before the attribution verb are an instrument phrase: (the | this | that | its | their | our | latest | new), then optional modifiers, then an instrument noun. Examples: "the poll said", "the latest survey says".
  - A pronoun ("…, it said") does **not** skip. An unknown speaker keeps firing, as today.
- **Unchanged:** distancing adverbs, veto, R0–R6, subject-free restatement.
- **Kept apart from R6:** A1′ neither uses nor changes `_speaker_is_subject`. Firing stays loose and release stays strict, as the R6 review required. R6's full probe set runs as a regression.
- **Flag:** `ENABLE_RECITAL_INSTRUMENT_SKIP`, default True after verification.

### A2′: release a measuring organisation at claim level, never for the claimant (replaces v1 A2)
The measurement/publication branch of `released_subjects` releases an organisation only if all three hold:
1. **Kind and claimant.** The subject is kind `org` and is **not the claim's claimant**. Names are compared normalised; containment either way counts as a match.
2. **Act before finding.** The claim states the measurement act or publication noun **before** the finding, in the subject's own clause (the existing closed lists and clause rule). A finding head follows: `shows | show | finds | found | suggests | estimates | concludes | that | :`. If there is no finding head, **withhold**.
3. **Finding not about itself.** The finding (the text after the head) does **not** refer back to the organisation. Referring back means one of:
   - the whole subject phrase;
   - its acronym, where the claim or the entity gives one;
   - `its | their | our | own`;
   - `the (company | firm | group | party | campaign | organisation | organization | bank | charity | association | union)'s`.

   A single token never counts, so "Ireland's" and "central to" do not.

**Plumbing needed for rule 1:** `runner.attach_claim_subjects` has to write `metadata["claimant"]`. At present, a claimant that is also a typed ORG entity comes out of `subject_kinds` as plain `org`, so "is the claimant" cannot be read from the metadata today.

When all three hold, the release covers every element of the claim. The element restriction is dropped for this branch only.

Other points:
- **Unchanged:** the saying branch keeps the element restriction. Executive-comms domains are never released.
- **F11 closed:** "Exxon study shows its emissions fell" now withholds on every element. Today an element naming Exxon is released.
- **Receipt:** each release records why, in the interested-party summary: `release_reason: "claim reports this organisation's own research; organisation is not the claimant"`.
- **Flag:** `ENABLE_MEASURER_RELEASE`, default True after verification.

### R3′: narrow the recital release for a measurer (replaces v1's "R3 uses the same function")
For an organisation released by A2′, the one match R3′ skips is an `according` match whose phrase names that organisation's **instrument noun**. Example: "according to Central Bank of Ireland research | data | figures | analysis…".
- **Saying verbs always fire:** "Vote Leave has repeatedly claimed…", "the Central Bank said…".
- **Both paths:** the reasoning path and the evidence path (F9), so #10 does not depend on the mapper's wording.
- **Claimants and unreleased organisations:** nothing is skipped.

### Place-name fix: dropped (F12)
Out of family A's scope. The saying branch keeps today's token test. A proper fix needs its own design.

### Tests, written first (the review's adversarial set becomes the regression suite)
**Still fires, both directions:**
- every F1 and F2 sentence;
- "According to the company, Tesla…" and "According to its spokesperson, Tesla…";
- "Vote Leave has repeatedly claimed … £350m" (a news source, Vote Leave claim);
- "…, it said";
- R6's full probe set.

**Now skipped:**
- "According to the September 2026 toplines, Democrats…", plus the no-comma form;
- "Democrats hold a two-point lead, the poll said";
- "the latest survey says".

**A2′ releases:**
- #10 verbatim;
- #10 with "central to";
- "Cook poll finds Democrats lead" (Cook is not the claimant).

**A2′ withholds:**
- Tesla, Vote Leave, Labour, Reform, Pfizer and NHS England, each as claimant;
- "An Exxon study shows the company's emissions fell";
- "Exxon's emissions fell 20%, an Exxon analysis estimated" (no act before the finding);
- the F11 element naming Exxon.

**Other test changes:**
- `test_the_element_can_withhold_a_release` is rewritten deliberately. Cook as a non-claimant measurer is now released on "Democrats lead…". The guard it stood for moves to the Exxon and claimant cases.
- **TRU-018F:** whitehouse.gov stays gated, and every recital fire stays.
- **Mutants:** removing any rule must fail a test. That includes the claimant exclusion, the finding-head requirement and R3′'s saying-verb exclusion.

### Verification (free)
1. **Read the stored fields first** via the tru8 MCP `tru8_get_result_raw`:
   - #7: `subject_kinds`. Is `democrats` an ORG?
   - #10: the e2 description, `subject_kinds`, `claimant`, and the Central Bank ref's reasoning.

   The audit files hold only 8-character prefixes, so the founder supplies the two full check ids.
2. Unit and adversarial suite, plus mutants.
3. Fire-diff over the 10 corpus claims and the 19 public payloads. The public payload carries scope-note reasons but not ref reasoning, so only the evidence path can be diffed there. Report lost and gained fires by direction and by claim type (a boast or accusation versus a report).
4. Bench: the 018F pins hold.

### Risks that remain
- **The instrument list is closed.** A missing noun keeps firing, which is safe but a miss.
- **A2′'s claimant signal is only as good as extraction's `claimant` field.** A campaign that extraction misses as claimant is released. That exposure is limited to the organisation's own domain, and R3′ never silences sayings.
- **A2′ still releases an interested measurer quoted by a third party.** Example: "the Guardian reports Tesla data show…", where the claimant is the Guardian writer. This is the reading the founder accepted, and the element receipt discloses it.

---

## Build log: A1′ — 2026-09-29 (founder: "proceed"; A2 parked on the claimant signal)
- **Code:** `recital_scope.InstrumentSkip`, applied on both paths (`_assess` for the reasoning, `_assess_evidence` for the evidence), before R6. Wired in `claim_map_analyzer` under `ENABLE_RECITAL_INSTRUMENT_SKIP` (default True).
- **Review G1 applied:** there is no skip when the instrument has an owner:
  - a possessive, or `X's`;
  - White House, Downing Street, No 10 or WH;
  - campaign, administration, government, party, press, office or spokes*.

  `release` is not an instrument noun.
- **Dropped as redundant:** the "phrase names a subject" check. A subject inside the phrase gets its own anchored match, which is never skipped. A mutant proved it untestable.
- **Tests:** `tests/unit/pipeline/test_recital_instrument_skip.py` has 60 cases: the review's F1, F2, F4 and G1 sentences, both directions, both paths, and flag-off. There are 2 wiring tests in `test_assertion_evidence_wiring.py`.
- **Mutants:** 5 of 5 killed (owner check, the according branch, the verb branch, wiring, and the redundant check shown removable).
- **A2 status:** PARKED. `extract.py:524-530` defines claimant as "the body issuing a statement or figures", so it cannot separate an independent measurer from a party to the claim. It needs a new extraction signal, which is a founder decision (prompt change; re-keys cassettes).
