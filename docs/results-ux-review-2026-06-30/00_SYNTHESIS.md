# Results-presentation UX review — competitor research → match/improve

> 2026-06-30 · Lens: **how rivals present results/evidence, and how we make our signed-in results faster + easier to read.**
> Method: 5 parallel research streams (3 direct rivals + adjacent best-practice + a code-grounded survey of our own current UX). Confidence marked HIGH (publicly verifiable, cited) vs LOW (behind sign-in / inferred).
> This is a **review + opportunity map**, not a build plan. The signed-in redesign is to be designed + agreed separately (phased-build-loop).
> Competitor set is the finalised one (`audit/2026-06-23_release_plan.md`): direct = Webcite, Factiverse, scite.ai; adjacent harvested for patterns only.

---

## 1. What each rival actually offers (results UX)

| Rival | Results surface | At-a-glance device | Evidence unit | Stance model | Export/share | Key weakness |
|---|---|---|---|---|---|---|
| **scite.ai** (closest analog) | Public **scite report**: tally header + Cited-by/References tabs + left filter rail | **Clickable colour+glyph tally** (supporting / mentioning / contrasting counts that *are* the filter) | **Citation-statement card**: verbatim quote + section-of-paper tag + classification + **confidence %** + link | No verdict — shows the landscape | CSV/RIS, shareable report URL, embeddable badge, dashboard aggregate tallies | "Research-cockpit" overload; **colour drift** (contrasting = red vs blue across surfaces) |
| **Webcite** | **None public — API-only (JSON).** Hero "Verify" is gated | `stance_breakdown` numeric tally (in JSON) | JSON citation object: snippet + stance + 5-type + `is_primary_source`/`is_fact_check_site` + `highlight_terms` | **Emits a verdict** (4-value) — and per-citation stance is 5-value (mismatch) | JSON (free) / JSON+CSV ($20) — no permalink, no human report | **No human-readable surface at all**; single opaque credibility donut, no rationale |
| **Factiverse** | Per-claim cards in a results column; **gated/blurred behind sign-in** | "**Supported rate**" + one-line "what's supported vs disputed" summary | Source card: snippet + supporting/disputing/neutral + credibility-ranked link | **Predicted veracity** (NLI majority of credible sources) | CSV/PDF + CMS + API | Verdict-style aggregation; **proof is gated** (no public report); reviewers call the presentation layer thin/under-designed |

**The convergent pattern (all three):** a **stance tally** + **stance-split evidence cards** + **top-of-results filters**. That is the table-stakes shape of an evidence-results page.

**The shared gap we already beat:** **none has a public, linkable, well-designed human-readable report.** Webcite is JSON-only; Factiverse blurs results behind login; scite is academic-only. Our `/r/[id]` + six rendered views are a genuine edge — *if* the first-glance answer reads fast.

---

## 2. Our differentiators to PROTECT (research-confirmed)

1. **Public, rendered, shareable report** (`/r/[id]`) — no direct rival has one. Strongest asset for the "defend my sourcing" buyer + SEO + the research funnel.
2. **Six lenses** (Evidence/Sources/Timeline/Gaps/Map/Video) — no rival offers multiple views of one analysis.
3. **No-verdict + receipts for exclusions + signed record + ~30 gov/legal/academic sources** — unique combination; every rival adds a verdict or a score and none publishes exclusion receipts.
4. **Mechanical orientation from element states** — more inspectable than scite's deep-learning label or Factiverse's NLI prediction. Lean into "here's *why*, mechanically."

Guardrail: do not trade any of these away while chasing parity polish.

---

## 3. Our current baseline + the readability gap (from the code survey)

Our signed-in results live at `/dashboard/check/[id]` (mirrored at `/r/[id]`). The first-glance answer is **`ClaimSummaryPanel`** — claim text (H2) + neutral element-state counts (supported/disputed/contextual/gaps, clickable) + a text orientation line + tier-mix footer + an "explore" rail to the six lenses. Detail lives in the six views; the default is the Librarian (Evidence) ledger.

**Honest friction for "reading results fast" (from `web/components/evidence-views/...`):**
1. **First-glance answer is text-dependent.** Counts are neutral zinc numbers + a prose orientation line — you *read*, you don't *pattern-match*. Scanning many claims, you can't see the shape in <1s. (This is the dominant gap — every rival has a visual tally and we don't.)
2. **No summary-level sort/filter across claims** — can't "show me just the disputed claims" without opening each.
3. **Orientation is prose, not visual** — can't compare claims' "leans" side by side.
4. **No evidence preview at summary altitude** — to see *what* supports/challenges, you must open the Librarian view.
5. **Detail lenses are dense on mobile** (Librarian → horizontal-scroll table). Known issue ([[feedback-mobile-different-ui]]).
6. **Gaps are prose** — Seeker names gaps in text, no glanceable "what's missing" device, no jump-from-gap.
7. **Processing is a static ETA** — no live, auditable sense of the work happening.

---

## 4. The match/improve opportunity map (ranked by readability payoff)

Each item: the borrowed pattern → our current state → how it respects our invariants. **Effort** S/M/L. All framed as *faster/easier to read*, none introduces a verdict.

| # | Opportunity | Borrowed from | Our state today | Invariant check | Effort |
|---|---|---|---|---|---|
| **1** | **Visual distribution bar at claim altitude** — one horizontal stacked bar: supports / challenges / context, each segment labelled by **word or icon + count + share**. The single highest-leverage readability win. | Ground News bias bar (#1); the universal tally (scite/Webcite/Factiverse) | Neutral text counts only | **Neutral palette + icon/position, NOT traffic-light** (Google validates text-only stance). Shows *distribution of evidence*, never a true/false ruling. Use zinc/structural tones. | M |
| **2** | **Make the bar/tally the filter control** — click the "challenges" segment → Evidence view filtered to challenges. | scite clickable tally → filtered evidence | Counts are already clickable→filter; under-leveraged + invisible | Pure navigation; no scoring | S |
| **3** | **Neutral synthesis line with inline cite-back** — a strictly descriptive summary ("N sources address this; X support, Y challenge, Z context") with inline numbered refs that hover-preview the platformed snippet. | Elicit/Consensus synthesis-on-top; Perplexity hover-cite (#4,#6) | Prose orientation line, no refs | Descriptive only; refs drive visits (source-platforming rule); we already compute `orientation_basis` | M |
| **4** | **Standardise the evidence card** — favicon + domain + title + date + **Tier/Type badge** + stance + verbatim snippet + archived link, with a "where/what-kind" tag. Cap visible cards per stance + "view all N" (receipts cover the rest). | scite verbatim+section card (#2); Perplexity favicon cards (#10); Consensus quality badges (#11) | Ledger cards exist but inconsistent; no favicon | Classify-don't-score (Tier/Type, not a number); snippet platforming preserved | M |
| **5** | **Summary-level sort/filter across claims** — sort the multi-claim grid by evidence shape ("most disputed first"), filter to disputed/gapped. | Factiverse/scite top-of-results filters | None at claim-grid altitude | Navigation only | M |
| **6** | **Quantified, glanceable gaps** — Seeker shows "no challenging evidence for element 3", "coverage thin on the economic angle" as scannable labels + jump-from-gap. | Ground News Blindspot (#7) | Gaps named in prose | Matches Seeker/known-unknowns; receipts-adjacent | S–M |
| **7** | **Citation/reference export** — per-claim RIS / BibTeX / CSV + a citable bibliography. Researcher table-stakes; **Perplexity lacks clean export → beatable**. | Consensus citation export (#12) | PDF/CSV/JSON only | Pure export; serves the researcher funnel | M |
| **8** | **Per-element coverage/strength label** — a small **3-level worded** label (e.g. well-evidenced / partial / thin), tied to the actual `evidence_refs` + basis. | Parallel Basis calibrated 3-level confidence (#8) | Element states only | **Must read as evidence STRENGTH/COVERAGE, never a verdict on the claim.** Tied to refs we already compute. Risk item — design carefully or skip. | M |
| **9** | **Live, expandable pipeline steps during processing** — show ingest→extract→retrieve→classify→map executing, each expandable to per-source retrieval. | Perplexity progressive reasoning (#5) | Static ETA bar (SSE already wired) | Reinforces no-hidden-curation; justifies latency | M |
| **10** | **Mobile: purpose-built dense-view** — replace horizontal-scroll Librarian table with a mobile-native evidence list. | (our own known issue) | Responsive desktop table | [[feedback-mobile-different-ui]] | L |

---

## 5. Guardrails / anti-patterns (do NOT borrow)

- **No verdict colour for stance.** scite (green/red) and Consensus bake true-false into hue; Google deliberately uses text-only. We use words/icons/position + neutral structural colour (Tier/Type), never green/red for supports/challenges. (Invariant.)
- **No single opaque score/donut.** Webcite's 96% credibility donut + Originality's "Fact Check Score %" collapse a distribution into one verdict-shaped figure with no rationale. Violates classify-don't-score + receipts. Prefer the distribution bar + 3-level worded labels.
- **No locale-coded "side" colour.** Ground News' left/right colours invert US vs UK — any colour tied to a side misleads.
- **Don't gate the proof.** Factiverse/Webcite's biggest weakness is no public report. Keep `/r/[id]` open + indexable.
- **Don't ship a "research cockpit."** scite's overload lesson → progressive disclosure; the summary reads in 1s, depth on demand.
- **Lock one colour/icon token set** across every surface (scite's colour drift is a cautionary tale).

---

## 6. Recommended next step

This review is the brief. The natural sequencing for the signed-in redesign (to be designed + agreed under the phased-build-loop, **not** started yet):

1. **Opportunities 1–3 first** (visual distribution bar + click-to-filter + neutral cite-back synthesis) — they rebuild the *first-glance answer*, the dominant gap, and are mostly frontend on data we already compute.
2. Then the **evidence-card standardisation (#4)** + **claim-grid sort/filter (#5)** + **glanceable gaps (#6)**.
3. **Export (#7)**, **coverage label (#8, careful)**, **live pipeline (#9)** as follow-ons.
4. **Mobile (#10)** as its own track (different UI, not responsive).

Open decisions to settle with the founder before designing: (a) how far the distribution bar goes (claim altitude only, or also the multi-claim grid); (b) whether the per-element strength label (#8) is worth the verdict-adjacency risk or should be dropped; (c) priority of export vs visual-summary work.
