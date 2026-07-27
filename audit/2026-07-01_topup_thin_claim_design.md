# Design — "Top up a thin claim" (extend re-search to thin elements)

**Date:** 2026-07-01. Status: **BUILT + INDEPENDENTLY VERIFIED + COMMITTED (both phases).** Method: [[phased-build-loop]] / DBTV.
**Handoff:** scoped with founder over a discussion; a fresh agent implemented. This doc is the spec — read it + the Reuse Map before writing code.

## BUILD LOG (2026-07-01)
Both phases ran under [[phased-build-loop]] (design→approve→build→INDEPENDENT verify→sign-off). Founder chose the **new claim-level endpoint** (not per-element fan-out) and approved migrating `ResearchButton` onto a shared hook to avoid a duplicated poll loop.
- **Phase 1 (backend):** new `POST .../claims/{claim_id}/research-thin` (`checks.py`, mirrors `start_gap_research`; console-only; 1 credit for all thin elements) + `backend/app/pipeline/support_structure.py` — the single backend port of `web/lib/support-structure.ts`'s thin/echo thresholds (`element_is_thin`/`thin_element_ids`). Tests: `test_thin_support.py` (parity table locked to the TS test) + a path-separation test. Independent verify: **5/5 ACs PASS**; 43 tests green; route registers.
- **Phase 2 (frontend, dashboard-only):** `web/hooks/use-research-poll.ts` (extracted start→poll→refresh loop, now shared by gaps + top-up); `TopUpButton.tsx` (per-element "Get more sources" + claim-level "Strengthen this claim", 1 credit, neutral/orange); `elementIsThin`/`thinElementCount` in `support-structure.ts` (parity-locked to backend); `ElementList`/`ClaimSummaryPanel` optional `topUp` prop; dashboard call site wires it, `/r/` passes nothing (no trigger there). `ResearchButton` migrated to the hook (Seeker unchanged). Independent verify: **7/7 ACs PASS**; tsc 0; vitest 50/50; Seeker non-regression diffed vs HEAD.
- **REMAINING (founder):** live eyeball tonight on a real completed dashboard check with a thin element (motivating case `TRU-DE7E-8259`, element 02) — pixel/interaction + the top-up actually completing + evidence refreshing were NOT machine-verified (browser not driven; avoided `npm run build`/`start` to protect the dev cache).

## Goal
Let a signed-in user pull MORE evidence into the **existing** pool for a claim/element that came back **thin**, from the claim/Map surfaces (not just the Gaps view). Founder's motivating case: check `TRU-DE7E-8259` — element 01 excellent, element 02 (the interesting one) average/poor; the user should be able to strengthen element 02 without starting over.

## THE KEY INSIGHT — most of this already exists
The **re-search mechanism IS the top-up.** `run_element_re_search` (`backend/app/pipeline/re_search.py:64–317`) already: plans queries (with bounty text) → retrieves new evidence → classifies → **dedupes by URL against existing** → **re-maps new + existing evidence together into the same `claim_map`/pool** → saves. That's the "adds to the same array" the founder loves. It already **charges 1 credit** and works on **any element (not just gaps)**. So the backend for "top up a thin element" is essentially DONE. The new work is mostly **frontend surfacing** + a small **claim-level bundle** decision.

## SETTLED DECISIONS (do not re-litigate)

### 1. "Thin" definition (LOCKED)
An element shows the top-up trigger iff it is **NOT a pure gap** AND **any** of:
- **≤ 2 mapped sources** (`evidenceRefs.length <= 2`), OR
- carries the **thin/echo sourcing note** (from `web/lib/support-structure.ts` — commentary-only, single-outlet, or echo), OR
- **state === `unresolved`**.

**Excluded (no trigger):** 0-source elements (those are GAPS → already handled by the Seeker re-search), `disputed` elements (evidence-rich, not thin), and well-covered elements (≥3 sources / ≥2 domains / ≥1 primary-or-reporting tier + resolved state).
All three signals are already computed per element → **"thin" is a pure frontend read, no pipeline change.**

### 2. Triggers — BOTH (founder-confirmed)
- **Per-element "Get more"** on each thin element in the platformed roster (the `ElementList` we shipped in `ClaimSummaryPanel`) — precise, 1 run.
- **Claim-level "Strengthen this claim"** — tops up ALL the claim's thin elements in one run for one unit (mirrors the existing gap-research "all gaps, one charge").
- **Dashboard only.** The public `/r/[id]` report is read-only — no trigger there.

### 3. Accounting — "a top-up = another pipeline run = 1 unit" (LOCKED)
A top-up is just another (honed, dedup-against-existing) pipeline run, so it counts as **1 unit exactly like a check** — **no feature-specific / per-element cap** (that idea was rejected as over-engineering a global concern).
- **Credit tiers (Free 3 / Starter 40 / Pro 200):** draws **1 credit** from the monthly quota — **already how re-search works today** (`_check_credits` + `_deduct_credit`, `checks.py:1546–1586`). No new code.
- **£20 Console (fair-use, no credit system):** counts as 1 pipeline run against a **global fair-use ceiling** — but that ceiling is **DEFERRED** (revisit once usage data exists). It's a **Console-policy** item governing checks + top-ups globally, NOT part of this feature. Today Console is effectively unlimited.
- Note: a top-up genuinely costs us LESS than a full check (skips ingest/extract/decompose), so counting it as a whole run is conservative — safe on margins.

## WHAT'S ACTUALLY NEW TO BUILD
1. **Frontend — surface the trigger on thin elements.** In the `ElementList` roster (digest) — a "Get more" affordance on each thin element (reuse the "thin" read above). Prominent on thin, hidden on well-covered.
2. **Frontend — claim-level "Strengthen this claim"** button on the claim section (digest / Map).
3. **Backend — decide the claim-level bundle:** either (a) a NEW endpoint that re-searches the claim's THIN elements in one run/charge (mirror `start_gap_research` which bundles all gaps), or (b) the frontend fires per-element calls (simpler, but multiple charges — worse UX). **Recommend (a)** — one run, one charge, mirroring gaps.
4. **Frontend — wiring + states:** reuse `ResearchButton`/`BountyField` patterns, `apiClient.startElementResearch` / `getResearchStatus`, the "1 credit" label, 402-limit handling, status polling.

## REUSE MAP (from 2026-07-01 research — file:line)
- **Retrieval + merge:** `run_element_re_search()` `re_search.py:64–317` (re-maps new+existing to the same claim_map; dedupe by URL). Use as-is.
- **Existing endpoints** (`backend/app/api/v1/checks.py`):
  - `POST /{check_id}/claims/{claim_id}/research-gaps` (all gaps, 1 credit) — lines ~1590–1690; JWT console-only gate ~1611.
  - `POST /{check_id}/claims/{claim_id}/elements/{element_id}/research` (one element, 1 credit) — lines ~1693–1790. **This already does per-element top-up.**
  - `GET .../elements/{element_id}/research/status` — lines ~1793–1828 (Redis polling).
  - Concurrency guard (no double-run on same element) ~1661–1672 / 1763–1774; requires check `completed`.
- **Credit charge:** `_check_credits()` `checks.py:1546–1578` + `_deduct_credit()` `1581–1586` (works for free-trial `user.credits` AND subscription monthly quota). Currently flat 1 credit — fine, keep.
- **Frontend:** `web/components/evidence-views/seeker/ResearchButton.tsx`, `BountyField.tsx`; `web/lib/api.ts:329–365` (`startGapResearch` / `startElementResearch` / `getResearchStatus`).

## Availability conditions (per trigger)
- Check status `completed`.
- Element is "thin" (per §1) / claim has ≥1 thin element (for the claim-level button).
- Not already running (backend guards).
- Within credits (credit tiers) — 402 → show "limit reached" (existing pattern). Console: no gate yet (deferred ceiling).

## Acceptance criteria (for the build phase)
1. Thin elements in the digest roster show a "Get more" trigger; well-covered / gap / disputed elements do NOT.
2. Claim-level "Strengthen this claim" appears when the claim has ≥1 thin element; runs one top-up over its thin elements for one charge.
3. Top-up reuses `run_element_re_search` → new evidence merged into the SAME pool, deduped by URL, re-mapped; no duplicate existing evidence.
4. Credit tiers: 1 credit deducted per top-up run (existing behaviour); 402 handled.
5. Console: runs without a credit charge (ceiling deferred); no new cap code.
6. Dashboard only; `/r/` unaffected. Not-yet-run/completed + concurrency guards respected.
7. Tests: backend endpoint (if new bundle endpoint) + frontend trigger visibility logic (thin read); tsc 0.

## DEFERRED / OPEN (not blocking the build)
- **Console global fair-use ceiling** — revisit with usage data (Console-policy, governs checks + top-ups; not this feature).
- Whether the claim-level bundle is a new endpoint (recommended) or per-element fan-out.
- Whether to also expose top-up on the Map view element roster (digest is primary).
