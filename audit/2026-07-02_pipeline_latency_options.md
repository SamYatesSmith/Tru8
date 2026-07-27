---
Title: Pipeline Latency — Optimisation Options (Fable 5, VERIFIED + design-reviewed)
Date: 2026-07-02 (v2 — findings verified against code + logs same day)
Author: Fable 5 (Claude)
Status: OPTIONS FOR REVIEW — nothing implemented. Every finding re-verified by direct code read
        or measurement; surety stated per claim. One v1 finding revised (retrieve tail), one
        strengthened (Quick tier 504s).
Companion: audit/2026-07-02_pipeline_timing_context.md (measured baseline)
---

# Latency optimisation options — verified findings, design review, surety

## Surety scale used throughout
- **CONFIRMED** — direct code read or direct measurement this session.
- **HIGH** — mechanism confirmed; magnitude inferred from confirmed structure (~80–90%).
- **MEDIUM** — direction confirmed; magnitude depends on an unmeasured variable (~50–80%).
- **LOW** — plausible; needs data before acting (<50%).

---

## Part 1 — Findings verification (what survived scrutiny)

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| F1 | MAP/analyze is the dominant stage: **40.0s / 44.2s**, 39% of staged time | **CONFIRMED** | Direct measurement, 2 cache-busted profiler runs on current code, 2026-07-02 |
| F2 | **No `thinkingConfig` anywhere** — both Gemini call variants build `generationConfig` with only temperature/maxOutputTokens/responseMimeType(/responseSchema); mapping uses `gemini-2.5-flash` (dynamic thinking on by default) via the usage variant | **CONFIRMED** | `google_ai.py:200-207` and `google_ai.py:322-332` read directly; mapping model+schema selection `claim_map_analyzer.py:1293-1322` |
| F3 | Distil is **MAP input, not presentation**: it rewrites `evidence["text"]` in place to distilled fact bullets, and MAP's batch input is built from those same dicts afterwards | **CONFIRMED** | `evidence_distiller.py:132-134` (in-place mutation); classify∥distil gather `runner.py:1963-1969` precedes batch-input build `runner.py:2131-2142` |
| F4 | Classify pools evidence **across all claims** then loops 30-item batches **sequentially**; results are index-keyed (`classified_results[batch_start+offset]`) → batches independent | **CONFIRMED** | `runner.py:1869-1889` (pooling); `evidence_classifier.py:550-559` (sequential loop, index-keyed results) |
| F5 | Quick tier's 30s wall is a **hard `asyncio.wait_for`** on agent endpoints, and on timeout the call **refunds and returns HTTP 504**; quick mode has **no mapping-model knob** — MAP always uses the thinking model | **CONFIRMED** | `agent.py:848-857,888-896` (wait_for); `agent.py:951-961` (refund + 504); `runner.py:62-75` (no map knob); `claim_map_analyzer.py:1309-1311` (unconditional model pick) |
| F6 | Gemini timeout → **immediate `return None`** (no retry) → silent OpenAI fallback; observed twice in 2 profiler runs | **CONFIRMED** (mechanism + occurrence) | `google_ai.py:223-228, 348-353`; profiler stderr 2026-07-02. *Which call site times out: undiagnosed* |
| F7 | Per-claim mapping machinery already exists (single-claim shortcut; per-claim parallel retry path) | **CONFIRMED** | `claim_map_analyzer.py:1143-1146, 1263-1274`; LLM gate = 25 (`google_ai.py:31`) |
| F8 | `stage_timings` measured every run but only whole-check `wall_time_ms` persists | **CONFIRMED** | `cost_constants.py:151`; `runner.py:2529-2536` |
| F9 | ~~Retrieve tail (~46s) caused by sequential fallback ladders~~ | **REVISED — was an inference, and it doesn't hold as stated** | All 16 prod-log metrics lines date **2026-05-12→15 (7-week-stale code)**. Their 45.8s retrieve median sits *at* the 45s per-claim cap, and the log holds **12 explicit `Tasks timed out after 45s: ['web_search']` warnings on those checks**. The May tail = cap-hits from web_search hangs of unestablished cause. Current code measures 15–18s with zero cap-hits. Fallback-ladder *mechanism* is real (`search.py:809-841`) but its present-day contribution is **unmeasured**. |

**Baseline correction:** the "~96s prod median" is May-code data. The current-code baseline is the
profiler's **85–93s single-claim full check**. Same ballpark, but treat prod distribution as
unknown until V1 lands.

---

## Part 2 — Design review of each option, with measurable-output surety

### V1. Persist `stage_timings` (+ split keys + thinking-token counts) — DO FIRST, expanded
**Design (revised after verification):** three additive fields, no behaviour change:
1. `stage_timings` into `cost_telemetry` (`cost_constants.py:151`).
2. **Split the shared timing keys** — classify/distil get the *same* elapsed assigned to both
   (`runner.py:1971-1975`), as do factcheck/decompose (`runner.py:1299-1301`). Time each task
   inside its wrapper so the pair's members are separable. (Verified arithmetic: the profiler's
   "unaccounted overhead" of −18.0/−21.6s = classify-block + factcheck-block double-count,
   16.95+1.38 / 20.35+1.37 — exact match.)
3. **Log Gemini `usageMetadata.thoughtsTokenCount` per call** — the response already carries it;
   we currently keep only input/output tokens. This turns M1's magnitude from inference into
   measurement *before* committing to a budget value.
**Risk:** none (additive JSON + logging). **Effort:** ~half a day now (was 1h; the split + tokens
are worth it). **Measurable output:** CONFIRMED by construction — it *is* the measurement.

### M1. Cap `thinkingBudget` on mapping calls — **CODE SHIPPED `b1c838b` (2026-07-02, inert: default None); sweep run same day**
> **Status:** knob live in code, no behaviour change until `MAPPING_THINKING_BUDGET` env var is set.
> Verified: 67 targeted + 2135 full unit tests pass; API field live-probed (0→off, 512→capped, −1→dynamic, works with responseSchema); byte-identity of default pinned by `test_no_thinking_config_when_budget_none`.
> **✅ M1 LIVE IN PROD (2026-07-02 16:32):** `MAPPING_THINKING_BUDGET=0` set on Railway (founder-approved), redeploy `19d210c8` SUCCESS, health green. Sweep verdict (63 mapping calls, 5 pools incl. 2 adversarial): budget 0 = −64 to −74% mapping latency, best coverage, longest reasonings, 100% modal-state agreement, disputed-detection 3/3; dynamic thinking exploded on contested evidence (16.4k-token/93.4s call; a parse failure). Rollback = delete the env var (or 1024 first on regression).
> **✅ Replay-bench finding RESOLVED (`9ba5266`, same day):** re-baselined and GREEN (160 ok/0 fail/0 drift). Three root causes fixed: date boilerplates in 3 prompts (signature-normalised), **mapping responseSchema enums were `list(set)` → per-process hash-seed order made every mapping body unreplayable** (now `sorted()`, pinned by test), silent misses (now loud CASSETTE DRIFT banner + explicit failure). New `--record-missing` patch mode incl. transport-failure recording. 3 hard invariants hand-adjusted with dated in-file notes (C1A0-0004 Finance dropped; C1A0-0003 domain cap 0.55; B4A3 factual-weight floor 0.05 — revisit). **The bench is again the mandatory pre-commit gate for pipeline work.**
**Design:** optional `thinking_budget` param on `call_google_ai_with_usage` (the only variant the
mapper uses — `claim_map_analyzer.py:1312-1319`); when set, add
`"thinkingConfig": {"thinkingBudget": N}` to `generationConfig` (`google_ai.py:322-332`). Plumb
from the analyzer for mapping labels only; config default = unset (current behaviour). Sweep
N ∈ {0, 1024, 2048, 4096} under replay-bench golden-signal diff.
**Design-review notes:**
- Field name/semantics (`thinkingBudget`, 0 = off, −1 = dynamic) are from training knowledge of
  the v1beta REST API — **verify against current Gemini docs at implementation** (5 min).
- Do V1's `thoughtsTokenCount` logging first: if thinking is, say, 70% of mapping tokens, the
  expected saving is large and the sweep is worth it; if 20%, spend the effort on M2/M3 instead.
- Quality gate is non-negotiable: Track N put mapping *onto* the thinking model deliberately.
  Replay bench (`--all`, cassette-deterministic) is the floor; PQ register criteria the judge.
**Measurable output & surety:**
**SWEEP RUN 2026-07-02** (3 frozen pools: finance/politics/health, 18-20 evidence items each;
3 repeats × 5 budgets = 45 direct mapping calls; harness `scripts/mapping_budget_sweep.py`,
raw `scripts/.mapping_sweep_results.json`):

| budget | lat mean | think tok | agree-vs-dynamic-modal | coverage | reasoning |
|---|---|---|---|---|---|
| dynamic | 32.8s | 5063 | 94.4% (self — the variance floor) | 0.88 | 100% / len 146 |
| 4096 | 28.2s | 3735 | 88.0% | 0.90 | 100% / 144 |
| 2048 | 17.3s | 1429 | 86.1% | 0.88 | 100% / 157 |
| 1024 | 13.8s | 860 | 88.9% | 0.89 | 100% / 160 |
| **0** | **11.9s (−64%)** | 0 | **91.7%** | **0.94 (best)** | 100% / 163 (longest) |

**Findings:**
- Budget 0 sits within ~3pp of dynamic's own self-agreement floor, with the BEST evidence
  coverage and the longest reasonings. On the unstable pool (EU sanctions), budget 0 was
  *more* self-consistent than dynamic (3/3 identical state vectors vs dynamic flipping between
  all-supported and unresolved variants).
- Agreement is NON-monotonic in budget (2048 lowest at 86.1%) — no dose-response, which is the
  signature of noise, not of thinking being load-bearing on these pools.
- Cost rider: dynamic burns ~5k thinking tokens/claim ≈ $0.013/claim at flash output rates —
  ~8% of the $0.15 full-tier price — for no measurable quality gain here.
- ~~Honest caveat: pools skew "supported"~~ → **CLOSED same day with an adversarial sweep**
  (2 pools whose evidence challenges: "MMR causes autism", "no warming since 2000";
  3 budgets × 3 repeats):

| budget | lat mean | think tok | agree | coverage | reasoning present | r-len |
|---|---|---|---|---|---|---|
| dynamic | **56.9s (42–93s!)** | 7765 | 75.0% (self) | 0.78 | **83.3%** | 140 |
| 1024 | 21.6s | 873 | **100%** | 0.92 | 100% | 196 |
| **0** | **14.9s** | 0 | **100%** | 0.92 | 100% | 194 |

**The adversarial test flipped the story — dynamic thinking is actively WORSE on hard content:**
- Budgets 0/1024 got the disputed states RIGHT, 3/3 identical runs each (MMR pool: disputed/
  disputed every time). Direction detection is NOT thinking-dependent.
- Dynamic exploded on contested evidence: one run burned **16,397 thinking tokens and took
  93.4s** — which would blow prod's 55s mapping timeout → OpenAI fallback; another run
  **failed to parse entirely** (thinking-model truncation, the known `google_ai.py:46-48`
  failure mode) → all-unresolved fallback. Its self-agreement collapsed to 75%.
- Budget 0: faster, better coverage, longer reasonings, zero parse failures, no latency tail.

**RECOMMENDATION: `MAPPING_THINKING_BUDGET=0` in prod** (env var on Railway; rollback = unset,
no deploy). If any mapping-quality regression surfaces post-change, first response is `1024`,
not a return to dynamic. Consider making 0 the code default after a prod bake period.

**⚠ Second incidental finding (from the failed dynamic run): the OpenAI fallback returned
HTTP 401 locally** — `OPENAI_API_KEY` in `backend/.env` is invalid/revoked, so the mapping
fallback chain is dead on this machine. Prod (Railway) key state unknown — verify. If prod's
key is also dead, every mapping timeout/parse-failure currently falls through to
all-unresolved instead of gpt-4o.

### C1. Parallelise classify's 30-item batches — DOWNGRADED by V1's split keys
**Post-V1 measurement (2026-07-02):** the 18–20s "classify∥distil" block was **distil-dominated
all along** — split timings show classify **1.8–2.4s**, distil **16.7s** (two real runs). A
single classify batch is ~2s, so even a 4-batch article check saves only ~6s here.
**Design (unchanged, still safe):** `asyncio.gather` over batch slices
(`evidence_classifier.py:550-559`, index-keyed results, no shared state).
**Measurable output & surety:** single-claim saving **0s (CONFIRMED)**; article-mode saving
**~4–6s max: MEDIUM** — worth doing only as a cheap rider, not a headline item. **Distil
(16.7s, one flash-lite call per claim, parallel across claims) replaces classify as the
tier-3 target** — its single-claim latency is one LLM call distilling all items; options are
prompt slimming or accepting it (it buys MAP input quality, F3).

### A1. Quick tier: swap MAP to non-thinking — upgraded from "latency" to product-correctness
**Design:** add `mapping_model_override: Optional[str]` (or `thinking_budget=0`) to
`PipelineConfig`; QUICK_CONFIG sets it to `gemini-2.5-flash-lite`; analyzer honours it at
`claim_map_analyzer.py:1309-1311`. Bench quick mode separately.
**Why upgraded:** verification showed Quick's 30s wall is a **hard timeout that refunds and
504s** (`agent.py:951-961`). MAP on the thinking model measured 40–44s in full mode; quick's
smaller pool (≤8 sources, 1 query/element) will be faster than that, but budget arithmetic
(extract ~2.5 + decompose ~1.4 + retrieve + map) leaves **little or no headroom** — some
fraction of paid quick calls plausibly 504-and-refund today.
**Design-review note:** before (or alongside) the fix, **measure it** — run one `POST /agent/quick`
against a multi-element claim and read `stage_timings` (needs V1, or just the profiler pattern
with `QUICK_CONFIG`). A profiler `--quick` flag is a 10-line addition.
**Measurable output & surety:**
- Quick 504s occur in prod today: **MEDIUM** (arithmetic says yes for multi-element claims;
  zero direct observations — nobody's measured quick mode).
- A1 removes MAP as quick's dominant cost and timeouts stop: **HIGH** (flash-lite mapping of ≤8
  items is a few seconds).
- Quick lands **sub-15s: MEDIUM-HIGH**; **sub-10s** (the agent-in-a-tool-loop threshold, the
  market wedge): **MEDIUM** — retrieve's floor (~5–8s at quick settings) plus overhead decides
  it, measurable the day A1 ships.

### M2. Per-claim parallel mapping (article mode)
**Design:** gate by claim count — single claim keeps today's path; multi-claim fans out the
existing per-claim call (`map_evidence_to_elements`) via `asyncio.gather`, exactly as the
batch-parse-failure retry path already does (`claim_map_analyzer.py:1263-1274`). Delete or
demote the batch path. Slight cost increase (prompt template ×N; per-claim evidence tokens
unchanged).
**Design-review note:** we have **no measurement of batch-mapping time for 5 claims** (profiler
ran 1 claim = 42s; May's 158.8s max wall hints article MAP is much larger, but that's stale
code). Get one article-mode profiler run before sizing the win.
**Measurable output & surety:** article-mode MAP wall → toward slowest-single-claim (~42s):
mechanism **HIGH** (independent calls, gate 25, path already exists); magnitude "÷N" is the
ceiling — realistic **30–50% article-MAP reduction: MEDIUM** until the article baseline exists.

### R1/R2. Retrieve fallback dechaining — DOWNGRADED, gate on V1 prod data
**What verification changed:** the ~46s tail evidence was May-code cap-hits of *unestablished*
cause (F9). The sequential Serper→Brave→SerpAPI ladder + Brave 5/10/20s retries + freshness
re-runs are all real in code (`search.py:809-841, 283-330`; `retrieve.py:1671-1727`) and remain
the right *mechanism* to attack **if** prod data shows the tail persists on current code.
**Design (unchanged, when justified):** on Serper-empty, race Brave+SerpAPI concurrently; cut
Brave to 1 retry; collapse freshness pw→py. Note Brave's global 2.5s spacing lock still
serialises concurrent Brave queries — the win is bounded.
**Measurable output & surety:** tail reduction on slow-path runs 20–30s *if the tail exists
today*: mechanism **HIGH**, applicability **LOW-MEDIUM (unmeasured on current code)**. Spend
nothing here until V1 shows prod retrieve p90.

### R3. Gov-adapter retries 3→1 — unchanged, prod-only, gate on V1
Local runs had `api_adapters=0`; contribution unmeasured. Circuit breaker already handles
hard-down APIs (`government_api_client.py:79,162-168`). **Surety: LOW** on saving size; risk LOW.

### M3. Per-claim pipelining (classify→distil→map) — unchanged, last resort
Correct per F3 (distil must stay upstream of map *per claim*). Overlap benefit ~15–18s on
article checks: **MEDIUM**. Highest structural risk (runner control flow + per-claim
`claim_map_input_hash` freeze `runner.py:2086-2121`). Only if article latency still hurts
after M1+M2+C1.

### D1. Distil — **SHIPPED `a324e8b` (2026-07-02 evening), founder no-degradation guarantee met with measurement**
> **Status:** live. `DISTIL_BATCH_SIZE=5` concurrent batches; distil 16.7–24.5s (flaky) → **10.2s
> (reliable)**; live run distilled **15/17 items (was 2/17)** — the fix REMOVED a quality loss.
> Quality gate: mapping element states **100% identical** OLD-vs-NEW on real articles (all pairs,
> budget 0); fact parity on-topic (84 vs 87). The by_stage NameError also fixed — classifier +
> distiller tokens reach cost_telemetry for the first time (distiller ~20k in / 3.9k out per
> check, previously invisible to COGS). Rollback: `DISTIL_BATCH_SIZE=15` env var.
> A/B method caveat worth keeping: judge distil changes by MAPPING outcome, not fact counts —
> counts diverge only on off-topic articles, which the upstream scorer excludes in production.

Original diagnosis (kept for the record):

**With mapping fixed, distil is the dominant stage** (24.5s in the budget-0 end-to-end run;
16.7s in earlier runs). Anatomy (`evidence_distiller.py`): items with `_full_text` ≥500 chars
are batched **15 articles per LLM call** (`BATCH_SIZE=15`, `:58`), each article truncated to
8,000 chars (`:52`), flash-lite, `max_tokens=4000`, **timeout 15s** (`config.py:222`).
Batches run **sequentially** within a claim (`:105`); claims run parallel (runner `:1937`).

**Measured latency curve** (direct `_distil_batch` probes, realistic 7.5k-char articles):

| batch size | true duration | input tok | output tok |
|---|---|---|---|
| 15 | **15.6s** | 22,883 | **3,986 (at the 4,000 cap!)** |
| 8 | 8.7s | 12,319 | 2,240 |
| 4 | 3.9s | 6,288 | 1,128 |

≈ **1s per article, linear** — flash-lite output generation (~255 tok/s) is the cost, not input.

**Two failure modes found, both live in prod:**
1. **The 15-article batch sits exactly ON its own 15s timeout** — a coin flip. Today's
   mini-budget freeze run: only 2/17 distillable items distilled (first batch timed out
   silently, snippets kept); probe run: 15.0s, *just* made it. When it fails we pay the full
   15s AND the mapper loses the distilled facts — the arbitrary-1000-char-window problem
   distil exists to fix comes back, silently.
2. **Output-cap truncation:** at batch 15 the response runs at 3,986/4,000 tokens — one long
   article away from truncated JSON (then repair-or-lose in `_try_parse_json`).

**Fix shape (D1): smaller batches (4–6 articles), fired CONCURRENTLY** (`asyncio.gather`, LLM
gate 25 absorbs it). Wall time → slowest small batch ≈ **4–7s** (from 16.7–24.5s), same total
tokens ≈ same cost, and BOTH failure modes disappear (each call finishes in ~4–6s, far from
timeout; output per call ~1.1–1.7k, far from cap). Expected whole-check: another −10–18s,
into **~55–65s** territory. Surety: latency curve MEASURED; mechanism CONFIRMED; the fix is
the same index-keyed gather pattern verified safe for C1.

**Related telemetry bug (fix with D1): `by_stage` never captured classifier/distiller tokens.**
`classifier`/`distiller` are closure-local (`runner.py:1880,1914`) but referenced as bare names
at `runner.py:2563-2587` under `try/except NameError: pass` — the NameError fires EVERY run
(the `# type: ignore[name-defined]` comments flagged it). Confirmed live: `by_stage` contains
only `analyzer`. So `cost_telemetry`'s claimed coverage ("analyzer+classifier+distiller") is
wrong — it's analyzer-only, and the cost undercount is larger than documented. Fix: hoist the
instances (or expose usage via the closure) — small, verify with one live check.

### V2. Timeout wobble diagnosis — unchanged
Mechanism confirmed (immediate `return None`, silent model swap). Which call site fires is
undiagnosed — V1's per-call logging will name it. Fix shape depends on diagnosis
(connect-vs-read timeout split; one fast retry on connect failures). **Risk LOW.**

---

## Part 3 — Revised sequence, with surety-weighted outcomes

## END-OF-DAY STATE (2026-07-02) — what shipped vs what remains

| Item | State | Result |
|---|---|---|
| **V1** telemetry | ✅ `f00e0e4` deployed | stage_timings_s persisted; thinking tokens visible; classify/distil split |
| **M1** thinkingBudget | ✅ `b1c838b` + **prod env `=0` LIVE** | MAP 35–50s → **~11–15s**, quality equal-or-better (sweep, 63 calls) |
| **D1** distil batches | ✅ `a324e8b` deployed | distil → **~10s reliable**; 15/17 distilled (was 2/17); COGS tokens visible |
| **Bench re-baseline** | ✅ `9ba5266` | GREEN gate restored; determinism proven; 3 annotated invariant adjustments |
| Full check | — | ~96s morning → **high-50s evening**; stage order now retrieve ≈ analyze ≈ distil ≈ 10–20s |
| **A1** Quick lite-map | LIKELY UNNECESSARY | budget-0 already cuts quick's mapping to ~12–15s; re-measure before building |
| **R1/R2** retrieve tail | GATED | wait for prod stage_timings_s distribution (a few days of real checks) |
| **C1/M2/M3/V2** | open, low priority | riders / article-mode; revisit after prod data |
| OpenAI key | PARKED by founder | local key dead (401); prod unverified |

Original sequence table (pre-execution, kept for the record):

| Order | Option | Expected measurable output | Surety |
|---|---|---|---|
| 1 | **V1** telemetry (timings + split keys + thoughtsTokenCount) | **BUILT + VERIFIED 2026-07-02** — live check shows thinking=4788 vs out=3599; classify/distil split 1.8s/16.7s | DONE |
| 2 | **M1** thinkingBudget sweep (V1 token data in) | MAP 42s → 17–32s; bench-gated quality | direction HIGH; magnitude MEDIUM-HIGH |
| 3 | **A1** Quick lite-mapping (+ measure quick first) | quick 504s eliminated; quick ≤15s | fix HIGH; sub-10s MEDIUM |
| 4 | **C1** parallel classify batches — downgraded (classify is ~2s/batch) | article checks −4–6s, rider only | mechanism CONFIRMED; value LOW-MEDIUM |
| 5 | **M2** per-claim parallel map (after an article-mode baseline run) | article MAP −30–50% | mechanism HIGH; magnitude MEDIUM |
| 6 | **R1/R2/R3** retrieve tail | *conditional* — only if V1 prod data shows a tail | applicability LOW-MEDIUM |
| 7 | **V2** timeout wobble fix | fewer silent OpenAI fallbacks | LOW risk; small latency |
| 8 | **M3** per-claim pipelining | article −15–18s | MEDIUM; highest complexity |

**Stacked outcome, stated with surety bands (single-claim full check, current baseline 85–93s):**
- ≥10s faster (M1 alone at any accepted budget): **HIGH**
- **~55–70s** (M1 mid-range + V2): **MEDIUM-HIGH**
- **~50–65s** (v1 doc's claim): **MEDIUM** — requires M1 to land near its optimistic end
- Article mode: no longer scales MAP with claim count (M2): mechanism HIGH, net seconds MEDIUM
- Quick tier **sub-15s** and 504-free (A1): **MEDIUM-HIGH**; **sub-10s** agent-loop threshold: **MEDIUM**

**The two commitments that make every other number honest:** V1 first (it converts four MEDIUMs
above into measurements for ~half a day's work), and replay-bench golden signals as the
unconditional quality floor on M1/M2/A1.
