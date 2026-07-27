# Claim Integrity — specification loss through extraction atomisation

> **SOT for this problem.** Status ledger + evidence base + design space, in one place,
> DECOUPLING_STATE-style. Read this, not the conversation that produced it.
>
> **Status: CLOSED 2026-07-22 — §5.3 acceptance PASSED on attempt 3 (TRU-32FA-40B0,
> 36.0s, graded B+).** Full arc: floor fixes proven on E323-8862 (B+, causal
> specificity perfect) → e03 root-caused via Railway logs to the recovery timeout
> discarding completed mapping (NOT mapper recall — that hypothesis retracted) →
> lean fix `a0751b7` (35s floor + recovery items scored + extend-after-map) →
> attempt 2 (11F0-F1AE) FAILED, flat bump insufficient (4/4 starved → 42 items →
> died 0.7s pre-mapping) → structural fix `bbe13fa` (phase-split: Phase A budget
> via asyncio.wait, Phase B mapping under own 25s grace never cancelled once
> inputs paid for, 24-item round-robin cap) → attempt 3 with a PARAPHRASED
> sentence (identical text would have replayed the 1h SERP / 6h extract / 24h
> evidence caches — founder catch): all 3 elements directional, challenges-only
> badges, baseline anchored, claim typed causal_interpretive, 0 supports.
> Also closed same day: `7289fa0` P0 (progress-stream NameError from 2521b97 —
> the "stuck check" was UI-only; check had completed).
> **RESIDUAL WATCHES: (1) phase-split deployed but LIVE-UNVERIFIED — verify on
> the next check whose elements starve (Phase A timing / cap / Phase B completes);
> (2) parked next lever, retrieval-side: quantitative time-series pool depth on
> trend claims (GVP eruptions-by-year, USGS quake stats — recovery queries find
> them, main-pass SERP rarely does); (3) dedup-blindness (recovery cannot re-offer
> already-pooled items to the mapper) — real in code, never yet the operative
> defect, do not build speculatively.**
>
> Prior status (2026-07-21): LIVE-VERIFIED — TRU-702E-A68C (prod, 55.6s focused). The
> tectonic sentence ran as ONE INTACT VERBATIM claim, 4 elements incl. the causal
> link as its own element (2 supporting), e02/e03 anchored to "the last 50 years",
> shared 14-source pool with USGS/BGS counter-evidence surfaced (e01 disputed,
> e03 challenged — detection-method explanation). No selection screen (focused).
> vs the morning split-claim run (27F32CF7): 3× "predominantly supported" over
> drifting pools → now the honest mixed landscape. Watch item confirmed again:
> claim typed `empirical` not `causal_interpretive` (cosmetic, no gate cares).
> NOTE 2026-07-21: the fa35465 deploy killed two in-flight checks (57e7dcde,
> f2f97f6e) → stuck "processing" + 2 credits burned; SSE reconnect loop + per-
> stream held DB sessions caused an API brownout (CORS-looking errors). Cleanup
> (mark-failed + refund via railway) + durable guards (SIGTERM fail+refund,
> SSE session release) tracked in OPEN_WORK.
> B (context-carry) + E (recombination) + causal-element prompt rule implemented.
> **Verification evidence (2026-07-21):**
> - Routing controls **4/4** (multi-sentence / question / paragraph stay split; tectonic recombines — no over-merge)
> - Probe re-run: COND 4 causal element **6/6** (prompt rule closed the tectonic miss; that case still types `empirical` — watch item, no downstream gate distinguishes it), anchors 6/6, cap 6/6; COND 3 anchors 5/5, 0 vague windows
> - Unit tests: new `tests/unit/pipeline/test_claim_integrity.py` 18/18; full touched-seam sweep (extract + analyzer + batch + §20 decoupling suites) **160/160**
> - Replay bench: cassettes re-patched (`--record-missing`) for the intentional prompt change; corpus **re-golded with dated in-file notes** (also pays off the owed F7 re-gold); double pure replay → **all 8 observations byte-identical** across fresh processes
> - Bench live behaviour: TRU-B4A3-C42D (mini-budget causal chain) + TRU-C1A0-0004 recombined 2→1 claims as designed; B4A3 decomposed into the full causal chain (spike element + BOTH causal links) with element_resolution 1.0, 12 unique domains
> - **Bench baseline going forward: 147 ok / 2 warn / 4 fail. The 4 fails are ABSOLUTE v3 quality-band floors on retrieval pools (factual_weight/top_domain), NOT golden mismatches.** Attribution confounded 3 ways (07-09 retrieval ships never re-golded + this change + live SERP drift at re-record). Principled note: causal-link elements legitimately retrieve analysis/commentary — the factual-weight floor was calibrated on fragment claims and may need recalibration for recombined causal claims. Regression bar for future commits = no NEW fails vs this baseline. Monitor: B4A3 claim-0 primary items 5→0 (BoE/DMO fetched but excluded by scoring) — sits on the UK-adapter 0-yield ceiling row.
> Opened 2026-07-21 (founder observation on check 27F32CF7). Register pointer: `audit/OPEN_WORK.md` → "Pipeline quality — active".

---

## 1. The problem (founder-observed, code-confirmed)

**Motivating case — check `27F32CF7` (2026-07-21, text mode).** User submitted ONE
causal compound sentence:

> "Compared to the last 50 years, tectonic plate movement is extremely active
> currently, **causing** a large rise in volcanic eruptions and earthquakes"

Extraction atomised it into 3 sealed claims:

| Claim | Kept | Lost |
|---|---|---|
| 01 "Tectonic plate movement is extremely active compared to the last 50 years" | 50-yr baseline | causal role |
| 02 "There is a large rise in volcanic eruptions" | — | 50-yr window, tectonic frame, causal link |
| 03 "There is a large rise in earthquakes" | — | same |

**The causal connective — the user's actual thesis — was never extracted as a claim
at all.** Nothing in the pipeline researched "elevated tectonic activity is *driving*
the rise." Downstream, claims 02/03's elements invented their own vague comparison
windows ("a recent period vs a preceding period") and retrieval drifted (1000 AD
eruptions, Cretaceous plate motion, 1985 Mexico City quake in the pools).

**Founder constraint (LOCKED for this work): the user's claim MUST stay intact —
results must reflect their curiosity/requirement.** Related founder line from the
specificity-gap item: NO scolding screen.

### The three loss points (code refs)

1. **Causal spine dropped at extraction.** `extract.py` Rule 3 (atomic, no
   conjunctions) splits compounds; nothing tells the model a causal link is itself
   a claim (Rule 9's own example "sugar causes diabetes" proves causal claims are
   legal). The split into effect-fragments is LLM judgement, not a hard rule.
2. **Decompose runs blind.** `claim_map_analyzer.py:1121-1127` — `decompose_claim()`
   receives ONLY the claim text. Not the original submission, not sibling claims.
   Fragments that lost their anchor get elements with invented baselines.
3. **Cross-claim URL dedup severs shared evidence.** `runner.py:1575` (Stage 3.6)
   removes a URL from later claims if an earlier claim retrieved it — a source
   addressing BOTH cause and effect appears under only one claim. (Global URL
   tracking is Critical Invariant #1; any change here is dedup *semantics for
   sibling claims*, not removal of global tracking.)

Sealed-claim confirmation: selection (`claim_selector.py`) ranks per-claim
significance only; no inter-claim relationship exists anywhere in the data model,
selection UI, retrieval, mapping, or report. (`related_claims` in `query_answer.py`
is the optional user-query stage, keyword matching — different feature.)

---

## 2. Evidence — claim-integrity probe (2026-07-21)

**Tool:** `backend/scripts/claim_integrity_probe.py` (local-only, live Gemini
extract + decompose, no retrieval/mapping spend). Results dot-file:
`backend/scripts/.claim_integrity_probe.json`. Metrics are mechanical regex on
output text — no LLM judging LLM. Re-run after ANY prompt/routing change here.

**Pool:** 6 compound causal submissions, varied domains, each with explicit
user-stated anchors (timeframe/place) + causal connective (tectonic, food_prices,
arctic_ice, antibiotics, teen_social, water_sewage).

| Condition | Metric | Result |
|---|---|---|
| **1. Current extraction** | causal thesis survives as any claim | **2/6** |
| | all fragments keep full user anchor | 1/6 inputs |
| **2. Current decompose** (bare fragment) | ≥1 element carries user's anchor | **2/7** |
| **3. Candidate B** (fragment + submission as context) | ≥1 element carries user's anchor | **7/7** |
| **4. Candidate E** (intact sentence, one claim) | within 5-element cap | **6/6** |
| | ≥1 element anchored | **6/6** |
| | explicit causal-link element present | **5/6** (\*) |
| | claim_type = causal_interpretive | **5/6** |

(\*) teen_social's causal element read "primary contributing factor to" — the
probe's regex missed it; hand-verified present. Recorded JSON says 4/6 on this
metric for that reason.

**E's one partial miss = the founder's exact case.** Tectonic decomposed intact →
3 elements (cause + 2 effects), ALL carrying the 50-yr anchor, normalised claim
kept "leading to" — but typed `empirical` and no explicit causal-link element.
Fix candidate: decompose-prompt nudge — "when the claim asserts causation, the
causal link is itself an element" — then re-run this probe.

**Exemplar of E working (water_sewage):** elements = (1) investment fallen since
1989, (2) sewage discharges risen since 1989, (3) "The fall in investment …
**caused** the rise in sewage discharges" — the causal link as its own testable
element, typed `causal_interpretive`.

---

## 3. Design space

| Option | What | Probe verdict | Scale |
|---|---|---|---|
| **A** | Extraction preserves causal spine (link becomes a claim) | untested as prompt change; E subsumes it for text mode | small |
| **B** | Carry original submission into decompose as context | **works: 2/7 → 7/7 anchor recovery** | small-medium |
| **C** | Claim-relationship metadata (typed edges, UI, report) | not needed if E lands | large |
| **D** | Rethink URL dedup for sibling claims | shrinks if E lands (siblings become elements, one pool) | medium |
| **E** | Single-thesis text submissions stay ONE intact claim; decompose atomises at element layer | **strongest: 6/6 cap, 6/6 anchored, 5/6 causal element** | **large — this doc exists because of E** |

### Reinforced recommendation (2026-07-21, evidence above)

1. **E primary** for single-thesis text submissions. The only option that satisfies
   "claim stays intact" *structurally*: the user's thesis IS the claim; atomisation
   happens at the element layer where connectivity is guaranteed by design (one
   shared evidence pool, cross-element mapping, one orientation across cause AND
   effects). Contract-legal: `causal_interpretive` has existed in the LOCKED
   claim-map contract since Track B; 1-5 elements is the designed decomposition
   layer. E is currently starving that claim type of its natural input.
2. **B complement** for article mode, where splitting into separate claims IS
   correct (a 12-claim article is many theses) — context-carry fixes decompose
   blindness there. Also covers text mode wherever extraction still splits.
3. C/D deprioritised pending E.

---

## 4. Open design questions (the reason this is a doc, not a register row)

1. **Routing rule** — when is a text submission "single-thesis"? Candidates:
   sentence count, extraction-count-plus-derivation check (all claims from one
   sentence → recombine), or an extraction-prompt mode for text inputs. Must NOT
   scold or block (founder). Article mode unaffected.
2. **Selection-screen UX** — E shows ONE intact claim where today three cards
   appear unconnected (the founder's original observation). Selection gate remains
   (ALL input modes pause — verified live 2026-07-06); what does the card show —
   the thesis + its elements preview?
3. **Decompose prompt nudge** — causal-link-as-element (see §2 miss). Re-probe after.
4. **>5-part compounds** — element cap is 5 (contract, hard). Overflow rule needed
   (fall back to split? merge effects?).
5. **§20 decoupling interaction** — `should_apply_grounds` (flag-OFF, see
   `audit/DECOUPLING_STATE.md`) also intervenes at the extract/decompose seam for
   opinion claims. E's routing must compose with grounds-decompose, not race it.
   An opinionated causal compound ("X is a disaster and it's causing Y") hits both.
6. **Credits/quick mode/agent API** — 1 claim vs 3 changes retrieval volume
   (3 claims × 2 elements × 2 queries → 1 claim × ~3-4 elements × 2 queries),
   1 credit either way. Check quick-tier + `/agent/` assumptions about claim counts.
7. **Specificity gap relationship** — the parked item (2026-07-20) is user-vague
   input; THIS is pipeline-*induced* vagueness (user specified; atomisation
   discarded). E fixes the induced case; the parked item remains parked.

## 4a. BUILD PLAN (LEAN — founder-directed 2026-07-21; supersedes any fatter reading of §4)

Efficiency mandate: no new UI (selection screen already renders N cards — E just
sends 1; zero frontend work), no test overkill, ~40-60 lines product code total.

| # | Change | Where | Size |
|---|---|---|---|
| 1 | B: optional `source_context` on decompose + one prompt context line, wired from runner + call-sites | `claim_map_analyzer.py` | ~15 lines |
| 2 | E: mechanical post-extraction recombination — text mode + all claims from one sentence → original carried as ONE claim; uncertain → today's split (fail-safe) | `runner.py` extract seam | ~20 lines |
| 3 | Causal-link-as-element | `DECOMPOSITION_PROMPT` | 1 sentence |
| 4 | Nothing else. No overflow guard (parse caps at 5 — watch item). No UI. No dedup change. No agent-API sweep (claim count already varies 1-12). | — | — |

Verification (proportionate): 2-3 multi-thesis controls in the probe (**over-merge
is the one new risk E creates**), unit tests on the routing function, existing
decoupling suite covers the §20 seam while flag-OFF, `replay_bench --all` once
pre-commit, one live tectonic resubmit as end-to-end proof. Ships as 1-2 commits.

## 4c. NEXT — RAISE THE FLOOR (founder-directed 2026-07-21; the active thread)

Founder decision after the B− review: **raise the floor before the ceiling.**
The worst-case outputs (starved element presented as "nothing found", weak
generic evidence carrying a "+SUPPORTED" badge on a specific causal element,
badge contradicting the orientation prose) harm trust more than a higher
ceiling helps. Work = the five findings in §4b, floor-first priority:

| Priority | Finding | Why it's floor |
|---|---|---|
| 1 | Element-level coverage recovery (§4b.1) | A user is told "no comparison exists" when the data does — worst possible output |
| 2 | e04 generic-vs-specific causal mapping (§4b.2) | The report's only "+SUPPORTED" badge sat on a K-12 worksheet — misleads badge-readers |
| 3 | Challenges-only state presentation (§4b.3) | Badge contradicts prose in the same element card |
| 4 | Decompose anchor drop on the subject element (§4b.4) | Comparison claims must keep their baseline in EVERY element that asserts the comparison |
| 5 | Ownership-grouping note refinement (§4b.5) | Understates legitimate academic diversity (lower priority — the note errs toward caution) |

Approach discipline (standing): mechanical fixes over prompt-only (NF-11),
probe + replay-bench verification per §5, efficiency mandate per §4a — small
hard code, no speculative machinery. Design review with founder BEFORE build
(this is a quality-semantics thread, not a bug-fix thread).

## 4d. FLOOR DESIGN — founder-APPROVED 2026-07-21 (all 5; build handed to Opus same day)

> **✅ SHIPPED + PUSHED 2026-07-21 `9ca94d3..cad0020`** (4 commits: recovery trigger /
> mapping specificity + baseline anchoring / badge + portfolio note / verify-pass
> completeness fix). Verify pass (Fable) found + closed 3 gaps pre-push: completion
> AND recovery mapping passes were serialising elements WITHOUT the [CAUSAL LINK] tag
> (rule inert on exactly the path fix 1 routes to — all FOUR prompt builders now
> armed, unit-tested); Seeker UnknownElementCard badge now passes basis
> (RelatedClaimCard deliberately NOT — its cross-user payload is privacy-safe
> description+state only; adding basis would leak other users' evidence structure).
> Accepted build deviations: (a) "starved" = has-refs-but-0-directional; 0-ref
> elements stay with the unresolved trigger / Seeker (no regression vs before —
> residual watch: a lone 0-ref element on an otherwise-healthy ≥3-element claim
> still doesn't trigger recovery); (b) payload field is `rule_applied` not `rule`.
> **Gates:** pipeline 966/0 + vitest 77/77 + tsc clean (verifier-run at HEAD);
> probe causal 6/6, tectonic subject element now carries "compared to the last
> 50 years" (verified from probe JSON, all 3 assertion elements anchored);
> fix-2 live A/B (scripts/causal_specificity_eval.py, local-only): legitimate
> specific supports 4/4 unchanged, generics → context/unmapped, demotion backstop
> correctly NOT built; **bench 147 ok/3 warn/3 fail — fails DOWN from the 4-fail
> baseline, no NEW fails. NEW BENCH REFERENCE going forward: 147/3/3.**
> Remaining acceptance (§5.3): live tectonic re-run post-deploy — e02 gains
> directional evidence, e04 not +Supported on worksheet-grade items, e03 reads
> "− Challenged", e01 keeps the 50-yr baseline.
>
> ✅ **INCIDENT CLOSED 2026-07-22 (root cause found in Railway logs — NOT a stuck
> check):** the founder's check WAS TRU-E323-8862 and it completed normally in
> 53.2s at 17:58:22 UTC. The rolling "extracting claims" UI was a **P0 prod bug
> introduced by `2521b97` itself**: the SSE-session change referenced
> `async_session` inside `stream_check_progress` (checks.py:2043) without a
> function-local import → `NameError` on EVERY `GET /checks/{id}/progress`
> reconnect (initial-submission streams use a different path and kept working).
> The founder's tab reconnected at 18:02:56, got a 500, and rolled forever on
> the last cached stage over a finished check. **Hotfixed `7289fa0`** (import +
> regression test that executes the real handler through the ASGI stack —
> proven to FAIL on pre-fix code). Inflight-guard note from triage: the
> registry DOES cover Phase 1 — `inflight_register` is the first line of
> `run_pipeline_and_save`, wrapping extract onward.
>
> **SAME LOGS closed the §5.3 gap too (fix `a0751b7`, 2026-07-22):** on E323,
> recovery fired correctly (2/4 starved), the query planner found the e03
> bullseyes (USGS/BGS/OWID/aa.com.tr), 20 items retrieved+classified — then
> the 20s recovery timeout cancelled the mapping call 5.4s in (0 recovered),
> and the already-pooled items shipped unscored+unmapped (the report's junk
> sources: recovery bypassed the SCORE stage entirely). Bug-B's own class
> recurring at n=1. Lean fix (founder-approved): floor 20→35s
> (`RECOVERY_TIMEOUT_SECONDS`, env rollback lever); recovery items now pass
> the relevance scorer (main-pass `llm_relevance` receipt shape); pool-extend
> moved AFTER the mapping attempt. Two review-pass hypotheses RETRACTED by the
> logs: "main-mapper recall miss" (mapper never saw #25) and
> "dedup-starves-recovery" (real in code, but NOT the operative defect — parked
> as a watch item, not built). Bench 147/3/3 = reference exactly, zero drift.
> THEN re-run the §5.3 acceptance check (still owed).

Efficiency mandate re-affirmed at approval: fewest lines achieving the correct
outcome. Traces (3 parallel agents, line-verified) behind each mechanism.

| # | Finding | Approved mechanism | Size |
|---|---|---|---|
| 1 | Element starvation invisible | New trigger: element with 0 supports AND 0 challenges (directional==0) → recover. Drop the `len(selected_claims) <= 2` skip (`runner.py:2303`); qualifier = existing 0.4 unresolved ratio OR any starved element; extend element selector in `_recover_single_claim` (`runner.py:2378`). Downstream machinery (`retrieve_for_elements` + `map_evidence_to_specific_elements` + caps) UNTOUCHED — it is already element-level; only the trigger was claim-level and `unresolved`-string-only (a context-only element derives `contextual`, invisible today). Founder accepted: recovery now also reaches ordinary 1-2 claim checks; +10-20s only on checks with a starved element. | ~15-20 lines, runner.py only |
| 2 | Generic-mechanism +Supported on causal elements | Mechanical causal-link tagger (regex on element description: caus/driving/leads to/because of/contributing factor — same detection the probe uses) → `[CAUSAL LINK]` marker on the element line in BOTH mapping prompts + one SPECIFICITY CHECK rule: general-mechanism / educational / reference material maps as context, not supports, on causal-link elements. LLM keeps the genericity judgement (no mechanical signal exists — no element type, no educational/reference evidence type, content_basis is capture-completeness); mechanical part is gating WHERE the rule applies (cannot leak onto empirical elements). NF-11 discipline: verify via before/after mapping sweep incl. adversarial pool; CONTINGENCY (designed, NOT built): deterministic supports→context demotion at the 3 pre-state-derivation insertion points (`_parse_mapping_response` ~1847 / completion ~2098 / recovery ~2252) — build ONLY if sweep shows the rule ignored. | ~10 lines + 2 prompt sentences |
| 3 | Challenges-only badge "± Disputed" contradicts prose | Presentation-only. `{supports:0, challenges:N}` already tags `rule="all_challenges"` in `basis.state_derivation` (`claim_map_analyzer.py:743-745`) and basis rides the payload generically. Both badge components + PDF template render "− Challenged" when `state=='disputed' && rule=='all_challenges'`; label in shared/constants. State stays `disputed` — NO enum/contract change, no migration, historical checks render correctly. Build-time check: confirm `rule` survives into payload (else 1-line backend add). Founder approved label "− Challenged". | ~15 lines, frontend + PDF |
| 4 | Comparison baseline dropped from subject element | One decompose rule (both prompts): comparison claims → EVERY element asserting the compared quantity/trend states the baseline explicitly. (No anchoring rule exists today; `_context_block` is empty for E-recombined claims since context==claim text.) Probe anchor metric is the mechanical check: tectonic ≥3/4 anchored incl. e01, no pool regressions. | 1-2 prompt sentences |
| 5 | nature.com "single website" note | `PORTFOLIO_HOSTS` set (nature.com, sciencedirect.com, springer.com, onlinelibrary.wiley.com, tandfonline.com, academic.oup.com, journals.plos.org) → single-outlet note detail becomes "All via a single publisher platform, which may host multiple journals." No counting change. BOTH parity-locked files (`support_structure.py` + `support-structure.ts`) + parity test. Founder approved host list. | ~10 lines ×2 |

Packaging: 3 commits — (1) recovery trigger; (2) both prompt changes together
(one cassette `--record-missing` re-patch; recovery change may also surface
cassette misses where corpus cases now trigger recovery); (3) badge + note
(display only). Gates per commit: probe holds/improves, `replay_bench --all`
no NEW fails vs 147 ok/2 warn/4 fail, unit tests (tagger, trigger, parity).
Final acceptance: live tectonic re-run — e02 gains directional evidence
(OWID/GVP class), e04 not +Supported on worksheet-grade items, e03 reads
"− Challenged" matching prose, e01 carries the 50-yr baseline.

## 4b. First live report review (TRU-702E-A68C, founder-requested honest grade 2026-07-21): OVERALL B−

Careful-reader outcome is scientifically CORRECT (premises contested with
BGS/USGS/Nature receipts; morning split run had said "supported" ×3). Five
findings, none built yet — review before acting:

1. **Element-level coverage recovery (worst, grade D on e02).** Recovery
   triggers on low-coverage CLAIMS; one intact claim with 16 refs looks
   healthy while e02 (eruption rise) starved at 1 context item — although
   OWID significant-eruptions + weekly GVP-style reports directly answer it
   and THIS pipeline retrieved both in the same-day split run. Intact-claim
   mode needs an element-level recovery trigger.
2. **e04 scope looseness.** Causal element "+SUPPORTED" by a grades-6-12
   worksheet + Statista infographic — generic-mechanism evidence carrying a
   SPECIFIC causal-trend badge whose premises e01-e03 just contested. Mapper
   SCOPE CHECK should treat generic-mechanism items as context on
   specific-causal elements.
3. **Badge vs orientation mismatch.** e03 badge "± DISPUTED" with 0 supports;
   orientation prose correctly says "challenged with none supporting".
   Challenges-only needs its own presentation (or unresolved-with-challenges).
4. **e01 anchor drop.** The plate-motion element lost "compared to the last
   50 years" (survived in e02/e03). Decompose wording nudge candidate.
5. **nature.com = "single website" thin-sourcing note** — three distinct
   Nature-portfolio journals grouped as one outlet; mechanically true,
   epistemically misleading. Ownership-grouping refinement candidate.
   Also noted: no geodetic/GPS plate-rate data in e01's pool — the most
   direct evidence class for the question (retrieval-quality thread).

## 5. Verification loop for any build

1. `python -m scripts.claim_integrity_probe` — anchor/causal metrics must hold or improve.
2. `python -m scripts.replay_bench --all` before any pipeline-quality commit (standing rule).
3. Live re-run of the 27F32CF7 input end-to-end; expect one intact claim, causal
   element, anchored windows, shared evidence pool (USGS earthquake→eruption
   source mapping onto the causal element is the acceptance smell-test).

## 6. What NOT to do

- Don't ship prompt-only for the routing rule without a mechanical backstop
  (NF-11 lesson: `feedback_nf11_prompt_only_failed`).
- Don't remove global URL tracking (Critical Invariant #1) while touching D.
- Don't resurrect C (relationship metadata) unless E is rejected — it's the
  heavyweight path to the same outcome.
- Don't conflate this with §20 opinion decoupling in naming or docs — this is
  extraction **atomisation** integrity; decoupling is opinion→grounds. Both live
  at the same seam, hence §4.5, but they are different mechanisms.
