# Astra regrade — 9 September 2026

The founder asked whether the branch has reached Astra's 8/10. Astra's 14 hands-on inputs (`tmp/tru8-hands-on/tru8-hands-on-assessment.md`, register rows 1–14) were re-run locally on the branch at `da9b61c` in two arms: **default** (the configuration that ships at merge, both candidate flags OFF, the new same-study gate ON) and **candidate** (`ENABLE_PASSAGE_MAPPING` on inside the process). Text, URL and image inputs; the research-focus variant; the EV strengthening. Runner `tmp/astra-regrade.py`; artefacts `tmp/astra-regrade-{default,candidate}/`; grader's views `tmp/astra-regrade-*-summary.txt`. Local database, live retrieval and models. Grader: Claude, against Astra's per-test findings and its three non-negotiables. This is not the knowledgeable-human review the 8/10 gate requires.

## Verdict

**Default arm: about 7/10, not 8.** Astra's two headline failures are gone and reliability was clean, but three of the fourteen inputs had their contested part silently removed at extraction, which fails Astra's first requirement ("structure must faithfully reflect the material") before any evidence work begins. That defect is fixed in this commit (below) and re-verification is owed.

**Candidate arm: not ready, must stay OFF.** It fixes what it was built for (creatine, SELECT's absolute claim, the Sweden focus decomposition) and breaks Astra's headline test in the other direction (the true Bank Rate reads "context only"), adds wrong-direction passage supports on SQLite, and cross-contaminates elements on JWST.

## Cost and reliability

| Arm | Checks | Completed | Median | Max | Cost (partial floor) |
|---|---:|---:|---:|---:|---:|
| default | 14 + 1 strengthening | 14 / 14 | 56 s | 84 s | $0.52 |
| candidate | 14 | 14 / 14 | 48 s | 118 s | $0.77 |

No stalls, no errors, every check ended honestly. Astra saw three of fourteen stall past 16 minutes in production; that was never reproduced locally and the Railway trace remains owed. Total spend about £1.00, over the ~£1.50 estimate's lower end and under its upper.

## Default arm against Astra's findings

| # | Astra's finding | Now |
|---|---|---|
| 1 Brexit | correct, parliamentary sources | ✅ same |
| 2 SELECT | challenges population and absolute/relative; composite endpoint not resolved | ◐ absolute 20% disputed (close split: one source still supports it); population is a caveat, not a challenge, because **"everyone who is overweight" was rewritten to "overweight individuals" at extraction**; composite vs heart attacks still conflated |
| 3 creatine | trivial premises inflate support; absence of evidence read as evidence of no effect | ❌ both still present |
| 4 JWST | (stalled for Astra) mixed true/false | ❌ **the false "orbits the Earth every 90 minutes" conjunct was dropped at extraction**; reads "supports all 2" |
| 5 Bank Rate 4.25% | (stalled) | ✅ challenged by four sources reporting 3.75% |
| 6 Sweden + focus | (stalled) | ❌ **the causal clause was dropped at extraction**; researched as a ranking claim; the ranking reads disputed (Norway lower), correctly |
| 7 SQLite BUSY | official page mapped only as support | ✅ **sqlite.org now challenges "cannot occur"**; six challenges, none supporting |
| 8 EV | questions labelled supported; strengthening 23→81 with 12 mapped | ❌ questions still read "supported"; ✅ strengthening 24→41 completed with a retained revision |
| 9 URL wal.html | false gap on the 3.22.0 read-only change | ❌ still a gap (`no_evidence`); ✅ claim selection works, 3 claims researched |
| 10 LANTERN-COG | abstention | ✅ three elements `unresolved`, no fabricated support |
| 11 inflation | correct distinction | ◐ elements are true restatements, so a false claim's orientation reads "supports all 3" |
| 12 Venus image | OCR fine; unnecessary premise | ✅ OCR; ❌ premise elements still there |
| 13 Sweden | good separation; gaps view "all settled" | ❌ causal clause dropped (8 s: the 24 h pool cache replayed #6); ranking disputed correctly; gaps copy fixed in step 1 |
| 14 Bank Rate 3.75% | **correct rate labelled disputed** | ✅ **supported on both elements**; the temporal gate scoped four stale items |

Fixed since Astra: 14, 7, 5, 10, reliability, strengthening coherence, gaps copy. Unchanged: 3, 8, 9, 12. New and worse than anything Astra saw: the extraction rewrite on 2, 4, 6/13.

## The extraction defect

`recombine_single_thesis` (claim integrity, §4a) guards the case where a single-sentence submission is split into fragments. The quieter loss was unguarded: the extractor returns ONE "normalised" claim with a conjunct missing, and nothing compares it with what the user typed. Fix in this commit: `restore_single_thesis` — text input, one declarative sentence, one claim, and the claim is missing a content token (a word of four or more letters, or a number) the source carries → the user's sentence is restored verbatim with `restored_from` and the dropped tokens recorded. Pure rewording that keeps every content token is left alone. Tests: the JWST, Sweden and "everyone" cases restore; Venus rewording does not; the fragment case stays on recombine's seam. **The rule also fires on two of the ten corpus claims** — the bench moved from 185/1/13/2 to 149 ok / 1 warn / 15 fail / 2 unexercised with `cassette_drift` on `TRU-82CF-2F81` and `TRU-C1A0-0001`. Read before believing it: the cached extraction for 82CF is "BP plc reported £28bn profit in 2022" — the extractor had dropped "under the Energy Act", the very conjunct that makes the claim contestable, and the cassettes were recorded on that wording. The drift is the fix working. **A `--record-missing` re-record was attempted (founder-approved) and DISCARDED:** the patched 82CF cassette still missed 26 requests on immediate replay, its recorded pool had one domain and five web results against the golden's thirteen, and the file tripled in size (4.5 → 14.9 MB) — not a recording to trust. Both cassettes were restored from git. The two claims need a full `--record` with the live pool inspected before goldens are updated; until then the bench reads 149/1/15/2 with those two drifts attributed to the fix. Whole backend suite: 3,946 passed / 0 failed. The extract stage itself is untouched by the branch, so this is model variance in an existing prompt, not a regression; the mechanical guard is the durable answer (NF-11 lesson).

## Candidate arm

Better: creatine is one element, `contextual`, no trivial premises; SELECT's absolute-20% element is `all_challenges` with the bad support gone; Sweden with focus decomposes into no-lockdown (supported), ranking (disputed), causation (disputed) — the best record in either arm; inflation reads `disputed` as a whole; JWST supports carry exact quotes.

Worse: **Bank Rate 3.75% reads `context_only` on both elements** — the temporal gate scoped five items and the flag-only `fact_applicability` gate scoped five more, leaving nothing directional on a true, current, official value (the same over-scoping removed the true WAL-since-3.7.0 claim in #9). **SQLite BUSY gained four passage-review supports** whose quotes are about readers not blocking writers, or literally "to absolutely prevent SQLITE_BUSY errors, you have a few options" (which presupposes they occur), moving the element from `all_challenges` to a 2× split. **JWST's launch element received a mirror-size quote as support and vice versa** — cross-element contamination in passage review, the class the 2026-09-08 factorial run had already flagged. Passage review `failed` outright on SELECT (0 of 16) and stayed `partial` on three others. Slower (SELECT 118 s).

Reading: the mechanical scope gates and the review are now conservative enough to be honest on ambiguous evidence, and too eager on day-scoped true facts; passage review still binds quotes to the wrong element. Activation needs the fact-anchor gate narrowed (a source that states the value and a date within the window must count) and per-element passage binding fixed, then a fresh two-arm regrade.

## Re-verification of the extraction fix (founder-approved, three live checks, default configuration)

| Input | Before | After `restore_single_thesis` |
|---|---|---|
| JWST | one claim, orbit conjunct gone, "supports all 2" | full sentence; **orbit element `disputed / all_challenges` (3 challenges)**, mirror and launch supported — the mixed claim now reads as mixed |
| SELECT | "everyone" gone, population a caveat | full sentence; **"population represents all people who are overweight" `disputed / all_challenges` (4)**, absolute 20% `all_challenges` (3), the causal reduction supported |
| Sweden + focus | causal clause gone, researched as a ranking | full sentence; no-lockdown supported (4), **causation `disputed / all_challenges`**, ranking `challenges_dominant_2x` — the separation Astra praised on its completed run |

Artefacts `tmp/astra-regrade-reverify/`; 58–80 s each; about 15p. With this, the three ❌ rows above for #2, #4 and #6/#13 become ✅ on structure, and #2's population challenge that Astra credited is back.

## Absence of evidence is not evidence of absence (default path, same day)

The creatine element read `disputed / all_challenges` on three sources that say evidence is *lacking* ("there isn't enough evidence", "no strong evidence linking", "no large trials have demonstrated"). A new default-on mechanical gate, `absence_of_evidence` (`app/utils/absence_of_evidence.py`, `ENABLE_ABSENCE_OF_EVIDENCE_GATE`), re-labels such a reference to `context` in either direction, with a receipt quoting the sentence; a measured null result ("found identical rates", "no significant difference") never matches. Placed after recital, before the redundancy gates. Tests drive the three real creatine sentences through the real parser (element → `contextual`), keep a measured null as a challenge, scope a "no evidence of harm" support symmetrically, and pin order and receipt-key registration. Re-verification on a live creatine check is owed.

## Question-shaped elements read Addressed, not Supported (default path, same day)

Astra finding 8: the EV claim's grounds elements are open questions and read "+ Supported". A question cannot be supported; evidence addresses it. Both badge components and the PDF now print **Addressed / Contested / Context only / Open** for an element whose description is interrogative, from one table (`shared/constants/index.ts::QUESTION_STATE_LABELS`, parity-locked to `checks.py::QUESTION_STATE_LABELS` by tests on both sides). The state enum, styling, arithmetic and signed manifests are untouched; only the word the reader sees. Astra's fuller ask — show the substantive answer beside the question — needs the mapper to write one and is not attempted here.

## The SQLite URL false gap is a design consequence, not a retrieval miss

`retrieve_evidence_for_claims(exclude_source_url=…)` excludes the **whole domain** of a submitted URL from evidence: claims extracted from `sqlite.org/wal.html` cannot be evidenced by `sqlite.org/changes.html`, the page that proves the 3.22.0 change. The rule protects independence (an outlet must not corroborate its own article). For reference documentation it manufactures a gap. Changing it is a retrieval-semantics decision for the founder (see the register); the candidate change is to exclude only the submitted URL itself and let the interested-party and echo gates handle self-corroboration, with a receipt on same-domain items.

## Founder decisions on the remaining default-path misses (same evening)

- **Source exclusion narrowed to the submitted page** (`retrieve._source_exclusion`): a claim extracted from a URL cannot be evidenced by that page; other pages on the domain are eligible and carry `metadata.same_domain_as_source`, leaving self-corroboration to the interested-party and echo gates. `RETRIEVAL_CACHE_VERSION` → `2026-09-09`. Tests pin page identity (scheme, `www.`, fragment, query, trailing slash are presentation) and the skip/tag/untouched outcomes. The corpus is all text-mode, so the bench cannot see this change.
- **Decomposition prompts gain one rule**: no element for a trivially true prerequisite the claim's truth does not turn on (measurability, that a substance can be taken, that a body or trial exists, that a method is valid); elements are the contestable parts. Applied to both the single and batch prompts. This re-keys every corpus cassette; the founder approved a full re-record.

## What 8/10 still needs

1. Re-verify the extraction fix on #2, #4, #6/#13 (three checks, ~15p).
2. Default path: absence-of-evidence challenges (#3), question-shaped elements badged `supported` (#8), the #9 false gap (retrieval, not mapping), decomposition premises (#12).
3. Candidate: the three regressions above, then a regrade; only then the activation decision.
4. Astra's gates that are the founder's: a knowledgeable human over ≥200 directional relationships, 3–5 users on real tasks, the Railway trace of the three production stalls.
