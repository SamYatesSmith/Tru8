# Consolidation — 2026-05-11

> **Purpose.** `OPEN_WORK.md` is the *register* (what's open right now). This doc is the *order* — what ships V1, what's deferred, what needs scoping, in sequence.
>
> Re-issued when the sequence changes materially (rough cadence ~1/quarter). When `OPEN_WORK.md` and this doc disagree, OPEN_WORK is more current; resequence this doc.
>
> **Relationship to other docs.**
> - `audit/OPEN_WORK.md` — register, canonical for *what's open right now*
> - `audit/pipeline-issues/2026-05-06_v1_quality_plan.md` — canonical V1 plan body
> - `audit/track-i/PROGRESS.md` — canonical Track I detail
> - `audit/2026-05-11_landing_reframe_scope.md` — scope for the strategic positioning question that Step 7 originally collapsed
> - **This doc** — the *order* across all of the above

---

## What shipped after this doc was first written (2026-05-11 → 2026-05-12 PM)

Eleven commits total since this doc was first written. All LOCAL — branch 11 ahead of origin/main, **not pushed**.

**2026-05-12 PM — pool diversity Steps 1/2/3 (user-frustration response):**

| Step | Commit | Summary |
|---|---|---|
| Step 1 | `5f361ef` | Class-targeted query augmentation — per-element news / officials / academic site:-filtered queries based on claim domain + jurisdiction. `max_queries_per_element` 3→5. 17 new tests. |
| Step 2 | `f3d8fe7` | Per-element mapper completion pass — NF-19 mitigation. New `COMPLETION_PROMPT` constant with deliberately permissive context-tier framing (opposite of main MAPPING_PROMPT's "don't pad" rule). Wired into BOTH `map_evidence_to_elements` and `map_evidence_batch` (production hot path runs completions in parallel via asyncio.gather + per-claim 25s timeout). `analyze_timeout` 90→120s. 13 new tests. **Bench evidence on TRU-B4A3-C42D**: unique_domains 3→11, mapping rate 50%→80%. |
| Step 3 | `1ab949a` | Mechanical year anchor on LLM-generated queries — recurring-topic recency-bias fix. New helper `query_date_anchor.py::augment_plans_with_date_anchor`. Surfaced by TRU-B56C live test (Nov 2023 Autumn Statement returned 2025 Budget content). 18 new tests. |

**Live testing surfaced a new structural ceiling we did NOT close:** TRU-B56C-AF05 and TRU-04E3-7F48 (both UK Politics/Finance) showed **all four UK government adapters at 0 yields** (Hansard, GOV.UK Content API, ONS, Companies House). This bottleneck is the **Hansard 0-yield item (ELEVATED 2026-05-12 PM)** in OPEN_WORK — now the dominant Politics/Finance ceiling. Steps 1/2/3 cannot help because web search alone cannot substitute for direct gov.uk/parliament.uk content surfacing.



**2026-05-12 — NF-20-B + cleanup (Commit A, pending):**

| Item | Summary |
|---|---|
| `_propagate_article_dates` in extract.py | New static method, wired into `_validate_and_refine_claims` between dedup and merge. Article-level DATE union injected into dateless claims with `source: "article_inheritance"` provenance. Conservative + idempotent. |
| Dead-plumbing cleanup | Removed `temporal_analysis`/`article_title`/`article_date` dead params on `extract_evidence_for_claim`; removed `freshness` dead param on `_execute_planned_queries`; removed DEPRECATED `temporal_window`→`freshness` block at retrieve.py:1234-1243; removed orphan `TEMPORAL_TO_FRESHNESS` constant. |
| 17 new tests | `test_extract_date_propagation.py` (15) + `test_query_planner.py::TestB4InjectOnPropagatedDates` (2). |
| Bench | TRU-B4A3-C42D golden refreshed (Bug A merge now fires on mini-budget claims post-propagation — intended). 4/5 corpus clean. |
| Live verification owed | TRU-E4C5-shape re-submit on local dashboard. |

**2026-05-11 — three threads + Step 5 + Librarian parity:**

| Thread / step | Commit | Summary |
|---|---|---|
| Step 5 Phase 1-5 (instrumentation) | `645c34d` | `[B3 QUALITY]` / `[DOMAIN CAP]` / `[COVERAGE RECOVERY] Timed out` matchers + 3 hard-invariant families + universal V3 Poor floors + 34 unit tests. **Phase 6 golden refresh + Phase 7 4-claim corpus entry now block Step 6.** |
| Librarian parity | `ae30383` | `LibrarianView.tsx` filter relaxed `'excluded'` only — matches Cartographer/Chronologist/Correspondent. **Side-effect: V3 floors now judge true user-visible landscape; some claims' unique_domains jumps from ~1-2 to ~12-15.** |
| Thread B (priority) | `a6a7146` | Evidence cross-attribution between non-contiguous claim positions. Affected every multi-claim check post-Step-4 UI cap. 8 regression tests. |
| Thread A | `9ca32ff` | Facebook/Instagram leak via two recovery paths in `retrieve.py` (commit `330ab44` only patched the third path in `runner.py`). 10 regression tests. |
| Thread C | `ddfddb2` | Bug A extension for single-event over-decomposition (TRU-E317 GBR coral). C3 prompt + C1 backbone extension (LOCATION+DATE). 10 regression tests. C2 deferred. **Live verification owed.** |

`778/778` pipeline unit tests pass (+27 new across A/B/C). Bench: 54 ok / 9 warn / 2 fail — both fails are TRU-B4A3-C42D known-unstable jaccards (provider variance, see Tier 4 entry), not related to these threads.

---

## Verification basis (2026-05-11, original)

Compiled by reading the canonical docs above and then verifying each non-trivial claim against current code rather than trusting documentation. Findings:

**Verified against code:**
- Local alembic head: `classification_method_64` (the 2026-05-07 migration is applied locally)
- `AUTHORITATIVE_TLDS` allowlist at `backend/app/services/evidence.py:140-151` — no UK institutional `.co.uk` / `.org.uk` entries → **SC-11 confirmed open**
- Replay bench corpus directory has 5 entries (TRU-5647-FA4F, TRU-82CF-2F81, TRU-93DD-F4B7, TRU-A3E8-3199, TRU-B4A3-C42D); ~~no `[B3 QUALITY]` / `[DOMAIN CAP]` matcher in `backend/scripts/replay_bench/`~~ → **Step 5 Phase 1-5 instrumentation shipped `645c34d` 2026-05-11; Phase 6/7 remain**
- `backend/tru8_mcp/pyproject.toml` v1.0.0, MIT, entry point + classifiers set → **I-07 submit-only**
- `web/components/marketing/stitch-video.tsx` still a Play-button placeholder → **I-15 deferred confirmed**
- `_inject_freshness_for_historical_dates` actually lives in `backend/app/utils/query_planner.py` (file-locator note for NF-20-B; OPEN_WORK didn't pin the path)

**Stale-doc fix applied (see "Stale-doc fixes" section below):**
- I-14 custom 404 page — `web/app/not-found.tsx` exists as a real 20-line component. Closed.

**Not re-verified (carrying detail from OPEN_WORK):**
NF-11 v2, NF-17, Hansard 0-yield, Classifier Mode B, SC-08, SC-12, SC-13, SC-14, SC-16, Track P P0a/P0b/P2/P3/P4, Threads 1/3, Cost control Phase 3+. OPEN_WORK has dated evidence for each (specific URLs, specific log lines); none of these have been touched in any recent commit, so they remain open. If any becomes active work, re-verify at that point.

---

## Tier 1 — V1 ship-gate (active, sequenced)

| # | Item | Detail | Status |
|---|---|---|---|
| 1 | **Step 5 Phase 6: golden refresh** | `python scripts/replay_bench.py --all --update-golden` to activate V3 floors on the existing 5 corpus entries. ~10 min, ~$0.25. Floors land as universal Poor thresholds (5 unique domains, ≤45% top share, ≤40% Wikipedia, ≥15% factual weight, ≥30% element resolution); golden refresh confirms current corpus passes them. Per `645c34d` commit message. | NEXT (user-runnable) |
| 1a | **Live verification of Thread C** | Re-submit a GBR-coral-shape article (1-2 sentence single-event prose, multi-aspect) into local dashboard. Expect: LLM extract produces 2-3 claims instead of 5; `[EXTRACT] CLAIM MERGE` does NOT fire upstream of `ddfddb2`'s mechanical passes. If still ≥4 claims → next escalation is C2 (article-level LLM event-clustering pass, deferred in `ddfddb2`). | Owed; user-runnable |
| 2 | **Step 5 Phase 7: 4-claim corpus entry** | New corpus entry with genuine multi-entity-anchor structure that survives Bug A. TRU-15A8 (Russia spending) is the V1 plan candidate. Decision-point: does TRU-15A8 still produce 4 claims after Bug A + Threads B/C? Needs a quick local re-submit before locking. | After 1 + 1a |
| 3 | **Step 6: V1 acceptance live re-run** | Re-run remaining 3 articles (GBR coral, Sha'Carri, UK election retest with authority-weighted override). All 7 must land at "Good" or better on V3 framework. **Gated on Step 5 complete.** | After Step 5 |
| 4 | **Deploy gate: `alembic upgrade head` on Railway** | Production needs `classification_method_64` before next deploy of `76e8c1d`/`8b83d7b` to avoid `StringDataRightTruncationError` on Bug D / B3 floor fires. Local at head. Also relevant: 5 local commits are unpushed (branch ahead of origin/main by 5). | Required before next prod deploy |
| 5 | **Step 7: Landing copy + reframe — see Tier 1.5** | Originally scoped as a copy update. The user reframed 2026-05-11 as a positioning decision. Scope doc below. | Scope first, then build |
| 6 | I-07 MCP publication | Package code is 100% ready. PyPI + 4 registry submissions (mcp.so, PulseMCP, Smithery, official MCP registry) remaining. Parallelisable with everything else above. | Submit-only |

---

## Tier 1.5 — Strategic, needs scoping before it can sit in a tier

**Landing reframe.** Step 7 of the V1 Plan was originally scoped as "1-3 claim sweet spot copy". The 2026-05-11 conversation reframed this as a positioning decision — does the site lead with consumer-news-aggregation, agent/API, or parallel tracks? This is revenue-shaping and requires research before committing.

**Scoping doc:** `audit/2026-05-11_landing_reframe_scope.md`.

**Hard constraint:** V1 ships under current consumer-led positioning. Reframe decision is post-launch + post-MCP-publication, after directional usage data accumulates.

**What this means for V1 Step 7:** the copy update to reflect 1-3 claim sweet spot still happens (small, scoped change to current consumer-led landing). The structural reframe is a separate workstream that the scope doc enables.

---

## Tier 2 — Phase 2 quality ceiling (deferred to post-V1, known suboptimal)

Don't fix without explicit Phase 2 trigger — V1 ships acknowledging these.

| Item | What | Why deferred |
|---|---|---|
| **NF-19 mapping efficiency (Layer 3)** | Mapper LLM picks 1-2 representative items per element instead of comprehensive mapping. TRU-EF20 had 22 retrieved, 4 shown. **This is the real ceiling on close-split disposition quality.** | Bigger than one commit — needs per-element mapper architecture, prompt restructuring, or post-LLM completion pass. Authority-weighted state override (`8486708`) is an upper-layer mitigation. |
| NF-11 v2 scorer rubric | LLM exploits rubric loopholes; GOV.UK Growth Plan excluded at score=1 on snippet judgement. Per-item exclusion logging prereq SHIPPED (`92b83d4`). | Needs typed-entity discriminator OR different mechanism, NOT prompt-only (NF-11 v1 lesson — `feedback_nf11_prompt_only_failed.md`). |
| Bug C: mapper batch capacity at 4-5 claims | Mapping rate drops 70% (2 claims) → 41% (4) → 48% (5). | V1 soft cap at 3 mitigates without architectural change. |
| Wikipedia LLM-promotion-to-primary audit | Mapper sometimes promotes Wikipedia to primary tier inappropriately. | Likely subsumed by NF-19 work. |
| API `prepare_query` deep audit | Wider audit of all adapter query construction (Mass Eye and Ear, Google Health, BlackRock IR, SIPRI). | No production signal forcing it; defer to data-driven. |

---

## Tier 3 — Coverage gaps (post-V1, small + scoped)

Ship one-at-a-time when capacity allows. None are V1 blockers.

| Item | What | Location |
|---|---|---|
| SC-11 `.co.uk` institutional allowlist | `bankofengland.co.uk`, `ifs.org.uk`, `obr.uk`, `resolutionfoundation.org` runtime-blocked despite being authoritative | `backend/app/services/evidence.py:140-151` |
| ~~NF-20-B B4 freshness inheritance~~ | **CLOSED 2026-05-12.** Article-level DATE propagation in extract.py + tightly-coupled cleanup of 3 dead temporal params + DEPRECATED freshness-from-temporal_window block. See OPEN_WORK closed table for full detail. | `backend/app/pipeline/extract.py::_propagate_article_dates` |
| NF-17 Companies House `prepare_query` | Queries every ORG without filtering for company-likeness/jurisdiction | `backend/app/services/government_api_client.py` |
| Hansard 0-yield investigation | Returned 0 across 3 mini-budget claims despite 38+ contributions | Adapter location TBD; 4-step probe per Session 7 pattern |
| Classifier Mode B | Domain primary-swap on cross-domain claims (UN→Demographics, etc.) | 2/40 baseline; needs >1 production data point before fixing |
| SC-08 scorecard corpus expansion | ≥1 claim per `VALID_DOMAINS` entry (~30 claims) | Hygiene |
| SC-14 Chronicling America replacement | 75% timeout under concurrency; benchmark vs DPLA | Conditional on measurably-better data |
| SC-16 Companies House 401 | Missing `COMPANIES_HOUSE_API_KEY` env var (free registration); now relevant given NF-17 | Railway env |
| Track P P0a — ECB SDW | Eurozone interest-rate / monetary policy adapter | New adapter |
| Track P P0b — Europe PMC | EMBL-EBI corpus; genuine independence vs Semantic Scholar/OpenAlex | New adapter |
| Track P P2 — SEC EDGAR | US public-company filings; would have made TRU-5411 BlackRock Good | New adapter |
| Track P P3 — Eurostat | Natural pair with ECB SDW | New adapter |
| Track P P4 — fact-check aggregators | CONDITIONAL on Google Fact-Check utilisation audit | New adapter |

---

## Tier 4 — Observability & operations

| Item | Status | Notes |
|---|---|---|
| Thread 1: Sentry observability gap | Partial — backend HTTPException 5xx capture shipped `29052ba`; frontend DSN in Dockerfile build args shipped `5c86c53`. Need to verify frontend events are now flowing. | Quick check via Sentry MCP would close this |
| Thread 3: Data lifecycle / strategic asset | Open — no curated export, no labelled corpus split, no analytics layer. Needed for NF-11/12 eval and as future product surface. | Not pre-release |
| TRU-B4A3-C42D bench instability | Open — provider-side variance dwarfs regression signal on this corpus case. | Flagged for Step 5 bench-instrumentation work. Mitigation candidates: lower jaccard floors specifically, seed deterministic search-mock, or replace corpus entry with TRU-15A8 (V1 plan candidate) |
| Cost control Phase 3.1-3.3 | Post-launch, data-gated | Weekly Sentry counters on mapper-fallback, 30p kill switch, blended-cost review |
| Cost control Phase 4.1-4.6 | Data-gated post Phase 3 | Six hypotheses, each unblocked by Phase 3 data |
| Railway env vars (residual) | Partial | `PUBMED_API_KEY` set 2026-04-23; Stripe Live IDs presumed set per I-03 closure; Sentry DSN now in build args; Companies House key still missing (see SC-16) |

---

## Tier 5 — Optional polish & deferred

| Item | Status |
|---|---|
| I-06 OG card visual review | Functional-complete; cross-platform render testing remains |
| I-15 Demo video | Deferred; placeholder in `stitch-video.tsx` unchanged |
| SC-12 TTL on `domain_status_tracker` | ~1,270 stale runtime blocks; deferred post-release |
| SC-13 NF-03 `api_adapters=0` miscount | PARKED — fix if `runner.py` touched for other work |
| NF-14 web-search ceiling on niche claims | Track P candidate (UK marine biodiversity specialist) |
| Bills B2.3 ORG-led trim weakness | Edge case on copula verbs; user discretion |
| Claim-fragment extraction (TRU-B4A3-C42D claim 2) | Open-observe; needs ≥2 more data points |
| PQ-10 (JSON-REPAIR on Flash Thinking mapping) | Parked — mapping completes via repair path |

---

## Open verification questions for user

1. **Production alembic head** — is `classification_method_64` deployed? Local is at head. If production lags, deploy is real-blocking and Tier 1 #3 stays open.
2. **Acceptance status** — has anything been re-run beyond the 4 articles tested 2026-05-07/08? Treating as "no" per commit log; confirm.
3. **Thread 1 Sentry state** — has frontend started receiving events since `5c86c53` (Sentry DSN in Dockerfile build args) shipped? A 2-minute Sentry MCP check would close this thread.
4. **Threads 4 & 5** — classifier drift (Monitor) and sparseness reframe (closed in spirit). Drop from this consolidation as Tier-3 work covers their real targets (NF-11, Track P, claim extraction). OK?

---

## Stale-doc fixes applied today (2026-05-11)

| Item | Evidence | Files updated |
|---|---|---|
| I-14 custom 404 page | `web/app/not-found.tsx` exists (20 lines, Stitch styling, "Back to home" link). Was listed `[~] Mostly Done` in PROGRESS.md, `OPTIONAL POLISH` in OPEN_WORK.md. Both wrong. | `OPEN_WORK.md` (moved to Closed), `track-i/PROGRESS.md` (status + task checkbox + summary table) |

---

## Cadence

Next consolidation pass: when V1 ships, when Phase 2 starts, or when materially new items appear. Rough target: ~1 per quarter.

When this doc and `OPEN_WORK.md` disagree, OPEN_WORK is more current (it's edited per-fix). Use this doc for *direction*, OPEN_WORK for *state*.
