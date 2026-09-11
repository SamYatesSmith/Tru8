# Run-to-run variance sources — post-retrieval and retrieval (2026-09-11)

**Trigger:** wildfire checks `580fd5b4` / `12f607d1` shared one evidence pool (24 h per-claim cache replay) yet disagreed on two tiers, one mapping, one thin-sourcing flag and one NOTE line. Heatwave pair `a093c7d2` / `bebfa026` (6 min apart) did NOT share a pool. Code reading only; no spend; every line cited is the working tree at `04e9e86`.

**Headline:** the cache replays the *raw* pool (post-filter, pre-classify, `_full_text` included). Everything after it — scoring, classification, distillation, decomposition, mapping, completion pass, coverage recovery — is re-run live, every call at temperature 0.1–0.2 with no seed, and the mechanical layer (tier weights, support floor, thin/echo notes) amplifies a single tier flip into a state change. The identical-pool disagreement is model sampling plus that amplification, not a caching bug.

---

## A. Evidence cache — what a replay actually reuses

| Source | file:line | Deterministic? | Magnitude | Cheapest measurement | Candidate fix |
|---|---|---|---|---|---|
| Key = `RETRIEVAL_CACHE_VERSION` + md5 of the **exact claim text** | `app/services/cache.py:174-181`, `:51-57`; version `app/core/config.py:455` | yes | any byte difference in the claim text is a miss | grep `[CACHE HIT]` / `[CACHE OK]` / `[CACHE SKIP]` in Railway logs for the two check ids | none needed; document the key |
| Payload = the post-filter pool **before** scoring/classify/distil, incl. `_full_text` | write `app/workers/pipeline.py:299-320`; `_full_text` set `app/pipeline/retrieve.py:1994`; distil cleanup runs later `runner.py:2149-2206` | yes (JSON list, order preserved: `cache.py:85`, `:69`) | — | `redis-cli GET tru8:evidence_extract:<ver>:<md5>` while the 24 h key lives | keep; this is the free frozen pool for every measurement below |
| Replay skips **only** the planner + search + fetch. Scoring, classify, distil, decompose, map, completion, recovery all re-run | hit path `workers/pipeline.py:213-236` (no `query_plan` written → no queryPlan on the page); runner stages `runner.py:1857-1911`, `:2094-2228`, `:2422`, `:2474-2759` | n/a | this is the whole reason an identical pool disagrees | — | — |
| Quality gate: pools `< MIN_SOURCES_FOR_CACHE` (2) are never written | `workers/pipeline.py:306-310`; `config.py:341` | yes | rare | log line `[CACHE SKIP]` | — |
| Runner-level retrieve timeout keeps partial evidence but **never reaches the cache write** | `runner.py:1608-1630` vs write at `workers/pipeline.py:299` | yes | a slow first run leaves no key for the second | log `[STAGE ERROR] ... stage=retrieve` on the first check | write the partial pool too, tagged |
| Redis unavailable → `get`/`set` return None/False silently | `cache.py:62-63`, `:78-79` | — | whole check runs fresh | `Cache set error` warnings | — |
| Claim extraction has its own 6 h cache keyed on the submitted content md5 | `workers/pipeline.py:56-95`; `cache.py:24`, `:164-172` | yes | a byte-identical submission gets byte-identical claim text, so the evidence key matches; any edit (whitespace, punctuation, URL vs text mode) re-extracts at temp 0.1 (`extract.py:907-909`) → different wording → different evidence key | compare `claims[].text` of the two checks in the DB | — |
| Coverage recovery re-runs on a replayed pool: qualifies on element **states**, searches live, appends `ev-rec-*`, classifies and maps them with fresh calls | `runner.py:2474-2498`, `:2546`, `:2626`, `:2675-2691` | **no** | adds live-search items to a "replayed" pool | count `ev-rec-*` ids per check | none (by design); label them on the page |
| Post-filter recovery (`ev-rpf-*`) fires when a claim has < 5 items after scoring — live search | `runner.py:1919-2022` | **no** | only thin pools | count `ev-rpf-*` | — |

**Heatwave pair miss — candidates, in order of likelihood:** (1) claim text differed by a byte (the md5 key is unforgiving; the extract cache only helps if the *submission* was byte-identical); (2) the first run hit the runner-level retrieve timeout path and never wrote the key; (3) the first pool had `< 2` items; (4) `ENABLE_STRUCTURED_EXTRACTION` suffix (`cache.py:179-180`) differed between deploys. A pd/pw plan gives a 1 h TTL (`workers/pipeline.py:152-161`), so 6 min is not the TTL. Decide from the log lines named above — the code alone cannot.

## B. Classification (`app/pipeline/evidence_classifier.py`)

| Source | file:line | Deterministic? | Magnitude | Cheapest measurement | Candidate fix |
|---|---|---|---|---|---|
| Model `GOOGLE_LLM_MODEL` (default `gemini-3.5-flash-lite`), **temperature 0.1**, no seed, `thinkingConfig` omitted → provider default | `:715-717`, `:1063-1069`; `config.py:117-119`; OpenAI fallback temp 0.1 `:1093` | **no** | UNMEASURED for this stage; 93.7% accuracy (PQ) is vs labels, not self-agreement | frozen pool × k repeats of `classify_batch` on deep copies (pattern: `scripts/recital_repeat_probe.py`); ~3k tokens in, ≈ 0.05p/call on flash-lite → 20 repeats ≈ 1p | temperature 0.0 + `seed`; `responseSchema` for the classify label |
| Whole-batch heuristic fallback on any failure: 45 s timeout (not retried, `google_ai.py:434-439`), parse failure, both providers down | `:718`, `:784-789`, `:825-830`; `_parse_classification_response` drops bad entries `:960-995` | **no** (latency-dependent) | a whole batch switches classifier; `classification_method` = `heuristic` is the stored tell | compare `classification_method` per item across the two checks (free, DB) | — |
| No `responseSchema` on classify; JSON repair may drop indices → those items go heuristic | `claim_map_analyzer.py:2134-2146` shows schemas exist only for mapping labels; classify passes none `:1063-1069` | no | per-item | as above | add a schema |
| Batch composition = pooled list in `evidence.items()` insertion order, sliced by 30; prompt order = pool order | `runner.py:2107-2115`; `:43`, `:780-782` | yes given pool order (replay preserves it) | ≤ 30 items → ONE batch, identical prompt both runs | — | — |
| Prompt reads `snippet` then `text` (300 chars) while distil runs **concurrently** and overwrites `text` | `:914-916`, `:719`; concurrency `runner.py:2208-2228`; overwrite `evidence_distiller.py:164`; main web items carry `text` only `retrieve.py:1980` | **race** for batch ≥ 2 only (batch 1's prompt is built before the first await) | nil at 16 items; real at > 30 | — | build all classify prompts before `gather` |
| Post-passes (URL override, quality floors, factcheck promotion, arXiv) | `:809-821`, `:621-700`, `:843-870` | yes given (tier,type) | — | — | — |
| 429/503 retry with jittered backoff = a fresh sample of the same body | `google_ai.py:34-36`, `:250-253`, `:480-497` | no | rare | — | — |

## C. Relevance scoring and distillation

| Source | file:line | Deterministic? | Magnitude | Cheapest measurement | Candidate fix |
|---|---|---|---|---|---|
| Scorer: Google temp 0.1, 60 s; OpenAI fallback gpt-4o-mini temp 0.1 | `relevance_scorer.py:364-366`, `:470-498` | no | score-1 items are **excluded** (`:728-760`) → pool membership for mapping changes; failure → pass-through, no exclusions (`:680-684`) | k repeats on the frozen pool; ≈ 0.1p/call | temp 0 + seed |
| Scorer has its own 1 h Redis cache keyed on claims + sorted URLs | `:178-188`, `:639-660`; TTL `config.py:354-355` | yes within 1 h | the wildfire pair (13 min) very likely **replayed scores** → not a suspect there; any URL difference re-samples the whole call | `relevance:v2:*` key present | — |
| Cap 50, round-robin, stable order (sorted claim pos, list order) | `:204-307`, `:618-637` | yes | — | — | — |
| Distil: `gemini-3.5-flash-lite`, **temp 0.0**, 15 s timeout, batches of 5 concurrent, timeout not retried | `evidence_distiller.py:68-72`, `:127-141`, `:207-213`; `config.py:303-316` | no (0.0 is not bit-deterministic; timeouts are latency) | a failed batch keeps the raw snippet for 5 items (`:144-146`) → `content_basis` snippet↔distilled → the **mapper reads different text** (`snippet or text`, `claim_map_analyzer.py:1739`) | `content_basis_breakdown` in each element basis (free, DB); k repeats ≈ 0.3p/run | longer timeout; retry once |
| Shared 25-slot Google semaphore across classify, distil, other in-flight checks | `google_ai.py:31-32` | no | latency → timeouts | — | — |

## D. Decomposition and mapping (`app/pipeline/claim_map_analyzer.py`)

| Source | file:line | Deterministic? | Magnitude | Cheapest measurement | Candidate fix |
|---|---|---|---|---|---|
| Decomposition: flash-lite, **temp 0.2**, no schema, then conditional repair calls (atomicity, unstated quantity, direction at temp 0.0) each gated on the previous output | `:1831-1835`, `:1596`; `config.py:648`; `:2334-2338` | **no** — highest temperature in the pipeline | element wording = the mapping target; audit 2026-07-15 §314 already records "element sets differ per run" | **free:** compare `claim_map_input_hash` (`runner.py:2361-2393`, elements + evidence ids) between the two checks. If it differs, decomposition, not mapping, is the first cause | temp 0; seed; cache the claim_map by claim text |
| Mapping model `MAPPING_GOOGLE_MODEL` (default `gemini-3.7-flash`), **temp 0.2** (`ANALYZER_TEMPERATURE`), 1000-char snippets, evidence in pool order | `config.py:658-659`, `:652`, `:292-293`; `:1598`, `:1734-1756` | no | measured on frozen pools (`audit/2026-07-02_pipeline_latency_options.md:79-104`): self-agreement **94.4 %** dynamic / **91.7 %** budget 0 on easy pools; **75 %** dynamic / **100 %** budget 0 on adversarial pools | `scripts/mapping_budget_sweep.py --sweep --repeats N --budgets 0` (existing harness, ≈ 1p/call) | temp 0; seed; thinking off |
| `MAPPING_THINKING_BUDGET` default **None = dynamic thinking**; prod env value on the 3.7 model unverified today | `config.py:711-716`; `:1611-1613`, `:2162-2164`; 2.5→3.x field split `google_ai.py:41-56, 93-113` | config | dynamic thinking was the *least* self-consistent arm | `thinking_tokens` in `cost_telemetry.by_stage` (free) | pin 0 / lowest level and verify the request body |
| Null-reasoning retry re-samples the whole mapping | `:1768-1786` | no | — | log `Null reasoning detected` | — |
| **Completion pass**: second call (temp 0.2, 25 s) on whatever the main pass left unreferenced; its input set is the main pass's output → cascade; failure preserves main pass | `:3238-3297`, `:2035`, `:1794` | no | a Copernicus page "mapped↔unmapped" is exactly this pass's remit | `[MAP COMPLETION]` log; `census added N refs` | run once, merge deterministically |
| 55 s Google timeout → **OpenAI gpt-4o** fallback = a different model | `:1615`, `:2148-2240`; `config.py:649` | no | `metadata.mapping_model` is the stored tell | compare across the two checks (free) | — |
| State is mechanical from refs with **tier weights 3/2/1**, strict `>` 2×, support floor 3 | `:933`, `:1084-1122`, `:992-996`; override `:2531-2539` | yes given refs+tiers | one tier flip (primary 3 ↔ commentary 1) moves the weighted count; a lone item's tier decides supported vs unresolved | recompute from stored refs (free) | — |
| Thin / echo / repetition notes keyed on `tier == "primary"` and tier mix | `:1396-1449`; `app/utils/corroboration.py:262-270`, `:500` | yes given tiers | the thin flag present↔absent follows the Senedd tier flip directly | recompute (free) | — |
| Scope gates: deterministic given inputs; recital gate arms only when `subjects` non-empty | `:2979-3083`, `:2549-2579`; `scripts/recital_repeat_probe.py:13-17` | yes | — | — | — |

## E. Google AI client (`app/services/google_ai.py`)

| Source | file:line | Deterministic? | Magnitude | Cheapest measurement | Candidate fix |
|---|---|---|---|---|---|
| Default temperature 0.1 for every caller that omits it | `:259`, `:372` | config | — | — | — |
| Body sends only `temperature`, `maxOutputTokens`, `responseMimeType`, optional `responseSchema`, optional `thinkingConfig`. **No `seed`** — the Gemini `generationConfig` accepts one (best-effort determinism), we never set it | `:401-418`, `:278-285` | config | unmeasured | add `seed`, repeat the classify probe with and without | plumb `seed` from settings |
| Timeouts never retried; 429/503 retried ≤ 5× with jitter | `:434-439`, `:34-36`, `:480-497` | no | — | — | — |

## F. Retrieval — why two identical retrievals differ by 25/40 URLs (measured `audit/2026-08-20_independent_source_lane_design_review.md:135`)

| Source | file:line | Plausible share of the 62 % |
|---|---|---|
| Query planner is an LLM call → query strings differ per run (they are the cassette keys) | `app/pipeline/query_planner.py` ("Try Google first…"); merge `retrieve.py:504-572` | large: a different query is a different result set |
| Serper → Brave → SerpAPI per-query fallback on failure or empty | `app/services/search.py:814-835` | medium: a provider swap changes ranking wholesale |
| Web ∥ API merge under a 45 s all-or-nothing wait; fetch-phase 30 s deadline cancels stragglers by latency | `retrieve.py:1812-1816`, `:2436-2471` | medium: which pages survive is latency |
| Fetch failure → engine snippet instead of page text (`is_snippet_fallback`) | `:2560-2576` | content, not membership |
| Runtime blocklist is **process state** written by earlier checks' 403s | `app/services/evidence.py:23-70` | small |
| Weighted round-robin and dedup are deterministic given candidate order | `:2340-2345`, `:2195-2235` | nil |
| Web search has no result cache (`cache_search_results` has no callers); API adapters go through `search_with_cache` | `retrieve.py:2923` | — |

---

## Ranked: the three most likely causes of the identical-pool disagreement

1. **Classifier sampling at temperature 0.1, no seed, no schema, whole-batch heuristic fallback** (`evidence_classifier.py:1063-1069`, `:784-789`). Explains the Senedd and ISRM tier flips directly, and the thin-sourcing flag by arithmetic (tier feeds `_STATE_TIER_WEIGHTS` and the `tier == "primary"` tests in `corroboration.py:262-270, :500`). Three of the four observed deltas trace here. Check `classification_method` on both records first: if one says `heuristic`, it was a timeout, not a roll.
2. **Mapping sampling at temperature 0.2 with dynamic thinking by default, then a second cascade call (completion pass)** (`claim_map_analyzer.py:1751-1756`, `:3285-3290`; `config.py:711-716`). Explains Copernicus mapped↔unmapped and the NOTE wording (a fresh `uncertainty`/`reasoning` string each run). Measured self-agreement is 75–94 % with dynamic thinking; verify `MAPPING_THINKING_BUDGET` is actually 0 in prod on the 3.7 model and read `thinking_tokens` in the stored telemetry.
3. **Distil timeout coin-flip changing the text the mapper reads** (`evidence_distiller.py:69`, `:144-146`; mapper reads `snippet or text` `:1739`). The 15 s deadline on 5-article batches, sharing a 25-slot semaphore with the classifier, decides per batch whether the mapper sees bullets or a raw snippet. `content_basis_breakdown` in each element basis shows it for free.

**Not ranked but check first because it is free:** decomposition at temperature 0.2. If `claim_map_input_hash` differs between `580fd5b4` and `12f607d1`, the elements themselves differed and cause 1–3 were mapping onto different questions.

## Measurement design (no search; model calls only)

The replay bench **cannot** measure any of this: cassettes replay recorded model responses byte-for-byte (`scripts/replay_bench/cassette.py:14-26`), so the bench proves the *code* is deterministic given fixed model output, which it is. What can measure model variance is a frozen-pool repeat harness, and two already exist (`scripts/mapping_budget_sweep.py`, `scripts/recital_repeat_probe.py`).

Proposed `scripts/variance_probe.py` (ask before running — paid):
1. **Freeze** the wildfire pool from the live Redis key (`tru8:evidence_extract:2026-09-09:<md5>`, has `_full_text`) or, failing that, the stored `analyzer_input_evidence` ledger entry. Freeze the stored claim_map elements too.
2. **Arm A — classify only:** `classify_batch` × 20 on deep copies. Report per-item tier agreement. Cost ≈ 1p total.
3. **Arm B — map only, elements fixed, tiers fixed to run 1's:** `map_evidence_to_elements` × 10 with `MAPPING_THINKING_BUDGET` at the prod value, then × 10 at 0. Report per-element ref-set Jaccard and state agreement. Cost ≈ 20 calls (main + completion) ≈ 20–40p.
4. **Arm C — full post-cache chain** (classify → distil → derivation → map → completion → state) × 10 with elements fixed, then × 5 with `decompose_claim` re-run. Cost ≈ 7 calls/run ≈ 3p/run → ~45p.
5. **Arm D — same as A and B with `seed` plumbed and temperature 0**, to price the fix before shipping it.
Read-out: which arm's disagreement rate matches the four-delta pattern observed today. Total ≈ £1.

Free first: pull both checks' `classification_method`, `content_basis_breakdown`, `mapping_model`, `thinking_tokens` and `claim_map_input_hash` from the DB. Those five fields already partition the four deltas among causes 1–3 and decomposition without a single model call.
