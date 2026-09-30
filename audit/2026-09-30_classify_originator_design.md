# Design: PRIMARY means originator (classification, class D)

**Status:** DESIGN, **revision 2**, 2026-09-30; verified against code and data the same day (§12). Not built. Rev 1 was reviewed (`audit/2026-09-30_classify_originator_review.md`: APPROVE WITH CHANGES, 5 HIGH, 7 MED, 2 LOW). Every finding is taken; §10 maps each one to where it landed. Needs founder approval.
**Brief:** `audit/2026-09-30_classify_originator_brief.md`. **Evidence:** `audit/2026-09-28_primary_tier_review.md` (classes A–E).
**Difficulty:** 3+ (new model call; tier feeds `_STATE_TIER_WEIGHTS` AND the mapping prompt; cassettes).

## 1. The fault, and why it happens
The LLM classifier calls non-originators PRIMARY: KFF explainers, a trade coalition, a UnitedHealth white paper, a commercial country profile quoting EU forecasts, a course page. Class D was the largest remaining H4 cause on the 28 Sep re-measure.

Three causes in `evidence_classifier.py`:
1. **The prompt's tie-break points the wrong way** (`:73`): *"If uncertain, prefer the more conservative label (closer to primary, closer to data)."*
2. **Primary is defined by genre, not by origin.** *"Government data, official statements, … raw statistics, datasets."* A table of someone else's figures looks like "raw statistics".
3. **The model sees 300 characters** (`snippet_length`, `:880`) of the item's `snippet` (`:1078`). At classify time that is still the search snippet: distillation replaces `snippet` only afterwards (`text_provenance.finalize_distilled_payload`). The pre-distil snippet is kept as `text_provenance.original_snippet`; on held-out candidates it has a median of 493 chars, so the cut loses over a third. "According to the European Commission…" is often outside it.

## 2. Size of the fault on data it was not tuned on
Held-out: the 14 Astra regrade records, all runs (`tmp/astra-regrade-*/*/owner.json`; 144 runs, 2,507 items; local, free; recorded before round 2).
- 413 unique PRIMARY URLs (by method: `llm` 396, `llm+override` 12, `heuristic` 5). 241 rest on the model's verdict alone (`llm`, not identity-settled, no adapter). Today's caps (the 24 Sep news/aggregator caps plus the 28 Sep round 2) catch 12 of them. **229 remain.**
- 119 of 144 runs have candidates; median 3, max 29 per run.
- **Skew:** one record (`t09_sqlite_url`) supplies 80 of the 229 URL–record pairs; sqlite.org hosts are 44 URLs. Every result is reported per record and per host cluster, not only pooled (§7).
- **Input:** 84 of the 229 URLs (37%) have no `text_provenance` in any run. Coverage recovery never captures it: 146 recovery occurrences of candidates, 0 with provenance, stored snippet median 163 chars.
- **Overlap with the A− records, found on verification:** Astra `t04_jwst` is the same claim as A− #18, and `t06_sweden_focus` / `t13_sweden` the same as A− #19 (claim text identical). The 28 Sep caps were tuned on those pools (orbitalradar in #18). **The held-out set is therefore the other 11 records: 209 candidates** (80 with no provenance; the 44 sqlite.org URLs are all inside it). The 20 overlapping candidates are reported separately and never counted toward a target.
- The two classifier commits since 9 Sep (`173a26c` 24 Sep, `b7a3d8f` 28 Sep) were tuned on the A− records only, so the other 11 records are clean for the tier caps.

## 3. Options considered
| Option | What | Verdict |
|---|---|---|
| A. Host whitelist | Primary only where identity proves it | **Rejected 28 Sep.** Not revisited. |
| B. `primary` + type `analysis` → lower | The model's own type says "explainer" | **Rejected.** Demotes sqlite.org's WAL page (typed `analysis`); misses 176 of 241 candidates typed `data` / `official_statement`. |
| C. Attribution phrases as a rule | "according to", "data from" | **Rejected as a rule; shadow count only.** Originators quote others; compilers (EuroMOMO) say "data from 27 countries" and are originators. |
| D. Rewrite the classifier prompt | Originator definition; fix the tie-break | **Deferred to its own measured step (§9).** Re-rolls every tier in both directions; could not be attributed alongside E. |
| **E. Originator review** | A second, focused, lower-only model pass on primaries that rest on the model's verdict alone | **Proposed.** |

## 4. The proposal: originator review
### 4.1 Candidates
Runs at the END of `classify_batch`, after every existing cap and floor. An item is a candidate only if ALL hold:
- it was in this call's `needs_classification` set (already-classified items and the "all already classified" early return, `:922`, are untouched);
- `tier == "primary"` after the existing passes, and `classification_method == "llm"`;
- the host does NOT satisfy `_identity_settles_tier`;
- `external_source_provider` is empty;
- it carries no `originator_review` receipt yet (idempotent on a second call).

**Not reviewed, with a receipt (`originator_review.status = "not_reviewed"`, reason named):**
- **coverage recovery** (`reason: recovery_budget`). The review would sit inside Phase A's `asyncio.wait` budget (`runner.py:2559-2760`), which has overrun twice; a timeout there cancels the claim's whole recovery pool. Recovery items also have no page text. Moving it into Phase B is a follow-up (§9).
- quick tier: the LLM classifier is off there, so the review never runs. Declared in `tier_limitations.py` if a new `PipelineConfig` flag is added.

**Named gap, logged, not fixed here:** news stories arriving via the **Marketaux** adapter are forced primary by `_high_confidence_override:559-564` (3 held-out occurrences, rte.ie). Fix separately, as round 2 did for Wikipedia: a reporting cap for non-data adapters.

### 4.2 Input (claim-independent, deterministic)
Per item: title, host, URL, then ≤1,200 chars of text:
1. **`_page_opening`**: the first 1,200 chars of `_full_text`, copied as a transient key in the loops that call `capture_text_provenance` before classification: the main path (`runner.py:2096-2104`, before classify and distil start) and re-search (`re_search.py:103`, before its classify at `:112`). The distiller's own capture (`evidence_distiller.py:115`) is a no-op there, since capture returns early once provenance exists. Coverage recovery has no such loop, which is one reason it is skipped (§4.1). Copied only when the flag is on. Transient: persistence copies named fields and `metadata` only (`runner.py:3286-3329`), so it is never stored; and `classify_batch` pops `_page_opening` from every item it was given once the review has read it. (It cannot ride on the `_full_text` cleanup: that is two separate places, the distiller's `_cleanup_full_text` and the no-distil branch at `runner.py:2286-2290`, and neither knows the new key.)
2. otherwise `snippet` (still the search snippet at classify time, see §1).

Why not the `text_provenance` windows: every one is chosen by the claim's element terms (`select_passages`), **including whether the `start == 0` window is kept at all** (it is kept only if it matches an element term, or as the fallback when nothing matches). It is present in 370 of 418 candidate occurrences that have provenance, so using it would still make the input, and so the tier, depend on the claim.

**Never `text`:** distillation rewrites it concurrently (`runner.py:2254-2260`), which would make the input and the cassette key vary between runs. And `_full_text` itself is popped by the distiller mid-classify, which is why the opening is copied before the gather.

**Offline eval input differs from runtime, stated plainly:** stored payloads have no `_full_text`. The eval uses the `start == 0` window where stored, else `original_snippet`, else the stored snippet, and reports results split by which one it used.

The prompt marks the page text as untrusted data. The claim is never sent.

### 4.3 The question
One call per ≤15 candidates, concurrent, `ORIGINATOR_REVIEW_MODEL` (default `GOOGLE_LLM_MODEL`), OpenAI fallback, response schema with a `role` enum (as `RESPONSE_SCHEMA` does in the relationship review):
```json
{"index": 0,
 "originator": "<the body that produced the information this page presents>",
 "role": "originates | hosts_original | relays | user_content | unclear",
 "cue": "<verbatim phrase from the text that shows the role, or empty>"}
```
Definitions. **Every worked example comes from the 28 Sep tuning pools, none from the held-out set:**
- **originates:** the publisher produced the information: its own data, measurement, study, record, decision, statement about itself, or documentation of its own product. **Compiling or modelling other bodies' raw data into a new dataset, series or estimate counts as originating** (the new series is theirs). A trade body's own survey originates; its summary of others' figures does not.
- **hosts_original:** a complete, unaltered copy of another body's own document or dataset (a PDF of a report, a filing, a guideline, an archive snapshot). The document is still primary; where it is hosted does not change that.
- **relays:** the page explains, summarises, excerpts or re-displays information produced by someone else: explainers, guides, encyclopaedia and course pages, FAQs, white papers built on others' figures, calculators, comparison sites, country profiles quoting forecasts. Tuning examples: the KFF explainers, lloydsbanktrade's profile, the libretexts course page.
- **user_content:** forum posts, issue threads, mailing-list messages, comments **by people who are not the project's maintainers or the publisher**, even on the originator's own host. The format alone never decides it; who is speaking does (founder, label audit 2026-09-30: a contributor describing their own codebase in an issue originates it). A maintainer's own post is `originates`.
- **unclear:** the text does not show who produced it (including pages that are mostly navigation, cookie or login boilerplate).

Institutional newsrooms announcing multi-centre work ("trial presented by our physician") are `originates` only for what the institution itself did; otherwise `relays`. Stated in the prompt with a tuning example if one exists; otherwise the rule text alone.

### 4.4 What it does with the answer
| role | result |
|---|---|
| originates | unchanged |
| hosts_original | unchanged |
| relays | **reporting**, only with a verified cue |
| user_content | **reporting**, only with a verified cue |
| unclear | **unchanged** (recorded, rate reported) |
| missing / invalid / call failed / cue not verified | unchanged, row recorded `invalid` or `failed` |

- **Verified cue:** 12–600 chars and an exact substring of the text actually sent, with no normalisation: the rule `relationship_scope_review.py` applies to its quotes (`:612-615`). No cue, no change.
- **Every lowering goes to reporting**, one step. `relays → commentary` is two steps and would put a professional society's trial summary below a newspaper story on the same trial; it is a later, separately measured question.
- **Lower-only**, never raises, never touches reporting/commentary.
- **Type unchanged**; the original type is kept in the receipt. (Follow-up: a lowered item typed `academic` still reads as peer-reviewed.)
- **All-or-nothing per pool:** tier changes are applied only after every review call for that `classify_batch` call has returned or failed, so a cancellation never leaves a half-applied pool.
- **Receipt** on every candidate: `metadata.originator_review = {status, role, originator, cue, from_tier, to_tier, original_type, input_kind: "page_opening" | "snippet"}`; `classification_method = "originator_review"` when lowered. **Exposed on the owner payload as `originatorReview`** (today `api_metadata` reaches no payload), so receipts can be read without database access.
- Timed as its own key in `stage_timings`. `originator_review` contract and model join `compute_pipeline_fingerprint` (`manifest_signer.py`).

### 4.5 Flags
- `ENABLE_ORIGINATOR_REVIEW` (default **False**), `ORIGINATOR_REVIEW_MODEL`, `ORIGINATOR_REVIEW_TIMEOUT_S = 15`.

## 5. Consequences for the rest of the pipeline (read before judging the eval)
- **Tier is in the mapping prompt** (`claim_map_analyzer.py:1790, 2019, 3568, 3800` print `[Tier: …]`; `:417`, `:698` tell the mapper to prioritise primary/reporting). So a tier change can change what the mapper decides, not only the weights, and it **re-keys the mapping cassettes** of any claim it touches.
- **Lower-only per item is not neutral per state.** Run through `_derive_element_state_with_authority` with the factual floor of 3:
  - supports primary + reporting vs one primary challenge → `disputed` (`close_split`); lower the challenger → `supported` (`supports_dominant_2x`);
  - one lone primary support → `supported`; lower it → `unresolved` (`support_floor`).
  So it can raise an element as well as lower one. And the review sees only non-identity primaries, so one side can be reviewed while the other is not.
- Tier also gates the universal caveat (`:1250`), the same-study keeper (`:3180`), derivation chains, and F4's "no primary anchor".
- In re-search, classify and distil are sequential, so the review adds its full latency there.

## 6. Must-survive set (hard gate: any lowered = fail)
Checked with `_identity_settles_tier` (JRC checked as a `*.europa.eu` host, which `_GOV_PATTERNS` matches): JRC, NASA, OWID and whereyourmoneygoes.gov.ie ARE identity-settled and never reach the review. Every other host below is not, so it does reach the review; for those this is a real test (review finding 13, corrected for these four).
- From 28 Sep: cso.ie ×3, oecd.org, thirlwall.public-inquiry.uk, centralbank.ie, worldweatherattribution.org, globalcarbonbudget.org, research.rug.nl, esawebb.org, portal.research.lu.se, esd.copernicus.org; JRC, CSO, Cook's own poll page, NASA, OWID, whereyourmoneygoes.gov.ie.
- From the Astra pools (an eval gate only, never a prompt example; the esa.int pages come from `t04`, an overlapping record): sqlite.org's own documentation pages; sci.esa.int / esa.int mission pages; NAO; FCA; IEA's own data tools; ICCT's own studies; EuroMOMO; IHME; NICE.
- Original documents on another host: the NEJM SELECT PDF on `mediacenteratypon.nejmgroup-production.org`; Commons Library CBP-7960 on `brexitlegal.ie`; the Uganda Clinical Guidelines on `nms.go.ug`.
- Pre-existing exception, named: round 2 already `tracker_cap`s an esa.int "live launch" page. The gate is judged end to end with that one item excluded.

## 7. Measurement plan (all before any flag flips)
1. **Blind labels for the 209 held-out candidates (plus the 20 overlapping ones, labelled but reported apart).** A separate agent labels originates / not-originates / unclear from a **separately written rubric with no worked examples from any Astra record**. It never sees the review's prompt or output.
   - **The founder audits 30, stratified:** at most 3 per host, every record represented. More than 3 disagreements → the rubric is revised and the labelling redone.
2. **Tuning set = the 28 Sep class D items** (KFF ×2, hcttf, UnitedHealth, lloydsbanktrade, libretexts), fetched free from public payloads. Used to write the prompt; never to judge it. The off-topic AAP item is dropped: off-topic is relevance, not origin.
3. **Offline review on the 209 (and the 20 overlapping, reported apart), run TWICE on identical inputs** (paid; cost measured on the first run and stated before the second). Report:
   - the per-item **flip rate** between the two runs; no target margin smaller than it counts;
   - per record and per host cluster, and split by offline input kind (`start == 0` window / `original_snippet` / stored snippet, §4.2);
   - the `unclear` rate, and recall with and without it.
   Targets, set now:
   - must-survive: **0** lowered;
   - genuine originators lowered: **≤ 5%** pooled AND no host cluster above 10%;
   - non-originators lowered: **≥ 60%** (lowered from rev 1's 70% because `unclear` now keeps the tier and a verified cue is required; the eval will show whether that is too cautious).
4. **Offline state replay = the weight effect only.** Apply new tiers to the stored claim maps (held-out and the 18 re-run pools) and re-derive states. Tag every change by cause: support floor, challenger lowered, supporter lowered. **Read every disputed → supported change one by one; each is a sycophancy candidate until shown otherwise.** Re-run the annotations (echo, repetition, universal caveat) too.
5. **Mutation check.** Remove each rule (candidate filter, identity exemption, idempotency skip, recovery skip, lower-only, verified cue, `unclear` unchanged, all-or-nothing apply); a test must fail each time.
6. **Replay bench**, control arm first (flag off), then flag on. The flag-on arm re-records mapping for touched claims (paid, noisy): **cost stated and founder asked before it runs.**
7. **Live:** two checks with the flag on. Read every `originatorReview` receipt and every relationship whose ref changed tier; the mapper's reaction to a new label is only visible here.

## 8. What it will not fix
- Unmapped rows keeping a badge (decided 28 Sep).
- Adapter items, including Marketaux news (named gap, §4.1).
- Coverage-recovery items (skipped with a receipt, §4.1).
- Identity-settled explainers (a `.gov` "what is inflation" page stays primary).
- A genuine originator that is weak (an interested party's own statement): correctly primary; the interested-party gate handles its weight.

## 9. After this
- Option D (prompt tie-break and originator definition) as its own measured step.
- The review in coverage recovery's Phase B, with page text captured for recovery items.
- `relays → commentary` for explainers, measured separately.
- A reporting cap for non-data adapters (Marketaux).

## 10. Review findings → where they landed
| # | Finding | Landed |
|---|---|---|
| 1 H | Held-out contaminates prompt and labels | §4.3 tuning-only examples; §7.1 separate rubric, stratified audit; per-host reporting §7.3 |
| 2 H | Thin, claim-selected input | §4.2 opening window first, no element windows; §4.4 `unclear` unchanged, verified cue |
| 3 H | "republishes" lowers the original | §4.3 `hosts_original`; §6 three URLs added |
| 4 H | Recovery Phase A budget | §4.1 skipped with receipt; §4.4 all-or-nothing; own stage timing |
| 5 H | Tier in mapping prompt | §5; §7.4 weight-only replay; §7.6 ask before paid re-record; §7.7 read mapper effect live |
| 6 M | Not state-neutral | §5; §7.4 cause tags, read every disputed → supported |
| 7 M | Lower without verified cue | §4.4 ≥12-char verbatim cue; schema enum; untrusted-data marking |
| 8 M | Two-step drop, blurred roles | §4.4 every lowering → reporting; roles redefined §4.3 |
| 9 M | Race with distil on `text` | §4.2 never `text` |
| 10 M | Forums, compilers, newsrooms, boilerplate | §4.3 `user_content`, compiler rule, newsroom rule, boilerplate → `unclear` |
| 11 M | Marketaux news via adapter | §4.1 named gap; §9 |
| 12 M | Signal vs noise | §7.3 two runs, flip rate, split reporting; AAP dropped |
| 13 M | Q2 rationale wrong | §6 corrected; must-survive is now a real test |
| 14 L | Receipts invisible | §4.4 `originatorReview` on owner payload |
| 15 L | Housekeeping | §4.1 idempotency, early return, quick tier; §4.4 fingerprint, timings; §1 snippet figure corrected; §5 re-search latency; §6 esa.int exception |

## 11. Decisions for the founder
Q1–Q4 are settled by the review: **`unclear` leaves the tier unchanged**; identity-settled hosts are not reviewed; type unchanged; prediction-market odds pages count as originating their own odds. The founder decision now is whether to approve this design so the free steps can start (§7.1 labelling, §7.2 tuning fetch), with each paid step (§7.3, §7.6, §7.7) asked for separately with its cost.

## 12. Verification log (2026-09-30, against code and data, not documents)
Method: every line reference re-read in the source; every figure recomputed from `tmp/astra-regrade-*/*/owner.json` with the live cap functions (`_apply_quality_floor`, `_identity_settles_tier`); the state example run through `_derive_element_state_with_authority`. Script: session scratchpad `verify.py` (not committed; free, local). No code changed.

**Confirmed:** tie-break `:73`; `snippet_length` `:880`; the prompt reads `snippet` `:1078`; early return `:922`; adapter override `:558-564`; `[Tier: …]` at `claim_map_analyzer.py:1790/2019/3568/3800`; "prioritise primary/reporting" `:417/:698`; universal caveat tier-gated `:1250`; same-study keeper `:3180`; recovery Phase A `asyncio.wait` + cancel (`runner.py:2754-2757`) and its two overruns (docstring, 22 Jul); classify ∥ distil gather `:2254-2260`; re-search classify then distil, sequential; quick tier `enable_llm_classifier=False`; `RESPONSE_SCHEMA` and the 12–600-char quote rule in the relationship review; `api_metadata` written (`runner.py:3329`) but read by no API payload; fingerprint carries `relationship_review_contract`. Counts: 144 runs, 2,507 items, 413 / 241 / 12 / 229, 176 of 241 typed data or official, 119 runs with candidates (median 3, max 29), 80 `t09` pairs, 44 sqlite.org URLs, 84 without provenance, 3 Marketaux rte.ie items; `sqlite.org/wal.html` typed `analysis`; the esa.int "live launch" page is `tracker_cap`ped by today's caps; both state flips reproduce.

**Corrected in this revision (rev 1 or the review had them wrong):**
1. The classifier reads `snippet`, not `original_snippet`; the pre-distil median is **493**, not 461.
2. The page-opening window is present in **370 of 418** candidate occurrences with provenance (not 266 of 311), and its presence depends on the claim's element terms, so it cannot be the review's input. Replaced by a transient `_page_opening` (§4.2).
3. Recovery: **146** candidate occurrences, not 126.
4. The 12 caught are by the 24 Sep caps AND round 2, not round 2 alone.
5. JRC, NASA, OWID and whereyourmoneygoes.gov.ie **are** identity-settled (review finding 13 was wrong for these four).
6. **Held-out contamination:** three Astra records repeat A− claims #18 and #19. Held-out is now 209 candidates from 11 records.
7. `_page_opening` must be popped by `classify_batch` itself; the `_full_text` cleanup lives in two other places.
8. The distiller also calls `capture_text_provenance` (`evidence_distiller.py:115`); it is a no-op on the main path, and re-search captures at `re_search.py:103`.
9. The verified-cue rule is an exact substring with no normalisation (`relationship_scope_review.py:612-615`); rev 2 had said "whitespace-normalised".
10. Receipt `input_kind` and the eval split now name the inputs actually used (`page_opening` / `snippet` at runtime; three stored kinds offline).

**Final pass:** every line reference and figure in §§1–11 re-read after the corrections; zero failing claims. `git status` shows no change under `backend/`, `web/` (beyond pre-existing untracked design files) or `shared/`.

## 13. Build log (2026-09-30, founder: "proceed"). Flag OFF; nothing paid run.
**Code, all behind `ENABLE_ORIGINATOR_REVIEW=False`:**
- `app/services/originator_review.py` (new): candidate filter, page-opening input, prompt with tuning-only examples, `role` enum schema, 12–600-char exact-substring cue check, lower-only apply after every call returns, receipts.
- `evidence_classifier.py`: `classify_batch(..., review_originators=True)`; the review runs last and only on items classified in this call; `_page_opening` popped on both return paths; `_call_originator_review` (Google with schema, OpenAI fallback); `_call_openai` takes an optional system prompt (unchanged request when omitted).
- `runner.py`: page opening copied beside provenance capture; coverage recovery passes `review_originators=False`; `stage_timings["originator_review"]`. `re_search.py`: page opening copied before its classify.
- `response_builder.py`: `originatorReview` on the owner/agent payload only (`_load_claims_data`), never on the public page.
- `config.py`: three settings. `manifest_signer.py`: contract and model in the fingerprint when on.

**Tests:** `tests/unit/pipeline/test_originator_review.py`, 42 pass. **Mutation check: 20/20 killed** (method filter, lower-only, adapter skip, idempotency, identity exemption, verified cue, cue-in-sent-text, `unclear` unchanged, `hosts_original` unchanged, never `text`, opening preferred, failed call safe, recovery flag, opening popped, flag gate, scoped to classified, owner-only receipt, fingerprint, runner recovery wiring, re-search wiring). The first run killed 17; the three survivors exposed missing tests, now added.

**Eval material (`audit/originator_eval/`):** `build_inputs.py` → `heldout_inputs.json` (229: 209 held-out + 20 overlap; inputs 131 opening window / 14 original snippet / 84 stored snippet). `labelling_rubric.md` written separately from the prompt. `label_view.json` (id, URL, host, title, text only). `blind_labels.json` by a separate agent restricted to those two files: **originator 96 / not_originator 129 / unclear 4**. `founder_audit.md`: 30 stratified (11 records, 27 hosts, ≤3 per host, seed 20260930) for the founder.

**Blocked:** the tuning fetch (§7.2) needs the 28 Sep re-run check ids in full; they are not recorded anywhere readable, and reading the API key from `~/.claude.json` was refused by the permission layer. The prompt's tuning examples are written from the tier review's descriptions meanwhile.

**Verification, flag OFF (2026-09-30):**
- Unit suite **4,310 pass, 0 fail** (Docker up). The first full run failed 7 fingerprint tests: they mock `settings` with a MagicMock, so the flag read truthy and the model name was not JSON. Fixed by requiring the flag `is True` in `compute_pipeline_fingerprint`; mutants re-run, still 20/20.
- Replay bench `--all`: 125/7/10/5 with drift on 5647, 82CF and 93DD; **93DD replayed alone: no drift, 14/1/2** (its two fails are the known thin-pool v3 floors). Combined **139/8/11/5 + known 5647/82CF drift, identical to the canonical record.** Flag off changes no request.
- Lint: no unused imports; `black` clean on the new and changed classifier files.

**Founder label audit (2026-09-30):** first read 28 agree / 2 disagree, revised the same day to **27 strong agree, 1 likely disagree (#28), 2 to inspect (#17, #30)**; pass (≤3). #28 (a GitHub issue labelled not_originator for being an issue): the format was deciding, not the speaker. **Rubric v2 and prompt contract v2** now say who is speaking decides (§4.3). A rule briefly added for #30 (an authored paper originates) was withdrawn when the founder revised #30 to `unclear`. #17 (T&E) names a live boundary: originating an analysis or tool vs the underlying raw data; §4.3's compiler rule already calls the new analysis `originates`. Full blind relabel under rubric v2 is running; the founder's 30 verdicts (`founder_verdicts.json`) are the answer key for those items. `founder_inspect.md` holds the full stored text of #17, #19, #22, #28 and #30.

**Blind relabel under rubric v2 (2026-09-30):** 101 originator / 119 not / 9 unclear (was 96 / 129 / 4). 19 of 229 labels changed:
- **11 from the new speaker rule, as intended:** GitHub issues, sqlite.org forum threads and one mailing-list announcement moved to `originator` where a maintainer or the project team speaks, and to `unclear` where the speaker is not shown.
- **8 with no rule behind them (h033, h034, h036, h054, h125, h141, h156, h188).** That is labeller run-to-run noise: **about 3.5%**. The eval's "≤ 5% of originators lowered" target sits close to it, so a miss of a point or two against these labels is not evidence on its own; per-item disagreements get read, not just counted.
- Against the founder's 30: v2 matches 28 (#4 AfrAsia flipped by noise; #19 is now `unclear`, which the founder had flagged to inspect).

**Final eval labels** (`eval_labels.json`): v2, with the founder's 30 verdicts overriding. Held-out 209: **91 originator / 110 not / 8 unclear.**

## 14. Offline eval 1 (2026-09-30) — FAIL. Model `gemini-3.5-flash-lite`, contract v2, flag still OFF.
Founder-approved spend: cost probe $0.0035 (15 items), full eval **$0.114 (~9p)**, 229 items × 2 runs, 32 calls. Result file: `audit/originator_eval/eval_result_20260930T102510Z.json`.

| Target (set before the run) | Run 1 | Run 2 | Verdict |
|---|---|---|---|
| Must-survive lowered = 0 | 0 | 0 | pass |
| Genuine originators lowered ≤ 5% | 11/91 (12%) | 13/91 (14%) | **fail** |
| Non-originators lowered ≥ 60% | 45/110 (41%) | 51/110 (46%) | **fail** |
| Flip rate between identical runs | 27/229 (12%) | | **too noisy to trust any margin** |

`unclear` 4/209; invalid or failed 6/209.

**Read one by one: the 14 originators it lowered.** Three shapes, none a labelling error:
- **Secondary analyses of a named trial read as relaying** (4): SELECT sub-analyses on doi.org / jacc.org, an Emerald empirical paper. "In the SELECT trial…" was taken as a source attribution.
- **Pages that publish their own odds or market-implied probabilities read as relaying the body they forecast** (5): centralbank.watch, prediqt, rateprobability, robinhood, bluegamma → "relays Bank of England". Q4 had settled these as originating their own odds.
- **The cue check proves the words are on the page, not that they show the role** (4): GitHub issues lowered on "Notifications You must be signed in…" boilerplate; a Richard Hipp reply on sqlite.org lowered as `user_content` while the model itself named Hipp as the originator.
- One lab blog quoting its own lead author.

**Read: the 59 non-originators it kept.** 54 were answered `originates` with the page's own publisher named as the originator ("Coddy Tech", "Xojo", "CalculatorLib", "CORE"). The model is answering "who wrote this page", not "who produced the information".

**What this means:**
1. Flash-lite is not stable enough for this question: a 12% flip rate swamps every target. That matches the relationship review, which also needed `gemini-3.7-flash`.
2. The verified-cue gate is weaker than the design assumed: a verbatim quote is necessary, not sufficient.
3. **Contamination from here on:** these reads came from the held-out set. A prompt revision informed by them cannot be judged on the same 209. A model-only re-run (no prompt change) still can.

## 15. Offline eval 2 (2026-09-30) — model-only re-run on `gemini-3.7-flash`. Same prompt (v2), same 209.
Founder-approved. Result: `audit/originator_eval/eval_result_20260930T104328Z.json`. **True cost $0.257 (~20p)**; the script printed $0.178 because it left out thinking tokens, which bill at the output rate (script fixed).

| Target | Run 1 | Run 2 | Verdict |
|---|---|---|---|
| Must-survive lowered = 0 | 0 | 0 | pass |
| Genuine originators lowered ≤ 5% | 3/91 (3%) | 1/91 (1%) | pass |
| Non-originators lowered ≥ 60% | 69/110 (63%) | 76/110 (69%) | pass |
| Invalid or failed | 40/209 | 35/209 | **fail: my code** |
| Flip rate, items reviewed in both runs | 5/175 (2.9%) | | stable (flash-lite: 12%) |

On reviewed items only: originators lowered 3/81 and 1/86; non-originators lowered 69/91 (76%) and 76/101 (75%).

**Answer to "model or code?":** both, separable. The model was the instability (12% → 2.9% flips) and most of the "who wrote the page" confusion. The invalid rows were my code: Gemini counts thinking tokens against `maxOutputTokens`, and my cap of 3,000 truncated 3 replies mid-JSON (45 items lost) and clipped others (34 rows not returned).

**Fixed (free):** `MAX_OUTPUT_TOKENS = 8192`; `ORIGINATOR_REVIEW_MODEL` defaults to `gemini-3.7-flash`; the eval script counts thinking tokens; a test pins budget, schema and model (43 tests). No prompt change, so the 209 remain a fair test for a confirming re-run.

**Still open, from eval 1's reads (a prompt matter, needs a fresh test set):** the verified-cue gate proves presence, not relevance; odds pages and trial sub-analyses are not named in the prompt.

## 16. Eval 3 (2026-09-30) — confirming re-run after the output-cap fix. 3.7-flash, prompt v2, same 209.
Founder-approved. `eval_result_20260930T105009Z.json`. **Cost $0.239 (~18p), thinking tokens included.**

| Target | Run 1 | Run 2 | Verdict |
|---|---|---|---|
| Must-survive lowered = 0 | 0 | 0 | pass |
| Genuine originators lowered ≤ 5% | 2/91 (2%) | 2/91 (2%) | pass |
| Non-originators lowered ≥ 60% | 87/110 (79%) | 91/110 (83%) | pass |
| Invalid or failed | 17 (15 = one call timed out at 15 s) | 1 | timeout: open |
| Flip rate, reviewed in both runs | 16/211 (7.6%) | | boundary pages only (a hospital newsroom on a trial, a bank's market sheet, rate-odds pages, SPIE design papers) |

Truncation is gone. Originators lowered, read: rateprobability (odds page), a sqlite.org thread (lowered as user content on "By anonymous on…" although the lead developer also answers), Cleveland Clinic's newsroom on a multi-centre trial, AfrAsia's market sheet (cue = a currency table).

**Offline state replay (free; `state_replay.py`), weight effect only:**
- The replay re-derives all 400 stored element states exactly, and detects change (lowering EVERY primary moves 6 elements supported → unresolved).
- Eval run 2's 103 lowered URLs: 122 elements touched, **0 state changes.**
- Eval run 1's 101: **3 changes.** Two `supported → unresolved` (support floor; "Venus is a planet", "falling inflation implies a price-level change": lone primary supports lowered). One **`disputed → supported`** (JWST "6.5-metre primary mirror"), read one by one as §7.4 requires: the lowered challenger is a SPIE paper describing an early 5 m design, lowered as `relays` on the cue "5 meter diameter, segmented, lightweight primary mirror", which shows no relaying at all. The resulting state is right (the mirror is 6.5 m), for the wrong reason: the real fault is a historical design mapped as a challenge.
- So on these pools the review changes labels almost always and states almost never, and the states it can move are exactly the boundary items that flip between runs.

**Open before any flag flip:**
1. **Per-call timeout.** 15 s cost a call on 3.7-flash; the relationship review needed 40 s on the same model. Per-call latency is not yet recorded, so the right value is unmeasured.
2. **Cue relevance.** The cue gate proves the words are on the page, not that they show relaying (AfrAsia's currency table; SPIE's own mirror spec; GitHub boilerplate in eval 1). A candidate rule: for `relays`, the cue must name the other body the page relays. Found on held-out reads, so it needs a fresh test set to judge.
3. Replay bench with the flag on (paid: re-records mapping) and two live checks (paid).

## 17. Timeout and cue check tightened (2026-09-30, founder: "fix the timeout and tighten the cue check"). Flag OFF; contract v3.
**Timeout:** `ORIGINATOR_REVIEW_TIMEOUT_S` 15 → **40** (the relationship review's value on the same model; 15 s lost a call in eval 3). Every review now records `call_seconds` per call in its stats, so the value can be resized on measured latency.

**Cue check:** a verbatim cue proved presence, not relevance (a currency table, GitHub boilerplate, SPIE's own mirror spec all passed). A lowering (`relays`, `user_content`) now also needs, in order, each failing to its own `invalid_reason`:
1. a named originator (`originator_not_named` for "unknown"/empty);
2. an originator that is not the publisher, by host or by the model's own new `publisher` answer (`originator_is_publisher`);
3. a cue that names the originator, as a whole word, ignoring words that only name a kind of body ("office", "bank", "national"…) unless nothing else is left (`cue_names_no_other_body`).

**Why the prompt changed too (contract v3):** replaying the tightened rule over eval 3's answers (diagnostic only; those rows were read) showed it would block about half the CORRECT lowerings (non-originators lowered ~80% → ~40%), while blocking the wrong ones (originators lowered 2 → 0–1). The rows show why: when 3.7-flash said `relays`, it usually put the page's own publisher in `originator` ("Coddy Tech", "EBSCO") while its own cue named the real source (Coddy's cue mentions SQLite). One field was carrying two questions. v3 asks for `publisher` and `originator` separately and tells the model the cue must name the body relayed (or the speaker).

**Verification:** 52 review tests; **27/27 mutants killed** (new: originator named, not the publisher, answered publisher is self, cue names the body, generic words filtered, URL passed, output headroom; the two role mutants survived once because a test used originator "x", which the new rule rejects on its own; the test now isolates the role). Unit suite **4,320 pass**. `black` clean.

**Fresh test set:** v3 was shaped by reading eval 3's rows, so it cannot be judged on the 209. The replay corpus was mined offline for free (`capture_fresh.py`: a `classify_batch` hook during a cassette replay; bench result unchanged at 125/7/10/5 + known drift) but yields only **11** candidates: too few to measure a 5% rate. A fresh set of ~200 needs new checks on new claims.

## 18. Directional read of v3 (2026-09-30) — the tightening made it WORSE. Recommend reverting to v2's cue rule.
**Fresh set attempt:** 3 full checks (~$0.22) then a classify-only harness (`run_fresh_harvest.py`, 4 claims, ~$0.09) yielded only **22** fresh candidates, ~2 per claim; ~200 would need ~80 more claims (~£1.50). Stopped and asked; the founder chose the cheap directional read.

**Directional read (~$0.24):** v3 on the 143 held-out pages whose rows were never read during design (`read_ids.json` lists the 72 excluded), plus the 22 fresh pages (blind-labelled 13 originator / 7 not / 2 unclear).

| On the 143 unread | Originators lowered | Non-originators lowered |
|---|---|---|
| v2 (eval 3, same pages) | 0/66, 0/66 | 55/70 (79%), 60/70 (86%) |
| **v3** | 1/66, 1/66 | 40/70 (57%), 41/70 (59%) |

Fresh 22 (too small to judge alone): originators lowered 1/13 and 0/13; non-originators 3/7 and 2/7.

**Reading:** on pages nobody read, v2 already made no wrong lowerings; v3's stricter cue rule cut correct lowerings by a third and gained nothing. The v3 changes were shaped by ~10 bad rows among the read ones; on unread data they were not a problem worth that price. **Lesson: judge a fix on rows you did not read before building it.**

**Latency (measured, v3 run):** per call 3.5–15.8 s (20 calls). The 40 s timeout has ample room; 20 s would also hold.

**Spend today on this track:** ≈ $1.17 (~£0.92): evals 1–3 ~$0.61, fresh-set attempts ~$0.31, directional read ~$0.24.

## 19. Reverted to contract v2; flag-on bench started (2026-09-30, founder: "proceed as recommended", route A)
- **Reverted:** prompt, schema and `_decide` are back to exactly what eval 3 measured (contract v2). The v3 helpers (`_name_tokens`, `_names_publisher`, `_cue_names`, the generic-word lists, the `publisher` field) are deleted, not left dormant; their tests went with them.
- **Kept:** `ORIGINATOR_REVIEW_TIMEOUT_S = 40` (measured calls 3.5–15.8 s), `call_seconds` in stats, `MAX_OUTPUT_TOKENS = 8192`, `ORIGINATOR_REVIEW_MODEL = gemini-3.7-flash`.
- 43 tests pass; **21/21 mutants killed** on the reverted code.
- Route A next: flag-on bench (`--record-missing`: only the review's calls and the mapping calls its tier changes re-key go live; cost read from the appended cassette entries), then two local live checks with the flag on, then the founder decides on switching it on in production.

## 20. Route A verification (2026-09-30): flag-on bench + two local live checks. PASS.
**Flag-on bench** (`ENABLE_ORIGINATOR_REVIEW=true`, `--record-missing`, then a pure replay):
- Recording cost **$0.073 (~6p)**: 18 new Gemini calls (review calls + mapping calls re-keyed by tier changes), no search. 7 cassettes gained entries; none lost any.
- Per claim, flag on vs flag off: identical on 018F, 93DD (alone: 14/1/2), B4A3, 0001, 0003, 0004, 0005. **A3E8: 16/1/1 → 15/2/1**, the new warn being `tier_reporting` 4±4 → 9: primaries the review lowered, as designed (golden counter to widen if the flag goes on by default). 5647/82CF/93DD drift in `--all` as before.
- **Flag-off bench on the patched cassettes: 125/7/10/5 + the same three drifts, identical to before.** The new recordings do not disturb the default path.

**Two local live checks, flag on** (`live_checks.py`; owner payloads in `audit/originator_eval/live_checks/`):
- `ad8aeb92` Python 3.13 free-threading ($0.068, review stage 8.7 s). Kept primary: docs.python.org, python.org release, PyO3's own docs, PyTorch's own announcement. Lowered: two py-free-threading.github.io guide pages (cue: "Most of the content on this page is also covered in the Python 3.13 release notes."), and a user's PyAV GitHub issue (boundary). Both elements `supported`, unchanged.
- `b76825fc` global sea level 1993–2023 ($0.092, review stage 14.6 s). Kept primary: Copernicus C3S, AVISO. Lowered: a climate.us page relaying Climate.gov (debatable: it may be a faithful copy of NOAA's article, which `hosts_original` should keep). Both elements `supported`, unchanged.
- Review adds ~1p per check. Its 9–15 s runs inside classify, which runs beside distil (~10 s), so it may add up to ~5 s of wall time; not yet measured against a flag-off run of the same claim.
- A pre-existing Pydantic warning (`api_metadata` typed `str`, holds a dict) prints during `build_check_response`; not introduced here.

**Spend today on this track: ≈ $1.40 (~£1.10).**

## 21. Switched ON by default and shipped (2026-09-30, founder: "Proceed please. Push also.")
- `ENABLE_ORIGINATOR_REVIEW` default **True**. Rollback: `ENABLE_ORIGINATOR_REVIEW=False` on Railway (no redeploy needed).
- A3E8 golden `tier_reporting` 4 → 9 with a dated note. Corpus README header: **158/13/12/5 + known 82CF drift** (93DD `--all`-only drift; 14/1/2 alone).
- Unit suite **4,311 pass** with the flag on by default. A probe replacing the review's model call showed **no unit test reaches it** except the one test that calls it on purpose, so the default does not put Gemini calls into the suite.
- **Asked "are you POSITIVE it improves the product?" — the honest answer given:** not positive. Measured: badge honesty improves (0/66 originators wrongly lowered, ~80% of relayers lowered, on never-read pages; right pages kept in both live checks). Not proven: any A− grade lift (never run on those records) or reader-visible gain beyond the badge (no element state changed in any replay or live check). Costs: ~1p/check, a few seconds (unmeasured), 5–8% of boundary pages unstable between runs.
- **Watch after deploy:** `originatorReview` receipts and `stage_timings_s.originator_review` on the first real checks; any genuine originator lowered is a regression to read.
- **Later (route B):** fix the classifier's own prompt (the "if unsure, prefer PRIMARY" tie-break and the 300-char read), measured on its own.

## 22. First production check with the review ON (2026-09-30, `ed83167`) — PASS
Check `3fc387b0-2128-416c-ac9f-64adf1922793` (TRU-3FC3-87B0), "The EU AI Act entered into force on 1 August 2024", run by the founder from the dashboard; receipts read with `tru8_get_result_raw`.
- 18 sources, **5 receipts, all `reviewed/relays`, primary → reporting, input `page_opening`**: four artificialintelligenceact.eu pages (home, /the-act/, /implementation-timeline/, /high-level-summary/; an independent institute's site re-presenting the Act) and a sas-dhrh.github.io copyright toolkit page. Each cue is the page's own self-description ("This site exists with the aim of providing helpful, objective information…", "In this article we provide you with a high-level summary of the AI Act…").
- Kept PRIMARY: commission.europa.eu news, digital-strategy.ec.europa.eu, sciencedirect.com. **No genuine originator lowered.**
- The element stays `supported` (4 supports incl. both Commission pages); the review changed badges, not the finding.
- Note: the model named the originator "European Union" in all five; the cues are self-descriptions, not attributions. Correct outcome; the cue rule accepts any verbatim phrase by design (§18).
