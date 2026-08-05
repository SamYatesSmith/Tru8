# Agent tier quality — four findings, scoped for design review

**Date:** 2026-08-05
**Status:** SCOPED, not built. Design review owed before any code.
**Origin:** Live audit of the paid agent path, prompted by the founder question
*"will a developer receive what they pay for?"* — asked while publishing to Smithery.
**Spend:** 52p across 4 live checks (approved).

---

## Why this exists

The MCP endpoint's plumbing was fixed and verified this week (500s, CORS, capability
listing). None of that touched the question of whether the *output* is worth its price.
Four live checks were run against production to answer that, and the answer is mostly
reassuring with one exception that would cost credibility on first contact.

Evidence base — the four production checks:

| Check | Claim | Tier | Result |
|---|---|---|---|
| `1aebb543` | UK CPI below 2% Sept 2024 | quick | 8 sources, primary 3 / commentary 4, both elements supported |
| `618efbc4` | same substance, reworded | full | 18 sources, primary 13 / commentary 0, **one element wrongly disputed** |
| `19d2951e` | Online Safety Act royal assent Oct 2023 | full | 13 sources, GOV.UK ×5 + Hansard ×4, exact date cited, all supported |
| `33d818e9` | Semaglutide reduces MACE in obesity | full | 15 sources, PubMed ×10 + WHO ×7 + NICE + FDA, all supported |

**What the tier comparison establishes.** On matched claims, full substitutes primary
sourcing for commentary rather than merely adding volume: primary 3 → 13, commentary
4 → 0. The 8p difference buys the thing Tru8 is differentiated on. Defaulting the MCP
tool to `quick` was presenting the weakest configuration to first-time callers; the
default has been changed to `full` (see F5 below — it needs sign-off, not just a diff).

---

## F1 — Time-pinned claims are shown as disputed when they are settled

**Severity: HIGH.** This is the one that would embarrass us.

### Symptom

`618efbc4` — "UK CPI inflation dropped under 2% in September 2024". The claim is true;
ONS reports 1.7%, and the pipeline *retrieved that source*. Element `e2` still came back
`state: disputed`, `rule_applied: close_split`, weighted 9 support vs 16 challenge, and
the claim orientation read *"evidence is mixed"*.

The six challenging items are all period mismatches:

- 2.6% in June (a different month)
- 2.0% in May 2024
- 3.27% for calendar 2024 (an annual average against a monthly figure)
- "still well above the Bank of England's 2% target" (undated commentary)

A settled fact was made to look contested. That is invariant #7's false-balancing
failure, in the direction we said we would never distort.

Note the 7p tier got the same claim *right*. Not because it reasons better — because it
retrieved fewer off-period sources. We were lucky, not correct.

### Root cause — verified in code, mechanical

The evidence block handed to the mapper is built as:

```
- {evidence_id}: [{title}] [Tier: …] [Type: …] {snippet}
```

There is **no date field**. Meanwhile `MAPPING_PROMPT` already instructs:

> "Evidence from one time period does NOT support a claim about a different time period."

So the prompt asserts a rule the payload cannot support. The model can only apply it when
a date happens to appear inside the snippet text. This is the NF-11 lesson exactly: a
fragile behaviour was asked for in a prompt instead of enforced by a mechanism.

### Proposed fix — two parts, both needed

1. **Give the mapper the data.** Add the evidence date to the payload line
   (`[Published: 2024-10-16]` / `[Published: unknown]`). Necessary but not sufficient —
   it still leaves correctness to the model's judgement.
2. **Make the correctness mechanical.** A temporal-scope tagger in the shape of the
   existing `app/utils/scope_sensitivity.py`: extract the element's explicit time
   reference and the evidence's, and where both exist and disagree, force the
   relationship to `context` — never `challenges`. A gate, not a suggestion.

### The risk that must be designed against

Over-firing is worse than under-firing. If the gate downgrades genuine challenges to
context, we hide real disputes — the same invariant breached from the other side. It
must fire **only** when the element carries an explicit period AND the evidence carries
an explicit, different period. Anything undated or ambiguous is left untouched.

### Sequencing constraint

Touches `app/pipeline/claim_map_analyzer.py`, which **already has a held mapping-prompt
reframe in the working tree** (see OPEN_WORK HELD section). A bench re-record is already
owed for that change and must stay separately attributable, or golden drift cannot be
assigned to a cause. Replay bench required before commit either way.

### Verification that can fail

- `618efbc4`'s claim pinned as a regression case: element must not be `disputed`.
- A counter-case where a genuine same-period contradiction must still read `challenges`.
- Replay bench at 135 ok / 2 warn / 1 fail or better.

---

## F2 — The receipts understate what was withheld

**Severity: MEDIUM-HIGH.** Directly "did I get what I paid for", and it touches invariant
#5 (*every exclusion has a receipt*).

### Symptom, two parts

**(a) The declared list is incomplete.** `QUICK_LIMITATIONS` (`app/api/v1/agent.py:578`)
declares six omissions. `QUICK_CONFIG` (`app/pipeline/runner.py`) turns off ten things:

| Disabled in quick | Declared? |
|---|---|
| `enable_api_adapters` | ✅ `no_api_sources` |
| `enable_factcheck_lookup` | ✅ |
| `enable_llm_relevance_scorer` | ✅ |
| `enable_llm_classifier` | ✅ `heuristic_classification` |
| `enable_coverage_recovery` | ✅ |
| `enable_query_answering` | ✅ |
| `enable_evidence_distillation` | ❌ **undeclared** |
| `enable_post_filter_recovery` | ❌ **undeclared** |
| `max_sources_per_claim` 20 → 8 | ❌ **undeclared** |
| `max_queries_per_element` 3 → 1 | ❌ **undeclared** |

The two undeclared caps are the ones that shrink breadth — the thing we sell.

**(b) Cache hits declare nothing at all.** The lookup path (`agent.py`, Step 1) matches on
`claim_text_hash` + user only — **tier is not part of the match**. So a caller requesting
`full` can be served a cached `quick` result, charged 2p, and receive
`limitations: []` with `executedTier: "lookup"`. Nothing in the response reveals that the
underlying analysis was the reduced pipeline. `Check.executed_tier` already stores
`quick | full`; it is simply not read here.

### Proposed fix

- Derive the limitations list **mechanically from the config diff** rather than
  maintaining it by hand, so it cannot drift from `QUICK_CONFIG` again.
- On a cache hit, read `check_row.executed_tier` and attach that tier's limitations, plus
  surface the source tier (e.g. `_meta.cachedTier`) alongside the existing `cachedFrom`.
- De-duplicate: `QUICK_LIMITATIONS` is copy-pasted in `app/api/v1/agent_x402.py:114`.

### Verification that can fail

A drift guard asserting the declared list matches the actual `QUICK_CONFIG` diff — it
should fail today, and fail again if someone disables a stage without declaring it.

---

## F3 — `max_age_hours=0` silently means "any age is fine"

**Severity: LOW severity, trivial fix, but it is a documented parameter that lies.**

`agent.py`: `if body.max_age_hours and check_row.completed_at:` — `0` is falsy, so the
freshness filter is skipped entirely. The tool documents *"Skip cache hits older than
this many hours"*, so `0` should mean "never serve cache". Today there is **no way for a
caller to force a fresh run**, which also made the tier comparison above harder to
construct (paraphrases were required to defeat the cache).

**Fix:** `is not None`, and decide explicitly that `0` means always-fresh. Update the tool
docstring to say so.

---

## F4 — `mappingModel` in the metadata is probably lying

**Severity: MEDIUM.** Not a user-facing quality bug, but it means we cannot trust the
telemetry we would use to judge F1 — and it is in the claim map metadata.

### Symptom

Across four production checks, `mappingModel` reported `gemini-2.5-flash-lite` three
times and `gemini-2.5-flash` once. Config default is `MAPPING_GOOGLE_MODEL =
gemini-2.5-flash`, and `decompositionModel` was Flash-Lite on all four.

### Root cause — HYPOTHESIS, needs confirming

`_last_model_used` is instance state on the analyzer (`claim_map_analyzer.py:1849`),
written by **every** LLM call and read after the fact by the batch mapping path
(`:1776` → `:1781`). Decomposition runs on `google_model` (Flash-Lite). Where calls
interleave — per-claim retries use `asyncio.gather` — the decomposition model's name can
land in the mapping metadata.

If that is right, the model is **not** varying and the label is wrong. If it is wrong,
mapping is silently running on Flash-Lite on some checks, which given our own measurement
(Flash-Lite 50.7% parrot vs Flash 17.2%) would be a quality problem in its own right.
**Both possibilities are worth one investigation; they need opposite fixes.**

### Proposed fix

Thread the model name back as a return value from the call rather than reading shared
instance state. Confirm first with a concurrency test that reproduces the leak.

---

## F4b — Two mapping stages run on the cheaper model, undeclared — OPEN DECISION

**Found while fixing F4. Not built: it changes model spend on every check.**

`is_mapping` — which selects both the mapping model and the longer mapping
timeout — is `label in ("mapping", "batch_mapping")`. Two other stages do mapping
work and are not in that set:

| Stage | Label | What it does | Model today |
|---|---|---|---|
| Completion pass | `map_completion` | Re-examines leftover evidence and assigns relationships | `google_model` (Flash-Lite) |
| Coverage recovery | `recovery_mapping` | Cross-element mapping for low-coverage claims | `google_model` (Flash-Lite) |

Both assign `supports` / `challenges` / `context` — the exact judgement that
went wrong in F1 — on the model our own measurement puts at a 50.7% parrot rate
versus Flash's 17.2%. There is no comment suggesting this was decided; the
completion pass was added 2026-05-12 and the label set was never extended.

**Why it is not simply fixed here:** promoting both to the mapping model raises
per-check cost on every check, and changes pipeline behaviour, so it needs the
replay bench and a founder cost decision. Recorded rather than done.

---

## F5 — Default tier changed to `full` (done, needs sign-off)

`tru8_mcp/server.py`: `max_tier` default `quick` → `full`, with the docstring rewritten to
explain that it is a **ceiling, not a floor** — cached and consensus hits still return at
their own lower price, so the default costs 15p only on genuinely new claims.

**Not yet resolved:**

- Applies to the hosted endpoint on deploy; **stdio users need a `tru8-mcp` 1.0.4
  release** to see it.
- Measured full-tier runs took roughly 60–90s. **Cloudflare's default origin timeout is
  100s.** That headroom has not been measured properly and a 524 would be indistinguishable
  from a broken server to a first-time caller. Worth measuring before this is called safe.

---

## Build status — 2026-08-05

| Finding | State |
|---|---|
| F2 receipts | **DONE**, mutation-verified. Limitations derived from config (`app/core/tier_limitations.py`), 5 stored-check call sites fixed across `agent.py` + `agent_x402.py`, `_meta.cachedTier` added. 6→11 declared slugs. |
| F3 `max_age_hours=0` | **DONE**, mutation-verified. Both truthiness sites (cache + consensus freshness). |
| F4a metadata lies | **DONE**, mutation-verified. Cause was ordering, not a race: the completion pass runs between the mapping call and the metadata write. Model now captured at the call. |
| F4b cheap model on mapping stages | **OPEN** — decision above. |
| F1 temporal scoping | **NOT STARTED** — design below, needs bench. |
| F5 default tier | Changed, uncommitted, sign-off + Cloudflare headroom outstanding. |

Tests added: `tests/unit/test_tier_limitations.py` (9), `tests/unit/agent/test_tier_receipts.py` (5),
`tests/unit/pipeline/test_mapping_model_metadata.py` (3). 148 pass across the agent suite.

## F1 rule design — the decision that emerged while scoping

The gate was approved as "hard, narrowly scoped". Building it surfaced a choice
that changes what it does:

**Downgrade challenges only, or any relationship whose period does not match?**

Recommend **symmetric** — downgrade `supports` too. Reasons: a source about a
different period is not evidence about this element in *either* direction, so
scoping it is honest; and a gate that only ever removes challenges is exactly
the shape of a sycophancy mechanism, which invariant #7 forbids. Symmetric
scoping cannot be characterised that way because it can equally turn a
`supported` element into `unresolved`.

**Granularity, and when it may fire at all.** Fire only when:
- the element carries exactly one unambiguous month-level period, AND
- the evidence text carries at least one explicit period, AND
- none of the evidence's periods matches the element's.

Evidence carrying **no** explicit period is left alone. That deliberately leaves
part of the observed CPI failure unfixed — undated "still above target"
commentary keeps its `challenges` — because inferring a period from silence is
guessing, and over-firing hides genuine disputes.

Expected effect on `618efbc4`: the May-2024, June and annual-2024 items scope
out; the undated commentary does not.

## Recommended order

1. **F2 + F3** — cheap, no pipeline risk, no bench, and they are the honesty defects.
2. **F4 investigation** — needed before F1 can be judged, because it decides whether
   mapping telemetry can be trusted at all.
3. **F1** — highest value, highest risk, needs the bench and must be sequenced against the
   held mapping-prompt change.
4. **F5** — settle the Cloudflare headroom question, then decide on the 1.0.4 release.

## Open questions for the founder

1. **F1 gate strength:** hard (force `context`) or advisory (attach a caveat, leave the
   relationship)? Hard is more honest about settled facts; advisory is safer against
   over-firing. Recommend hard, narrowly scoped.
2. **F5:** is a `tru8-mcp` 1.0.4 release wanted now, or batched with the `remotes[]`
   registry work already open?
3. **Bench budget:** F1 needs a replay bench run (~$0.25, ~10 min) and possibly a re-gold.
