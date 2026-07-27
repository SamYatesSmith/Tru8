---
Title: Pipeline Timing — Context Pack for Fable 5 review
Date: 2026-07-02
Author: Claude (Opus 4.8) — code + live-log grounded, NOT from prior docs
Purpose: Give Fable 5 an accurate, current map of WHAT runs WHEN, HOW LONG it takes, and WHY,
         so it can propose where to cut latency ahead of general release.
Status: CONTEXT ONLY — no changes made. All prior timing docs are stale (see §7).
---

# Tru8 pipeline timing — context for a latency review

## 0. How to read this / trust model

Everything here is grounded in **current code** (`file:line` cited) and **real runtime data**
mined from `backend/logs/pipeline.log` (16 real full-mode checks, 2026-05-12 → 2026-07-02).
The older `audit/COST_*.md` docs quote "15-second / 90-second" figures — those are unsourced
marketing rounds and partly describe an **older** cost model. Ignore them for timing. See §7.

**One caveat on the real numbers:** the logged checks ran **locally** in *focused* mode
(single/low claim count) with `api_adapters=0` (no government-API keys set locally). Production
with adapters live could differ — most likely *slower* on the retrieve leg, not faster. To get
authoritative per-stage seconds, run the profiler (§8) — it already exists.

---

## 1. Headline: what a check actually costs today (REAL, measured)

**Whole-check wall time**, from the 16 real `[PIPELINE METRICS]` lines in the live log (all `mode=full`):

| Metric | min | median | mean | p90 | max |
|---|---|---|---|---|---|
| **whole-check wall time** | 55.3s | **96.1s** | 99.5s | 144s | 158.8s |

So the number a user *feels* today is **~1–2.5 minutes**, not the "15s/90s" the stale docs advertise.

### Measured per-stage split (profiler, 2 cache-busted runs, 2026-07-02)

`python -m scripts.profile_stage_timings --runs 2` on a single well-known claim (a real full run,
Serper hit on the first query). Wall 84.8 / 93.4s. **Mean seconds per stage:**

| Stage | mean s | % of staged | note |
|---|---|---|---|
| **analyze (MAP)** | **42.1** | **39%** | ⭐ dominant — the Gemini "thinking" model |
| classify | 18.7 | 17.7% | runs **concurrently** with distil ↓ |
| distil | 18.7 | 17.7% | concurrent pair ⇒ ~18–20s **wall**, not 37s |
| retrieve | 16.7 | 13–17% | ⚠ **fast path** — Serper hit; see bimodal note ↓ |
| llm_relevance | 7.5 | 5–8% | flash-lite scorer (timed out + retried once here) |
| extract | 2.5 | 2–3% | |
| factcheck | 1.4 | 1.2% | runs **concurrently** with decompose |
| decompose | 1.4 | 1.2% | concurrent pair ⇒ ~1.4s wall |
| ingest / url_dedup / coverage_recovery | 0.0 | 0% | text claim, ≤2 claims ⇒ recovery skipped |

The profiler's "sum of stage timings" (103–115s) **exceeds** wall-clock (85–93s) by ~18–21s — that
gap is exactly the **classify∥distil overlap** (they're `asyncio.gather`'d), so don't add those two.

### The one big rock is MAP, and retrieve is bimodal

1. **MAP / analyze — ~42s, 39%, the steady dominant cost.** The Gemini 2.5 *flash-thinking* model,
   12k output tokens, one batched call + parallel completion passes (`runner.py:2128`, budget 120s;
   here it ran well under, ~40–44s, so no fallback fired). **This is the #1 latency lever.**
2. **RETRIEVE is bimodal, not a fixed cost — but the tail's cause is UNPROVEN (verified 2026-07-02):**
   - **Fast path ~16s** on current code (this profiler run, Serper hit first).
   - **Slow path ~46s median** in the live log — BUT those 16 metrics lines are **all from
     2026-05-12→15 (7-week-old code)**, and their retrieve median of 45.8s sits *at* the 45s
     per-claim cap: the log carries **12 explicit `[CLAIM N] Tasks timed out after 45s:
     ['web_search']` warnings on those very checks**. The May tail was the cap being HIT — by
     web_search hangs whose root cause (fallback ladders? page-extraction stalls? since-fixed
     code?) was never established. Current code shows no cap-hits locally.
   The sequential fallback-ladder mechanism is real in code (§4), but its contribution *today* is
   unmeasured. Re-measure in prod (persist `stage_timings`) before optimising retrieve.
3. **classify∥distil ~18–20s wall** (concurrent). **llm_relevance ~7.5s** (and its flash-lite call
   *timed out and retried* in both profiler runs — a reliability wobble worth noting).

---

## 2. The pipeline shape (two phases, one optional pause)

```
PHASE 1 (article mode pauses at the end; focused/single-claim flows straight through)
  INGEST      10%   fetch URL / OCR / transcript                    serial
  EXTRACT     20%   LLM → ≤12 atomic claims                         serial, 1 LLM call
  SELECT/RANK 28%   LLM ranks, keeps top 5 (article mode only)      serial, 1 LLM call
  [PAUSE]     30%   status=waiting_for_selection (article mode)     — user gate —

PHASE 2
  FACTCHECK   35%   Google Fact-Check API           ─┐ run CONCURRENTLY (asyncio.wait)
  DECOMPOSE   45%   LLM → 1–5 elements per claim     ─┘  1 batched LLM call
  RETRIEVE    60%   per-element multi-source search      serial await, HEAVILY parallel inside
  URL-DEDUP    ·    global URL dedup (no event)          serial, no LLM
  SCORE        ·    LLM relevance 1–5, ≤50 items         serial, 1 LLM call (no own event)
  POST-FILTER  ·    backfill thin claims (no event)      serial, no LLM
  CLASSIFY    75%   tier/type, batches of 30    ─┐ run CONCURRENTLY (asyncio.gather)
  DISTIL       ·    per-claim distillation      ─┘  parallel fan-out per claim
  MAP/ANALYZE 85%   evidence→element mapping             serial await; THINKING model; 120s budget
  ORIENTATION  ·    mechanical, NO LLM (free)
  COVERAGE-REC ·    targeted re-retrieval if >40% unresolved (skipped ≤2 claims)  parallel per claim
  QUERY       90%   optional user-question answer        serial, 1 LLM call (only if user_query)
  COMPLETE   100%

POST-COMPLETION, fire-and-forget (do NOT block the result):
  Video recs (YouTube, ≤5/claim, parallel) · Wayback auto-archive (sequential, ~15 req/min, 120s/req)
```
Sources: phase split `runner.py:584-1064`; progress % `progress.py:41-54`; concurrent groups
`runner.py:1270-1277` (factcheck∥decompose), `runner.py:1963-1969` (classify∥distil);
fire-and-forget `checks.py:721-769`.

---

## 3. Stage-by-stage: what, model, concurrency, timeout, why-slow

Models: **Gemini 2.5 flash-lite** is primary for decompose/select/score/classify/distil/query;
**Gemini 2.5 flash (the "thinking" model)** is used **only for MAP** (`config.py:375`,
`claim_map_analyzer.py:860-864`). OpenAI `gpt-4o` / `gpt-4o-mini` are fallbacks only. **No Claude
anywhere** — that's a greenfield option for Fable 5 to weigh.

| Stage | LLM calls / model | Concurrency | Timeout / budget | Why it costs what it costs |
|---|---|---|---|---|
| INGEST | 0 (fetch/parse; OCR/transcript if media) | serial | none (under 180s SSE cap) | I/O bound on the source; video transcript can be large |
| EXTRACT | 1 (ClaimExtractor, gpt-4o-mini label) | serial | — | single LLM round-trip; cache-checked (`workers/pipeline.py:65`) |
| SELECT/RANK | 1 (flash-lite, 30s cap) | serial | 30s | article mode only; skipped if ≤1 claim |
| FACTCHECK | 0 (Google FC API) | ∥ with decompose | shares budget; ~2–5s | sequential per-claim + per-URL loop inside (`workers/pipeline.py:110-131`) |
| DECOMPOSE | 1 batched (flash-lite) | ∥ with factcheck | 30s call cap | one call for all claims; per-claim retry fan-out on parse fail |
| **RETRIEVE** | 0 LLM here (search+embeddings) | **very parallel** (see §4) | **180s** stage, **45s per-claim** | **biggest rock**; external APIs, page fetches, fallback ladders |
| URL-DEDUP | 0 | serial | — | cheap; global dedup, cap 2 claims/URL |
| SCORE (relevance) | 1 (flash-lite 60s / OpenAI 90s) | serial | 60–90s | one call over ≤50 items; round-robin fair-select over cap |
| POST-FILTER-REC | 0 | **sequential** per thin claim | — | each thin claim = another search round (`runner.py:1753`) |
| CLASSIFY | 1+ (flash-lite, **batches of 30**, sequential batches) | ∥ with distil | 45s/call | >30 evidence items ⇒ multiple sequential batches |
| DISTIL | 1 per claim (flash-lite) | parallel per claim | — | fan-out; off in quick mode |
| **MAP/ANALYZE** | 1 batched **thinking-model** call + per-claim **completion passes** | top call serial; completions parallel | **120s budget** (55s map + 25s completions + 30s fallback) | **thinking model is deliberately slow**; 12k output tokens; prime 2nd rock |
| ORIENTATION | **0 (pure function)** | — | free | mechanical derivation from element states |
| COVERAGE-REC | classify + map per recovered claim | parallel per claim | scaled: `max(20, n×7)`s | skipped for ≤2 claims; only fires if >40% elements unresolved |
| QUERY | 1 (flash-lite) if `user_query` | serial | — | optional; non-critical try/except |

Full stage/model/timeout citations are in the appendix (§9).

---

## 4. Why RETRIEVE is ~half the clock (the concurrency model)

Retrieve is *already* heavily parallel — the latency is external, not from serialisation:

- **Claims** fan out via `asyncio.gather`, capped at `Semaphore(10)` (`retrieve.py:176,449`).
- **Within a claim**, web-search and government-adapter retrieval run as two concurrent tasks under
  a **45s per-claim timeout** (`CLAIM_TIMEOUT=45`, `retrieve.py:1306-1320`); partial results kept.
- **Web queries** all fire concurrently (`retrieve.py:1609-1631`); **page fetches** all concurrent,
  shared `Semaphore(25)` pool (`retrieve.py:371`, `config.py:340`).
- **Government adapters** all fire concurrently but each is a **synchronous** `httpx.Client` wrapped
  in `asyncio.to_thread` (`retrieve.py:2223`) — so their real ceiling is the default thread-pool,
  and each adapter can block **timeout(10s) × retries(3) + backoff(1+2+4s) ≈ 37s worst case**
  (`government_api_client.py:38-41,237`), bounded by the 45s per-claim cap.

**The additive-latency traps** (where time quietly stacks up):
1. **Web fallback chain is sequential** Serper → Brave → SerpAPI (`search.py:809-841`). If Serper
   returns hits, the others never run (fast). If Serper returns **0**, you pay Brave's 2.5s spacing
   + a **5/10/20s** timeout-retry ladder, then SerpAPI's 2.5s spacing + up to **10s cold-start**.
2. **Freshness fallback** re-runs queries pw→pm→py on 0 results (`retrieve.py:1671-1727`).
3. **Zero-result-without-exclusions retry** re-runs the whole chain once (`search.py:789-804`).
4. Not all "30+" sources fire — adapters are filtered by domain/jurisdiction/keyword and hard-capped
   at **~3–8 per claim** (`_DEFAULT_ADAPTER_CAP=3`, `retrieve.py:58,2184`). So breadth is already
   throttled; the tail latency is the fallback ladders above, not raw source count.

---

## 5. Where the time goes — summary for the reviewer (now measured, §1)

- **MAP/ANALYZE ~42s (39%) — the single dominant stage.** Gemini flash-*thinking*, 12k tokens.
  This is where the biggest, most reliable win is.
- **RETRIEVE — bimodal: ~16s (Serper hits) to ~46s (fallbacks fire).** Already concurrent; the win
  is in *avoiding the slow sequential fallback ladders* (§4), not adding parallelism.
- **classify∥distil ~18–20s wall** (they overlap). **llm_relevance ~7.5s** (with an observed
  flash-lite timeout+retry — a reliability, not just latency, issue).
- **Cheap:** extract ~2.5s, factcheck∥decompose ~1.4s.
- **Free / near-free:** ingest, orientation (pure function), url-dedup, coverage-recovery (skipped
  ≤2 claims), fire-and-forget video+archive.

**Serialisation points worth questioning** (candidate levers, NOT decisions — for Fable 5):
- RETRIEVE, SCORE and MAP are each `await`ed **serially** at the top level even though nothing
  downstream of retrieve needs *all* of score before *some* mapping could start. The current order is
  retrieve → dedup → score → classify∥distil → map.
- CLASSIFY runs its 30-item batches **sequentially** (`evidence_classifier.py:550`) — parallelisable.
- POST-FILTER recovery loops thin claims **sequentially** (`runner.py:1753`).
- MAP's top batched call is serial; only its completion passes parallelise.
- The **thinking model** for MAP is the single biggest model-choice lever: is flash-thinking's quality
  worth ~2× the latency of flash-lite here, or would a non-thinking model + better prompt/schema hold
  quality? (No Claude in the stack today — an untested option.)

---

## 6. The agent-market angle (the "dream")

The fast path the user is dreaming about **already exists in architecture** — it just may not be
fast/good enough yet:

- **`QUICK_CONFIG`** (`runner.py:62-75`): `max_wall_time_seconds=30`, 1 query/element, 8 sources/claim,
  **no API adapters, no fact-check, no LLM relevance, no post-filter, no coverage recovery, heuristic
  (non-LLM) classify, no distil, no query-answer.** That strips out most of §3's expensive rows.
- The **Agent Commerce Gateway** already exposes tiers built for this: **Lookup ($0.02)**,
  **Consensus ($0.03)**, **Quick ($0.07)**, **Full ($0.15)** (`agent_pricing.py`), plus the MCP
  `tru8_check` tool with tier fallback. Consensus/Lookup can answer from *cached cross-user consensus*
  with little or no fresh pipeline work.

So "agents research a claim" is a **latency + tiering** problem, not a greenfield build. The review
question for Fable 5: **can a Quick/Lookup call reliably return in a few seconds** (sub-10s, ideally
sub-3s for Lookup) so an agent will actually wait on it in a tool-call loop? Today's *Full* median of
~96s is a non-starter for an interactive agent; a well-tuned Quick/Lookup is the wedge.

---

## 7. Staleness of existing docs (do not reuse their numbers)

| Doc | Timing content | Verdict |
|---|---|---|
| `audit/COST_ANALYSIS.md` (2026-03-10, untracked) | "15-second" / "90-second" marketing rounds only | **STALE** — costs GPT-4o as primary decompose; superseded |
| `audit/COST_PER_CLAIM.md` (2026-03-10, untracked) | none (cost/token only) | stale cost model; no timing |
| `audit/cost_control_plan.md` (2026-04-29, untracked) | none (cost/margin) | most architecture-aligned but no timing |
| `audit/mapper_efficiency_plan.md` | none | superseded |

**Real timing lives in runtime, not docs:** `stage_timings` (14 stages) is measured per run into
`result["pipeline_stats"]["stage_timings"]` and `total_stage_time` (`runner.py:2529-2536`), and
whole-check `processing_time_ms` → `cost_telemetry.timing.wall_time_ms` is persisted to Postgres
(`cost_constants.py:151`). **Only whole-check wall time is persisted**; per-stage is transient per run.

---

## 8. How to get authoritative per-stage numbers (recommended before optimising)

```bash
cd backend
docker compose up -d                 # Postgres + Redis + Qdrant
python -m scripts.profile_stage_timings --runs 3     # cache-busted, per-stage table + mean/min/max
# ~$0.10–0.25 per run (LLM + search). Add --claim "..." to test a specific claim.
```
This reads the live `stage_timings` and prints the per-stage split + "dominant stage" — the single
missing number (real MAP duration) this context pack can't get from the log. For production wall-time
distribution: `railway run python -m scripts.check_cost_snapshot` (reads `cost_telemetry`).

`replay_bench` does **not** record timing (cassettes capture HTTP for determinism only); its `--fast`
flag is unimplemented. If we want historical per-stage timing, we'd extend `cost_telemetry` to persist
`stage_timings`, not just wall time — a small, high-value change.

---

## 9. Appendix — key constants & citations

- Config: `PipelineConfig` full `runner.py:40-60` (queries/elem=3, sources/claim=20, wall=180s);
  `QUICK_CONFIG` `runner.py:62-75` (queries/elem=1, sources=8, wall=30s, adapters/factcheck/relevance/
  recovery/llm-classify/distil/query all off).
- Models: `GOOGLE_LLM_MODEL=gemini-2.5-flash-lite` `config.py:68`; `MAPPING_GOOGLE_MODEL=gemini-2.5-flash`
  `config.py:375`; analyzer picks thinking model when `is_mapping=True` `claim_map_analyzer.py:1294-1311`.
- Timeouts: retrieve stage 180s `runner.py:1343`; per-claim retrieve 45s `retrieve.py:1306`;
  analyze/map budget 120s `runner.py:2128`; mapping call 55s `claim_map_analyzer.py:864`;
  decompose 30s `claim_map_analyzer.py:863`; relevance 60/90s `relevance_scorer.py:337,457`;
  classify 45s `evidence_classifier.py:496`; coverage-rec scaled `max(20, n×7)`s `runner.py:301-312`;
  government adapter 10s×3 + 1/2/4s backoff `government_api_client.py:38-41,237`.
- Concurrency: claims Semaphore(10) `retrieve.py:176`; URL-fetch Semaphore(25) `retrieve.py:371`;
  web fallback sequential `search.py:809-841`; adapter cap ~3–8 `retrieve.py:58,2184`.
- Fire-and-forget: video/Wayback launched post-completion `checks.py:721-769`; never block result.
- Real data source: `backend/logs/pipeline.log`, 16 `[PIPELINE METRICS]` lines, 2026-05 dev runs,
  `api_adapters=0` (no local gov keys), focused/1–2 claim.
