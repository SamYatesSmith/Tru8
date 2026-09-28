# Family A: gates that misread who is speaking — design, for review before any build

**Date:** 2026-09-28. **Status:** DRAFT → independent review → founder approval. Difficulty 3 (touches both TRU-018F-guarding gates).
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
