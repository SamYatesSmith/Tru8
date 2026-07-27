# V1 Quality Plan — 2026-05-06 (rev. 3)

## Decision

V1 ships with **Option 1: best quality on 1-3 claims, advisory beyond**.

Quality is **multi-dimensional and judged on what reaches the user**, not on retrieval-side efficiency. Mapping rate is treated as a diagnostic, not a quality criterion.

Architectural alternatives (per-claim mapping, hybrid batching) deferred to Phase 2.

## Build directive — "no half measures"

User directive 2026-05-06: ship comprehensively, not quickly. Phase 1 has no deadline. Each deliverable lands when it genuinely improves accuracy, variation, reliability, or consistency — and not before. Acceptance is verified by live re-run of the 7 test checks, not just unit tests passing.

Implications:
- Bug A is not "tighten the prompt" — it's the prompt + mechanical post-processing + claim-quality gate + few-shot regression set, all locked behind a corpus that proves it works.
- Bug D (demote) is not a one-line cap — it's cap + receipt + log + Librarian-view interaction tested.
- Bench guardrails are not "add 3 signals" — it's 6 V3 signals captured, calibrated, locked, AND a new 4-claim corpus entry that exercises the multi-claim cascade.
- Acceptance is a live re-run, not a green CI badge.

---

## Findings — 2026-05-06 live tests (7 checks)

Seven checks across Health, Finance, Climate, Sports, Politics. Measurements from `pipeline.log`.

| Check | Domain | Claims | Retrieved | Scorer kept | Tier mix (P/R/C) | Mapped/Total | Map rate (diag) | Coverage Rec | User verdict |
|---|---|---|---|---|---|---|---|---|---|
| TRU-7C40 (mammogram) | Health | 4 | 34 | 13 (38%) | 18 / 0 / 5 | 4/23 | 17% | TIMED OUT 20s | "inconsistent" |
| TRU-5411 (BlackRock) | Finance | 4 | 8 | 4 (50%) | 2 / 12 / 0 | 8/14 | 57% | TIMED OUT 20s | "poor" |
| TRU-8EBE (Ozempic) | Health | 2 | 23 | 18 (78%) | 5 / 6 / 7 | 6/18 | 33% | Skipped (<3) | "impressive" |
| TRU-A755 (GBR bleach) | Climate | 2 | 24 | 23 (96%) | 11 / 11 / 1 | 16/23 | 70% | Skipped (<3) | (unstated) |
| TRU-EF3F (Sha'Carri) | Sports | 2 | 22 | 9 (41%) | 4 / 3 / 3 | 9/10 | 90% | Skipped (<3) | (unstated) |
| TRU-15A8 (Russia $) | Finance | 4 | 35 | 25 (71%) | 11 / 7 / 9 | 11/27 | 41% | TIMED OUT 20s | (unstated) |
| TRU-B3A4 (UK elec) | Politics | 5 | 43 | 13 (30%) | 17 / 2 / 6 | 12/25 | 48% | Partial | (unstated) |

### Mapping rate by claim count

| Claim count | Observed | Median |
|---|---|---|
| 2 | 33%, 70%, 90% | 70% |
| 4 | 17%, 41%, 57% | 41% |
| 5 | 48% | 48% |

**Important caveat:** mapping rate is not a clean quality signal. A claim retrieving 23 sources and mapping 6 high-quality items can still be excellent — the 17 unmapped items may have been redundant or off-target. Mapping rate is now treated as a diagnostic measurement only.

---

## Diagnosis

Four contributing failure modes plus one structural reframe.

### Bug A — Extractor over-decomposition AND claim-quality validation

Articles with one substantive claim split into 3-4 micro-claims. Some include study-design details, sub-statistics, parallel facts that aren't independently verifiable from web evidence.

- TRU-7C40: ONE 2020 Nature study claim → 4 claims (one false-pos %, one UK count, one US count, one false-neg %). Three are study-design details with no separable web evidence.
- TRU-5411: ONE comparative paragraph → 4 claims. Two pairs are connected facts.
- TRU-8EBE: TWO genuinely independent claims correctly extracted.

**Files:** `backend/app/pipeline/extract.py`

**Approach:** tightened prompt + mechanical merge rule + claim-quality gate (weak-anchor sub-statistic claims merge into parent).

**Acceptance:** TRU-7C40 → ≤2 claims; TRU-5411 → ≤2; TRU-8EBE unchanged at 2.

### Bug B — Coverage recovery has fixed 20s budget (CONFIRMED at scale)

`runner.py` `RECOVERY_TIMEOUT_SECONDS=20` regardless of claim count. **Confirmed today on TRU-7C40, TRU-5411, TRU-15A8** (all timed out). TRU-B3A4 ran partial recovery.

**Approach:** scale per claim — `RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 7`, total = `qualifying_claim_count × per_claim`.

**Acceptance:** no silent timeouts on TRU-5411 / TRU-7C40 / TRU-15A8 re-runs.

### Bug C — Mapper batch capacity (REDUCED scope)

Mapping rate drops from 70% (2 claims) → 41% (4 claims) → 48% (5 claims). The drop is real but **mapping rate is not a quality signal**. Bug C is acknowledged via the soft cap at 3, not fixed architecturally in V1.

### Bug D — Domain concentration (NEW)

TRU-B3A4 had **Wikipedia 12 of 25 items (48%)**. The classifier called them primary via LLM override, inflating "primary count" misleadingly. For a UK election claim, primary sources should be ONS, Parliament, Electoral Commission.

**Files:** `backend/app/pipeline/runner.py` (analyzer input stage) or `evidence_classifier.py`.

**Approach:** per-claim domain share capped at 35%. Excess items demoted to commentary.

**Acceptance:** TRU-B3A4 re-run shows no single-domain share >35% per claim.

### Reframe — Quality is measured on mapped output, not retrieval pool

**The pivot:** what the user sees is the mapped set. Quality should be measured there. The retrieval pool is internal. Mapping rate measures efficiency (cost/recovery), not quality.

This reframes the entire acceptance framework — see "Quality framework V3" below.

---

## Why the bench missed all of this

Five blind spots:

1. Corpus has no 4-claim entry (max 3 at TRU-B4A3-C42D).
2. `b3_receipts.shown / unmapped` not captured.
3. `[COVERAGE RECOVERY] Timed out` logged but not captured.
4. Tier-mix-appropriateness not signal at all.
5. **Mapped-set quality** (unique domains, Wikipedia share, factual weight) not captured because the log line didn't exist before this revision.

(5) addressed by `[B3 QUALITY]` log enhancement landed alongside this plan.

---

## Quality framework V3 (six dimensions, mapped items only)

**Quality is judged on what the user sees.** Mapping rate is diagnostic only.

| Dimension | What it captures | Excellent | Good | Mediocre | Poor |
|---|---|---|---|---|---|
| **Unique domains per claim** | "Sparseness" — your gut for variety | ≥10 | ≥7 | 5–7 | <5 |
| **Top single-domain share** | Single-source dominance | ≤25% | ≤30% | 30–45% | >45% |
| **Wikipedia share** | "Too much Wikipedia" — your gut | ≤15% | ≤25% | 25–40% | >40% |
| **Factual weight share** | academic + official_statement + data | ≥40% | ≥25% | 15–25% | <15% |
| **Authoritative anchor** | ≥1 named primary source for the domain | ≥2 | ≥1 | weak | none |
| **Element resolution** | % elements with state ≠ unresolved | ≥70% | ≥50% | 30–50% | <30% |

### Authoritative anchor named-list (V1)

| Domain | Expected anchors |
|---|---|
| Finance/UK | ONS, Bank of England, Companies House, FCA, HMT |
| Finance/US | SEC EDGAR, FRED, Treasury, Federal Reserve |
| Politics/UK | Hansard, GOV.UK, Electoral Commission, ONS, Parliament Bills |
| Politics/US | GovInfo.gov, Library of Congress, Federal Register |
| Climate / Science | NOAA, IPCC, NASA, peer-reviewed journals (Nature/Science) |
| Pharma / Medical | PubMed, regulator (FDA / EMA / MHRA), Cochrane, named medical journal |
| Sports | Governing body (World Athletics, FIFA, UEFA) + official results database. **V1 limitation:** no dedicated sport adapter — coverage is web-search only. Sports claims will tend to score lower on unique_domains and Wikipedia share. Sport adapter add is Phase 2. |
| History / Archaeology | Library of Congress, JSTOR (via OpenAlex), Internet Archive, named museum/institution |

### Verdict rule

A check is **"Good" if it scores Good or better on all six dimensions**. **"Excellent"** requires Excellent on at least four of six. Failing any one to Mediocre = Mediocre overall. Failing any one to Poor = Poor overall.

### What we deliberately do NOT measure

- **Whether the claim is true.** "We organise; you decide."
- **Whether each individual source is itself accurate.** We classify by tier and type, not content correctness.
- **Whether better evidence exists in the world that we missed.** We surface what we retrieve.

The framework measures the **quality of the evidence landscape**, not the truth of the claim.

---

## Approximate V3 scoring of today's 7 checks

Approximate because mapped-set breakdown wasn't logged until today's enhancement. Re-runs post-enhancement will give exact numbers.

| Check | Verdict | Driver |
|---|---|---|
| TRU-7C40 mammogram | **Mediocre** | Mapping pulled too few items (only 4 mapped); element resolution likely low |
| TRU-5411 BlackRock | **Poor** | No anchor — 0 primary on Finance/US claim, no SEC, no IR |
| TRU-8EBE Ozempic | **Good** | PubMed + EMA anchor present; 18 unique domains; balanced tier mix; user "impressive" matches |
| TRU-A755 GBR bleaching | **Good or Excellent** | 11 primary tier; appears varied; needs re-run for exact figures |
| TRU-EF3F Sha'Carri | **Mediocre** | Only 6 unique domains; Wikipedia 30% share; sparse |
| TRU-15A8 Russia | **Good** | SIPRI ×6, ONS ×5, 15 unique domains; primary anchor present |
| TRU-B3A4 UK election | **Poor** | Wikipedia 48% share fails domain dominance; no Hansard or Electoral Commission anchor |

This roughly matches user verdicts where given (8EBE good ≈ user "impressive"; 5411 poor ≈ user "poor"; 7C40 mediocre ≈ user "inconsistent").

---

## Phase 1 — V1 quality floor

Six deliverables. Log enhancement (#0) is the prerequisite that lets the rest measure honestly.

### 0. Log enhancement — `[B3 QUALITY]` per-claim signal capture (LANDED)

`backend/app/pipeline/runner.py` — added `_compute_claim_quality_signals` + per-claim `[B3 QUALITY]` log emission after `[B3 RECEIPTS]`.

Per-claim log format:
```
[B3 QUALITY] claim=N mapped=M unique_domains=K top_domain=X@Y% wikipedia=Z%
factual_weight=W% element_resolution=R% tier_mix={...} type_mix={...}
```

Status: **DONE this session** (commit pending). Regression tests pass.

### 1. Extractor over-decomposition + claim-quality fix (Bug A)

`backend/app/pipeline/extract.py` — prompt + mechanical post-processing.

- Tightened prompt with methodology-detail rule.
- Mechanical merge rule for shared-subject claims.
- Claim-quality gate: weak-anchor claims merge into parent.

**Acceptance:** TRU-7C40 → ≤2 claims; TRU-5411 → ≤2; TRU-8EBE unchanged at 2.

### 2. Soft cap at 3 in claim selection UI

`web/components/claim-selection/`

When extractor produces >3 claims, surface advisory note + visual divider. Top 3 pre-checked.

**Acceptance:** copy unambiguous; advisory items visibly differentiated.

### 3. Coverage recovery timeout scaling (Bug B)

`backend/app/pipeline/runner.py` — `RECOVERY_TIMEOUT_SECONDS_PER_CLAIM = 7`.

**Acceptance:** no silent timeouts on TRU-5411 / TRU-7C40 / TRU-15A8 / TRU-B3A4 re-runs.

### 4. Domain concentration cap — DEMOTE (Bug D)

`backend/app/pipeline/runner.py` (analyzer-input stage) or `evidence_classifier.py`.

**Decision: DEMOTE, not hide.** Mission alignment with "we organise; you decide" + "no hidden curation, every exclusion has a receipt."

**Implementation spec:**
- After classification + B3 receipts, per claim, compute single-domain share on `receipt_status='shown'` items.
- If any domain's share > 35%, sort that domain's items by `relevance_score` ascending. Demote the lowest-relevance items until share ≤ 35%.
- Demoted items get: `tier='commentary'`, `evidence_type='analysis'`, `classification_method='domain_concentration_cap'`, `exclusion_reason=None` (NOT excluded — still shown), and a new field `receipt_note='demoted: domain dominance'` for UI surfacing.
- Items are NOT removed from the user view. The Librarian view's tier×type heatmap then reflects the honest authority shape.
- Log line per demotion: `[DOMAIN CAP] claim={pos} domain={d} pre_share={X}% post_share={Y}% demoted={N}`.

**Acceptance:** TRU-B3A4 re-run shows no single-domain share >35% per claim AND demoted items still appear in the evidence list with the receipt note visible in the Librarian view.

### 5. Bench guardrails (V3 signals + 1 new corpus entry)

`backend/scripts/replay_bench/capture.py` + corpus.

- Capture all 6 V3 signals per claim from `[B3 QUALITY]` log line.
- Hard invariants per claim:
  - `unique_domains ≥ 5` (Mediocre floor; Poor would FAIL)
  - `top_domain_share ≤ 0.45` (Poor would FAIL)
  - `wikipedia_share ≤ 0.40` (Poor would FAIL)
  - `factual_weight_share ≥ 0.15` (Poor would FAIL)
  - `element_resolution ≥ 0.30` (Poor would FAIL)
  - `coverage_recovery_timed_out == False`
- Tolerant counters per claim for the same signals — track drift toward Mediocre.
- Add a 4-claim corpus entry post-Bug-A-fix.

**Acceptance:** bench fails if any V3 signal regresses past its Poor floor; tier-mix or factual-weight drift produces warn.

---

## Phase 1 sequencing

Order matters. Each step builds on the prior; the bench guardrails go last so they lock the *fixed* behaviour, not the buggy baseline.

| Step | Deliverable | Status |
|---|---|---|
| 0 | `[B3 QUALITY]` log enhancement | DONE 2026-05-06 `82ea722` |
| 1 | **Bug A — extractor over-decomposition merge** | DONE 2026-05-07 `2deb174` (live-verified) |
| 2 | **Bug B — coverage recovery timeout scaling** | DONE 2026-05-07 `c132704` |
| 3 | **Bug D — domain concentration cap (demote)** | DONE 2026-05-07 `76e8c1d` |
| H1 | Hotfix — `classification_method` varchar(20)→varchar(64) | DONE 2026-05-07 `8b83d7b` (closes truncation regression that surfaced from Bug D + 3 pre-existing B3 floor values) |
| 4 | **Soft cap at 3 in claim selection UI** | NEXT (frontend, parallel) |
| 5 | **Bench guardrails — V3 signals + 4-claim corpus entry + `[DOMAIN CAP]` matcher** | After Step 4 |
| 6 | **Acceptance live re-run** — full V3 verdict on all 7 checks | Final gate |
| 7 | **Marketing/landing copy update** | Post-acceptance |

After step 6 passes, V1 is ready to ship.

### Live verification (2026-05-07) — partial

Bugs A/B/D were live-verified end-to-end across the same 7 inputs on the dashboard (TRU-AF28-0162, TRU-AE6C-EBDF, TRU-B05F-C945, TRU-217C-41E5, TRU-4A89-F795, TRU-ED9B-BC49, TRU-7D80-1F63). All completed without crashes. Bug A merge fired correctly on 3 of 7 (BlackRock 4→2, Russia 4→1, UK election 5→2); the other 4 saw the LLM extract ≤2 claims directly so Bug A was a correct no-op. Bugs B and D had no fire conditions on the 7 inputs (recovery skipped at ≤2 claims gate; no domain crossed 35% primary-tier dominance) — both correct as defensive structural fixes, not regressions. **Step 6's full V3-verdict acceptance** still requires the Step 5 bench instrumentation; today's verification is "no crash + Bug A behaviourally correct".

### Two open issues surfaced during live verification — out of V1 plan scope

1. **Silent claim-dedup ImportError** — `_deduplicate_similar_claims` in `extract.py:686` imports `get_embeddings` from `app.services.embeddings`, but that symbol does not exist on the module. Production catches the ImportError and silently returns claims unchanged. The cosine-≥0.85 dedup pass has been a no-op for an unknown duration. Bug A papers over it for redecomposition cases but a truly-duplicate LLM emission would now flow through to merge as `"foo. foo."`. Needs its own commit.

2. **Naive merged-text concatenation reads as duplicate** — `_merge_claim_group` joins claim texts with `". "` separator. When merged sentences share a long prefix (e.g. *"Russia's military spending..."* × 4 on TRU-B05F-C945), the result reads as a repetitive paragraph even though the facts are distinct. Real UX problem. Two paths: synthesise a parent sentence via small LLM call, or expose the first sentence + show the rest as a "details" line. Requires user decision on V1 vs V2 placement.

---

## Phase 2 — post-launch, data-gated

- Distribution of substantive claim count + V3 signal medians across first N production checks.
- If 4-5-claim articles >5% of usage AND any V3 dimension <Good consistently → ship Option C (mapper batching).
- API adapter `prepare_query` audit (Mass Eye and Ear, Google Health, BlackRock IR, SIPRI).
- SEC EDGAR adapter (Track P P2) — would have made TRU-5411 Good.
- Wikipedia LLM-promotion-to-primary audit.
- Authoritative anchor list expansion (more domains, more named sources).

---

## Acceptance criteria for V1 ship

- [x] **`[B3 QUALITY]` log emission** — DONE `82ea722`.
- [x] **Bug A fix landed** — DONE `2deb174`; live-verified 2026-05-07 on the 7 diagnostic checks (3 fired, 4 stochastic-no-op, 0 regressions).
- [ ] Soft cap UI shipped with clear copy and visual differentiation.
- [x] **Coverage recovery scales with claim count** — DONE `c132704`. No silent timeouts on 3+ candidate runs (floor 20s preserves 1-2 candidate behaviour). Live verification didn't exercise the path (all 7 ≤2 claims after Bug A merge).
- [x] **Domain concentration cap applied** — DONE `76e8c1d`. Demotes excess primary/reporting items at any domain whose share >35% per claim, idempotent. Hotfix `8b83d7b` widened `classification_method` varchar(20)→varchar(64) after the column truncation surfaced live. Cap had no fire conditions on the 7 live checks (pool sizes too small / no ≥36% concentration).
- [ ] Bench: V3 signals captured; Poor-floor invariants locked; 4-claim corpus entry passing.
- [ ] All 5 (now 6) corpus claims pass post-Phase-1.
- [ ] **Live re-run of all 7 today's test checks lands at "Good" or better on the V3 framework.**
- [ ] Marketing/landing copy reflects 1-3 claim sweet spot.

---

## Deliberately NOT in V1

- Option B (per-claim mapping) and Option C (hybrid batching).
- API adapter `prepare_query` deep audit.
- New adapter builds (SEC EDGAR, Track P).
- Wikipedia LLM-promotion-to-primary audit.
- Tier-mix-shape *enforcement* (vs measurement). V1 measures and warns.
- "Up to 5 claims" promise.

---

## Open questions for iteration

### Resolved 2026-05-06

1. ~~`factual_weight_share` includes `data` type?~~ **Yes** — academic + official_statement + data.
2. ~~`element_resolution` threshold?~~ **Lowered marginally** — Good ≥50%, Excellent ≥70%. Acknowledges Seeker-view legitimacy of unresolved elements without removing the signal entirely.
3. ~~Sports needs domain-specific thresholds?~~ **No.** Sports' lower scores reflect a real V1 limitation (no dedicated sport adapter — web-search only). Logged as Phase 2 work; V1 accepts that Sports claims will tend to score lower on variety dimensions.

### Resolved 2026-05-06 (cont'd)

4. ~~Soft cap at 3 or 4?~~ **3.** Conservative ship; if production data shows Bug A fix robust at 4 substantive claims, raise to 4 in Phase 2.
5. ~~Domain concentration: demote or hide?~~ **Demote.** Mission alignment: "no hidden curation, every exclusion has a receipt." Items remain visible; tier reclassified honestly. The Librarian view's tier×type heatmap then shows the real authority shape. Implementation: when single-domain share >35%, demote excess (lowest-relevance first) to tier=commentary, type=analysis, with `classification_method='domain_concentration_cap'`.
6. ~~4-claim corpus entry — real or synthetic?~~ **Real.** Use one of today's 4-claim checks (TRU-15A8 Russia is the strongest candidate — primary-anchor present, Bug B confirmed, multi-domain sourcing).
7. ~~Phase 1 time budget?~~ **No deadline.** User directive: "do things properly. No half measures. We need well-considered, comprehensive implementations that genuinely make the product BETTER — improving accuracy, quality, variation, reliability, consistency." Phase 1 ships when all six deliverables pass acceptance and re-run of the 7 test checks lands at Good or better.

### Still open

(none — all V1 framework decisions locked.)

---

## Risks

- **Bug A is prompt-driven** — same fragility as NF-11 v1. Mitigate with mechanical post-processing rule.
- **Domain concentration cap may demote legitimate Wikipedia-dominant sources** for genuinely Wikipedia-dominated topics (obscure historical claims). Need negative test in bench.
- **V3 thresholds are best-guess.** Calibrate on real runs before locking.
- **Authoritative anchor list is opinionated** — different operators may disagree. Document assumptions; allow per-deployment override.
- **Soft cap may feel like a regression** to early users. Clear copy is mitigation.
- **Bench guardrails may produce noise initially.** Tune tolerances after 2-3 runs.
- **`element_resolution` may still over-penalise** Seeker-view-honest claims even at the relaxed ≥50% Good threshold. Monitor on first-N production runs; lower further if false-positive Mediocre/Poor verdicts cluster on legitimate unknown-rich claims.
- **Sports claims will tend to verdict Mediocre in V1** because no dedicated sport adapter exists — coverage is web-search only, which inflates Wikipedia and Reddit share. This is a known V1 limitation, addressed in Phase 2 via sport adapter add. Mark Sports verdicts as "expected limitation" rather than treating them as quality regressions.
