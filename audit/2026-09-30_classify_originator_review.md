# Review: PRIMARY means originator (design rev 1)

**Reviewer:** independent design review, 2026-09-30. Nothing built, nothing edited, no paid or network calls.
**Under review:** `audit/2026-09-30_classify_originator_design.md`.
**Data checked:** `tmp/astra-regrade-*/*/owner.json` (144 runs, 14 records, 2,507 items), the 241-item dump, and the code named in the brief. Scripts were free local Python.

## Verdict: APPROVE WITH CHANGES

Option E (a second, lower-only model pass on primaries that rest on model judgement alone) is the right shape, and the candidate filter is mostly right. But five things must change before any paid eval:
- the prompt and rubric are contaminated by the held-out set (F1);
- more than a third of candidates have no page text to judge (F2);
- "republishes" would lower the original document itself (F3);
- the review would run inside coverage recovery's Phase A budget (F4);
- the bench and state-replay plan misses that tier is in the mapping prompt (F5).

## Numbers confirmed
- 413 unique PRIMARY URLs; 241 non-identity, `llm`, no adapter; round-2 caps catch 12; **229 remain**. Correct.
- 176 of 241 are typed `data` or `official_statement` (91 + 85). Correct. `sqlite.org/wal.html` is typed `analysis`. Correct.
- The tie-break is at `evidence_classifier.py:73`, and `snippet_length = 300` is at `:880`. Correct.
- Per run: 119 of 144 runs have candidates; median 3 and max 29 per run. So the main pool needs at most 2 calls of 15. Coverage recovery and re-search each call `classify_batch` again, so a check can make more calls than that.

## Findings

**1. HIGH — The held-out set is no longer held out for the prompt or the labels.**
Evidence:
- §4.2's prompt definitions use held-out items as their examples: "sqlite.org on SQLite; Novo Nordisk on its own trial".
- §2 characterises the 229 host by host, and §5 draws its must-survive list from them.
- §6.1 gives the blind labeller the §4.2 definitions, so the labeller and the reviewer share one rubric. Agreement between them then measures consistency, not correctness.
- The founder's random 30 will be clustered: `t09_sqlite_url` supplies 80 of the 229 URL–record pairs, and sqlite.org hosts account for 44 of the 229 URLs.

Required:
- Take every prompt example from the 28 Sep tuning pools only.
- Write the labeller's rubric separately, with no worked examples from the 229.
- Stratify the founder's audit: at most 3 items per host, and every record represented.
- Report precision and recall per record and per host cluster, not only pooled. A 5% rate over ~130 genuine originators, a third of them sqlite.org, can hide 15% on the rest.

**2. HIGH — Input: a third of candidates have no page text; the rest have claim-selected text.**
Evidence:
- `text_provenance` exists only where `_full_text` existed (`text_provenance.py:90-95`).
  - On the held-out set, 84 of the 229 URLs (37%) have none in any run.
  - All 126 coverage-recovery occurrences (`ev-rec-*`, `ev-rpf-*`) have none: `runner.py:2651-2672` classifies recovery items without capturing provenance.
  - Those items fall back to a snippet with a median of 160 chars. That is design cause #3 again.
- Where provenance exists, the passages are chosen by overlap with the ELEMENT terms (`select_passages`, `:29-80`). So "never sees the claim" is not true of the input, and the same URL can get different windows in different checks.
- With `unclear → reporting`, a thin input becomes a demotion.

Required:
- `unclear` leaves the tier unchanged (see Q1).
- Order the input as: the `start == 0` window first (present in 266 of 311 items that have provenance), then `original_snippet`, then `snippet`. Never read `text` (see finding 9).
- Items with no provenance are still reviewed, but may be lowered only on a verbatim cue (finding 7).
- Report eval results split by input kind: provenance, or snippet only.

**3. HIGH — "republishes" lowers the thing itself.**
Evidence: real held-out candidates where the host is not the originator but the page is the original document:
- `mediacenteratypon.nejmgroup-production.org/NEJMoa2307563.pdf` (the SELECT paper in NEJM, on a CDN host that `nejm\.org` does not match);
- `brexitlegal.ie/.../CBP-7960.pdf` (the Commons Library briefing);
- `nms.go.ug/.../Uganda-Clinical-Guidelines-2023.pdf` (a Ministry of Health guideline, outside the gov patterns — the exact non-UK/US case the whitelist was rejected for);
- archive snapshots (`web.archive.org`) the LLM calls primary.

The existing prompt defines primary to include "primary documents" and "court filings" (`:52-53`). A faithful copy is still the document.

Required:
- Add a role, `hosts_original` (a complete, unaltered copy of the originator's own document or dataset), which leaves the tier unchanged.
- Restrict `republishes` to re-display or excerpting inside the publisher's own page.
- Add these three URLs to the must-survive set.

**4. HIGH — Coverage recovery: the review would sit inside the Phase A budget.**
Evidence:
- `classify_batch` runs inside `_recover_prepare` (`runner.py:2559-2672`), under `asyncio.wait(timeout=recovery_timeout)` (`:2752`).
- That budget has already overrun twice, discarding paid-for evidence (docstring `:330-345`).
- A pending prep is cancelled whole (`:2755`): the claim loses all its recovery evidence, not just the review.

Required:
- In recovery, either skip the review with a receipt (`not_reviewed: recovery_budget`), or move it into Phase B before mapping.
- In every path, apply tier changes only after all review calls return, so a cancellation leaves no half-applied pool.
- Time it as its own key in `stage_timings`.

**5. HIGH — Tier is in the mapping prompt, so the bench and state-replay plan are wrong.**
Evidence:
- Mapping payloads print `[Tier: …]` (`claim_map_analyzer.py:1790, 2019, 3568, 3800`).
- The mapping prompt tells the model to "prioritise primary/reporting tier evidence" (`:417`, `:698`).
- Consequences:
  - Every tier change re-keys the mapping calls for that claim. §4.4's "new calls are new cassette entries" is false.
  - `--record-missing` re-records MAPPING live (paid and nondeterministic), so the flag-on arm differs by mapper noise as well as by tier.
  - The offline state replay (§6.4) re-derives states from weights only. It cannot see the mapper reacting to the new label.

Required:
- State the re-record cost and ask the founder before any bench run.
- Describe the offline replay as the weight effect only.
- Read the mapper effect from the two live checks, reading every changed relationship.

**6. MED — Lower-only per item is not neutral per state (invariant 7).**
Evidence: `_derive_element_state_with_authority` is asymmetric by design.
- The support floor (`FACTUAL_MIN_WEIGHTED_SUPPORT=3`) applies to supports only.
- Lowering a challenger can raise an element. For example, supports 3+2 against one primary challenge (5 vs 3) is `close_split` → disputed; lower the challenger to 2 and 5 > 4 gives supported.
- The review sees only non-identity primaries, so one side can be reviewed while the other, identity-settled side is not.
- Tier also gates the universal caveat (`:1250`), the same-study keeper (`:3180`), derivation chains, and F4's "no primary anchor".

Required:
- Tag each state change in the replay by cause: support floor, challenger lowered, or supporter lowered.
- Read every disputed → supported change one by one; each is a sycophancy candidate until shown otherwise.
- Re-run the annotations too (echo, repetition, universal caveat), not only the states.

**7. MED — Lowering without a verified cue departs from the house rule.**
Evidence:
- In `relationship_scope_review.py`, a quote not found in its block makes the row `invalid` and nothing changes.
- §4.3 instead blanks a non-verbatim cue and still lowers.

Required:
- Lower on `reports`, `explains` or `republishes` only with a verbatim cue of at least 12 chars found in the text sent. Otherwise record the row as `invalid` with no change.
- Use a response schema with a `role` enum, as `RESPONSE_SCHEMA` does.
- Mark the page text as untrusted data in the prompt.

**8. MED — `explains → commentary` is a two-step drop, and the roles blur.**
Evidence:
- A professional society's trial summary (`acc.org` on SELECT, "according to top line results") reads as `explains` → commentary, weight 1. A newspaper's story on the same trial is reporting, weight 2.
- The `reports` definition is tangled with examples of the other roles.
- H4 only needs the item out of PRIMARY.

Required: in this build every non-`originates` role maps to **reporting**. Measure explains → commentary later as its own step.

**9. MED — The review's input can race with distillation.**
Evidence:
- Classify and distil run concurrently (`runner.py:2254-2258`), and distil rewrites `text`.
- The review runs after the classifier's model call returns, so whether `text` is raw or distilled at that moment varies from run to run.
- Any read of `text` makes the request signature nondeterministic, which breaks cassette replay.

Required: read only `text_provenance`, `original_snippet` and `snippet`.

**10. MED — Real text shapes the rubric does not cover (the next first-live failure).** All found in the held-out candidates:
- **Forums, issue trackers and mailing lists** on or about the originator (`sqlite.org/forum`, `github.com/*/issues` ×8, `groups.google.com`). User content on an originator's host is not the originator's record. Define it (proposed: `reports`/reporting, or its own role).
- **Bodies that compile others' raw data into a new series or estimate** (EuroMOMO: "data from 27 participating countries"; IHME, Global Carbon Budget, ICCT). The attribution phrase is the rejected Option C cue, now handed to the model. The prompt must state that compiling or modelling others' raw data into a new dataset is `originates`.
- **Institutional newsrooms on multi-centre work** ("SELECT trial presented by Cleveland Clinic physician"). This needs a stated rule.
- **Pages that open with navigation or cookie boilerplate** (polymarket: "Trading is blocked in the United States…"). They will read `unclear`.

Required: add each shape to the prompt with a tuning-set example, and add one of each from the held-out set to the eval's reading list.

**11. MED — Adapter exclusion leaves news through the adapter door.**
Evidence: `rte.ie` news stories arrive via the **Marketaux** adapter as `llm+override` primary (3 occurrences in the held-out set; `_high_confidence_override:559-564` forces every adapter item to primary).

Required: either route non-data adapters (Marketaux) through the review, or cap them at reporting as round 2 did for Wikipedia. Log it as a named gap if deferred.

**12. MED — Measurement can't separate signal from noise yet.**
Required:
- Run the offline review twice on the same inputs and report the per-item flip rate. A target margin smaller than the flip rate means nothing.
- Report recall with and without `unclear`-driven lowers.
- Correct §6.2: drop the off-topic AAP item from the tuning targets. Off-topic is relevance, not origin, and AAP originates its own statements.

**13. MED — Q2's rationale is wrong.**
Evidence:
- cso.ie, oecd.org, centralbank.ie, thirlwall, worldweatherattribution, globalcarbonbudget, research.rug.nl, esawebb.org, portal.research.lu.se, esd.copernicus.org, NAO, FCA, IEA, ICCT, EuroMOMO, IHME, NICE, sqlite.org, esa.int and Cook are all **not** identity-settled, so all of them reach the review.
- The whitelist demoted them on 28 Sep because they are not settled. The exemption did not protect them.

Required: correct the text. The must-survive gate is therefore a real test of the review, which is good.

**14. LOW — Receipts are stored but not visible.**
Evidence:
- `metadata` persists to `Evidence.api_metadata` (`runner.py:3300-3330`), but no payload serialises it (`api/v1` has no `api_metadata` in any builder).
- Step 7 ("read receipts") would then need database access.

Required: expose `originatorReview` on the owner payload.

**15. LOW — Housekeeping.**
- Add `originator_review_contract` and the model to `compute_pipeline_fingerprint` (`manifest_signer.py`), as relationship review does.
- Scope the review to `needs_classification` items. Skip items that already carry a receipt, so a second call is idempotent.
- The `all already classified` early return (`evidence_classifier.py:922`) already skips it; keep it that way.
- §1's "median 212" was measured on the stored, post-distil snippet. The classifier saw `original_snippet` (median 461, cut to 300).
- In re-search, classify and distil are sequential, so the review adds its full latency there.
- The quick tier has the LLM classifier off, so the review never runs there. If a new `PipelineConfig` flag is added, declare it in `tier_limitations.py`.
- Round 2 already `tracker_cap`s an `esa.int` "live launch" page. Judge the must-survive gate end to end, and name that item as a pre-existing exception.

## Answers
- **Q1: `unclear` → unchanged.** Record it in the receipt and report its rate. Absence of an origin statement is not evidence of relaying, and inputs are thin for 37% of candidates. Revisit only if the eval shows `unclear` is mostly non-originators.
- **Q2: No.** Agree, for a different reason (finding 13): keep the build narrow. Identity-settled explainers are a known residual.
- **Q3: No.** Keep the original type in the receipt. Note as a follow-up that a lowered item typed `academic` still claims peer review.
- **Q4: Accept.** An odds page originates its odds. On the held-out set, both polymarket pages are already `tracker_cap`ped.

## Verification notes (author, 2026-09-30)
Every finding was re-checked against the code and data. All 15 stand in substance. Figures corrected: 370 of 418 occurrences carry a `start == 0` window (not 266 of 311); the pre-distil snippet median is 493 (not 461); 146 recovery occurrences (not 126). Finding 13 is wrong for four hosts: JRC, NASA, OWID and whereyourmoneygoes.gov.ie are identity-settled. New, not in this review: three Astra records repeat A− claims #18/#19, so the held-out set is 209 candidates from 11 records. Detail: design §12.
