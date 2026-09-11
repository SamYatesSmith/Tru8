# Determinism design — idempotent charging and stable records (2026-09-11)

**Status (updated 15:30 BST):** §1 idempotency **BUILT AND LIVE-VERIFIED** the same day (`19fe47e` + hotfix `81f2b29` + test `7d342f7`; resend 6 min later → same check, 0p); the stranded-check finding from the probe led to a fourth build, **agent-rail refund parity** (`c687230`, `app/services/agent_refunds.py`, deployed, unexercised live). §3–§4 variance design and the ~£1 measurement: **NOT started** — founder's go owed; the Friday wildfire pool cache has expired, so the measurement needs a fresh 24 h replay pair. Written from three same-day investigations, all free:
`2026-09-11_idempotency_root_cause.md` (code trace), `2026-09-11_variance_sources.md` (every
nondeterminism source after retrieval, with lines), `2026-09-11_variance_pairs.md` (two matched
pairs measured from public payloads). Nothing here is built.

## 0. The two problems in one sentence each
1. **Idempotency:** a retry of the same call can be charged again because the client's key is a
   fixed clock bucket, and the server trusts the key without checking who sent it.
2. **Variance:** the same claim produces a different record run to run, and only part of that is
   search churn; on a byte-identical pool the classifier, the mapper and the decomposer still
   sample differently, and the mechanical layer turns one flipped tier into a different state.

---

## 1. Idempotency — cause, fix, tests

**Cause (`tru8_mcp/tools.py:61`).** Key = endpoint + payload + `floor(epoch/600)`. Buckets align
to :00/:10/:20 UTC, so the chance a retry after gap *g* lands in a new bucket is *g*/600: 23% for the
140 s stream death the 2026-09-02 fix targeted, 57% for this morning's 340 s gap. Server layers
(`agent_auth.py:70-93`, `agent.py:836-867`) behaved as designed on a key they had never seen.

**Two more defects found on the way.**
- **Cross-caller collision.** The key carries no caller identity and `charge()` looks it up by key
  alone. Two hosted users sending the same claim in the same bucket: the second receives the first's
  check, uncharged. A billing and privacy hole, live today on `/mcp`.
- **Smart endpoint 409.** With `max_age_hours` unset, a retry after completion hits the lookup branch
  first (`agent.py:196-238`) and presents a lookup-tier request hash against the stored full-tier
  one → 409 instead of a replay. Today's calls escaped only because `max_age_hours=0`.

**Fix (about an hour, no spend).**
| Where | Change |
|---|---|
| `tru8_mcp/tools.py` | key = endpoint + canonical payload + sha256(api_key)[:16]; **no time term** |
| `app/core/agent_auth.py::charge()` | sliding TTL from `existing_tx.created_at` (600 s): pending or in-window → return it (replay); terminal and older → retire the old key (`key#txid`), insert fresh; `IntegrityError` → re-select. **Payer check:** a key owned by another user → 409, never a replay |
| `app/api/v1/agent.py` | a resend that arrives while the original is running waits for it (up to the tier's wall budget) and returns the original with `X-Tru8-Idempotent-Replay: 1`; the smart endpoint's lookup branch checks the idempotency table BEFORE tier resolution; reorder the link-before-visibility commit (`:862` vs `:866`) |
| `app/middleware/x402_audit.py` | same replay guard (x402 is OFF in prod; parity only) |
| Tests | key equal at t=590 s vs 930 s; key differs across API keys; server: aged 599 → replay, aged 601 terminal → new charge, aged 601 pending → replay, other payer → 409, resend-while-running → same check id, smart-endpoint retry with default `max_age_hours` → replay not 409 |

**Rollout:** server first (accepts old and new keys), then `tru8-mcp` 1.0.4 on PyPI (also the
chance to add `remotes[]` to `server.json`). The hosted `/mcp` route picks up the client change on
deploy because it imports the same `tools.py`.

---

## 2. Variance — what was established today

| Layer | Evidence | Deterministic? |
|---|---|---|
| Retrieval | 62% URL churn between identical runs (2026-08-20); planner strings, provider fallback, 45 s / 30 s deadlines cancelling by latency | no |
| Evidence cache | replays the RAW pool (post-filter, pre-classify, order preserved); everything after it re-runs live | replay is exact |
| Relevance scores, distillates | identical on the wildfire pair | cached with the pool / stable |
| Classification | 2 of 16 tiers flipped on an identical pool; both `classificationMethod: llm` (a model roll at temperature 0.1, not a heuristic fallback); tier is state-bearing | no |
| Decomposition | identical on the wildfire pair; different wording + order on the heatwave pair (temperature 0.2, highest in the pipeline) | no |
| Mapping | identical elements + pool → 13 vs 11 references; 0 relationship flips on shared pairs; sources move between elements or drop out; prod runs `MAPPING_THINKING_BUDGET=0` on `gemini-3.7-flash` (thinking floor "low"); temperature 0.2; then a completion pass on what was left unreferenced | no |
| Mechanical layer | tier feeds `_STATE_TIER_WEIGHTS`, the support floor, the thin/echo notes; one flip changes a flag or a state | deterministic given inputs — it amplifies, it does not add |
| Coverage recovery | fires only when mapping leaves an element thin; injects live-search items that can become an element's only supports | deterministic given states — a second amplifier |
| Google client | never sends `seed`; timeouts not retried; 429/503 retry is a fresh sample | fixable |

The cascade on the heatwave pair: decomposition sampled a different element set → mapping attached
different items → one element read thin → recovery added six sources → two OPINION items became the
element's only supports → state `unresolved`. One sample at the top, a different record at the bottom.

## 3. Variance — the design, in the order the evidence supports

**Principle.** Make everything after retrieval as deterministic as the provider allows, and make
the state-bearing decisions stable by construction rather than by luck. Keep retrieval dynamic
(founder's requirement) but give it a stable core.

| # | Fix | What it removes | Cost / risk | Measure first? |
|---|---|---|---|---|
| V1 | **`seed` + temperature 0 on classify, decompose, map, relevance** (one client parameter, per-stage config; Gemini `generationConfig.seed`) | most of the sampling churn on identical prompts | tiny code; Gemini's seed is best-effort, not a guarantee; re-keys nothing (cassettes match on body — **it changes the body**, so a bench re-record is owed) | **yes** — frozen-pool repeats, both arms |
| V2 | **Classification memo per source** (key: URL + content hash, TTL 7 d, `RETRIEVAL_CACHE_VERSION`-scoped): a source classified once keeps its tier and type across runs and across claims | tier flips → state flips; also saves the classify call on every repeat | small; a wrong tier persists for the TTL (receipt says `cached`); prompt changes need a version bump | measurement tells us how much V1 leaves |
| V3 | **Decomposition memo per claim hash** (TTL 24 h like the pool; version-scoped) | element-set churn on re-runs of the same text, which is the cascade's trigger | small; same version-bump discipline | after V1 |
| V4 | **Explicit mapping coverage**: the mapper returns a relationship for EVERY pool item per element, `not_relevant` included, so an omission is a decision, not a sample; the completion pass then has nothing to guess | reference-set churn (13 vs 11) | prompt + schema change; more output tokens (~+30%); re-keys mapping cassettes; quality must be re-graded (blind review, ~50p/run) | yes — after V1 measurement |
| V5 | **Recovery receipts on the page**: `ev-rec-*` items labelled "added by coverage recovery" with the trigger named | nothing — makes the amplifier visible | frontend only | no |
| V6 | Retrieval stable core — **author-supplied sources with receipts** (user or we add the URL at submission; fetched, classified, mapped like any item, tagged) + a measured **factcheck-outlet lane** | the recipient's own piece missing from the pool | ~1 day + a pence probe | lane: yes (pence) |

**Not proposed:** majority-vote classification (3× cost for what V1+V2 should give), forcing
mapping thinking up (measured 75–94% self-agreement dynamic vs 92–100% at budget 0 — thinking OFF is
already the more stable arm), any prompt-only "be consistent" instruction.

## 4. The measurement (ask before spending; ~£1 total)

Freeze the wildfire pool from the live Redis key (`tru8:evidence_extract:<ver>:<md5>`, alive until
~09:47 UTC 2026-09-12) plus the NHS and heatwave pools if still cached. Harness pattern:
`scripts/recital_repeat_probe.py` / `scripts/mapping_budget_sweep.py` (both exist).

| Arm | Calls | Cost | Reads |
|---|---|---|---|
| classify ×20, current config | 20 | ~1p | tier flip rate per source |
| classify ×20, temp 0 + seed | 20 | ~1p | what V1 buys |
| decompose ×10, each arm | 20 | ~5p | element-set agreement |
| map ×10, each arm (thinking 0, 3.7-flash) | 20 | ~40p | ref-set Jaccard, relationship flips, state agreement |
| full post-cache chain ×5, each arm (with recovery) | 10 | ~45p | end-to-end record agreement |

Output: one table, flip rates per stage per arm. Decision rule: if V1 takes classify and map
self-agreement above 95%, build V1 + V2 + V3 (a day, plus a bench re-record ~£1.45); V4 only if
mapping stays under 95% with V1.

## 5. Sequencing proposed
1. Idempotency fix today (no spend) — it is charging money and leaking checks across callers.
2. The ~£1 measurement (founder's go).
3. V1–V3 + bench re-record, then a 3× blind label review (~£1.50) to prove quality did not move.
4. V6 as its own decision (the commercial assessment's product change).
5. V4 only on the measurement's word.

Outreach is not blocked by any of this: notes describe the linked record, and the founder reads
every record before it goes.
