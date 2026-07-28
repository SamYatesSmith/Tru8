# Retrieval surface audit + claim-lane repair — design

**Date:** 2026-07-28 · **Status:** DESIGN, pre-build — **awaiting founder approval**
**Trigger:** criterion 17 FAILED live (3/3 runs) — `audit/OPEN_WORK.md` 2026-07-28 (cont.)
**Parent:** `audit/2026-07-27_phase2_element_retrieval_build_design.md` (Phase 2, §6b verified)
**Process:** phased-build-loop — criteria frozen in §5 *before* any code.

---

## 1. Why this is an audit and not a patch

Phase 2's live failure — the planner returns no plan for the claim lane `c0`, so
`element_wired` is `False` and the whole budget machinery is bypassed — is not a bug on its
own. It is the sixth instance of one premise.

**Every retrieval path in this codebase was written when "search the claim text" was the only
strategy that existed.** Phase 2 changed the strategy in exactly one path. Every other path
still believes the old contract. That is why the defects cluster so precisely, and it is why
patching `c0` alone would leave four more live routes doing the thing Phase 2 exists to stop.

The premise is *enumerable*, so this audit enumerates it rather than discovering the next
instance one 15-minute networked run at a time.

---

## 2. Class A — claim text becomes a search query

Each of these turns the raw claim into a query, outside the lane system. **None was touched
by Phase 2.**

| # | Site | Trigger | Form | Live? |
|---|---|---|---|---|
| **A1** | `runner.py:1971` POST-FILTER RECOVERY | claim's pool < `MIN_EVIDENCE_POST_FILTER` | **verbatim claim text**, `max_results=10` | ✅ **CONFIRMED firing on T4** |
| **A2** | `retrieve.py:1603` *"Fallback: Standard query formulation"* | no query plan for the claim | `extract_evidence_for_claim(claim_text)` → `evidence.py:274` `search_query = claim` | reachable |
| **A3** | `retrieve.py:2162` | planned query execution raises | same as A2 | reachable |
| **A4** | `retrieve.py:957` `_generate_recovery_queries` | `_ensure_minimum_evidence` | keyword extraction from claim text | ✅ fired on T2 |
| **A5** | `claim_map_analyzer.py:2051` | decompose fallback | `ClaimElement(element_id="e1", description=claim_text)` | reachable |

**Why this matters only for evaluative claims.** On a factual claim the claim text and its
elements overlap almost completely, so these routes are harmless — often good (Grenfell). On
an evaluative claim **the claim text *is* the judgement**, so every one of these constitutes
the pool by searching the judgement's own valence. Invariant #7, at the earliest possible
point, by five doors Phase 2 never closed.

**A4 does not launder it.** Keyword extraction keeps words ≥4 chars that are not stopwords —
so *"outstanding"* and *"success"* both survive into the query.

**The compounding chain, observed live:**

> `c0` dropped → pool shrinks (39/38/24 against a 40 cap) → A1 triggers → claim searched
> verbatim → valence reconstitutes the pool

Phase 2's blast-radius note predicted coverage recovery would fire **less**. It fired **more**,
on 2 of 3 runs, for exactly this reason.

---

## 3. Class B — "exactly one lane" assumptions still live

| # | Site | Effect |
|---|---|---|
| **B1** | `retrieve.py:394-395` — `element_wired` derived from the plans **returned** | **The live failure.** The LLM omits `c0`; `element_wired` goes `False`; per-lane request sizes (13/5) and weighted round-robin never execute. Criteria 8/9/10 are green in unit tests and **dead in production.** |
| **B2** | `retrieve.py:2046` FRESHNESS FALLBACK loops `for query in queries` with `max_results=sources_per_query` | The uniform pre-Phase-2 variable. Whenever freshness relaxes, per-lane depth is silently lost even on a correctly wired claim. |
| **B3** | `query_planner.py:219` — the prompt's only JSON example is `"element_id": "e1"` | The model has never been shown a `c0` lane in any example. Most probable cause of the omission. **Not the fix** (NF-11), but it explains the 3/3 consistency. |

Measured confirmation of B1 from the live run — per-query depth was uniform `max(3, 40//n)`
on all three checks: T4 8 queries → 5 each, T2 10 → 4, T3 6 → 6.

---

## 4. Design

Fix the class, not the instance.

### D-1 — `element_wired` comes from the lanes BUILT (closes B1)

`_build_retrieval_lanes` already knows whether it produced a claim lane. Thread that fact
forward on the claim rather than re-deriving it from LLM output in `_merge_element_plans`.
**An LLM omission must never silently disable a budget guarantee.**

### D-2 — synthesise the claim-lane plan when the planner omits it (closes B1's cause)

If no `c0` plan comes back, inject one mechanically. The claim lane's query *is* the claim
text — that is precisely what it was pre-Phase-2 — so synthesis is deterministic and needs no
model call. This restores *"add, don't replace"* (§4.1, founder decision D1) as a **guarantee**
rather than the planner's discretion.

Mechanical post-processing, not a prompt fix — `feedback_nf11_prompt_only_failed`. Adding `c0`
to the prompt example is worth doing as belt-and-braces but must never be the mechanism.

### D-3 — claim-text fallbacks become grounds-aware (closes Class A)

The decision in §5. The shape: on a **grounds-routed (evaluative)** claim, A1–A4 must not
search the claim text; they should draw on element descriptions instead. On a **factual**
claim they stay exactly as they are — they work, and Grenfell is the evidence.

This is the same principle Phase 1 applied to orientation: the mechanism is not wrong, it is
wrong *for one route*, and the route is already mechanically identified.

### D-4 — freshness fallback honours per-lane sizes (closes B2)

Use `per_query_sources[i]`, not `sources_per_query`.

### Out of scope, deliberately
Phase 3 mapper answeredness · `_grounds_applied` precision · `F-MMR-POOL` · A5's degenerate
decompose fallback (rot, logged in §7, not load-bearing).

---

## 5. Decisions needed before build

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **E1** | Class A on grounds-routed claims | (i) suppress claim-text fallbacks entirely — risks thin pools with no backfill · (ii) substitute element-derived queries · (iii) leave as-is and accept the valence leak | **(ii)** — keeps the safety net that A1–A4 exist to provide while removing the valence. (i) trades one honesty problem for a coverage one |
| **E2** | `c0` synthesis form | (i) claim text verbatim, as pre-Phase-2 · (ii) claim text + class augmentation | **(i)** for this phase — one variable at a time; augmentation already reaches `c0` downstream |
| **E3** | B2 now or later | (i) now, it is two lines · (ii) defer | **(i)** — it silently voids criterion 10 on a live path |

---

## 6. Acceptance criteria — FROZEN

Verified by a pass that did not build. Phase 1 §4a rules apply: mutate each guard, assert the
mutation applied, restore in `finally`, hash-verify after.

| # | Criterion | Evidence |
|---|---|---|
| 1 | Planner returns no `c0` plan → one is synthesised; merged plan has `element_wired=True` and a claim lane with ≥1 query | unit test + mutation |
| 2 | `element_wired` derives from lanes built, not plans returned — a plan list missing `c0` still yields `True` | unit test + mutation |
| 3 | Per-lane request sizes hold when `c0` was synthesised: claim lane 13, element lanes 5 | assert `max_results` per mocked call |
| 4 | Freshness fallback uses per-lane sizes | unit test + mutation (restore `sources_per_query` → fails) |
| 5 | Grounds-routed claim: no claim-text query from A1, A2, A3 or A4 | unit test per site |
| 6 | Factual claim: A1–A4 **byte-identical to today** | regression test — this is the Grenfell guard in unit form |
| 7 | `ENABLE_ELEMENT_RETRIEVAL=False` → today's behaviour, including caller-supplied elements (criterion 18 holds) | regression test |
| 8 | Full suite: no new failures vs 2924 passed / 11 failed (Redis) / 69 skipped | captured pytest output |
| 9 | Zero prompt bytes, **except** the optional `c0` example in D-2 — declared, not silent | `git diff` |
| 10 | **LIVE: `element_wired=True` observed in real telemetry**, on both a factual and an evaluative claim | `[RETRIEVE] Query lanes \| wired=True` in logs — **the check that would have caught today's failure at build time** |
| 11 | **LIVE: re-run the criterion 17 trio** — T4 no valence in ANY query incl. recovery · T2 alternative-treatments searched · T3 Grenfell no regression | networked run + logs |

Criterion 10 is the lesson of this whole phase made mechanical: **a guarantee that depends on
an LLM's cooperation is not a guarantee, and only live telemetry proves which you have.**

---

## 7. Rot found (logged, not all fixed)

- `retrieve.py:1214` docstring example still `[{"element_id": "e1", ...}]` — pre-lane vocabulary.
- `max_queries_per_element` — named for per-element behaviour that did not happen for months.
  It now does; the name is finally honest. No action.
- `claim_map_analyzer.py:2049-2053` — degenerate decompose fallback makes claim text element
  `e1`. Same premise as the rest, currently unreachable in the normal path. **Leave, log,
  re-check after this phase.**
- `retrieve.py:967` `queries[:2]` — recovery capped at 2 queries with a latency comment; the
  cap predates concurrent execution.

---

## 8. Risks + reversibility

| Risk | Mitigation | Reversible? |
|---|---|---|
| Synthesised `c0` re-introduces valence on evaluative claims | E1 makes the fallbacks grounds-aware; `c0` on a grounds-routed claim is the open question D3 deferred from Phase 2 — **revisit with measurements, now that we can measure** | flag |
| Suppressing claim-text fallbacks thins evaluative pools | criterion 5 + 6 split factual from grounds-routed; E1(ii) substitutes rather than removes | yes |
| Larger pools reintroduce the fetch-budget bite | that is the designed behaviour; criteria 3 + 10 confirm it live | flag |

**Rollback:** `ENABLE_ELEMENT_RETRIEVAL=False` still restores pre-Phase-2 behaviour without a
deploy, and now genuinely does for every caller (criterion 18).
