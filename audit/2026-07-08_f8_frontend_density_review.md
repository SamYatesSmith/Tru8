# F8 — Frontend Information-Density & Wayfinding Review

**Date:** 2026-07-08
**Status:** DESIGN REVIEW — awaiting founder sign-off. **No code until decisions are made.**
**Lens:** Information density, duplication, wayfinding — "elevate the interesting, cut the rest," from the fixed researcher-buyer perspective.
**Extends (does not replace):** `docs/page-review-2026-06-29/` (copy/positioning/design-grammar) and `docs/results-ux-review-2026-06-30/` (results redesign rationale). Both are prior lenses; F8 is the density/wayfinding lens the founder scoped for its own session.
**Ground truth:** live code as of 2026-07-08. Every claim below is cited `file:line`. Where a prior doc conflicts with code, the code wins and the conflict is flagged.

---

## 0. The brief (what we are solving)

The founder's observation, two surfaces:

1. **Entry point** (`/`, `/research`, nav, associated routes) is confusing for a *human* visitor. Per the researcher-buyer reframing, the human should be platformed more strongly; the API/agent audience currently competes for and wins attention.
2. **Results page** is too busy — it platforms similar information in multiple places, a confusion never resolved. Hypothesis: we platform too much at once.

The goal is **subtraction and hierarchy**, not addition. Cut noise, consolidate duplication, elevate the genuinely interesting signal. Keep the six-lens interactivity (a real edge — no rival has a public human-readable report) but reduce simultaneous density.

**What is already settled (do NOT re-litigate):**
- Two-variant front door is *intentional*: `/` developer-led, `/research` researcher-led (release-plan 2026-06-23). Any wholesale `/` CTA flip is a founder decision, not a silent fix.
- Nav already collapsed to Product · Compare · Pricing · Developers, single front door, no splash (`95a2610`; `audit/2026-06-17_homepage_nav_shape.md`).
- Locks: no verdict language/colour; UK English; six views named by ACTION (Evidence/Sources/Timeline/Gaps/Map/Video), professions internal only; classify-don't-score.
- Results signed-in UX (Evidence Digest, segmented switcher, neutralised colours, element badges, echo/thin/repetition notes, F5 PDF, F6 coverage note) is shipped and stable — so screenshot/asset refresh is unblocked.

---

## PART 1 — ENTRY-POINT FINDINGS

### 1.1 Route inventory (everything a human hits before `/dashboard`)

H = human researcher-buyer · A = API/agent-developer · B = both.

| Path | Purpose | Audience |
|------|---------|----------|
| `/` (`web/app/page.tsx:63`) | Landing — developer/API-led variant | B, leans **A** |
| `/research` (`web/app/research/page.tsx:90`) | Researcher-led pitch, Console-primary, CTA → `/dashboard` | **H** |
| `/compare` (`web/app/compare/page.tsx`) | Tru8 vs 4 grounding APIs, verbatim responses | B, leans A |
| `/pricing` (`web/app/pricing/page.tsx:21`) | Console (£20 human) + metered API pricing | B |
| `/developers` (`web/app/developers/page.tsx`) | API + MCP docs, quick-start, tiers | **A** |
| `/about` (`web/app/about/page.tsx:14`) | Mission — researcher framing | H |
| `/contact`, `/blog`, `/blog/*` | Contact, blog (one post is agent-oriented) | H (+1 A) |
| `/verify/[id]` (`web/app/verify/[id]/page.tsx`) | Public manifest verification | B (technical) |
| `/r/[id]` (`web/app/r/[id]/page.tsx`) | Public evidence report (pipeline output) | H (output) |
| Legal pages | privacy/terms/cookie/refund | H |
| **Sign-in / Sign-up** | **No route** — Clerk `AuthModal` from nav (`navigation.tsx:86`) | H |

**Note:** there is no routed "start free" page — auth is modal-only. The only routed human action destinations are `/research` → `/dashboard` or the auth modal.

### 1.2 The core entry-point problem — wayfinding contradicts the human-first reposition

The *copy* reframing is strong and consistent (StitchRecord, Compare, FAQ, `/research`). The *wayfinding* points the other way:

- **Every filled/primary CTA routes to `/developers`.** The single loudest control — the black primary button — on nav (`navigation.tsx:100`), mobile nav (`mobile-nav.tsx:165`), and the hero (`stitch-hero.tsx:59`) is all `Get API Key → /developers`. On a human-first reposition, the loudest button sends humans to API docs.
- **The human start is a footnote.** `stitch-hero.tsx:80-90` renders the human console link as a small underlined footnote; its own code comment calls it "Quiet human path — the secondary audience, never a splash" (`:80`). The human's real on-ramp on `/` is the product-preview sheet (`stitch-product-preview.tsx:144`) — sheet 05 of 6, **below** a full-bleed dark developer JSON wall (`stitch-developer-showcase.tsx:85`, sheet 03).
- **The clearest "what Tru8 does" moment has no CTA.** `StitchRecord` — "Not a verdict. A structured evidence record." (`stitch-record.tsx:85`) — is the strongest reframing prose on the site, and you cannot start from it.
- **The clearest "start here" moment is on a secondary route.** `/research` hero — "See the evidence for and against. Show your working." + `Start in the browser` → `/dashboard` (`research/page.tsx:104-117`, `research-start-cta.tsx:19`) — is the single best convergence of message + action on the whole site. But a visitor reaches it only via the outlined secondary nav button or the hero footnote.
- **Split-brain funnel.** `/` (dev-led, the actual front door where the logo + default traffic land) pushes the human to `/research` (2 hops to start); `/research` goes straight to `/dashboard` (1 hop). The "start" label mutates at each step: "Research App" (nav) → "Open the Research App" (footnote + preview) → "Start in the browser" (`/research`). One funnel, three names — it doesn't read as one path.

### 1.3 Duplication & dead-ends on the entry surface

- `Get API Key` appears twice above the fold on `/` (nav `:100` + hero `:59`), competing with the human's own CTA.
- **Two components tell the six-views story two ways:** `StitchProductPreview` (screenshots, on `/`) vs `StitchFeatures` (carousel, on `/research`) — maintenance + message-drift risk, and the screenshots are stale (pre-redesign results UI — the founder flagged this).
- `StitchCompareTeaser` renders on both `/` and `/research` (`page.tsx:108`, `research/page.tsx:152`).
- **Two mobile-nav implementations** across marketing: `MobileNav` on `/`, `/research`, `/pricing`; `MobileBottomNav` on `/compare`, `/about` (`compare/page.tsx:2`, `about/page.tsx:2`) — drift smell.
- Researchers get **stranded on developer pages**: neither `/developers` nor `/compare` body links back to the human console (corroborated by `docs/page-review-2026-06-29/00_SYNTHESIS.md` IA section); `/about` is a funnel dead-end.
- `/research` is diluted by imported homepage components that leak **profession names** ("Your Research Team" in `StitchFeatures`) and an **orphan "04 / COMPARE"** SheetHeader with no 01–03 (per the 06-29 review; still live).

**Entry-point verdict:** the density problem here is not word-count — it is **competing audiences and a diffuse funnel**. The human's best moment exists but is demoted below and behind the developer pitch, and the start-path is split across two routes with three different labels.

---

## PART 2 — RESULTS-PAGE FINDINGS (the duplication & density map)

### 2.1 Page structure (render order)

**Signed-in check detail** (`web/app/dashboard/check/[id]/check-detail-client.tsx:391-553`):
1. `CheckMetadataCard` (`:394`) — input type/status/content/submitted/credits
2. `ClarityResponseCard` (`:428`, only if a user question)
3. `EvidenceMetaStrip` (`:439`) — reference id, claims, sources reviewed, sources organised, time
4. `ClaimSectionStack` (`:448`) — multi-claim overview grid (one card per claim, each with a roster preview)
5. "Claim Detail" divider (`:459`)
6. **`ClaimSummaryPanel`** — the Evidence Digest (`:466`)
7. Prev/next claim nav (`:474`)
8. `ViewSelector` — segmented switcher (`:498`)
9. `ViewGuide` — dismissible per-tab paragraph (`:504`)
10. Active view body — one of six (`:506-546`)
11. `ShareSection` (`:550`) + `NavigationSection` (`:551`)

**Public report** (`web/app/r/[id]/public-report-client.tsx:234-492`) — same evidence stack (items 3–10 identical, shared components), differs only in chrome: a header + separate "Analysed" input block instead of `CheckMetadataCard`; adds Download-PDF, verify-integrity link, disclaimer, marketing CTA; views are `readOnly` (no top-up / re-search).

### 2.2 The digest is a near-complete report on its own

`ClaimSummaryPanel.tsx:164-367` (read first-hand) renders, in one framed card: identity row + type badge (`:171-182`) → claim restated (`:186`) → lean line (`:192`) → confidence/coverage line (`:201`) → **F6 topical-relevance count** (`:204`) → **"Elements examined" roster** with prose + `ElementList` (states, source counts, echo/thin notes, top-up buttons) (`:213-236`) → gaps link (`:237`) → **stance distribution bar** (click-to-filter) (`:251-298`) → **Key findings** (top-3 sources, favicon + domain + link) (`:301-332`) → **strongest support/challenge cards** (`:337-342`) → **tier-mix footer** (primary/reporting/commentary, → Evidence) (`:346-366`).

It is simultaneously a summary, a navigator, and a near-complete report — it already answers most of what the six tabs beneath it re-answer. This is the **single hottest density point on the page.**

### 2.3 The redundancy matrix — one evidence set, five renderings

**PROVEN (verified first-hand):** Evidence, Sources, and Map each independently re-pool `claim.evidence` with their own dedup `Set` and rebuild the identical element↔evidence map — `LibrarianView.tsx:57-63`, `CorrespondentView.tsx:68-75`, `CartographerView.tsx:54-63`. They differ **only in the grouping axis**: Evidence = tier×type heatmap + tier-sorted ledger; Sources = grouped by domain; Map = spatial node graph by tier. Timeline (`ChronologistView.tsx:115`) is a fourth rendering keyed on date. The digest is a fifth, compressed rendering. **Five surfaces over one evidence array; four are full re-renders.**

Columns: Dig = digest · Ovw = overview grid · Evd = Evidence · Src = Sources · Map = Map · Tml = Timeline · Gap = Gaps · Vid = Video · PDF = exported record.

| Information fact | Dig | Ovw | Evd | Src | Map | Tml | Gap | Vid | PDF |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Claim / normalised claim | ✔ | ✔ | | | | | | | ✔ |
| Orientation / lean line | ✔ | ✔ | | | | | | ✔ | ✔ |
| Stance tally (supports/context/challenges) | ✔ (bar) | | ✔ (disposition) | | ✔ (edges) | | | | ✔ (bar) |
| Confidence / coverage line | ✔ | | | | | | ✔ (cov%) | | |
| F6 topical-relevance count | ✔ | | | | | | | | ✔? |
| Element description | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | | ✔ |
| Element state | ✔ | ✔ | | | ✔ | | ✔ | | ✔ |
| Per-element source count | ✔ | ✔ | | | | | ✔ | | |
| Echo/thin/repetition note | ✔ | | | | | | | | ✔ |
| Gaps / "not yet found" | ✔ | ✔ | | ✔ | ✔ | ✔ | ✔ | | |
| Tier counts (primary/reporting/commentary) | ✔ | ✔ | ✔ | ✔ (as domains) | ✔ | ✔ | | | ✔ |
| Evidence item title | ✔ | | ✔ | ✔ | ✔ | ✔ | ✔ | | ✔ |
| Source favicon | ✔ | | ✔ | ✔ | ✔ | ✔ | | | |
| Source domain | ✔ | | ✔ | ✔ (axis) | ✔ | ✔ | | | ✔ |
| Type badge | | | ✔ | ✔ | | | | | ✔ |
| Publish date | | | ✔ | ✔ (range) | ✔ | ✔ (axis) | | | ✔ |
| Total-sources count | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | | ✔ | ✔ |

The **primary/reporting/commentary tier triple appears six times** (digest footer, overview strip, Map's `LandscapeSummaryStrip`, Sources' `CorrespondentSummary` as domains, Evidence heatmap+dividers, Timeline bands). A reader who scrolls every view meets the same fact six times in six units.

### 2.4 Density hotspots & the scaffolding/signal split

- **Hotspot 1 — the digest** (§2.2): already near-complete; the tabs beneath largely re-answer it.
- **Hotspot 2 — stacked summary strips:** every view leads with its own bordered stat strip restating the same counts in a new unit — `LandscapeSummaryStrip`, `CorrespondentSummary`, `TemporalInsightStrip`, `UnknownsSummaryStrip`, plus page-level `EvidenceMetaStrip`.

**Scaffolding / noise (candidates to cut or demote):**
- `CheckMetadataCard` (dashboard `:394`) duplicates input/status already implied by the Meta Strip.
- `ViewGuide` per-tab paragraphs — useful once, noise thereafter (already dismissible).
- The repeated tier-count strips.
- The overview `ClaimSectionCard` roster is a near-exact preview of the digest roster shown again on focus.
- The four-way re-grouping of one evidence set — four full renders whose only differentiator is the sort/layout axis.

**The single "really interesting" signal to ELEVATE:** the pipeline's distinctive output is the **element-level structure** — the claim decomposed into numbered checkable elements, each with a state, a source count, and (unique to Tru8) the **echo/thin/repetition sourcing-integrity note** (`EvidenceQualityNote`), plus the **gaps / known-unknowns** (Seeker). That roster + integrity + gaps is the "we organise, you decide" edge no competitor has. Today it is buried mid-digest (`ClaimSummaryPanel.tsx:213-248`) and only partially surfaced in Gaps. Four redundant evidence re-renders and six repeated tier strips pull attention toward the commodity "N sources by tier" view and away from it.

---

## PART 3 — VERDICT: are we platforming too much?

**Yes — on both surfaces, but for different reasons.**

- **Entry point:** the problem is not volume, it is **competing audiences and a diffuse funnel**. The human's best moment (message + action) exists but sits below and behind the developer pitch, split across two routes with three labels.
- **Results page:** the problem *is* volume-as-duplication. One evidence set is rendered five times; one tier triple six times; the digest already is the report. Six top-level tabs is at or past comfortable info-scent — a conclusion the team already logged (`audit/OPEN_WORK.md:43`: "consolidate Evidence/Sources/Map — three renderings of ONE set — under one home; keep Timeline/Gaps/Video distinct; six top-level tabs is at the edge of comfortable info-scent"). This review verifies and quantifies that hypothesis: it is correct.

### Cut / Consolidate / Elevate

**CUT**
- C1. `CheckMetadataCard` on the dashboard results view — fold its essentials into the Meta Strip (scaffolding duplication).
- C2. The redundant per-view summary strips — keep ONE canonical count surface (the digest/meta strip); drop or slim `LandscapeSummaryStrip`, `CorrespondentSummary`, the standalone strip in each view where it merely restates tiers.
- C3. Overview `ClaimSectionCard` roster preview when it merely pre-renders the digest roster (single-claim checks especially).

**CONSOLIDATE**
- **K1 (the big lever).** Fold **Evidence + Sources + Map** into ONE "Evidence" home with a **grouping toggle** (by tier×type / by source / by map) instead of three top-level tabs. Same data, same interactivity (`02_INTERACTIVITY_MAP.md` don't-drop list must be honoured), one home. This takes the tab bar from six to **four**: Evidence · Timeline · Gaps · Video. Directly executes the logged `OPEN_WORK.md:43` hypothesis.
- K2. De-duplicate the digest vs the views: decide the digest is the **answer** and the views are the **depth** — remove from the digest whatever is pure preview of a view (candidate: the strongest support/challenge cards or the Key findings list, since both live in Evidence), OR keep the digest complete and make the views leaner. (Decision D-RESULTS-2.)
- K3. Unify the two entry-point six-views components (`StitchProductPreview` / `StitchFeatures`) into one, with refreshed screenshots.

**ELEVATE**
- E1. Make the **element roster + sourcing-integrity note + gaps** the spine of the results page — the first and largest thing after the claim/lean, not a mid-digest block.
- E2. On the entry point, elevate the human start: give `/research`'s "Start in the browser" moment a real button on `/` (ghost/secondary at minimum — a founder call, see D-ENTRY-1), and give `StitchRecord` ("Not a verdict. A structured evidence record.") a start CTA.

**KEEP (locks / edges — do not touch):** the six lenses' interactivity and all URL-param state (`02_INTERACTIVITY_MAP.md`); no-verdict wording + colour; action-names-not-professions; classify-don't-score; the public human-readable report itself (the edge).

---

## PART 4 — FOUNDER DECISIONS

Nothing gets built until these are answered. Recommended option is listed first.

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| **D-ENTRY-1** | Human vs API CTA prominence on `/` | (a) Human start = filled primary, `Get API Key` = secondary; (b) both equal weight; (c) keep dev-led (status quo) | (a) — the reposition is human-first; the loudest button should start a human. Keep a clear API path, just not the primary. |
| **D-ENTRY-2** | One front door or two | (a) Keep `/` dev-led + `/research` human-led, but make the human path on `/` unmissable + unify the funnel label; (b) merge into one adaptive front door; (c) make `/research` the canonical `/` | (a) — two-variant is intentional; fix the funnel, don't rebuild it. Pick ONE start-label everywhere ("Open the Research App"). |
| **D-ENTRY-3** | Six-views marketing components | (a) Unify `StitchProductPreview` + `StitchFeatures` into one, refreshed screenshots; (b) keep both | (a) — kills drift + fixes stale screenshots (the one uncontested deliverable). |
| **D-RESULTS-1** | **Consolidate Evidence/Sources/Map → one "Evidence" home w/ grouping toggle (6 tabs → 4)** | (a) Yes, consolidate (execute `OPEN_WORK.md:43`); (b) keep six tabs; (c) consolidate a different subset | (a) — highest-value density lever; already logged; interactivity preserved via toggle. |
| **D-RESULTS-2** | Digest vs views division of labour | (a) Digest = answer, views = depth: trim overlap from the views' summary strips; (b) trim the digest instead; (c) leave both | (a) — the digest is the fast first-glance (the whole point of the redesign); slim the views' repeated strips, not the digest. |
| **D-RESULTS-3** | Cut scaffolding (CheckMetadataCard, repeated strips, ViewGuide default-on) | (a) Cut/fold per C1–C3; (b) keep | (a) — pure subtraction, low risk, no data lost. |
| **D-RESULTS-4** | Elevate element roster + integrity + gaps as the spine | (a) Yes — promote above the evidence re-renders; (b) leave mid-digest | (a) — this is the differentiator; make it the headline, not a sub-block. |
| **D-SCOPE** | Sequence | (a) Entry point first (unblocks screenshots + is lower-risk), then results consolidation; (b) results first; (c) parallel | (a) — front door is lower-risk and the screenshot refresh gates on nothing; do the consolidation as its own phased slice after. |

### Notes on risk
- D-RESULTS-1 is the largest change and touches the `02_INTERACTIVITY_MAP.md` don't-drop inventory — every `?view/?claim/?rel/?element` param, every analytics event, every in-lens control must survive the toggle. It should be its own phased-build slice with an explicit parity checklist.
- All entry-point items are copy/layout/routing — low blast radius, verifiable with `tsc --noEmit` + the browser (avoid `next build`/`start` churn against the founder's dev server; see the next-cache-churn rule).

---

## Appendix — stale prior-doc claims corrected here
- Summary-altitude green/amber counts: **neutralised** everywhere 2026-06-30 (`ccccd74`) — the 06-29 P1 "desaturate ClaimSummaryPanel" is done.
- `results-ux-review-2026-06-30` framing the digest/switcher as "to be built": **shipped** 2026-06-30.
- #14 corroboration + fact-check "remaining": **shipped**; evidence-quality notes now include echo + thin + repetition (F4, 2026-07-07).
- Page-review console-preview screenshots: pre-redesign UI — **stale** (D-ENTRY-3 fixes this).
- Task-brief profession↔action mapping was inverted vs live code: EVIDENCE tab renders `librarian`, SOURCES renders `correspondent` (`ViewSelector.tsx:40-47`, `check-detail-client.tsx:513/521`). Live labels used throughout.
