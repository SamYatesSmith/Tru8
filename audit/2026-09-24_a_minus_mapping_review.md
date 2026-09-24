# A− tier 4 mapping design — independent review (2026-09-24)

**Reviews:** `audit/2026-09-24_a_minus_mapping_design.md`.
**Method:** read-only. I read `relationship_scope_review.py` in full and its call sites, and ran its real `plan_review()` offline over the 19 stored public payloads, so every "does the review see it" judgement below uses the blocks the stage would actually send. I also ran the real `interested_party_match`, `element_asserts_attribution` and `is_out_of_period` on the cases. No model calls, no checks, no spend.
**Overall: APPROVE WITH CHANGES.** The direction is right: mapping is the binding stage, and a demote-only review with verified quotes is the right tool for it. But three statements in the design are wrong against the code: what M1 can catch, what M3 has left to fix, and what the quarter fix should be. The eval set also needs relabelling before its bar means anything.

| Part | Verdict |
|---|---|
| M1 relationship review | **APPROVE WITH CHANGES** |
| M2 empty-text floor | **APPROVE WITH CHANGES** |
| M3 scope-gate misfires | **REWORK** |
| Eval plan | **APPROVE WITH CHANGES** (relabel before running) |

---

## 1. `relationship_scope_review.py`: what it is

**Input per pair.** The stage sees:
- the element description only. No claim text and no source date: `published_date` is not in the pair.
- the title.
- one `mapping-text` block: `snippet or text`, cut to 1,800 characters. This is the same text the mapper saw, plus 800 more characters.
- up to two retained passages, ranked by overlap with the element's terms.
- line excerpts of 12–600 characters, capped at 8 per block.

So the review adds a second, narrower question. It adds very little new text.

**Prompt.** It asks for `compatible` only when the supplied text "establishes the existing relationship to the COMPLETE element assertion". It returns `mismatch` for an explicit different scope, and `unknown` for missing information. *"Missing information, a short snippet, or lack of proof alone is unknown."* The dimensions are population, outcome, study_design, study_identity, measure, time and result. The prompt is written almost entirely for biomedical trials: SELECT, MACE, prevention versus progression, named trials. It has no example of a period snapshot against a cumulative total, a sub-region against a region, or a partial element.

**Application.**
- **`mismatch` AND `unknown` both demote to `context`.** This is the important fact: this is an entailment gate, not only a scope gate.
- Three code overrides:
  - A named trial absent from the text forces `unknown`.
  - `contrary_result_is_the_challenge`: a challenge returned as `mismatch/result` is flipped back to `compatible` and kept.
  - `quantitative_result_not_quoted`: a support on an element stating a **percentage or ratio** needs that figure in the quote. Counts and currency are not covered.
- The quote must be verbatim in the block. Otherwise the pair is silently not applied and counted as uninspected.

**Receipts.**
- `basis.relationship_scope` per element, already in `_SCOPE_RECEIPT_KEYS` and in the public labels (`checks.py:2141`).
- The claim-level receipt is written to `metadata.scope_review`.
- The stage re-derives the state via `_derive_element_state_with_authority` with the claim's floor, and overwrites `uncertainty` with a generic sentence.

**Where it runs.** Behind `ENABLE_PASSAGE_MAPPING` only, at two sites:
1. `_complete_unmapped_evidence` (`claim_map_analyzer.py:3282-3297`). This runs after the main mapping (which applies the scope gates), after the completion census (which applies them to merged refs) and after passage review.
2. The coverage-recovery path, `map_evidence_to_specific_elements` (`:3764`), after the recovery gates and before `apply_orientation`.

So "after the gates and after recovery" is already true structurally, but it runs **twice** on recovered claims:
- The second run **overwrites** `metadata.scope_review`, losing the first run's compatible and invalid records. That is a partial invariant-#5 loss; element receipts survive.
- The second run **re-reviews refs the first run judged compatible**. That costs twice, and a second draw can demote what the first kept.

**Batch path.** The completion step, which now contains the review, sits under `_COMPLETION_TIMEOUT = 50 if ENABLE_PASSAGE_MAPPING else 25` (`:2072`). Decoupled onto a new flag with the timeout left alone, the completion call and the review share 25 s. The review will often be cancelled. That is safe, because the review stages a deepcopy and writes `interrupted`, but it is silently ineffective.

**Model.** The `scope_review` label is not a mapping label, so it uses `GOOGLE_LLM_MODEL` = `gemini-3.5-flash-lite`. That model's thinking cannot be disabled, so on long six-pair prompts it may use part of the `max_tokens=4800` budget. The `invalid_response` rate must be measured.

**Minor bug.** `receipt["status"]` tests `r["status"] == "unknown"`, but a scoped record's status is `"scoped"`. That branch is dead, and `needs_review` fires only on uninspected pairs.

**Did the 09-09 regrade fault this component?** No, not by name. What was found:
- The regrade faulted `fact_applicability` (Bank Rate over-scoping) and passage review (wrong-element quotes, SQLite, JWST).
- The review's own record (`2026-09-08_relationship_scope_review.md`, `2026-09-09_quantitative_result_guard.md`) is 42/42 on frozen creatine/SELECT pairs plus 8/8 synthetic controls, which are **all biomedical**.
- The integrated pilot records a 25 s timeout on Venus and 12/15 pairs assessed on SELECT.
- It has **never run on the default path or on political, economic or climate claims**, which make up the whole of the A− set.

**Decoupling is clean.** Touch points:
1. `config.py`: a new flag.
2. `claim_map_analyzer.py:3282-3297`: move the review call out of the passage block, under the new flag.
3. `:3764`: the recovery guard, onto the new flag.
4. `:2072`: `_COMPLETION_TIMEOUT` must also rise under the new flag.
5. `manifest_signer.py:46`: add a `relationship_review_contract` fingerprint term.
6. `relationship_scope_review.MAX_PAIRS`: the widening.
7. `tests/unit/test_relationship_scope_review.py` and the wiring tests that set `ENABLE_PASSAGE_MAPPING` to exercise the stage.
8. Cassettes: the new `scope_review` requests re-key.

`_call_llm` appends `APPLICABILITY_RULES` only for mapping and passage labels, so no passage-contract text leaks into the review. **Reconcile with `2026-09-23_figure_quote_review_design.md`.** It proposes the same decoupling under `ENABLE_FIGURE_QUOTE_REVIEW`, and the M1 design does not cite it. Ship one flag, and take its figure-parser swap (point 4 of M1 below).

## 2. Can the review catch each H2 instance with what it receives?

`plan_review` over the stored payloads gives **156 directional pairs** across the 19 records, not about 250. Of these, 31 (20%) are "thin": one block of fewer than 250 characters.

| # | Ref | What the review receives | Catchable? |
|---|---|---|---|
| 1 | Sky, YouTube on "one weekend" | ~130-char snippets, no weekend | **Yes** (unknown). ⚠️ But see the net effect below |
| 2 | GAO "37 models" (challenge) | Text has "Since 2010 … 37 models", "January 2011–February 2018" | **Doubtful.** The natural reading is "different figure" = `mismatch/result`, which the challenge exemption flips back to kept |
| 2 | KFF ×2 (challenges) | "over 40 models, 18 million patients"; no date; a 2018/2019 aside in passage 2 | **Doubtful**, same exemption. The date is not supplied |
| 4 | Reuters TikTok | "state elections in northeastern…" (truncated) | Yes (unknown or population) |
| 6 | Warren "17,000" | Distilled list states 17,000 | Likely, **only if the model says unknown**. The figure guard is percent-only, so a `compatible` on 28,700 is not caught |
| 6 | bgov "in 2025" | "all trades executed in 2025" | Likely (time) |
| 7 | Hill, Reddit April wave (challenges) | "50 percent to 44 percent"; **no date**; the element carries no date (decomposition dropped "September 8–11") | **No.** The deciding facts, the April date and the September period, are in neither the element nor the text |
| 8 | Belfast Telegraph, publicnow | 140–160-char snippets, no count or place | Yes (unknown) |
| 10 | IMF 2022 on "recent years" | 127 chars, no date; `published_date` not supplied | Only for the wrong reason ("no time stated"), which would equally demote any undated support |
| 12 | ACS "current 416 ppm" (challenge) | 121 chars; `publishedDate` is null | **No.** Staleness needs world knowledge; the exemption keeps the challenge |
| 13 | Geneva urban heat | Generic sentence | Yes, **but it is pair 14 of 16, beyond today's 12-pair cap**. Widening is needed |
| 14 | BBC single-donation record on "more money than any party" | "a record for a UK political party" | Yes (measure) |
| 16 | WWF Southern Europe | No figure; Southern Europe | Yes (unknown or population) |
| 17 | PurpleAir | Title + "enable JavaScript" | Yes, and M2 |
| 17 | EC Romania, Senedd (UK) | UK "second-highest on record" | Romania yes. Senedd **doubtful**: it reads as a contrary result, which the exemption keeps |
| 17 | Copernicus temperatures | Temperatures and drought, no burned area | Yes (measure), **but it is pair 13 of 13, beyond the cap** |
| 19 | Cato COVID deaths | "2,322 Covid-19 deaths per million" | Yes (measure) |
| 19 | ONS 2020 | 2020 weeks, no Sweden | Yes (population or time) |

**Reading.**
- M1 as specified clears H2 on about **7–9 of 13** records, not 12: #4, #6, #8, #13, #14, #16, #19, probably #17, and #1 with the caveat below.
- It **misses the P-on-challenge class** (#2, #7, #12), for two reasons:
  - The date is not supplied.
  - `contrary_result_is_the_challenge` is triggered precisely by "the source states a different number", which is how a wrong-period challenge looks. The design's line *"M1's time dimension should catch the April wave anyway"* (M4) is false as built.
- **Net-effect trap, #1.** The review demotes Sky and YouTube, but the sources that do state the weekend (Guardian, AP) were already demoted by the **recital** gate. e1 is left with the claimant's own Conversation piece, falls under `support_floor`, and H1, which passes today, fails. **Demote-only review makes every upstream false-demotion worse.** It must ship after, or with, the gate fixes, and the state replay must report per-record net H1/H2, not H2 recall.
- **Tested and rejected, a cheaper pre-filter.** "Element number or proper noun absent from the supplied text" triggers on 15 of 23 positives and 13 of 37 negatives. It is not a separator, so "review every ref" is justified.

## 3. M2 and M3 against the code

### M2, empty-text floor
Sound, and free. Required:
- Count content words **after removing the title**. PurpleAir's text is its title followed by "You need to enable JavaScript…", so a raw count passes it.
- Count across snippet, text and retained passages, never one field.
- Set N low (about 8), plus a closed boilerplate list.
- If M2 is a gate, it needs all of the following. The alternative is to apply it **before mapping**, so unreadable items are offered as context-only, which is simpler and touches no order pins.
  - An explicit **order decision**. Temporal-first and echo-last are test-pinned.
  - An entry in `_SCOPE_RECEIPT_KEYS`.
  - Symmetric tests.

### M3, scope-gate misfires: two of four items are already fixed; the quarter rule is wrong

**Loose tokens: already done.** `political` has been in `_STOP_TOKENS` since `17d5293` (22 Sep). Verified: `interested_party_match(<#7 subjects>, politicalwire.com)` → `None` today. #7 (21 Sep) predates it. Remove this from the build.

**#10 interested-party: already fixed.** Its claim contains "published", and `element_asserts_attribution(claim)` → `True`. The 22 Sep claim-level disarm already drops the gate. #10 (21 Sep 14:42) predates it. **Only #7 ("surveyed") remains.**

**Temporal: the defect is broader than quarters, and the proposed fix is wrong in general.**
- `is_out_of_period(Period(2026,9), text)` returns `True` for "Quarterly Bulletin Q3 2026", "in the third quarter of 2026" **and "In 2026 the economy grew"**. A bare same-year mention is read as a different period, because `(2026, None) != (2026, 9)`. Quarters are not parsed at all.
- But "a quarter contains its months" is wrong for **value** elements: a Q3 CPI figure is not the September CPI. Year-versus-month scoping is the gate's founding case (618efbc4, annual-2024 figures against September 2024).
- **Rule:** parse Q1–Q4, "first/second/third/fourth quarter", H1/H2 and the year. Treat a containing period as in-scope **only when the element is an event**: published, released, announced, held, launched, occurred, conducted. Use the same event-versus-state split `date_scope` already applies ("as of / by / until / since" are states). Value elements keep firing.
- Pin both sides:
  - "research published in September 2026" vs "Q3 2026 bulletin": no fire.
  - "CPI in September 2026" vs "Q3 2026 CPI": fire.
- Also trace #4: the temporal gate demoted cde.news (7 Sep 2026) on a 2026-09 element. That is unexplained, and not the quarter case.

**Publisher of the result: the precise rule.** An exemption, never a whole-gate disarm. It releases interested-party on a (subject, element) pair only when **all** of these hold:
1. **Subject S is an ORG** in `key_entities`. Retain entity type; `claim_subjects()` currently discards it. PERSON subjects are never released.
2. **Claim-level act:** the claim contains an S token and then, within 80 characters (allowing a coordinated subject list, as in "Cook…, GS… and New River Strategies surveyed"), a verb from a **closed measurement or publication list**: `surveyed|polled|published|estimated|measured|counted|analy[sz]ed`. Alternatively it contains S (or S's) followed by a noun from `poll|survey|study|research|analysis|bulletin|index|estimate|data`. `found/shows/reports` are excluded, as on 22 Sep.
3. **Element-level restriction (it can only narrow, never widen):** the element contains an S token or one of the same act words or nouns. Cook e2 "…in the **surveyed** competitive House districts…" is released. #10 e2 "Multinational activity has driven…" stays gated; that is conservative and accepted. This does not reopen the 22 Sep warning, which forbade element shape as a *release on its own*. Here the element can only *withhold* a release the claim already earned.
4. **Prong 1 (name-in-domain) only.** Executive-comms domains (whitehouse.gov, number10) are **never** released.
5. **Only S's own matches are released.** Other subjects stay armed: #7's "donald trump" keeps whitehouse.gov gated on the approval element.
6. **Symmetric:** it releases supports and challenges alike.

TRU-018F-44AA ("Donald Trump stopped 6 wars") fails tests 1 and 2, so the gate stays fully armed. Pin it, together with "Cook surveyed … Democrats 49" (released on the ballot and survey elements) and "Tesla reported record deliveries" (not released, because "reported" is not in the list).

**Fix the 22 Sep disarm the same way.** It is also whole-gate: `element_asserts_attribution("The White House published figures showing 6 wars ended")` → `True` disarms every subject and prong, which lets whitehouse.gov support "six wars ended". Restrict it to per-subject, prong 1, plus the element restriction. That is the real TRU-018F exposure today.

## 4. The eval plan

- **The negatives set is not all correct refs.** On the six "H2 pass" records:
  - #9 youcanknowthings is filed supports on **all four** elements, and it is the claimant's piece (the grader's S7 fail).
  - #3 the claimant's own column is a support (S7).
  - #11 the claimant's HSJ piece is a support (S7).
  - #9 the Wiley study is on e1; the grader calls the element the fault.
  - #18 @theU's *pre-launch schedule* is filed as launch support.
  - That is **about 8 of 37** where a demotion is correct or arguable, so a ≤5% bar would punish right answers.

  **Required:** a three-way adjudicated label (must-survive / should-demote / either) on **all 156 pairs**, including the correct refs on failing records. Those refs are the real over-demotion risk (#1 e2/e3, #4 e1, #6 Bloomberg, #16 JRC, #19 PMC).
- **The positives need adjudication too.** #19 Cato: "an outlier in terms of policy but not in terms of mortality" plausibly *does* challenge "lower than every other". #17 Senedd is arguable.
- **The pass bar.**
  - Split it by direction and by class (P/S/M/C/E).
  - Add the bar that matters: **no record that passes H1 today fails it after the replay** (#1 is the known trap).
  - Require zero demotions on a named must-survive list that includes **supports**, not only TTE and NASA Orbit: for example NASA Mirrors, Thirlwall Part Two and Van Veen PMC.
  - 37 negatives cannot support "≤5%": one error is already 2.7%, and the 95% upper bound is about 14%. Either enlarge the set or state the bound.
- **Variance.** Run 3 repeats. Flash-lite at temperature 0 still varies.
- **Leakage.** A held-out portion of 19 records is about 5 claims, too small. Use the **existing blind-labelled sets** as held-out: about 1,000 directional labels with justified/rejected verdicts in `audit/review_sheets/2026-09-09…09-10*/labels_reviewed.csv`, on different claims and with AI-reviewer error already measured. Keep all prompt examples domain-generic and never drawn from the 19.
- **Cost.**
  - 156 pairs is about 26 calls per pass. At the 09-09 rate (about 4p for 42 pairs, including mapping calls), that is roughly 5–15p per pass and ≤50p for 3 repeats.
  - "Under 5p" may be low. Ask with the range.
- **Latency.**
  - The stage runs **sequentially** after completion, and again after recovery. The worst case is about +50 s per claim, not +25.
  - Recalls from the pilots: Venus 7 s on one run, 25 s timeout on another; SELECT slow.
  - Adopt the 09-23 gate: default-on only if **p90 added ≤ 15 s**. Measure it end to end, because the offline eval cannot see the batch-path completion timeout.
  - Across a 12-claim check, there are up to about 36 concurrent flash-lite calls. Check the rate limits.

## 5. Required changes to M1 (beyond decoupling)

1. **Supply `published_date` and `dateBasis` per pair, and order the dimensions.**
   - The model must clear time, population and measure before it may answer on `result`.
   - Narrow `contrary_result_is_the_challenge` so it applies only after scope is affirmed.
   - Without both, #2 and #12 survive and #7 is unfixable. Record #7 as a decomposition dependency.
2. **Put domain-neutral dimension definitions in the prompt** (snapshot against cumulative total, sub-region against region, rate against count, partial conjunct). The prompt is biomedical today. Never use eval items as examples.
3. **Swap `_figure_forms` for `figure_scope`** (counts, currency), per the 09-23 design. Without it, "28,700" is never checked on a `compatible`.
4. **Recovery re-run:**
   - Skip pairs already assessed, keyed by (element, evidence, input sha).
   - Merge `metadata.scope_review` instead of overwriting it.
   - Fix the dead `unknown` status branch.
5. **Batch path:** tie `_COMPLETION_TIMEOUT` to the new flag, or run the review outside the completion timeout. Record the `interrupted` and `invalid_response` rates.
6. **Sequence after M3 and the recital fix**, and report per-record net H1 and H2 (the #1 trap).
7. **Correct the design's claims:**
   - 12/13 becomes about 7–9 of 13.
   - "about 250 pairs" becomes 156.
   - M3's stop-list and #10 items are already shipped.
   - The time dimension does not catch #7.

## 6. Missing options

- **A stronger reviewer for the review only.** Try `MAPPING_GOOGLE_MODEL` as one eval arm. The review needs precision, and its pair volume is small. Ask first; it is paid.
- **Skip the review on thin-only pairs, and disclose them as uninspected.** This is the alternative to demoting them on "short snippet → unknown", which on 20% thin inputs is the main over-demotion channel. Decide it from the eval, by direction.
- **No simpler mechanical route exists for P, S and C.** The token-absence trigger separates positives from negatives badly (see §2). M2 and the M3 gate fixes are the only parts that should be purely mechanical.
