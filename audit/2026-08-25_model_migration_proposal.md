# Model migration proposal — replacing Gemini 2.5 before 16 October 2026

**Date:** 2026-08-25 · **Status:** REVISED after design review, awaiting founder decision
**Deadline:** 52 days. Every primary LLM stage is on a model that retires.

---

## 0. Design review outcome — the first recommendation was WRONG, and is withdrawn

The first version of this document recommended moving the **whole pipeline to
`gpt-5.6-luna`** on the grounds that it was cost-neutral, an intelligence rise,
and zero new integration. Reviewed against the code and the benchmark sources on
the same day. **All three grounds are false or overstated. Five defects, one
fatal.** Recorded in full because the reasoning was wrong in ways worth not
repeating.

| # | defect | severity |
|---|---|---|
| 1 | **Luna fails at long context — 41.3% vs Terra's 72.5%.** The distiller is a **22,275-token** task and the pipeline's largest consumer (60% of all input). The proposal put the biggest stage on the model's measured weakness. | **FATAL** |
| 2 | **"Cost-neutral" was overstated.** $0.0200 vs $0.0203 covers only the 3 stages that report tokens. The ~40% uncounted input runs on `2.5-flash-lite` today and would move to Luna at **2× input / 3× output with no offsetting saving**. Whole-pipeline is a rise, not neutral. | HIGH |
| 3 | **The intelligence claim was measured at the wrong operating point.** Intelligence Index 51-52 is **Luna (max)**. The proposal runs at `reasoning_effort:"none"`. No published score exists at `none`. Citing one to justify the other is not evidence. | HIGH |
| 4 | **"Zero new integration" was wrong.** `evidence_distiller.py` has **no OpenAI path at all**. And the existing `_call_openai` (`claim_map_analyzer.py`) is a hand-rolled httpx POST that sends `max_tokens` (deprecated, incompatible with reasoning models) and `temperature`, uses loose `response_format: {"type":"json_object"}` instead of a strict schema, and **has no `reasoning_effort` parameter at all** — so on the code we actually have, thinking cannot be turned off. **The entire latency argument rested on a parameter the codebase cannot send.** | HIGH |
| 5 | **The PARROT argument was sibling substitution** — `gpt-5-mini`/`gpt-5` were measured; `gpt-5.6-luna` and `gpt-5.4-mini` were not. This is the exact error the 2026-08-01 audit warned about ("sibling substitution actively misleads"). The vendor-level pattern is weaker evidence than it was presented as. | MEDIUM |

**What survives review:** the §2 stage analysis, the §3 prices, the §4 relative
costs, the §6 test design, and the finding that **Gemini 3.7 Flash is the wrong
answer** (unchanged — same price as 3.6, no thinking-off, TTFT alone exceeds our
mapping stage). What does not survive is the vendor switch as a *deadline*
project. **See §5 for the corrected recommendation.**

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
Google's *large* one.** Tier risk is not uniform across vendors.

⚠️ **But do not lean on this table to choose a model — it does not name any
candidate we can actually buy.** Every row is a *previous-generation sibling* of
a live model. The 2026-08-01 audit established that sibling substitution actively
misleads (`2.5-flash-lite` ranks BETTER than `2.5-flash` on Vectara HHEM and 3×
WORSE on PARROT). The first version of this document used these numbers to argue
for `gpt-5.6-luna` and `gpt-5.4-mini`, **neither of which PARROT measured** — that
was defect #5 in §0. What the table legitimately supports is one narrow claim:
**within-vendor tier gaps are large on Google**, which is why our own Flash /
Flash-Lite split exists and why mapping deserves its own probe. Nothing more.

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

## 3b. MEASURED 2026-08-25 — thinking behaviour is NOT uniform across Gemini 3

Probed live against all three models rather than inferred from one. This
corrects the 2026-08-01 record and changes the mapping trade-off.

| model | bare `thinkingBudget=0` | `thinkingLevel` | thought tokens at floor |
|---|---|---|---|
| `gemini-3.5-flash-lite` | **400** "invalid argument" | `minimal` → 200 | **0** |
| `gemini-3.7-flash` | **200 — SILENTLY IGNORED**, thinking ran anyway (83) | `low` → 200 · `minimal` → **400** | **~70** |
| `gemini-2.5-flash` (today) | 200 | `low` → **400** | 0 |

**Two different failure modes, and the quiet one is worse.** On `3.5-flash-lite`
a bare budget is a hard 400 — loud, though it would still fall silently to the
OpenAI path because `call_google_ai_with_usage` returns `None` on a terminal
non-429/503 without retry. On `3.7-flash` the same field returns **200 and is
discarded**: thinking runs, bills at the output rate, and a thinking-off config
becomes a placebo nothing surfaces.

⚠️ **The 2026-08-01 probe checked `3.5-flash-lite` only and concluded a silent
ignore had been ruled out. It had been ruled out on one model of three.** This is
the same shape as every other finding in this document: a claim verified on one
instance and quoted forward as general.

### What this does to the mapping decision

Only **`3.5-flash-lite` preserves the M1 latency lever** — 0 thought tokens at
`minimal`, identical to `2.5-flash` at `thinkingBudget=0` today. `3.7-flash`
cannot: its lowest accepted level still spends ~70 thought tokens per call,
billed as output, on top of costing 2.5× more per token.

So the mapping choice is now a genuine three-way tension, not a simple
tier-preservation argument:

| | tier (PARROT) | thinking-off | cost |
|---|---|---|---|
| `gemini-3.7-flash` | ✅ Flash, matches today | ❌ ~70 thoughts/call | 2.40× |
| `gemini-3.5-flash-lite` | ⚠️ Lite — the tier PARROT scores worst | ✅ 0 thoughts | 1.84× |

**Shipped default is `3.7-flash`** (tier-preserving; erring toward the cheaper
model on the honesty-critical call is the wrong default). The premise-adoption
probe in §6 is what may justify demoting it — and if it does, the demotion buys
back both the money *and* the latency lever.

---

## 4. Costed options

Split estimate derived from the $0.0203 baseline: **mapping ~12,000 in / 4,750
out**, bulk ~25,047 in / 5,749 out. Console sells 200 checks for £20, so **10p
(~$0.125) of revenue per check** at full utilisation.

| # | bulk | mapping | $/check | x today | Console margin | verdict |
|---|---|---|---|---|---|---|
| 0 | `2.5-flash-lite` | `2.5-flash` | $0.0203 | 1.00x | 84% | today — retires 16 Oct |
| D | `gpt-5.6-luna` | `gpt-5.6-luna` | $0.0200 | 0.99x | 84% | ⛔ **withdrawn** — §0 defects 1-4 |
| **A** | **`3.5-flash-lite`** | **`3.5-flash-lite`** | **$0.0374** | **1.84x** | **70%** | ✅ **RECOMMENDED floor** |
| C | `gpt-5.6-luna` | `gemini-3.7-flash` | $0.0387 | 1.91x | 69% | inherits Luna's defects |
| E | `gpt-5.6-luna` | `gpt-5.4-mini` | $0.0423 | 2.08x | 66% | deferred to Nov (§5) |
| F | `gpt-5.6-luna` | `claude-haiku-4-5` | $0.0477 | 2.35x | 62% | no Anthropic client |
| **B** | **`3.5-flash-lite`** | **`gemini-3.7-flash`** | **$0.0487** | **2.40x** | **61%** | ✅ **if the probe earns it** |
| G | `gpt-5.6-luna` | `claude-sonnet-5` | $0.0834 | 4.11x | 33% | too thin |

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

## 4b. Can we afford it at 1,000 subscribers? — the question that actually matters

The current-volume answer (~40p/month) is true and useless. Here is the scaled one.

**⚠️ Utilisation is MODELLED, not measured. We have zero paying subscribers using
the product, so nobody knows what "the expected amount" is.** Everything below is
arithmetic on stated assumptions, and the assumption that moves the answer most
is the one we have no data for. Re-run this the moment real usage exists.

### Per-check cost, both cost centres

Search is derived from the real lane caps, not guessed: claim lane 3 queries x 13
results (**2 Serper credits each**, over the 10-result threshold) + 5 element
lanes x 2 queries x 5 results (1 credit each) = **16 credits per claim**, ~2.5
claims per check. LLM is the counted stages x1.5 to cover the ~40% that telemetry
misses.

| | LLM | search | total | pence |
|---|---|---|---|---|
| today, Serper **entry** tier | $0.0304 | $0.0400 | $0.0704 | **5.50p** |
| today, Serper **top** tier | $0.0304 | $0.0120 | $0.0424 | **3.32p** |
| post-migration, entry tier | $0.0560 | $0.0400 | $0.0960 | **7.50p** |
| post-migration, **top** tier | $0.0560 | $0.0120 | $0.0680 | **5.32p** |

**Serper's volume tier is worth more than the entire model decision.** Moving from
entry to top pricing saves 2.8p/check; the whole Gemini migration costs 2.0p. At
1,000 users x 50 checks that is ~2,000,000 credits/month — firmly top-tier
volume, but it has to be *procured*, not assumed.

### 1,000 Console subscribers at £20/mo = £20,000/month revenue

Serper at top tier, post-migration at 1.84x.

| checks/user/mo | checks/mo | COGS today | COGS after | margin today | margin after | delta |
|---|---|---|---|---|---|---|
| 20 (10% of cap) | 20,000 | £663 | £1,063 | 97% | **95%** | £400 |
| 50 (25% of cap) | 50,000 | £1,658 | £2,658 | 92% | **87%** | £1,000 |
| 100 (50% of cap) | 100,000 | £3,316 | £5,316 | 83% | **73%** | £1,999 |
| 200 (the full cap) | 200,000 | £6,633 | £10,632 | 67% | **47%** | £3,999 |

### The answer

**Yes — comfortably, and the 200-check cap is what makes it safe.**

| | break-even checks/mo for one £20 subscriber | headroom to the cap |
|---|---|---|
| today | 603 | 3.0x |
| post-migration | **376** | **1.9x** |

A subscriber who consumes **every check the plan allows is still profitable**, at
47% gross margin. That is the worst case the product can be made to produce, and
it survives. At any realistic utilisation the migration costs **£400-£1,000/month
against £20,000 of revenue** — one to five points of gross margin.

**What this does change:** the cap stops being a formality. Pre-migration it sat
at 3x break-even and could have been raised without much thought; post-migration
it sits at 1.9x. **Do not raise the 200-check cap, and do not add an unlimited
tier, without re-running this table.** That is the real constraint the migration
imposes — not affordability, but the loss of half the headroom that made the cap
uncontroversial.

**Two costs deliberately excluded**, both of which dwarf the migration at low
utilisation: **Stripe fees** (~50p per subscriber/month = **£500/month** at 1,000
subs, comparable to the entire migration delta at 20 checks/user) and hosting.
Neither is affected by the model choice, but neither should be forgotten when
"gross margin" is quoted at anyone.

---

## 5. Corrected recommendation — simplest and safest that clears the deadline

**Stay on Google. Change two env vars. Change nothing else.**

```
GOOGLE_LLM_MODEL   = gemini-2.5-flash-lite  →  gemini-3.5-flash-lite
MAPPING_GOOGLE_MODEL = gemini-2.5-flash     →  (probe decides: 3.5-flash-lite or 3.7-flash)
```

Cost: **$0.0374/check on the counted stages, 1.84×, ~70% Console margin** if both
land on `3.5-flash-lite`. Up to 2.40× if the probe promotes mapping to `3.7-flash`.

### Why this is the right shape under "simple and safe"

- **No new integration anywhere.** Same REST surface, same client, same auth, same
  `google_ai.py`. The distiller — which has no OpenAI path and is 60% of input —
  keeps working untouched.
- **Both risky unknowns are already closed by our own live probes** (2026-08-01,
  not vendor claims): `thinkingLevel:"minimal"` returns 200 on
  `gemini-3.5-flash-lite`, and the flat `responseMimeType`/`responseSchema` we
  send **still works on 3.x**, enums included. Nothing about structured output
  needs building.
- **The prompt family is unchanged.** `MAPPING_PROMPT` and its force-calibration
  reframe were tuned against Gemini behaviour. ForceBench's finding — the prompt
  moved violations 47.2% → 24.5%, more than any model choice did — says the prompt
  is the bigger lever, and a vendor change throws away that tuning.
- **No announced retirement** on `gemini-3.5-flash-lite`.
- **One thing to get right, not ten:** `google_ai.py:333-334` needs a
  `thinking_level` branch in the same commit as the model string, or every call
  400s. That is the whole build.

⚠️ **Not `gemini-3.1-flash-lite`, despite it being Google's named replacement for
our Flash-Lite** — it already carries a **7 May 2027** shutdown and its own
successor, i.e. migrating twice.

### The honest cost story

**Google deleted the price point we were on.** There is no cheap Gemini 3 tier:
`2.5-flash-lite` was $0.10/$0.40 and the nearest Gemini 3 equivalent is
$0.30/$2.50 — 3× input, 6× output. **Costs rise on every available path**,
including doing nothing (doing nothing ends in the pipeline not running). The
question is only how much, at what risk.

⚠️ **Every ratio in §4 is measured on the counted stages only. Whole-pipeline
ratios are WORSE for every candidate**, because the ~40% uncounted input all sits
on the cheapest model we run today and has no expensive stage to offset against.
The direction is certain; the magnitude is not, because output tokens for those
stages have never been measured. **Do not quote a whole-pipeline figure until
`cost_constants.py` counts every stage.**

### Where the founder's "spend margin on intelligence" instinct should land

**On mapping, and only on mapping** — it is the only call carrying the user's
claim in the prompt (`claim_map_analyzer.py:1474`), so it is where invariant #7
is won or lost. Everything else is plumbing. Run the §6 probe with two arms —
`3.5-flash-lite` and `3.7-flash` — and let the premise-adoption number decide.
That is a 0.56× cost step (1.84× → 2.40×) bought on evidence.

### Deferred, NOT rejected: `gpt-5.6-luna` as a cost project

Luna is genuinely interesting — $0.20/$1.20, real `reasoning_effort:"none"`,
1.05M context — but it is a **cost-reduction project for after the deadline**,
not a deadline project. Before it can be considered it needs, in order:
1. `OPENAI_API_KEY` restored (dead, 401).
2. The OpenAI client rebuilt: `max_completion_tokens`, `reasoning_effort`, strict
   `json_schema`, and an OpenAI path written for the distiller and `extract.py:1125`.
3. **A long-context measurement on the distiller task specifically**, given the
   41.3% figure. If Luna fails there, the distiller stays on Gemini and the
   three-model split has to justify its own complexity.

None of that is 52-day work alongside send week. **Do it in November, on measured
numbers, with the deadline already behind us.**

### What I am recommending against, and why

- **`gemini-3.7-flash` for the bulk** — 2.5× the price of `3.5-flash-lite`, and it
  cannot turn thinking off, so it is slower *and* dearer on nine stages that do
  not need the intelligence. Viable for mapping alone, if the probe earns it.
- **A vendor switch as a deadline project** — see §0. The integration is real, the
  latency lever does not exist in our code today, and the one benchmark that bears
  on our largest stage says the candidate is weak at it.
- **Claude (options F/G)** — no Anthropic client exists (`ANTHROPIC_API_KEY`
  deprecated at `config.py:59`). Same objection as Luna, plus a new SDK.

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

## 7. Build items for the corrected (Google) path

**Mandatory, in this order:**

1. **`google_ai.py:333-334` needs a `thinking_level` branch, in the same commit as
   the model string.** A lone `thinkingBudget` is a **hard 400** on 3.x, and
   `google_ai.py:254-256` returns `None` on any non-429/503 **without retry** — so
   mapping would fall silently to a dead OpenAI key. Loud in logs, invisible in
   product. This is the single highest-risk line in the migration.
2. **Manifest fingerprint.** `manifest_signer.py:39-46` hashes the model settings,
   so any change makes `GET /verify/{id}` return `{"valid": false, "reason":
   "data_modified"}` **for every historic check**. Nothing errors — the public
   verification endpoint simply starts lying. Resolve as part of the migration,
   not after. Prod state of `MANIFEST_SIGNING_ENABLED` is unverified.
3. **Temperature.** `temperature` is advised removed on 3.x (low values "may lead
   to looping or degraded performance"), but `DECOMPOSITION_TEMPERATURE=0.2` /
   `ANALYZER_TEMPERATURE=0.2` pin the determinism the replay corpus rests on.
   Decide deliberately; do not let it change by default.
4. **Re-record the replay corpus after the swap.** Cassettes are invalidated by
   construction. This is the *post*-migration regression net, not the pre-flight
   check — the §6 probe is the pre-flight check. Sequence them in that order.

**Fold in while there (cheap, unblocked, and already wrong today):**

5. **`cost_constants.py` says `UNVERIFIED`** but its 2.5 rates match Google's
   published page exactly. Restamp, add the 3.x rows, and **wire the uncounted
   stages into telemetry** — until that lands, no whole-pipeline cost figure can
   be quoted honestly (see §5).
6. **`LLM_RELEVANCE_MODEL` is pinned to `gpt-4o-mini-2024-07-18`** — a dated pin
   pointing at the previous generation, on a dead local key.

**Only if Luna is ever revisited (§5, deferred):** `OPENAI_API_KEY` restored;
`PRIMARY_LLM_PROVIDER` made to actually route (it feeds only the manifest hash —
the cascade is hardcoded in `query_planner.py`, `claim_map_analyzer.py:1797`,
`evidence_classifier.py:838`, `claim_selector.py`, `relevance_scorer.py:648`);
OpenAI paths written for `evidence_distiller.py` and `extract.py:1125`; and the
`_call_openai` body rebuilt (`max_completion_tokens`, `reasoning_effort`, strict
`json_schema`).

---

## 8. Decision needed from the founder

1. **Approve the Google path** — `GOOGLE_LLM_MODEL=gemini-3.5-flash-lite`, build
   the `thinking_level` branch, handle the manifest fingerprint. ← the ask
2. **Approve the mapping probe** — two arms, `3.5-flash-lite` vs `3.7-flash`, on
   the frozen pools. Cost is a few pence of API spend. The premise-adoption number
   decides whether mapping costs us 1.84× or 2.40×.
3. **Note only:** Luna is deferred to November as a cost project, not rejected.
   It needs a restored key, a rebuilt OpenAI client, and a long-context
   measurement on the distiller before it can be considered.

**Not asked for now:** any spend approval. The probe is pence; the migration is
config plus one branch.

---

## 9. Sources

- https://ai.google.dev/gemini-api/docs/pricing · /thinking · /deprecations · /models
- https://developers.openai.com/api/docs/pricing · /models/gpt-5.6-luna
- https://platform.claude.com/docs/en/about-claude/pricing
- https://artificialanalysis.ai/models/gemini-3-7-flash/providers · /gpt-5-6-luna
- PARROT arxiv 2511.17220 · ForceBench arxiv 2605.28044 (both verified against papers 2026-08-01)
