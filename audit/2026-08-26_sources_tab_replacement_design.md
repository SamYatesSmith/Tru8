# Replacing the SOURCES tab — design + pressure test

> ## ⛔ SUPERSEDED 2026-08-26 by `2026-08-26_compare_tab_design.md`
>
> **The INDEPENDENCE tab proposed here was REJECTED by the founder**, correctly:
> once the derivation headline was cut on measurement, what remained
> (concentration bar + sole-source badges) is **already on SOURCES today** — a
> cleanup, not a differentiator, and not worth a tab.
>
> **This doc is retained for its measurements only** (§3), which are what stop
> the echo tab being re-attempted. The design in §4–§6 is dead.
>
> Also rejected on the same day, recorded in the successor doc: diagnostic
> value / ACH (top bucket fires 0–10%), entity extraction (`key_entities` = 2
> generic nouns per claim), and "The Working Out" (per-ref `reasoning`, 100%
> populated — killed on the founder's product filter: **users want the software
> to work; they do not care how or why**). That filter retired the entire
> transparency family.

**Date:** 2026-08-26
**Status:** SUPERSEDED — measurements live, design dead
**Trigger:** Cold-reader feedback (founder's partner, 2026-08-25 evening): the
SOURCES tab *"feels redundant… too close to the collective of what the other
tabs do."*
**Related:** `2026-08-12_cold_viewer_pass` (prior cold-read), `OPEN_WORK.md`
2026-08-24 product gaps (item 1 Fix 1 uncertainty rendering, item 3 gaps-lens
provenance blindness — **this doc closes item 3**).

---

## 1. The complaint, verified

The cold read is correct, and there is a sharper defect underneath it.

**SOURCES is the one tab where you cannot open a source.** `SourceCard.tsx` is a
`<button>`; expanding it lists evidence titles as **plain text with no anchor**
(`SourceCard.tsx:118-124`). The only `Visit source →` in the results UI lives on
the EVIDENCE tab, inside `ReadingTable` (`ReadingTable.tsx:137-146`).

So the tab named for sources presents a degraded copy of the ledger beside it:
same titles, no link, no date, no tier stamp, no element refs. That is the
redundancy the cold reader felt — she just had no reason to name the cause.

### 1.1 What overlaps, what doesn't

| SOURCES shows | Also on |
|---|---|
| Tier counts (primary/reporting/commentary) | EVIDENCE — heatmap + filter pills |
| Per-domain date range | TIMELINE |
| "No primary sources" / "No academic" flags | GAPS |
| Evidence titles | EVIDENCE ledger (with links) |
| **Domain grouping** | nowhere else |
| **ConcentrationBar** | nowhere else |
| **"Sole source for E02"** | nowhere else |

Four of seven rows are duplicated elsewhere. The three that aren't are all
facets of one question — *how concentrated is this evidence, and where is there
a single point of failure* — wearing a list's clothes.

The subtitle already concedes the confusion: *"Is the full set here?"* is a
coverage question, which is GAPS's job.

**Diagnosis: not wrong, mis-scoped.** The tab was built as "here are the
sources"; the Evidence ledger then grew up and took that job properly.

---

## 2. Two datasets we compute, sign, and have never shown anyone

Searching for what could justify a replacement tab surfaced two assets already
paid for by the pipeline and rendered nowhere in `web/`:

1. **Six scope-gate receipts** per element — `temporal_scope`,
   `jurisdiction_scope`, `measure_scope`, `interested_party`, `recital_scope`,
   `echo_scope` (`claim_map_analyzer.py:1448`). Each carries the exact refs it
   re-labelled to `context` and why. They live in element `basis`, typed only as
   `[key: string]: unknown` (`shared/types/index.ts:265`). **Zero frontend
   readers.**
2. **`queryPlan`** — every query issued, per element lane, *including
   zero-yield queries* (`ClaimMap.metadata.queryPlan`). **Zero frontend
   readers** (grep: no matches in `web/`).

Additionally `annotate_derivation_chains` (`corroboration.py:524`) computes a
real per-source `derivation_chain` — naming which sources recite a given
primary — which is used to derive the aggregate and then **discarded**
(`runner.py:2295` annotates in memory; the payload keeps only
`derivation: {originals, derivative_count}`).

---

## 3. PRESSURE TEST — measured, not assumed

The first draft of this tab ("Paper Trail" — 8 UI elements built on the
derivation/echo story) was measured against real checks **before** being
written up. The result changed the design substantially.

### 3.1 Sample A — captured production checks

`backend/scripts/.6b54_capture_artefacts.json` + `.c051_capture_artefacts.json`
(9 July 2026, 2 checks, 4 claims, 13 elements, 13 non-empty evidence sides).

Both derivation fixes predate the capture — `b2a43bb` (2026-07-01, post-classify
derivation chains) and `d0d6d8b` (2026-07-07, F4 repetition detector) — so these
values reflect working code, not the pre-fix no-op.

| signal | fires on | share |
|---|---|---|
| `derivation.originals > 0` | 1 of 13 sides | **8%** |
| `derivation.derivative_count > 0` | 3 of 13 sides | **23%** |
| `repetition.max_cluster_on_side > 0` | 0 of 13 sides | **0%** |
| element has a SINGLE contributing domain | 2 of 12 populated | **17%** |
| element has ≤2 contributing domains | 4 of 12 populated | **33%** |

⚠️ **`sole_domain` is absent from these captures** — the field postdates them.
Its zeros are a capture artefact and were discarded, not reported.

### 3.2 Sample B — replay corpus, current code

10 corpus claims, `observation.json`, recorded 2026-08-17 (post element-level
retrieval and F7 re-gold, so tier mixes are current).

| claim | echo refs | interested-party | recital | domains | top-domain share |
|---|---|---|---|---|---|
| TRU-018F-44AA | 0 | 3 | 4 | 21 | 0.19 |
| TRU-5647-FA4F | **4** | 0 | 0 | 13 | 0.08 |
| TRU-82CF-2F81 | 0 | 0 | 0 | 7 | 0.25 |
| TRU-93DD-F4B7 | 0 | 0 | 0 | 8 | 0.12 |
| TRU-A3E8-3199 | 0 | 0 | 0 | 9 | 0.20 |
| TRU-B4A3-C42D | **2** | 0 | 6 | 14 | 0.12 |
| TRU-C1A0-0001 | 0 | 0 | 0 | 9 | 0.60 |
| TRU-C1A0-0003 | 0 | 0 | 0 | 6 | 0.44 |
| TRU-C1A0-0004 | 0 | 0 | 0 | 5 | 0.20 |
| TRU-C1A0-0005 | 0 | 0 | 0 | 5 | 0.38 |

- **Echo gate fires on 2/10 claims.**
- **Recital 2/10, interested-party 1/10** — collectively **4/10 claims carry at
  least one scope receipt.**
- **Domain concentration is populated and genuinely varied on 10/10** —
  top-domain share spans 0.08 → 0.60, unique domains 5 → 21.

### 3.3 The finding that changed the design

**The derivation/echo story — the thing I recommended as the differentiator — is
the rarest signal we produce.** On roughly 80% of checks the headline would read
*"10 sources → 10 originals"*: a non-statement dressed as an insight, and
exactly the "relatively meaningless element distracting from the interesting
derived information" this pressure test was asked to catch.

**Concentration is the only always-populated, always-varied signal.** Scope
receipts fire twice as often as derivation. So the spine of the tab must be
concentration + single-point-of-failure, with derivation and scope receipts as
**conditional headline bands** that take top billing on the minority of checks
where they fire.

⚠️ **Sample honesty.** Sample A is 2 checks on ONE topic (alcohol/heart) from
9 July — small, and predating the F7 re-gold that raised primary-tier counts
corpus-wide (2→10, 6→11, …), which plausibly *raises* the originals rate.
Sample B is current and more diverse but reports gate firings, not derivation.
**Neither sample measures elements 7 (shared owner) at all.** Before building
the conditional bands, re-measure `originals`/`repetition` on 20+ current
production checks (`railway ssh`, not `railway run` — the latter cannot reach
the prod DB).

---

## 4. Verdict on each of the 8 proposed elements

| # | Element | Populated | Verdict |
|---|---|---|---|
| 1 | Headline `8 sources → 3 originals` | ~8–20% | **CUT as headline.** Demote to a conditional band. |
| 2 | Independence bar (originals/derivatives/repetition) | ~8–20% | **CUT.** One solid block on 80%+ of checks. |
| 3 | Per-element strip | 100% renders, trivial ~80% | **KEEP, reframed** — lead with *domains*, not originals. |
| 4 | Origin cards + derivative expansion | ~20% | **KEEP, conditional.** Spectacular when it fires. Needs backend. |
| 5 | Unanchored repetition cluster | 0% observed | **KEEP, conditional, LOWEST priority.** Never once seen. |
| 6 | Sole-source flags | 17% sole / 33% ≤2 domains | **KEEP — the workhorse.** Most frequent real signal. |
| 7 | Shared-owner note | unmeasured | **DEFER.** Unmeasured + needs backend. Do not build on faith. |
| 8 | Method + limit note | 100% | **KEEP.** Cheap, and invariant #5 requires it. |

Net: **8 proposed → 4 kept, 2 conditional, 1 deferred, 2 cut.**

---

## 5. Revised design — INDEPENDENCE

**Tab label:** `INDEPENDENCE` · **subtitle:** *"How many voices, really?"*

Answers a question no other tab answers, and no competitor answers at all.
Ground News shows outlet *bias*; this shows source *independence* — the thing
that determines whether "well covered" means anything.

### 5.1 Always-on spine (every check)

1. **Concentration header** — unique domains, top-domain share, tier split by
   domain (not by item — unit-consistent, per the existing
   `CorrespondentSummary` discipline).
2. **ConcentrationBar** — carried over unchanged. Already the best thing on the
   old tab.
3. **Per-element independence strip** — *"E02 — 4 sources across 2 domains."*
   This is what closes the parked gap: the Gaps lens reading WELL COVERED on a
   claim propped by six echoes of one evaluation.
4. **Sole-source flags** — *"Only source for E02."* Grey `EvidenceQualityNote`
   idiom (mono 10px zinc-500, `NOTE ·` prefix), **not** the `amber-700` it wears
   today — consistent with the Fix 1 no-verdict-colour decision.
5. **Method + limit note** — how independence was determined, and the honest
   limit that the ownership map is partial.

### 5.2 Conditional bands (top billing when they fire)

6. **ECHO DETECTED** (~20%) — *"5 of these 8 recite 2 originals."* Origin cards:
   domain, title, date, tier, **Visit source →**, derivative count; expand for
   the sources reciting it.
7. **SET ASIDE** (~40%) — the scope receipts. *"3 sources were found but do not
   bear on this claim"* — different period, another country's national body, a
   different measure, a party with an interest, a recital of the claim itself,
   an echo of a source already counted. Symmetric by construction, so it
   *demonstrates* invariant #7 rather than asserting it.
8. **UNANCHORED REPETITION** (rare) — *"5 sources, same wording, no original
   found."* Build last.

### 5.3 Explicit non-goals

- **No independence score, no ranking, no good/bad colouring.** Structure only.
  A number here becomes outlet credibility scoring and breaks the "classify,
  don't score" lock.
- **No title list.** That is the ledger's job; duplicating it is the defect
  being fixed.
- **Every source name links out.** Fixes the naming lie in the current tab.

---

## 6. Build cost

**Frontend-only (ships without any backend change):** spine items 1, 2, 3, 4, 5,
plus band 7 (scope receipts are already in element `basis` with refs attached —
they need typing in `shared/types/index.ts`, currently `unknown`).

**Needs backend:** band 6 origin cards and band 8 cluster members require
persisting `derivation_chain` (and, for the deferred element 7,
`ownership_group`) onto the Evidence row. Both values exist at annotation time
and are discarded — a small addition plus a migration, no new computation.

**Deep-link hazard:** `?view=correspondent` is URL-persisted and deep-linkable.
Replacing the tab needs an alias or those links fail silently. A full reference
sweep is the companion workstream to this doc (§7).

---

## 7. Companion workstream — reference cleanup

Replacing the tab touches more than the component directory: tab registration,
the `ViewTab` union, deep-link parsing, both host pages (dashboard + `/r/`),
analytics `view_opened` values, tests, and any hardcoded "six views" phrasing in
marketing copy, the ViewGuide, developer docs, and backend/MCP descriptions.

A codebase-wide sweep was commissioned alongside this design. **Its results
append to this doc as §8 before any build starts** — the cleanup plan is a
prerequisite, not a follow-up.

---

## 8. Sweep results

*(pending — appended when the reference sweep completes)*

---

## 9. Open decisions for the founder

1. **Approve the direction?** INDEPENDENCE replaces SOURCES, spine + conditional
   bands.
2. **Frontend-only v1, or wait for the backend persistence** so the echo band
   ships with it? v1 is genuinely useful without it; the echo band is the
   headline differentiator.
3. **Re-measure first?** §3.3 flags that Sample A is thin and dated. A 20-check
   production measurement would firm up the conditional-band frequencies before
   any build effort.
4. **Timing.** This is presentation work, not pipeline work — but it is not
   send-week work either. Recommend: decide now, build after the outreach sends
   land.
