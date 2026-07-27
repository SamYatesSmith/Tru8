# Element-level retrieval — the unwired seam

**Date:** 2026-07-27 · **Status:** DESIGN, pre-build · **Severity:** HIGH, affects every check
**Origin:** decoupling live verification (`TRU-4B9D-65EA`) — the track exposed this, did not cause it
**SOT for the decoupling track:** `audit/DECOUPLING_STATE.md`

---

## 1. The defect, in one line

`retrieve.py:292` reads `claim.get("elements", [])`. Decompose writes elements to
`claim["claim_map"]["elements"]` (`runner.py:1453`, `opinion_symmetry.py:339`).
**Nothing in the codebase writes `claim["elements"]`.**

So the `else` branch fires on every check:

```python
# retrieve.py:301-308
else:
    # Pre-decomposition: synthetic single element from claim text
    elem_list = [{"element_id": "e1", "description": claim.get("text", "")}]
```

The query planner has never seen an element. **Per-element retrieval — "2 queries/element"
in CLAUDE.md — has never run in the main path.** The comment says *"pre-decomposition"*,
describing an ordering that no longer holds: decompose runs at `runner.py:1441-1465`,
retrieve at `:1588`. A correct fallback silently became the only path when the stages were
reordered. The parameter is still named `max_queries_per_element`.

### Evidence (five independent, from prod logs + code)

- `"Query planning complete: 1 element plans for 1 claims"` — on a **4-element** claim
- **3 Serper calls** for the whole check; 4 elements would need ~8–12
- Arithmetic closes exactly: 1 synthetic element × `max_queries_per_element=3` = 3
- The queries themselves: `UK COVID vaccine rollout success metrics`,
  `UK COVID vaccine program achievements`
- No transform between `selected_claims` and the retrieve call (`runner.py:1574-1588`)

### It explains all four live checks

| Check | What actually drove retrieval | Outcome |
|---|---|---|
| T4 vaccine | *"was a triumph"* → "success metrics", "achievements" | 4 questions never searched → all partial |
| T2 homeopathy | NHS + homeopathy spending | cost ✓ efficacy ✓ — inside the claim's orbit; **alternative treatments ✗ — the only question outside it, and the only one that returned "no evidence was found"** |
| T1 learning styles | learning-styles validity | both questions inside the orbit → both answered |
| T3 Grenfell | entity-rich factual text ≈ its own elements | works — and looks like proof the pipeline is healthy |

**Why it went unnoticed:** on factual claims the claim text and its elements overlap almost
completely, so claim-level retrieval returns roughly the right evidence. The defect only
shows when elements diverge from the claim text — exactly what the grounds stage does by
design.

### The severe consequence, for opinion claims

For an evaluative claim the claim text **is** the judgement, so the pool gets constituted by
searching its own valence. `"was a triumph"` → `success metrics`, `achievements`.
**Invariant #7 breached at pool constitution** — the earliest possible point, and the one
place no downstream honesty can repair.

---

## 2. Latency — answered first, with numbers

**Risk is LOW. Query count does not multiply wall-clock.**

| Mechanism | Where | Effect |
|---|---|---|
| Queries execute concurrently | `_execute_planned_queries` → `asyncio.gather(*query_tasks)` `:1691` | search latency ≈ flat in query count |
| Fetch budget fixed | `max_sources = max_sources_per_claim * 2` = **40** `:1330` | fetch cost flat |
| Fetch concurrency bounded | shared `url_fetch_semaphore` (25 slots) | no new contention |
| Per-claim ceiling | `CLAIM_TIMEOUT = 45s` `:1366` | already bounds the stage |
| Stage ceiling | `retrieve_timeout = 180s` `runner.py:1543` | ample headroom |
| Watchdog | `PIPELINE_WATCHDOG_SECONDS = 300` | not approached |

Current full check 41–58s measured. **The watchdog/refund risk I initially ranked #1 is not
the real exposure** — the code fans out.

---

## 3. The real trade — result depth collapses

```python
sources_per_query = max(3, max_sources // len(queries))   # :1675
```

With `max_sources = 40`:

| Queries | Results per query | Total candidates |
|---|---|---|
| 3 (today) | **13** | 39 |
| 8 | 5 | 40 |
| 12 | **3** (floor) | 36 |
| 15 | 3 (floor) | 45 |

**More queries does not mean more evidence — it means shallower results per query.**
We trade *13 deep results on 3 broad queries* for *3 shallow results on 12 targeted ones*.

Whether that is an improvement depends entirely on query precision, and there is a known
reason to doubt it: element descriptions are **entity-poor**, especially question-shaped
ones, while the planner is told to *"use EXACT names, numbers and entities from the element
description"* (`query_planner.py:160`). Top-3 of an imprecise query is thin.

**This is the design's central open question, not the latency.**

---

## 4. Design

### 4.1 Add, do not replace

The claim-level query is currently doing all the work and on factual claims it is *good*
(Grenfell). If elements **replace** it, one strong query is traded for several weaker ones
and the demonstrably-working factual path regresses.

**Keep claim-level retrieval as one route; add element-targeted queries alongside.**
This falls out of the prediction, not from preference.

### 4.2 The seam

Populate the key the planner already reads, from the elements decompose already produces.
Small change; the care is all in what follows it.

### 4.3 The budget question — needs a decision

`sources_per_query`'s floor of 3 was written when there were only ever ~3 queries. With
8–15 it becomes the binding constraint. Options:

- **(a)** Raise `max_sources` when elements are wired, so depth per query holds. Costs fetch
  budget — the one genuinely expensive axis.
- **(b)** Keep 40, accept top-3 per query, rely on precision. Free, unproven.
- **(c)** Weight the budget: claim-level query keeps depth, element queries take the floor.
  Preserves today's factual behaviour exactly and adds element coverage on top.

**(c) is the conservative default** and the only one that cannot regress the factual path.

### 4.4 Not in scope

Question shape (compound questions), the evidential floor for calling a question answered,
grounds-unaware orientation, and the Seeker's blindness are all **real and still open** —
see `DECOUPLING_STATE.md` "LIVE VERIFICATION 2026-07-27". They are downstream of this and
should be re-measured *after* it, since their inputs change.

---

## 5. Blast radius

**Stops being valid:**

- **Replay bench cassettes — all of them.** Query strings are cassette keys. The owed F7
  re-gold moves from owed to **blocking**.
- 2026-07-02 latency baselines, and the pending prod `stage_timings_s` read
- `cost_telemetry` per-check baselines
- Coverage recovery (Stage 5.1) trigger rate — it has been compensating for this defect and
  should fire markedly less; a behaviour change, not just volume
- Agent tier economics; quick tier (£0.07, `max_queries_per_element=1`) most exposed
- Consensus layer mixes pre- and post-fix element states
- Historical checks are not recomputed — before/after comparisons are cross-version

**Cost:** Serper calls 3–5×, at tenths of a penny each. Fetch and LLM stages sit behind caps
(40 fetch / 20 pool / 50 scorer / 20 map) and stay flat. Net COGS change small — inferred
from the caps, and `cost_telemetry` undercounts LLM by ~20–30%, so it is not a measurement.

---

## 6. Regression test — already built, for free

`TRU-25E5-0431` and `TRU-4B9D-65EA` are now a purpose-built before/after pair. We know
exactly what should change:

- T2 e03 (alternative NHS treatments) — currently *"no evidence was found"*; must be searched
- T4's four questions — currently unsearched; must be searched
- T4 queries must **stop mirroring the claim's valence** (no "success metrics"/"achievements")
- T3 Grenfell — **must not regress**. This is the guard on §4.1.

Measure on both sides: retrieve stage seconds · Serper call count · final pool size ·
per-element states · `sources_per_query` actual.

---

## 7. Open decisions

1. **§4.3 fetch budget** — (a) raise, (b) accept top-3, (c) weighted. Recommend (c).
2. Whether quick tier (1 query/element) gets element retrieval at all, or stays claim-level
   for cost reasons.
3. Order: this before or after the F7 re-gold. Doing it first invalidates the cassettes
   again; doing the re-gold first spends effort on a baseline about to move.
