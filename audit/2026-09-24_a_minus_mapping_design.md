# A− tier 4: mapping correctness (H1/H2): design, for review before any build

**Date:** 2026-09-24.
**Status:** DRAFT for independent review, then founder approval.
**Why this build:** the direction check (`audit/2026-09-24_a_minus_measurement.md`, last section) shows mapping is in **every** combination of fixes that produces an A− record. No A− is possible while wrong directional references remain.

## 1. The failures (19 graded records, `audit/a_minus/`)

**H2, a directional reference its own text does not support: 13 records.** Grouped by what was wrong:

| Kind | Instances (record: source) | Records |
|---|---|---|
| **P — wrong period** | #2 GAO "as of March 2018, 37 models" and KFF 2018 vs a 2010–2020 total; #6 Warren "over 17,000" and bgov "21,000 in 2025" vs 28,700 since 2025; #7 April poll wave (50–44) vs the September poll; #10 IMF 2022 vs "recent years"; #12 ACS "current 416 ppm" (stale) vs "now >420"; #19 ONS 2020-only vs 2020–22 | 6 |
| **S — wrong place, subject or scope** | #4 Reuters TikTok about Mecklenburg-Vorpommern filed for Saxony-Anhalt; #13 generic urban-heat text vs Europe's heatwaves; #16 WWF on Southern Europe, no figure; #17 Romania firefighters, Senedd UK-only; #19 ONS never mentions Sweden | 5 |
| **M — wrong measure** | #19 Cato COVID deaths vs excess mortality; #17 Copernicus temperatures vs burned area | 2 |
| **C — part of the element unaddressed** | #1 supports never mention "one weekend"; #8 "confirms the initiative" with no count or place; #14 a single-donation record filed for "more money than any party" | 3 |
| **E — empty text** | #17 PurpleAir "You need to enable JavaScript" filed as a challenge | 1 |

**H1, wrong badge: 6 records.**
- 3 are caused by **scope gates misfiring on the authoritative source**:
  - #7: interested-party on Cook's own poll release, and "political" in politicalwire.com.
  - #10: temporal ("Q3 2026" treated as not containing September), and interested-party on the Central Bank's own research.
  - #12: a false echo on the claim's own figure.
- 1 follows from a P error: #2.
- 1 is cross-element inconsistency: #13, where e3 restates e1 but was mapped differently.
- 1 is direction lost at decomposition: #17.

## 2. What exists today

| Mechanism | Status | Relevance |
|---|---|---|
| Mapping prompt rules (FINDING NOT TOPIC, period, measure) | live | Every case above slipped past them. **Prompt-only has failed; NF-11.** |
| Month-level temporal gate | live | Only fires on a single month-level element period with dated evidence. Year ranges, "now/current", "recent years" and snapshots ("as of 2018") are out of its reach. |
| Figure gate (`figure_scope.py`) | live | Arms only when the mapper's reasoning cites a figure. Warren's "aligning with the large trade count" cites none. |
| `relationship_scope_review.py` | **built, OFF** (behind `ENABLE_PASSAGE_MAPPING`) | A demote-only model review of directional refs over population, outcome, design, identity, **measure, time, result**, with an exact-excerpt receipt. It re-derives the state itself. Capped at 12 pairs, 25 s per call of 6. The 2026-09-09 regrade judged the flag's OTHER parts not ready (passage review binding quotes to the wrong element; fact-applicability over-scoping). This review itself was not singled out. |

## 3. Design

### M1: decouple and widen the relationship review (targets P, S, M, C: 12 of 13 H2 records)
- Its own flag, `ENABLE_RELATIONSHIP_REVIEW`, default OFF until the evaluation passes. This follows the precedent of `ENABLE_DISTIL_PASSAGE_INPUT`, which was split off from `ENABLE_PASSAGE_MAPPING` on 2026-09-22.
- Review **every** directional ref, not 12. Calls stay at 6 pairs each and run in parallel. Latency is bounded by the slowest call (25 s cap); a claim with 30 refs means 5 parallel calls. Measure it.
- **Demote-only and symmetric**, as built: a supports or a challenges ref may become `context` with a receipt; nothing is ever promoted or flipped.
- The receipt renders on the element's "Why" line when it changes a state.
- It must sit in the pipeline where it sees the final refs: after the scope gates and after coverage recovery (basis blocks go stale after recovery; known).

### M2: empty-text floor (E; mechanical; difficulty 2)
A directional ref whose evidence text (snippet + retained windows) has fewer than N content words, or matches boilerplate markers ("enable JavaScript", cookie/login walls, "Register Login"), becomes `context` with receipt `rule: no_readable_text`. Symmetric.

### M3: scope-gate misfires (H1 on #7, #10, #12; mechanical; difficulty 3)
- **Interested-party:** a source that is the **publisher of the result the claim reports** ("Cook poll finds…", "Central Bank research shows…") is the record of that result, not an interested account. Apply the same CLAIM-level disarm used for attribution claims on 2026-09-22, keyed on the claim naming the organisation as the source of the finding. Keep the TRU-018F guard: a claimant's statement about their own achievement stays gated. **Hard boundary to design with the reviewer:** "Cook finds Democrats lead" (the publisher's measurement) vs "Trump says he ended 6 wars" (a self-interested assertion).
- **Loose tokens:** add `political`, `politics` and similar generic words to the interested-party stop-list (`politicalwire.com` matched on "political").
- **Temporal:** a quarter (`Q3 2026`) contains its months; an element pinned to 2026-09 is in scope of a Q3 2026 source.
- **#12 echo:** NOT fixed here. The review showed the claim-figure exclusion breaks TTE's correct echoes. The badge also needs P ("current 416 ppm" stale), so #12 is expected to clear through M1.

### M4: not in this build (named)
- **#13 cross-element inconsistency** belongs to Build D (restated elements).
- **#17 direction lost** is decomposition (`direction_fidelity` exists; a trace is owed).
- **#7 decomposition dropped "September 8–11"**: M1's time dimension should catch the April wave anyway. Restoring the date is a decomposition fix.

## 4. Evaluation before any flag is turned on

**Labelled set from the 19 records:**
- **Positives:** every H2 ref listed in §1, about 25 refs.
- **Negatives:** every directional ref on records the graders passed on H2 (#3, #5, #9, #11, #15, #18). The graders affirmed these, and they include refs that must survive, e.g. TTE's piece as the causal challenge and NASA's Orbit page as the JWST challenge.
- Every other ref on failing records is reported but not scored.

**Run** `review_relationship_scope` offline over each stored payload (claim map + evidence text + textProvenance). Model calls only, no retrieval.
- Estimated cost: about 250 pairs, about 45 calls on flash-lite, **under 5p**. Founder's go required (ask-before-spending rule).

**Pass bar (proposed):**
- ≥70% of positives demoted;
- ≤5% of negatives demoted, **zero** on the named must-survive refs;
- each demotion's receipt excerpt actually present in the source text.

If it fails, iterate on the prompt against this set only, then re-test with a held-out portion, to avoid tuning to the test.

**State replay:** re-derive states with the demotions applied. Report every state change by direction, and the H1 records that clear.

## 5. Risks
- **Model judgement, not proof.** Its errors are silent. Mitigation: the exact-excerpt receipt, the render, and the negatives bar.
- **Over-demotion reads sceptical.** Supported elements fall to unresolved. The symmetry is in the rule, not in the outcome.
- **Latency:** up to +25 s worst case per claim. Measure p50/p90 on the eval.
- **Cassettes:** a new model call re-keys every corpus claim with directional refs. Bench re-record owed (pence; ask), plus a control arm.
- **Cost per check:** the new calls add about 0.1–0.3p per claim. Measure.

## 6. Build order
1. Offline evaluation of M1 as-is (needs the go).
2. M2 and M3, both mechanical, verified free by replay.
3. M1 flag + wiring.
4. Bench re-record.
5. The 19-record re-run, re-graded blind with the same checklist.

---

## Review outcome: 2026-09-24 (`audit/2026-09-24_a_minus_mapping_review.md`)

**Verdict: APPROVE WITH CHANGES overall.** The reviewer ran the real planning code on the 19 stored payloads (no model calls).

**Corrections to this draft:**
- **M1 reach is about 7–9 of 13 records, not 12.**
  - The review gets no source date.
  - Its keep-the-contrary-result exemption retains wrong-period CHALLENGES (#2, #7, #12).
  - The claim that it catches #7 is false as built.
- **#1 would get WORSE:** M1 removes the refs that don't state "one weekend", while the recital gate had already demoted the refs that do. So e1 falls to unresolved. M1 must ship AFTER the recital fix.
- **M3 is half done:** "political" is already in the stop-list, and #10 is disarmed by the 2026-09-22 attribution change (both records predate it). Only #7 remains.
- **The quarter fix as proposed is wrong.** A quarter figure is not a monthly value; containment applies only to EVENT elements.
- **The eval set is 156 pairs, not about 250.** About 8 of 37 "negatives" are claimant self-evidence or arguable. Relabel before running.

**Required changes:**
1. **M1:**
   - Pass each source's published date.
   - Check period, population and measure BEFORE result.
   - Narrow the contrary-result exemption.
   - Ship after M3 and the recital fix.
   - Report every record's net badge and wrong-ref outcome.
   - Merge with the 2026-09-23 figure-quote flag and parser.
   - p90 added latency ≤ 15 s.
2. **M2:** count words after removing the title; decide the gate order explicitly (or run it before mapping).
3. **M3:**
   - Exempt only the NAMED organisation, when the claim reports its survey or publication (fixed verb list).
   - Never release executive-comms domains; never reopen TRU-018F-44AA.
   - Fix the 2026-09-22 whole-gate disarm the same way.
   - Quarter or year contains its months for event elements only.
4. **Eval:**
   - Three-way labels on all 156 pairs.
   - Pass bar split by direction.
   - "No H1 regression".
   - 3 repeats.
   - The ~1,000 existing blind labels as a held-out set.

---

## Build log: steps 1–2, 2026-09-24 (founder-approved)

**M3 interested-party: per-subject release** (`interested_party.released_subjects`). It replaces the 2026-09-22 whole-gate disarm.
- **Which subject:** only the subject that the saying verb attaches to (within 80 chars), or, for an ORG, the measurement/publication verb or noun from the closed list.
- **Scope:** prong 1 only; executive-comms domains are never released.
- **Element restriction:** the element must name the subject or the act. It can withhold a release but never grant one.
- **Runner:** `metadata.subject_kinds` (org / person / claimant) is now written by the runner.

**Pinned by tests:**

| Case | Outcome |
|---|---|
| Cook "surveyed" (supports and challenges) | released |
| a person subject | not released |
| an element naming neither the subject nor the act | withheld |
| "The White House published figures showing 6 wars ended" | NO LONGER disarms the gate (the reviewer's found hole) |
| 018F conduct claim | still gated |
| Thirlwall | released as before |

Mutation-checked twice: restoring the whole-gate disarm is caught; removing the element restriction is caught.

**M3 temporal:** `element_is_event` and `contains_period` handle Q1–Q4, "Nth quarter of", H1/H2 and bare years.
- For EVENT elements only, a source dated to the containing period is in period.
- Value elements keep the strict rule, pinned both ways ("published in September 2026" vs Q3 bulletin: kept; "CPI in September 2026" vs Q3 CPI: scoped).
- "Q2 2026" does not re-read as "2026". Mutation-checked.

**M2 unreadable-text floor** (`app/utils/readable_text.py`, gate `readable_text`, flag `ENABLE_READABLE_TEXT_GATE`):
- Placed second, after temporal; joins `_SCOPE_RECEIPT_KEYS`.
- **It fires when either:**
  - a wall or boilerplate sentence is present and fewer than 5 content words remain once title and wall are removed; or
  - the text (title included) has fewer than 2 content words.
- **Figures count as content.**
- **Evidence for each choice:**
  - Two earlier drafts were caught by existing tests: a raw threshold flagged "The release setting is 37 units.", and title-stripping emptied a snippet that was its own headline.
  - On the 156 stored directional refs it fires on PurpleAir only (score 0; next lowest 9).
  - Mutation-checked.

**Verification:**
- Unit: **3,980 pass / 44 skipped**. Two batch-mapping fixtures used placeholder snippet "S"; they were given a real sentence, since those tests are about batch mechanics, not text.
- Bench identical to the Build A run: 147/9/11/5, known drift 82CF + 93DD only; 018F interested-party pin holds.

**Not done — the recital misfire (#1).** "Harborne on Saturday announced he was matching the donation" and "Trump announced he ended six wars" look the same to the gate. This is difficulty 3 on a TRU-018F-guarding gate, so it needs its own short design and review before any build. M1 (the relationship review) must not ship until it is fixed (#1 net-effect trap).

---

## Build log: M1 upgrades, 2026-09-24 (flag OFF; the eval decides)

**`ENABLE_RELATIONSHIP_REVIEW`** (default False) decouples the review from `ENABLE_PASSAGE_MAPPING`:
- It covers both call sites (completion and coverage recovery).
- `_COMPLETION_TIMEOUT` rises to 50 s under either flag.
- The manifest fingerprint gains `relationship_review_contract: v1` when the flag is on.

**The eight required changes:**
1. Every directional ref is reviewed (`RELATIONSHIP_REVIEW_MAX_PAIRS`, default 60; the old cap of 12 still applies when the flag is off).
2. Pairs carry `published_date` and `date_basis`.
3. The prompt checks TIME, then POPULATION/PLACE, then MEASURE before any result, with domain-neutral definitions (snapshot vs total, stale "current", sub-region vs region, count vs value, part vs whole).
4. A `scope_affirmed` field is added to the schema, and the contrary-result exemption now needs it true.
5. The figure check covers counts and currency (`figure_scope`), not just percentages and ratios.
6. A re-run (coverage recovery) skips pairs already decided and MERGES the receipt (`prior_runs`) instead of overwriting it.
7. The dead `unknown` status branch is fixed. One test pinned the buggy "complete"; it now reads "needs_review". The UI does not read that value.
8. `RELATIONSHIP_REVIEW_DEMOTE_UNKNOWN` switch: `unknown` can be recorded without demoting.

**Tests and verification:**
- 51 module tests, all 6 upgrade mutants caught (the cap first survived; a test was added).
- Unit 4,010 pass.
- Bench identical except 5647 drift. It replayed identically when run alone: the known flake.

**Eval tooling:** `backend/scripts/eval_relationship_review.py` replays the review on stored payloads and scores both unknown-policies from one run's decisions. The labelled set is `audit/a_minus/review_eval/labels.csv` (in progress).

**Cost correction:** 3 repeats × 156 pairs ≈ 99 calls on gemini-3.5-flash-lite ($0.30/M in, $2.50/M out; thinking counts as output) ≈ **$1.10 (≈85p)**, not the "<5p" first estimated. One repeat ≈ 30p.

---

## Eval result: 2026-09-24. **FAIL. Do not enable.** (3 repeats × 156 pairs, ≈85p, `audit/a_minus/review_eval/results.json`)

Labels: 114 must_survive / 27 should_demote / 15 either (`labels.csv`, blind adjudicator).

| Policy | Positives demoted (bar ≥70%) | Must-survive demoted (bar ≤5%) |
|---|---|---|
| demote on mismatch + unknown | 52/79 = **66%** (P 90%, E 100%, S 67%, C 53%, M 0%) | 61/332 = **18.4%** (supports 18.2%, challenges 18.8%) |
| demote on mismatch only | 26/79 = **33%** | 26/332 = **7.8%** (supports 3.8%, **challenges 17.7%**) |

**Other measures:**
- **Invalid (quote not verbatim, etc.): 113/456 = 25%**, mostly on supports.
- Latency p50 3.6 s, p90 9.8 s per claim.
- Calls: 2/99 failed.

**Disqualifying finding — it demotes genuine CHALLENGES:**
- NASA "Orbit" vs "JWST orbits the Earth every 90 minutes": 3/3 demoted.
- Three wildfire sources stating 2026 is running at twice the historical pace: 3/3.
- Two Sweden sources stating "37th of 42": 3/3.

The model files a real contradiction as a scope `mismatch` on `measure` or `time` ("the source says Webb orbits the Sun"). The contrary-result exemption, now gated on `scope_affirmed` + `result`, no longer catches it. Removing the challenges that expose a false claim is the sycophancy failure invariant #7 forbids. Under either policy this cannot ship.

What worked: wrong-PERIOD positives were caught at 90% (demote-unknown policy). The model sees dates once it is given them.
