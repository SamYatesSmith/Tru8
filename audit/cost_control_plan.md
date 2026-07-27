# Cost Control Plan — Agent /full Tier (Consolidated)

**Date drafted:** 2026-04-28
**Date consolidated:** 2026-04-29
**Status:** Pre-launch. No live users. No production data yet.
**Supersedes:** `mapper_efficiency_plan.md` — mapper items shipped as commit `b791f0a`; original spec preserved as historical record.

---

## Governing principle

**No change in this plan is permitted to degrade output quality.**

Quality has been earned through deliberate work — NF-12 mapper prompt rewrite, NF-15 typed entities at 97.2% accuracy, the 1000-char snippet bump, the move to gemini-2.5-flash on the mapper. Every saving has to come from waste, not from output.

Five phases:

- **Phase 1 — Required pre-launch.** Closes the active cost hole, ships the load-bearing instrumentation, resolves the launch-visible decision.
- **Phase 2 — Optional pre-launch cleanup.** Documentation alignments and rate-limit consistency.
- **Phase 3 — Post-launch monitoring & escalation.** Watches the single load-bearing variable (mapper-fallback rate) and runs the real-time budget kill switch.
- **Phase 4 — Production-data-gated hypotheses.** Cost levers, each unblocked only by production data identifying it as relevant *and* gated by eval parity.
- **Phase 5 — Structural pricing decision.** Per-claim pricing if and only if production cost data warrants it.

Anything that requires a quality trade-off is explicitly out of scope — see the bottom of this document.

---

## The cost problem in numbers

Validated 2026-04-29 against current code (`config.py`, `agent_pricing.py`) and current Gemini 2.5 Flash + OpenAI gpt-4o list rates.

Worst-case `/agent/full` variable cost depends almost entirely on **whether the Google AI mapping call succeeds or falls back to gpt-4o**:

| Scenario | LLM | Search | Total | vs 15p charge |
|---|---|---|---|---|
| 5 claims, Google primary, no retries | ~5p | ~2p | **~7–8p** | margin-positive |
| 5 claims, gpt-4o fallback on mapping | ~23p | ~2p | **~25p** | 1.7× charge |
| 5 claims, gpt-4o fallback + 1 retry | ~28p | ~2p | **~30p** | 2× charge |
| 12 claims (dashboard hole), Google primary | ~10p | ~4p | **~14–15p** | break-even |
| 12 claims (dashboard hole), gpt-4o fallback | ~38p | ~4p | **~42–45p** | 3× charge |

Two consequences drive the plan:

1. **The 12-claim dashboard hole is the active danger.** Phase 1.1 closes it.
2. **The mapper-fallback rate is the single load-bearing variable.** At <1% it's noise; at 30% it kills the margin. Phase 1.2 instruments it; Phase 3 watches it; Phase 4 acts on it.

Everything else in this plan is small change.

---

## What has shipped (`b791f0a`)

Two zero-quality-risk efficiency changes to the evidence mapping stage. Originally scoped in `mapper_efficiency_plan.md` (now superseded).

### Mapper Item 1 — Dropped `[Content: …]` from evidence formatting

Removed at three sites in `claim_map_analyzer.py` (per-claim mapping, batched mapping, coverage-recovery mapping). The `content_basis` field was rendered into the mapper prompt but never referenced by `MAPPING_PROMPT` or `BATCH_MAPPING_PROMPT` rules. `_compute_element_basis` continues to read `content_basis` directly from the evidence dict — basis breakdown metadata unaffected.

**Strategic value:** removes an unused field from the prompt. Honest cost saving: <0.05p per call. Worth shipping because it's free; not a cost lever.

### Mapper Item 2 — Gemini `response_schema` on mapping calls

`_MAPPING_RESPONSE_SCHEMA` and `_BATCH_MAPPING_RESPONSE_SCHEMA` defined alongside `_VALID_STATES` and `_VALID_RELATIONSHIPS`. Plumbed through `_call_llm → _call_google → call_google_ai_with_usage`. Older `call_google_ai` (used by 7 other modules) untouched. `uncertainty` omitted from schema rather than typed nullable, since Gemini's nullable handling varies across SDK versions; the defensive parser already treats missing uncertainty as `None`.

**Strategic value:** reliability, not direct cost saving. Each avoided per-claim retry on the mapping path saves ~18p in the worst case (fallback retry is the most expensive single call in the pipeline). One avoided retry per 100 calls outweighs 1000 calls of token-shaving.

### Open follow-on (Phase 4.6)

`response_schema` is enforced only on the Gemini path. The OpenAI fallback — where parse failures matter most because retries cost 5× more — has no equivalent constraint. Captured as Phase 4.6.

---

## Phase 1 — Required pre-launch

### 1.1  Enforce select-claims cap of 5 (single source of truth)

**Files:**
- `backend/app/api/v1/checks.py:1213-1215` — `SelectClaimsRequest.selected_positions` (no validator today)
- `backend/app/api/v1/agent.py:843` — hardcoded `max_selected = 5` literal in agent article auto-select
- `backend/app/core/config.py:343` — `MAX_SELECTED_CLAIMS` constant (the canonical value)

The docstring on `SelectClaimsRequest` says "Maximum 5 claims per check" but no Pydantic validator enforces it. A user clicking 12 boxes in the dashboard interactive flow today runs the worst-case 12-claim Phase 2 with no cost guardrail. Worst-case cost at 12 claims is **~15p on the Google-primary path (already at the 15p charge line) and ~45p if mapping falls back to gpt-4o** — i.e. the cap isn't a polish item, it's the difference between margin-positive and 3× the charge.

The agent path is *currently* safe — `agent.py:843` enforces the same cap, but as a hardcoded literal `5` rather than a reference to `settings.MAX_SELECTED_CLAIMS`. So the cap lives in three places: the config constant, the (missing) validator, and an unrelated hardcode. Three coincidentally-aligned facts instead of one fact.

**Change (one PR, three sites):**
1. Add `max_length=settings.MAX_SELECTED_CLAIMS` to `SelectClaimsRequest.selected_positions`.
2. Replace the `max_selected = 5` literal at `agent.py:843` with `settings.MAX_SELECTED_CLAIMS`.
3. Confirm `MAX_SELECTED_CLAIMS=5` in `config.py:343` is the intended value and add a comment noting it is the single source of truth referenced by both call sites.

**Quality impact:** zero.
**Cost impact:** drops dashboard worst case from ~45p to ~30p, normal case from ~15p to ~7–8p.

### 1.2  Sentry alarm: Google AI fallback fired

**File:** `backend/app/pipeline/claim_map_analyzer.py:830-836`

Today this logs at WARNING when Google AI times out and the pipeline falls back to OpenAI. Without an alert, we won't know if this fires on 1% or 30% of runs — and **that ratio is the single most important number for our unit economics** (see "Cost problem in numbers" above).

**Change:** add a counter or Sentry alert rule that fires on the warning text "Google {label} timed out", grouped by `label` so we can see whether it's mapping vs decomposition that's failing.

**Quality impact:** zero (observability only).
**Cost impact:** turns the load-bearing cost variable from invisible to measurable.

### 1.3  Persist per-stage LLM token usage

**File:** `backend/app/api/v1/agent.py:872-877` (where `pipeline_metrics` is attached to `tx_metadata`)

Today the attached metrics are aggregate (`llm_input_tokens`, `llm_output_tokens` total). The `ClaimMapAnalyzer._token_usage` accumulator (`claim_map_analyzer.py:860`) tracks per-stage but is not persisted. Per-stage data is the substrate for Phase 3.2 (kill switch), Phase 3.3 (200-run review), and any future Phase 4 decision.

**Change:** plumb stage-level token counts into `tx_metadata["metrics"]["by_stage"]`. Add a `model_used` field per stage to distinguish Google-primary from OpenAI-fallback runs.

**Quality impact:** zero. Pure instrumentation.
**Cost impact:** unlocks Phase 3 and Phase 4.

### 1.4  Manifest signing — enabled (deployment-only at production)

**Status (2026-04-29):** Decision taken. Manifest signing will ship enabled.

**Rationale:** M-04 is fully built and tested (30+ unit tests covering signing, verify roundtrip, key rotation). Failure mode is graceful — if the flag is on but the key is missing, `_manifest` returns null with a warning log (no crashes). The `/developers` page (line 877-878) explicitly tells agents the manifest exists and points them at `GET /verify/{check_id}`. Shipping with the feature disabled would contradict documented behaviour.

**What changed:**
- `backend/.env.example` — documented `MANIFEST_*` env vars with generation instructions.
- `backend/.env` — local dev key generated and `MANIFEST_SIGNING_ENABLED=True` set.

**What still needs to happen (deployment-only, no code):**
1. Generate a separate production key: `openssl rand -base64 32`
2. Set in Railway:
   - `MANIFEST_SIGNING_ENABLED=True`
   - `MANIFEST_SIGNING_KEY=<base64 output>`
   - `MANIFEST_KID=tru8-2026-03` (or current month-ish identifier)
   - `MANIFEST_SIGNING_KEYS={}` (leave empty until first rotation)
3. Deploy. Verify `_manifest` block populates in `/agent/full` responses.
4. Back up the production key somewhere safe (password manager / secrets vault). Losing it makes old checks unverifiable.

**Operational note:** rotation cycle assumed at 90 days, old keys remain valid for 180 days. Procedure documented in `backend/app/core/manifest_signer.py:6-10`.

**Quality impact:** zero. Manifest signing is a trust/credibility feature, not a pipeline quality feature.

---

## Phase 2 — Optional pre-launch cleanup

### 2.1  Tighten /agent/full rate limit to match documentation

**File:** `backend/app/api/v1/agent.py:662`

The /developers page advertises 5/minute. The code is currently `@limiter.limit("10/minute")`.

**Change:** change decorator to `@limiter.limit("5/minute")`.

**Caveat:** verify whether `slowapi` is rate-limiting per-IP or per-key in this app's configuration. If per-IP, "5/min × 60 × 24 = 7,200 max calls/day" is a ceiling-per-source, not a ceiling-per-attacker — an attacker rotates IPs, not keys.

**Quality impact:** zero.
**Cost impact:** caps blast radius of a misconfigured agent.

### 2.2  Fix webhook retry documentation

**File:** `web/app/developers/page.tsx` (around the "Delivery guarantee" block)

The page advertises "3 attempts, exponential backoff". The code is `MAX_RETRIES = 2` (`backend/app/services/webhooks.py:27`), giving exactly 2 attempts.

**Change:** update the page to "2 attempts" (smaller change, aligns docs with code).

**Quality impact:** zero (documentation only).

---

## Phase 3 — Post-launch monitoring & escalation

### 3.1  Production fallback-rate watch

After launch, monitor the Sentry counter from 1.2 weekly:

- **<1%** → no action; cost plan complete.
- **1–5%** → continue monitoring; consider Phase 4.1 as warm spare.
- **5–10%** → trigger Phase 4.1 (cap thinkingBudget) eval campaign.
- **>10%** → escalate to mapper architecture review (out of scope of this plan).

### 3.2  Real-time budget kill switch

**Trigger:** any single check exceeds 30p variable cost (computed from per-stage data persisted by 1.3).

**Action:** log Sentry critical with the full per-stage breakdown, and consider downshifting that key to Quick tier on subsequent calls.

The original plan was purely retrospective. This adds the real-time guardrail — an individual runaway check is caught at completion, not at month-end aggregation.

### 3.3  Blended-cost vs revenue review at 200 runs

After ~200 production calls, compute median and 90th-percentile variable cost from the persisted per-stage data:

- **Median ≤ 9p** → flat 15p pricing holds; no action.
- **Median 9–12p** → continue monitoring; consider Phase 4 levers.
- **Median > 12p** → escalate to Phase 5 (per-claim pricing).

This replaces the original Phase 2 (synthetic 50-check measurement). Real production traffic gives better data than a curated test set, with no manual effort.

---

## Phase 4 — Production-data-gated hypotheses

Each lever below is a **hypothesis**, not a decision. Each ships only after both:
(a) production data from Phase 3 identifies it as relevant, AND
(b) `eval_mapping_model.py` (or the relevant eval) confirms no quality regression.

**Kill criterion (applies to all):** if eval shows <90% element-state agreement with baseline at the lowest tested setting, abandon the hypothesis rather than tuning further. Evals are for ship/no-ship, not for parameter search.

### 4.1  Cap `thinkingBudget` on the mapper

**Current state:** `services/google_ai.py:200-207` does not set `thinkingConfig.thinkingBudget`. Gemini default is dynamic — model decides. For gemini-2.5-flash this means thinking is on with no cap.

**Hypothesis:** capping thinking at 1024 tokens preserves mapper element-discrimination quality.

**Test:** run `eval_mapping_model.py` at three settings — uncapped (baseline), thinkingBudget=2048, thinkingBudget=1024. Measure: element state agreement, context-share ratio per element, NF-12 mapper element-collapse rate, and **per-element reasoning quality** (manual spot-check of `reasoning` field — original plan only measured states).

**Ship criterion:** ≥98% element-state agreement with baseline AND no NF-12 collapse-rate increase AND no qualitative reasoning regression. Ship at the lowest setting that passes.

**Co-evaluate with 4.4** — same eval campaign, different parameter axes.

### 4.2  gpt-4o-mini for OpenAI fallback decomposition

**Current state:** `config.py:349 DECOMPOSITION_MODEL=gpt-4o`, `config.py:353 ANALYZER_MODEL=gpt-4o`. Both fire only when Google times out.

**Hypothesis:** decomposition (atomising a claim into 1–5 elements) is less demanding than mapping; gpt-4o-mini is sufficient.

**Test:** run NF-12 cases through three configurations — both gpt-4o (baseline), DECOMPOSITION=mini/ANALYZER=gpt-4o (split), both gpt-4o-mini.

**Ship criterion:** decomposition can move to gpt-4o-mini if element count, element text, and downstream mapping output are statistically equivalent to gpt-4o. **Mapping fallback stays on gpt-4o** unless eval is unambiguous — fallback is the worst time to also lose quality.

### 4.3  Trim mapper input from 20 → 16 sources

**Current state:** `config.py:325 MAX_SOURCES_PER_CLAIM=20`. Items beyond 20 are still shown in the Librarian view; mapper sees the top 20 by relevance.

**Hypothesis:** items ranked #17–20 rarely change mapping outcomes.

**Test:** run the same 20 claims through the mapper at MAX_SOURCES_PER_CLAIM=20 and 16. Compare element state assignments and mapped evidence_id sets.

**Ship criterion:** element-state agreement ≥99% AND mapped evidence_ids overlap ≥95%. Otherwise hold at 20.

### 4.4  Conditional distillation skip on primary-tier-rich claims

**Current state:** distillation runs on every evidence item with full text ≥500 chars (`evidence_distiller.py:65`).

**Hypothesis:** when a claim already has 3+ primary-tier sources (data, official records), distillation adds little — primary sources are usually already structured.

**Test:** run claims with strong primary-tier coverage twice (with/without distillation). Compare mapping output.

**Caveat:** primary-tier classification has a heuristic fallback. Test specifically on claims classified as primary by the heuristic (not just LLM) — if the heuristic mis-classifies a news source as primary, distillation gets skipped on the article that needed it most.

**Ship criterion:** mapping output unchanged → distillation becomes conditional. Otherwise keep universal.

**Co-evaluate with 4.1** — same eval campaign.

### 4.5  Asymmetric `ANALYZER_MAX_TOKENS` cap on fallback path only

**Current state:** `config.py:356 ANALYZER_MAX_TOKENS=12000`. Universal reduction is rejected (would truncate Gemini, see Out of Scope). But the fallback path (gpt-4o, 4× output rate) is where output token caps matter most — 12k tokens × $10/M = ~10p for a single output.

**Hypothesis:** capping at 6000 tokens on the OpenAI fallback path only does not truncate output (gpt-4o doesn't burn output budget on thinking like Gemini does).

**Test:** run NF-12 cases with the cap applied to OpenAI calls only. Verify no truncation in the JSON output.

**Ship criterion:** zero truncation events across the eval set. If truncation observed, raise cap to 8000 and retest.

### 4.6  OpenAI structured outputs on fallback (parity with Mapper Item 2)

**Current state:** Mapper Item 2 added `response_schema` on Gemini calls. OpenAI fallback has no equivalent — parse failures still happen on the most expensive code path.

**Change:** add `response_format: {type: "json_schema", json_schema: ...}` to gpt-4o calls when the fallback fires. Same enum/structure constraints as the Gemini schemas.

**Hypothesis:** parse-fail rate on the fallback path drops to near-zero.

**Test:** monitor parse-fail counter from 1.2 instrumentation; should be strictly lower post-change.

**Ship criterion:** parse-fail rate on fallback ≤ Gemini-path rate. No quality regression on eval (structured outputs preserve the prompt's contract).

---

## Phase 5 — Structural pricing decision

### 5.1  Per-claim pricing on /agent/full

**Trigger:** Phase 3.3 review shows median variable cost > 12p at production volume.

**Current model:** flat 15p per call regardless of claim count.

**Alternative model:** £0.05 base + £0.03 per selected claim, capped at 5 claims = £0.20 max.

**Trade-off:** simpler flat pricing is easier to communicate; per-claim pricing aligns price with cost. Note that the agent picks claim count and has no price-signal incentive — the cap (1.1) does the cost-bounding work either way. So this is primarily about whether the variance lands on us or on the customer.

**Decision:** evaluate after Phase 3.3 data lands. Don't pre-tune.

---

## Out of scope — explicitly rejected

The following levers were considered and rejected because they carry quality risk that cannot be ruled out without measurement, OR because they conflict with the no-quality-loss principle:

| Lever | Why rejected |
|-------|--------------|
| Universal `ANALYZER_MAX_TOKENS` reduction (12000 → 6000) | Would truncate mapping output mid-JSON when Gemini thinking model uses heavy budget. Asymmetric fallback-only version captured as Phase 4.5. |
| Reduce `MAX_SELECTED_CLAIMS` to 3 | Reduces product promise ("we cover the article"). Marketing-relevant, not just cost-relevant. |
| Switch mapper from gemini-2.5-flash → gemini-2.5-flash-lite (no thinking) | Direct quality risk on the highest-stakes call in the pipeline. Phase 4.1 captures the less drastic alternative (cap thinking, don't disable). |
| Disable evidence distillation universally | Mapper would receive raw article text instead of bullet-point facts. Quality risk on text-heavy evidence. Phase 4.4 captures the conditional-skip alternative. |
| Lower `EVIDENCE_SNIPPET_LENGTH` from 1000 to 500 | The 1000-char bump was a deliberate quality investment (PQ-01). Reverting it directly contradicts that work. |
| Reduce `max_queries_per_element` from 3 to 2 in Full mode | Halves search cost (~1p saving) but reduces evidence breadth on multi-element claims. Quality risk on coverage. *Reconsider only if Phase 3.3 shows search dominates the bill.* |
| Lookup cache window expansion | Originally listed as Phase 3.5 hypothesis; on review it's a 5-minute "verify retention policy is unbounded" check, not a hypothesis. Do as part of 1.3 if the question arises. |

---

## Order of operations

1. **Pre-launch:** Phase 1 (1.1, 1.2, 1.3, 1.4) + Phase 2 if convenient.
2. **Launch:** ship.
3. **Week 1–4 post-launch:** Phase 3 (3.1 weekly watch, 3.2 kill switch live, 3.3 review at ~200 runs).
4. **If Phase 3 escalation triggers:** Phase 4 hypotheses. Run 4.1 + 4.4 as a single eval campaign first (same `eval_mapping_model.py` invocation, two parameter axes). 4.6 can ship in parallel — it's reliability not quality.
5. **If 3.3 review warrants:** Phase 5 pricing review.

Pre-launch effort: ~half a day of code + the manifest decision.

---

## What this plan does not do

- It does not lower the price.
- It does not reduce the number of claims processed.
- It does not switch any model on the primary path (Gemini stays as the primary provider for every stage it currently serves). Phase 4.2 considers an OpenAI-fallback-only switch, which is a different code path.
- It does not relax any of the quality-improving changes shipped in NF-12, NF-15, the snippet bump, or the prompt rewrites.
- It does not pre-tune cost levers based on synthetic measurement; production data triggers Phase 4.

What it does do is close the worst-case dashboard hole, fix two documentation discrepancies, build the observability needed to make data-driven decisions, ship a real-time budget kill switch, and queue up six hypotheses that — only if production data warrants — could meaningfully reduce variable cost without touching output quality.
