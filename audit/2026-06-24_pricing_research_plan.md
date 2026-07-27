# Tru8 Pricing Research Plan — 2026-06-24

**Goal:** Produce a *defensible* pricing decision — **what to charge and how** — grounded in three things, re-confirmed, never analogy-based:
- **(A) Our cost** per check, small → large (COGS).
- **(B) Competitors' real pricing**, anchored to our actual output.
- **(C) Our decision** — price points + charging model synthesised from A + B + positioning.

**Discipline (load-bearing, [[feedback_knowledge_loop]]):** every number passes arithmetic self-consistency + is grounded in code/telemetry/cited source (not analogy) + is independently re-confirmed before it informs a price. The pricing cards (£7/£29) are **frozen as-is** until C lands — no interim edits.

**Why this is needed now:** today's `cost_telemetry` is *partial* — it undercounts LLM spend ~20–30% (extract / relevance-scorer / query-answer stages uncaptured), has **no per-query search cost** (Brave/Serper are the paid calls), an **unverified** rate card (`PRICING_VERSION="2026-06-15-UNVERIFIED"`), and **no infra amortization**. A price set on that is sand. This plan closes those holes first.

---

## Workstream A — COGS: what a check actually costs us

### A1 — Close the measurement gaps *(backend instrumentation; phased-build-loop)*
- Wire token capture into `final_result["llm_token_usage"]` + `by_stage` for the three uncaptured LLM stages:
  - EXTRACT — `extract.py::extract_key_claims` (gpt-4o)
  - RELEVANCE SCORER — `relevance_scorer.py:449` (gpt-4o-mini)
  - QUERY ANSWERING — query-answer path (gpt-4o, optional)
- Thread **real per-query search counts** (Brave/Serper) from `SearchService` → `retrieve.py` → `pipeline_metrics` + `cost_telemetry.search.web_queries`. Add per-adapter query counts where exposable.
- (Lower priority) count YouTube / Wayback / Google Fact-Check calls if material.
- **Acceptance:** `cost_telemetry.llm.coverage == "complete"`; `search` carries query counts, not just result counts. Unit tests assert the wired numbers (per [[feedback_test_wired_prepare_query_path]]).

### A2 — Verify the rate card *(web research + one data handoff)*
- **LLM unit prices:** verify Gemini 2.5 flash / flash-lite / pro + gpt-4o / gpt-4o-mini against *official current* pricing, dated + cited. Replace the `cost_constants.py:30-41` placeholders; bump `PRICING_VERSION`.
- **Search per-query rates:** Brave Search API + Serper.dev published tiers (and SerpAPI if still in the chain).
- **Other paid adapters:** confirm which cost money (WeatherAPI / Football-Data paid tiers, etc.); most are free.
- **Infra amortization:** Railway plan + Postgres / Redis / Qdrant / MinIO monthly → per-check share at an assumed volume. **NEEDS founder's actual monthly bills** (one number-dump, not a conversation).

### A3 — Measure small → large *(funded sample)*
- Cost matrix: `{quick, full}` × `{1, 3, 6, 12 claims}` across a few domains (politics/finance, health/science, general). Capture full `cost_telemetry` per run.
- Route: a small batch of **real runs** is the only true ground truth for tokens + live search counts (the deterministic bench freezes cassettes, so it can't measure live token/search spend reliably). Estimate the £ first; founder go/no-go.
- **Output:** per-check cost distribution — min / typical / max, split LLM / search / API / infra.

### A4 — Re-confirm
- Independent **second-method** recomputation: telemetry-derived cost vs a bottom-up hand model (calls × tokens × verified rates) — must agree within tolerance.
- Arithmetic self-consistency pass; sanity vs current charges (lookup 2p / consensus 3p / quick 7p / full 15p) → **gross margin per tier**.

**Deliverable A:** cost-per-check table (small→large) with confidence bounds + current-price margin.

---

## Workstream B — Competitor pricing: what the market charges
*(web research; runs in PARALLEL with A — no dependency)*

Anchored to our exact output (claim → open sources → tier+type classification → supports/challenges/context map → receipts → signed record, **no verdict**). For each competitor: **price · unit (per-call / seat / mo) · what's included · free tier · inferred cost model**.
- **Direct:** Webcite (per-source stance + source-typing + agent API), Factiverse (supporting/disputing, newsrooms), scite (no-verdict supports/contrasts, academic).
- **Adjacent / AEO (already cast in `/compare`):** Perplexity, Google Fact-Check/Check, Parallel.ai Basis.
- **Archival / provenance shape:** Page-Vault, Hunchly (dossier comparators).

**Deliverable B:** competitor pricing matrix + where our COGS floor sits relative to their prices (headroom above cost; position vs market). Flag product-name ambiguities (e.g. "Webcite" the founder named vs the legacy WebCite.org archiver).

---

## Workstream C — Pricing decision (synthesis, after A + B)
- **Model options:** per-check metered (prepaid balance, like `/agent`) vs researcher subscription (console seat + allowance) vs hybrid. Map each to **researcher value** (export / signed record / receipts / breadth) — not check-volume.
- **Price points from:** COGS floor (A) + target margin + competitor ceiling (B) + positioning (the lowest-WTP-end caveat — [[project-release-plan-2026-06-23]]).
- Platform fee **separate** from metered, never unlimited ([[project_competitor_pricing_review_2026_06_15]]); free-taster bound; where the soft paywall sits.

**Deliverable C:** pricing recommendation → unblocks `REPO-PRICE-NUM` + feeds item 3 packaging + the frozen pricing cards.

---

## Sequencing & ownership
| Phase | Depends on | Owner | Start |
|---|---|---|---|
| B competitor matrix | — | me (web) | **now, parallel** |
| A2 LLM/search rates | — | me (web) | **now, parallel** |
| A1 instrumentation | — | me (code, loop) | next |
| A2 infra line | your monthly bills | you → me | on handoff |
| A3 measurement | A1 + run funding | you (£ go/no-go) → me | after A1 |
| A4 re-confirm | A3 | me | after A3 |
| C synthesis | A + B | me | after A+B |

**What I need from you (batched, non-blocking, no back-and-forth):**
1. Your actual **monthly infra bills** (Railway + any DB/vector/storage add-ons) — one dump, feeds A2 infra.
2. A **go/no-go on funding the A3 measurement runs** — I'll give a £ estimate first.

Everything else I execute. Re-confirmation (A4 + an independent review of C) is baked in.

---

## RESULTS LOG

### A2 — Rate card VERIFIED (2026-06-24, web-cited)
- **LLM unit prices: all five placeholders confirmed CORRECT** (Gemini page updated 2026-06-18; OpenAI model cards). No numeric change needed to `cost_constants.py:30-41`.
  - Gemini 2.5 **"thinking" tokens bill at the OUTPUT rate** ($2.50/1M for Flash) — our MAP stage (Flash thinking) is the priciest LLM line.
  - Gemini 2.5 **Pro >200k-token tier doubles** to $2.50 in / $15 out (placeholder only covers ≤200k). Add as a note.
  - **gpt-4o / gpt-4o-mini are now LEGACY** (OpenAI headline = GPT-5.x); prices hold via model cards. We use gpt-4o for extract/decompose — re-verify before long-term commit.
  - Discounts available if needed: Gemini Batch −50%, context caching (Flash cached input $0.03/1M); OpenAI cached input −50%.
- **Search: chain confirmed Serper(primary) → Brave(secondary) → SerpAPI(tertiary)** (`search.py:740`).
  - Serper ~**$0.0003/query** ($0.30/1k floor) + 2,500 free — serves most queries → search cost is LOW.
  - Brave $0.005/query (16× Serper, free tier killed Feb 2026) — fallback only. SerpAPI $0.010–0.025 — rare.
- **Net:** rates are solid + search path is cheap. Remaining unknown = real per-check token volumes + query counts → A1.

### B — Competitor pricing matrix (2026-06-24, web-cited; unconfirmed flagged)
- **Webcite AMBIGUITY RESOLVED: it's `webcite.co`** (NOT the defunct webcitation.org archiver, NOT webcite.ai GTM tool). Closest analogue: citation + **stance** + source-typing + agent API. **Builder $20/mo** (500 cr, $0.03/overage cr) → **full verify ≈ 4 cr ≈ $0.12/call**. BUT it emits a **verdict** (supported/contradicted/mixed) — the exact line Tru8 won't cross.
- **The comparable self-serve tier clusters tightly at ~$20/mo:** Webcite $20, scite Personal $20 ($12 annual), Factiverse Pro ~€25 (*unconfirmed — 404 wall*), Perplexity Pro $20 (*medium conf*).
- **Per-call metered anchors:** bare search ~$0.005 (Parallel/Perplexity Search); Webcite full verify ~$0.12; Parallel research Task tiers $0.005–$2.40 by depth.
- **Defensible band for a no-verdict full evidence-map call: ~$0.05–$0.15; lookups ~$0.005–$0.02.**
- **NOT comparables (bound the market, don't anchor):** Page-Vault (sales-gated/$199–349/project capture), Hunchly ($169/yr seat capture), Google Fact Check API (free, resurfaces others' verdicts).
- **Our current CHARGES vs market:** lookup 2p (~$0.025) / consensus 3p (~$0.04) / quick 7p (~$0.09) / **full 15p (~$0.19)**. Our full sits *above* Webcite's full verify ($0.12) — we charge slightly more for a *less* opinionated (no-verdict) output. That tension is the core C-decision question.
- **Wedge confirmed:** no rival offers no-verdict map + exclusion receipts + signed record + ~30-API breadth together.

**Still needed for the decision:** our actual COST per check (A1 instrument → A3 measure → A4 confirm). Until then, margin is unknown — do NOT set a price.

### A3 (partial) — first grounded cost-per-check from prod (2026-06-24, `scripts/check_cost_snapshot.py`)
- **Volume:** 45 checks ever (39 completed, 3 failed, 2 waiting, 1 processing); ~13 last-30d; all since Mar 1. Only 5 carry telemetry (post-2026-06-15).
- **Bottom-up (n=5):** partial LLM **avg $0.0083 / median $0.0072**; 6,921 in / 2,474 out tokens; 5.4 LLM calls; 26 web results; 1.6 api adapters; 70s wall.
- **Internal reconciliation:** 6921×$0.30/1M + 2474×$2.50/1M = **$0.00826** = reported avg exactly → telemetry sound + **all captured tokens are Gemini Flash-priced (OpenAI confirmed not firing).**
- **Top-down vs bottom-up DISAGREE 35×** (£8.81÷40 ≈ $0.28 vs $0.008). Bottom-up is correct; the £8.81 Gemini bill is **~96% dev/test/replay-bench spend**, not the 40 prod checks. **Do NOT divide the bill by prod checks.**
- **Marginal cost/check ≈ $0.010–0.012 LLM + unmeasured search ($0.005 small → $0.12 large) → ~$0.02 small, ~$0.10+ large.** Search is the swing (A1).
- **STRATEGIC HEADLINE:** at this volume **fixed infra dominates** — Railway $22/mo ÷ 13 = **~$1.70/check fixed vs ~$0.02 marginal (~99% fixed).** Cost is NOT the pricing constraint — **volume is.** Marginal margin already ~80% at the 15p full charge. → Price Workstream C for **buyer value + market anchor** ($20/mo cluster; $0.05–0.15/call), NOT up from a ~2-cent cost floor. One $20/mo subscriber covers all infra.
- **Remaining cost work that still matters:** A1 to (a) close the ~20-30% LLM undercount and (b) measure real Serper **query** counts so the small→large search curve is known. Lower urgency now (marginal cost is immaterial to the price), but needed for the large-check tail + any future high-volume metered tier.

---

## Workstream C — Pricing recommendation (2026-06-24)

> **Status: RECOMMENDATION for founder decision.** Numbers below are PROPOSED (internal); none published until founder signs off (`REPO-PRICE-NUM`, [[project-pricing-not-set-2026-06-23]]). Currency shown £ (goal is in £, UK founder) with ~$ at £1≈$1.27; the £-vs-$ display choice is a separate open founder call.

### What sets the price: MARKET POSITION (not cost, not founder income)
- **Cost floor is irrelevant.** Marginal ≈ $0.02/check; fixed ≈ $22/mo (~£200/yr). One sub covers infra. Pricing up from cost would massively underprice — ignore it as a price-setter.
- **Founder income target is NOT a pricing input.** £30k/£15k is a *revenue/volume goal*, not a price. Price is set by what the market pays for what we deliver; the income figure then only tells us what *volume* that price requires — a reachability check, and a **floor, not a ceiling.**
- **Position vs competitors is the anchor.** The comparable self-serve field sits at **~$20/mo** (Webcite/scite/Factiverse/Perplexity) — but every one of them **ADDS a verdict.** We deliver something more complete and *different*: a no-verdict evidence MAP across ~30 open/gov/academic sources, tier+type classified, supports/challenges/context per element, with exclusion **receipts** and a **signed provenance record** none of them offer. For the buyer who must *defend* their sourcing (journalist/analyst/policy), that breadth + provenance is worth **at least parity — arguably a premium.**

### Position → price  — ✅ DECIDED 2026-06-24
- **Currency: £ DECIDED** (UK-heavy source base — Hansard/GOV.UK/ONS/Companies House/UK Legislation — makes UK researchers the natural beachhead; founder confirmed £).
- **Individual: £20/mo DECIDED** (parity-ish with the ~$20 anchor; the safe bottom of the £20–30 band — earn a premium later with conversion proof, don't bake it in). Annual £200/yr (~17% off).
- **Professional / Teams: £75–150/mo (proposed, TBD)** — where provenance value concentrates; the real ACV lever.
- Validate £20 reads "fair-to-cheap" via the buyer script (`2026-06-24_buyer_validation_script.md`) before publishing.

### Revenue is uncapped — £30k is a FLOOR, not a target
At £20/mo (£240/yr) individual, before Teams:
| Paying researchers | Annual revenue |
|---|---|
| 125 | £30k |
| 200 | £48k |
| 250 | £60k |
| 400 | £96k |

Add Teams and **£100k+ is reachable without leaving the 100–250 niche** — e.g. 200 individuals × £20/mo + 20 teams × £100/mo = £48k + £24k = **£72k/yr**. Price stays at the position-derived level; only the volume ambition moves.

### The API / Dev / agent route — a SEPARATE product, NOT bundled into the £20 sub
This is the part still open. The answer:
- **Two products (matches the existing `/pricing` "API + Console" framing):**
  - **Console — £20/mo, human, browser, fair-use unlimited.** Works *because humans self-limit* (10–50 checks/mo).
  - **API / Agents — metered, prepaid credits, pay-as-you-go.** For developers/agents building Tru8 in. Current per-call prices: lookup 2p · consensus 3p · quick 7p · full 15p (`agent_pricing.py`). Rails: credits (Stripe), x402/Skyfire (off).
- **Why API must NOT be bundled unlimited into the £20 sub:** an API key enables *programmatic* use. An agent firing 10,000 calls/mo at ~£0.03 marginal = ~£300 cost on a £20 sub. Flat-fee fair-use only holds for humans. So **API access stays metered, full stop.**
- **What the £20 Console CAN include:** a modest *personal-automation* API allowance (e.g. 50–100 calls/mo) so a solo researcher can script light tasks; heavy/agent use → buy credits.
- **Open API-route questions (low urgency — it's optionality, pays ~£0 now):**
  1. **Metered price vs market:** full 15p (~$0.19) sits *above* Webcite's full-verify (~$0.12) and far above bare search ($0.005). Cost-justified (marginal ~£0.03 → ~80% margin even at 10p), but for a price-sensitive dev buyer consider trimming full to ~£0.10–0.12. Decide once we know if an API buyer exists (the validation script Q9 probes this).
  2. **Stripe credit-pack blocker (`REPO-STRIPE`):** `STRIPE_PRICE_ID_CREDIT_PACK_*` unset → `/agent/credits/purchase` 500s. The credits route isn't actually buyable until this is set. Fix only when a real API buyer appears.
  3. **Keep MCP + API live + listed** (near-zero maintenance) as the agent-future option; don't invest more now ([[project-release-plan-2026-06-23]]).

#### How to separate the two paths (investigated 2026-06-24, code-grounded)
- **Already built + clean:** `/agent/*` debits a prepaid GBP balance `User.credit_balance_pence` per call (with refund-on-failure + `AgentTransaction`), entirely separate from the subscription. The metered product EXISTS — no metering system to build.
- **Three balances:** `Subscription.credits_per_month` (sub, `/checks/*`), `User.credits` (trial=3, `/checks/*` no-sub), `User.credit_balance_pence` (prepaid, `/agent/*` only).
- **THE LEAK:** `/checks/stream` + `/checks/run` accept Clerk JWT **OR** API key (`get_current_user_or_api_key`), both resolve to the same user → an **API key on a £20 sub rides the fair-use Console quota** (`checks.py:107-131`). Channel is already computed (`via="api_key"|"dashboard"`, `checks.py:638`) but only LOGGED, not used for entitlement. `/agent/*` is NOT leaked (uses the prepaid balance).
- **THE FIX (one wall, reuse existing machinery):** in `_validate_and_create_check`, branch on the `initiated_via` it already receives — `dashboard`(JWT)→subscription/trial quota (unchanged); `api_key`→debit `credit_balance_pence` via the existing `debit_credits`/`AgentTransaction`, never the sub. **~½ day + tests.**
- **DO NOT** gate API-key *creation* behind a plan tier (the investigation suggested it) — that re-couples the products. Keep key creation open; meter *usage*, not *access*.
- **Optional later:** personal-API allowance (~50–100 calls/mo before metering) for subscribers; a defined `/checks`-via-key rate (reuse 15p).
- **Sequencing:** not urgent today (~zero API users) BUT **must close before the £20 fair-use sub goes live with API keys enabled** → belongs in the item-3 packaging build. Dependency: `REPO-STRIPE` credit-pack env (metered purchase path).

**Metered-only reality check (unchanged):** £0.10/check needs ~300,000 checks/yr (~833/day); even £0.50/check needs 60,000/yr. The niche won't produce that → metered stays **upside/agent-optionality, never the engine.**

### Recommended structure (hybrid, subscription-led)
1. **Free taster** — 3–5 full checks, all features, to prove value + feed the funnel. (Marginal cost ~$0.10 total — trivial.)
2. **Researcher (individual) — the core. £20/mo · £200/yr (DECIDED).** Fair-use unlimited (cost ~2¢/check; soft cap ~200–300/mo then throttle — a user needs ~270 large or ~900 typical checks/mo to cost more than they pay). Includes a modest personal-API allowance (~50–100 calls/mo); heavy/agent use → metered credits. All 6 views, full exports (PDF/CSV/JSON), signed record, receipts, public report links.
3. **Teams** — proposed **£75–100/mo** (or £15–20/seat): shared workspace, retention, higher allowance. A handful of these materially cut the individual count needed.
4. **API / credits (metered, quiet)** — keep current agent prices (lookup 2p → full 15p), prepaid balance. Near-zero cost to maintain; preserves the agent-future option. Not load-bearing for £30k.

### Why these numbers
- £25/mo sits **at-to-just-above** the market anchor — justified by what we deliver beyond the verdict tools (breadth + receipts + signed provenance), without overreaching on a config-level moat. Tunable £20–30 on early conversion evidence.
- Annual option captures researchers who prefer one invoice + improves cash/churn.
- Teams is the lever that raises ACV (and total revenue ceiling) without pushing the individual price past what a solo researcher will pay.

### Honest risks (do not lose)
- **The crux is converting 100+ paying researchers** — contestable, low-WTP niche; this needs real marketing, not just a price.
- Don't over-price on the no-verdict differentiation (config-level, Webcite could copy).
- £30k assumes retention; without annual plans, churn erodes it.

### Decisions
- ✅ Subscription-led hybrid, priced from market position.
- ✅ Currency **£**.
- ✅ Individual **£20/mo** (£200/yr), fair-use unlimited + small personal-API allowance.
- ⏳ Teams price (proposed £75–150/mo) — TBD.
- ⏳ API metered price — keep 2/3/7/15p for now; revisit full vs Webcite's ~$0.12 if/when an API buyer appears.
- **NEXT (validate before publish):** run the buyer script (`2026-06-24_buyer_validation_script.md`, 8–10 researchers) to confirm £20 reads fair, no-verdict lands, and whether API demand exists. THEN this unblocks `REPO-PRICE-NUM` + the frozen pricing cards get rebuilt around this structure.
