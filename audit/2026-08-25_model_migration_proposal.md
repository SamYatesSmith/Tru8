# Model migration proposal — replacing Gemini 2.5 before 16 October 2026

**Date:** 2026-08-25 · **Status:** PROPOSAL, awaiting founder decision
**Deadline:** 52 days. Every primary LLM stage is on a model that retires.

---

## 1. The pressure, stated plainly

`GOOGLE_LLM_MODEL=gemini-2.5-flash-lite` (extract, decompose, classify, select,
query-plan, query-answer, distil, map-completion, recovery-mapping) and
`MAPPING_GOOGLE_MODEL=gemini-2.5-flash` (evidence mapping) **both retire on
16 October 2026**. When they go, the pipeline stops producing output.

Google's stated position is that the date is "earliest possible" and that a
confirmed date carries at least six months' notice once Gemini 3 is fully GA.
**Planning on that slip is not a plan.** The table date is the date we build to.

Two consequences shape everything below:

- **The decision cannot wait.** A model swap invalidates every replay cassette
  (request body is the cassette key), so the usual regression net does not
  apply. The verification has to be built alongside the change, not after it.
- **It is not a string swap.** Verified live 2026-08-01: a lone `thinkingBudget`
  is a **hard 400** on Gemini 3.x. The day the model string changes, every
  mapping call 400s, `google_ai.py:254-256` returns `None` without retry, and
  mapping falls silently to the OpenAI path. Loud in logs, invisible in product.

---

## 2. What each stage is actually asked to do

The stages are not equal, and pricing them as one blob is the mistake that makes
this look like a simple cost rise. Measured on `.6b54_capture_artefacts.json`
(37 evidence items — the representative capture): **37,047 input / 10,499 output**
across the three stages that report tokens.

| stage | model today | job | tokens | latency | intelligence needed |
|---|---|---|---|---|---|
| **mapping** (`claim_map_analyzer`) | `2.5-flash` | evidence to element relationship: supports / challenges / context, at asserted scope, specificity and strength | ~12k in / ~4.75k out | 11-15s | **HIGHEST — this is the product** |
| **distiller** (`evidence_distiller`) | `2.5-flash-lite` | compress 37 fetched sources to usable snippets | **22,275 in** (60% of all input) | **~63s — slowest stage** | LOW — summarisation |
| extract / decompose | `2.5-flash-lite` | atomise into 12 or fewer claims; claim to 1-5 atomic elements | mid | mid | MEDIUM — rule-following |
| classify | `2.5-flash-lite` | tier x type, heuristic fallback at 93.7% | ~2.8k in | low | LOW — has a fallback |
| query-plan / query-answer / select | `2.5-flash-lite` | search planning, article classification | low | low | MEDIUM |
| `opinion_symmetry` x4 | `2.5-flash-lite` | the entire opinion-decoupling honesty layer | uncounted | — | HIGH, currently underserved |

**The mapping call is the only one that carries the user's claim in the prompt**
(`claim_map_analyzer.py:1474`). That makes it the single point where invariant #7
— never sycophantic, never false-balancing — is won or lost. Everything else is
plumbing around it.

**Two corrections to the architecture doc, both already verified:** the distiller
and `extract.py:1125` are **Google-only with no OpenAI fallback**; and
`map_completion`/`recovery_mapping` run on flash-**lite**, not the mapping model,
because `is_mapping` is a label whitelist (`claim_map_analyzer.py:2025`) — the
same cognitive task on a cheaper model with no schema.

### The split we already run is right, for a reason nobody wrote down

Cheap and fast on the bulk, better model on mapping. The PARROT sycophancy
benchmark (arxiv 2511.17220 — follow rate, i.e. abandoning a correct answer when
the user asserts a wrong one) says why:

| model | follow rate |
|---|---|
| Gemini-2.5-Flash-**Lite** | **50.7%** |
| Gemini-2.5-Flash | 17.2% |
| Claude Sonnet 4.5 | 10.8% |
| GPT-5-Mini | **6.3%** |
| GPT-5 | 3.6% |

**Read the counter-signal, not just the ordering: OpenAI's *cheap* tier beat
Google's *large* one.** Tier risk is not uniform across vendors — which reframes
the whole migration. "Stay on a Lite tier" is dangerous on Google and not
obviously dangerous on OpenAI.

---

## 3. Verified prices, 25 August 2026

All confirmed against vendor primary sources today.

| model | input /M | output /M | notes |
|---|---|---|---|
| `gemini-2.5-flash-lite` | $0.10 | $0.40 | **retires 16 Oct** |
| `gemini-2.5-flash` | $0.30 | $2.50 | **retires 16 Oct** |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | `minimal` thinking available |
| `gemini-3.6-flash` | $0.75 to $1.50 | $3.75 to $7.50 | rises 1 Jan 2027 |
| `gemini-3.7-flash` | $0.75 to $1.50 | $3.75 to $7.50 | **identical price to 3.6** |
| `gpt-5.6-luna` | **$0.20** | **$1.20** | `reasoning_effort:"none"`, 1.05M ctx, vision |
| `gpt-5-mini` | $0.25 | $2.00 | |
| `gpt-5.4-mini` | $0.75 | $4.50 | |
| `claude-haiku-4-5` | $1.00 | $5.00 | no client in our codebase |
| `claude-sonnet-5` | $2.00 | $10.00 | no client in our codebase |

### Gemini 3.7 Flash specifically — the answer to "does it speed us up"

**No, and it cannot.** Thinking levels are `low` / `medium` / `high`. There is no
`off` and no `minimal`; the default is `medium`. `MAPPING_THINKING_BUDGET=0` —
the lever that took mapping 35-50s to 11-15s at equal-or-better quality — **has
no successor on this model**. Measured TTFT is 12.64s at high effort, which alone
exceeds our entire current mapping stage. Generation is genuinely ~40% faster
(371-389 tok/s vs 274), but we do not spend our time generating tokens; we spent
it on thinking, and we deleted that cost.

It is also a **regression against `gemini-3.5-flash-lite`**, which we live-probed
on 2026-08-01 as accepting `thinkingLevel:"minimal"` returning 200.

---

## 4. Costed options

Split estimate derived from the $0.0203 baseline: **mapping ~12,000 in / 4,750
out**, bulk ~25,047 in / 5,749 out. Console sells 200 checks for £20, so **10p
(~$0.125) of revenue per check** at full utilisation.

| # | bulk | mapping | $/check | x today | Console margin |
|---|---|---|---|---|---|
| 0 | `2.5-flash-lite` | `2.5-flash` | $0.0203 | 1.00x | 84% |
| **D** | **`gpt-5.6-luna`** | **`gpt-5.6-luna`** | **$0.0200** | **0.99x** | **84%** |
| A | `3.5-flash-lite` | `3.5-flash-lite` | $0.0374 | 1.84x | 70% |
| C | `gpt-5.6-luna` | `gemini-3.7-flash` | $0.0387 | 1.91x | 69% |
| **E** | **`gpt-5.6-luna`** | **`gpt-5.4-mini`** | **$0.0423** | **2.08x** | **66%** |
| F | `gpt-5.6-luna` | `claude-haiku-4-5` | $0.0477 | 2.35x | 62% |
| B | `3.5-flash-lite` | `gemini-3.7-flash` | $0.0487 | 2.40x | 61% |
| G | `gpt-5.6-luna` | `claude-sonnet-5` | $0.0834 | 4.11x | 33% |

**Every margin above is a CEILING.** Search spend is excluded, and telemetry
covers analyzer + classifier + distiller only — extract, relevance scorer, query
planner, article classifier, claim selector and four `opinion_symmetry` calls are
uncounted, so true input is nearer 60-65k. Rows B/C/G are floors twice over,
because Gemini thinking tokens can no longer be zeroed and bill at output rate.

**Tier note:** `QUICK_CONFIG` disables `enable_evidence_distillation` — the 22k-token,
63-second stage. The quick tier ($0.07) therefore never pays the distiller, and
its cost is dominated by mapping. It is the binding constraint on any mapping
upgrade, not the full tier.

---

## 5. Proposal

### Step 1 — move the whole pipeline to `gpt-5.6-luna`. Cost-neutral.

$0.0200/check against today's $0.0203. **Not a compromise to fit a budget — an
intelligence increase on nine of ten stages**, since everything except mapping
runs on `2.5-flash-lite` today and Artificial Analysis puts Luna (Intelligence
Index 52) at or above **Gemini 3.5 Flash** — a tier above the Flash-Lite class we
would otherwise be migrating to.

What it buys:

- **`reasoning_effort:"none"` genuinely exists.** The only candidate that keeps
  the latency lever. Worst case on speed is *maintained*, which is the bar set.
- **Google retirement risk leaves the critical path entirely.**
- **Single-vendor exposure ends.** Google becomes the fallback — including for
  the distiller and `extract.py:1125`, which today have **no fallback at all**.
- 1.05M context, vision (OCR path), structured outputs, cutoff Feb 2026.
- The OpenAI client already exists in the codebase. Zero new integration.

### Step 2 — spend margin on mapping only, and only on a measured number.

If the probe in section 6 shows Luna cannot hold invariant #7 on the mapping
call, promote **that one stage** to `gpt-5.4-mini` (option E): **$0.0423/check,
2.08x, 66% Console margin retained**. Same vendor, same client, same auth — a
config change, not a build.

This is the honest way to take the founder's "narrow the margin for intelligence"
instinct: spend it where the product lives, after a number says it is needed,
rather than across ten stages on a guess.

### What I am recommending against, and why

- **`gemini-3.7-flash` anywhere** — costs 3.7x more than Luna on the mapping call,
  cannot turn thinking off, and sits in the model family that PARROT scores worst
  on the exact failure mode our product exists to avoid.
- **`gemini-3.5-flash-lite` for the bulk** — 45% dearer than Luna and less capable.
  Its only advantage is REST-surface continuity, which is worth less than a
  vendor change is worth.
- **Claude on mapping (F/G)** — plausible on quality, but there is no Anthropic
  client in the codebase (`ANTHROPIC_API_KEY` is deprecated at `config.py:59`),
  so it is a new integration under a 52-day deadline. Revisit if the probe rules
  out both OpenAI tiers.

---

## 6. How we test it — and why the usual net does not catch this

**The replay bench cannot verify this change.** Three independent reasons:

1. Model strings and request bodies are cassette keys — a swap invalidates the
   entire corpus by construction.
2. Measured 2026-08-20: two identical runs differ by 25 of 40 URLs. The bench
   cannot resolve changes smaller than that noise.
3. It cannot run at all right now — the held mapping reframe is in the tree.

**The right rig already exists.** `scripts/mapping_budget_sweep.py` freezes 3
evidence pools (18-20 items each, `scripts/.mapping_sweep_pool.json`), calls the
mapper directly on deep copies, runs k repeats, and judges each arm against the
baseline's **own k-run self-agreement** rather than a single run. It sweeps
thinking budget; it needs a `--models` axis. **That is a parameter change on a
working harness, not a new build.** `scripts/eval_mapping_model.py` already
sweeps models on frozen claims and can supply the prompt-capture half.

### The acceptance test: premise adoption

Designed 2026-08-01, never built. **Run the identical frozen pool twice — once
with the `Claim:` line at `claim_map_analyzer.py:1474` present, once removed —
and measure the delta in `supported` badges in both valence directions.**

That is invariant #7 expressed as a single number, and no public benchmark runs
it. It is also the only test that can distinguish "cheaper model" from "model
that agrees with the user", which is the specific way this migration could
quietly destroy the product while every suite stays green.

**Pass condition:** premise-adoption delta no worse than the `2.5-flash` baseline,
in both directions. A model that under-credits genuine support fails as hard as
one that over-credits weak support — false balance is an invariant #7 breach too.

**Public benchmarks cannot settle this and we should stop asking them to.** Small
models are excluded from Vectara's HHEM leaderboard outright; neither
`gemini-3.5-flash-lite` nor `gpt-5.6-luna` carries a published grounding,
attribution or sycophancy score. Established 2026-08-01, re-confirmed today.

---

## 7. Build items — none of these are optional

1. **`OPENAI_API_KEY` is dead locally (401).** Today it is the fallback; under
   this proposal it is **primary**. Nothing can be evaluated until it is live.
   **This is the first blocker and it is a founder action.**
2. **`PRIMARY_LLM_PROVIDER` controls no routing** — it only feeds the manifest
   hash. The Google-first cascade is hardcoded in five files (`query_planner.py`,
   `claim_map_analyzer.py:1797`, `evidence_classifier.py:838`, `claim_selector.py`,
   `relevance_scorer.py:648`). Inverting primary/fallback is a real change.
3. **`evidence_distiller.py` and `extract.py:1125` have no fallback.** Moving them
   to OpenAI without adding Google as fallback swaps one single point of failure
   for another. Add the inverse path in the same commit.
4. **Manifest fingerprint.** `manifest_signer.py:39-46` hashes the model settings,
   so any change makes `GET /verify/{id}` return `{"valid": false, "reason":
   "data_modified"}` **for every historic check**. Nothing errors — the public
   verification endpoint simply starts lying. Must be resolved as part of the
   migration, not after. Prod state of `MANIFEST_SIGNING_ENABLED` unverified.
5. **Temperature.** `DECOMPOSITION_TEMPERATURE=0.2` / `ANALYZER_TEMPERATURE=0.2`
   pin determinism the replay corpus rests on. Reasoning models typically reject
   `temperature`; confirm behaviour at `reasoning_effort:"none"` before assuming.
6. **`LLM_RELEVANCE_MODEL` is pinned to `gpt-4o-mini-2024-07-18`** — a dated pin
   that already points at the old generation. Fold into the same pass.
7. **If any Gemini path survives**, `google_ai.py:333-334` needs a `thinking_level`
   branch **in the same commit as the model string**, or every call 400s.

---

## 8. Decision needed from the founder

1. **Approve Step 1** (whole pipeline to `gpt-5.6-luna`, cost-neutral). — the ask
2. **Restore `OPENAI_API_KEY`** — blocks all evaluation, including Step 2.
3. **Note only:** Step 2 (mapping to `gpt-5.4-mini`, 2.08x, 66% margin) is a
   config change to be taken *after* the probe, not now.

---

## 9. Sources

- https://ai.google.dev/gemini-api/docs/pricing · /thinking · /deprecations · /models
- https://developers.openai.com/api/docs/pricing · /models/gpt-5.6-luna
- https://platform.claude.com/docs/en/about-claude/pricing
- https://artificialanalysis.ai/models/gemini-3-7-flash/providers · /gpt-5-6-luna
- PARROT arxiv 2511.17220 · ForceBench arxiv 2605.28044 (both verified against papers 2026-08-01)
