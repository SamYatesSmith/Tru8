# F8 — Implementation Design Review & Phased Plan

**Date:** 2026-07-08
**Status:** PLAN — awaiting founder sign-off per phase. **No code until Phase 0 (preview env) + the phase's design are approved.**
**Companion to:** `audit/2026-07-08_f8_frontend_density_review.md` (the findings + decisions this plan executes).
**Method:** phased-build-loop — each phase runs design → your approval → build → INDEPENDENT adversarial verify (evidence) → your sign-off, reviewed in the preview environment (Phase 0) BEFORE it lands on `main`.

This document is the **design review of the approach and the implementation**, broken into manageable sections. It leads with the **main change** (the results-page consolidation), because that is the deepest lever and the one that most needs a careful, staged build. Entry-point work follows as lower-risk, independently-sequenceable phases.

---

## Phase 0 — Preview environment (build this FIRST; it enables every review below)

### The problem
`web/railway.toml` + `backend/railway.toml` both deploy via Dockerfile, and Railway auto-deploys `main`. Combined with the trunk-based-on-`main` workflow ([[feedback_git_workflow]]), **every commit lands in production instantly** — there is no place to eyeball a change first. F8 is visual and iterative; it needs a look-before-land step.

### Chosen approach — DECIDED 2026-07-08: LOCAL prod-build review on an F8 feature branch
Founder chose **local prod-build only** (no hosted Railway/staging preview). F8 deviates from trunk-based-on-`main` for its duration so nothing lands in prod until signed off. Workflow:

1. **All F8 work lives on branch `f8-frontend`** — never committed to `main` until a phase is signed off. `main` stays deployable/untouched.
2. **Per phase (me):** build the phase on the branch; verify locally with `tsc --noEmit` + vitest; run a **local production build for visual review**.
3. **Founder reviews the change locally BEFORE it lands** — either by running the `f8-frontend` branch in their own dev server, or via screenshots I capture from the local prod build.
4. **Sign-off → I merge the phase to `main` → Railway auto-deploys.** The local review is the gate.

**Protecting the founder's dev cache ([[feedback_next_cache_churn]]) — hard rule for every phase:**
- I will **not** run `next build`/`next start` against the shared working tree while `npm run dev` may be open. Local prod builds go to a **separate build dir** (`next build`/`start` with an isolated `distDir`/`.next`), or in a throwaway copy, so the founder's dev `.next` is never corrupted.
- For my own fast checks and the independent verifier: prefer `tsc --noEmit` + vitest; only do a full prod build in the isolated dir when a visual capture is needed.

**Branch handling note (single shared working directory):** checking out `f8-frontend` in the working dir switches the founder's tree to the branch (their dev server would then show F8 WIP — which is the review surface). If they want to keep `main` running undisturbed while I work, the alternative is a **git worktree** for `f8-frontend` in a separate folder — decide per preference (see D-ENV-2 below).

### What I need from you on Phase 0
- **D-ENV-2:** review mechanics — (a) I capture screenshots from the local prod build for you to review, or (b) you run the `f8-frontend` branch yourself to click through it, or (c) both. And: work in-place on the branch (dev shows WIP) vs a separate git worktree (keeps your `main` dev clean).

---

# THE MAIN CHANGE — Results-page consolidation (3 phases)

The results page renders **one evidence set five times** and the tier triple six times (proven in the findings doc). The main change collapses that. It is split into three phases so nothing big lands unverified: a safe warm-up (M1), the structural consolidation (M2), then the hierarchy/elevation pass (M3).

## Phase M1 — Cut the safe scaffolding (decision D-RESULTS-3)

**Goal:** pure subtraction, no architecture change — proves the preview→review→land loop on low-risk work and removes the most obvious duplication first.

### Approach
Remove/fold results-page chrome that duplicates the meta strip, and stop showing per-tab guidance by default. Nothing that carries evidence data is touched.

### Implementation
- **`CheckMetadataCard`** (dashboard `check-detail-client.tsx:394`): fold its two genuinely-unique fields (input content/URL, credits used) into `EvidenceMetaStrip`; remove the standalone card. The public report already shows input as an "Analysed" block, so this brings the two surfaces closer. Files: `check-detail-client.tsx`, `EvidenceMetaStrip.tsx`, `CheckMetadataCard.tsx` (delete or retire).
- **`ViewGuide`** (`:504`): render collapsed by default (already dismissible) so the per-tab paragraph is opt-in, not a wall on every view. File: `ViewGuide.tsx`.
- **NOT in M1:** the redundant per-view summary strips (`LandscapeSummaryStrip`, `CorrespondentSummary`) — deferred to M3, because after M2 they live inside one home and the de-dup is cleaner to reason about there.

### Verification
`tsc --noEmit`; vitest for any touched component; preview eyeball dashboard + `/r/` — meta info still present, no data lost, page shorter.

### Risk / rollback
Low. Single-commit revert. Only risk = losing an input field in the fold — the verifier checks the input URL/content is still visible on both surfaces.

---

## Phase M2 — Consolidate Evidence + Sources + Map into one "Evidence" home (decision D-RESULTS-1) — **the core change**

**Goal:** take the top-level switcher from **6 tabs → 4** (Evidence · Timeline · Gaps · Video) by folding Sources and Map into Evidence as a **grouping sub-toggle**, with **zero loss** of interactivity or deep-links.

### Approach (design rationale)
Evidence (Librarian), Sources (Correspondent), and Map (Cartographer) each independently re-pool `claim.evidence` and differ **only in grouping axis** (by tier×type / by source / by spatial map) — verified: `LibrarianView.tsx:57`, `CorrespondentView.tsx:68`, `CartographerView.tsx:54`. So they are not three views; they are **one view, three groupings**. The right primitive is a single "Evidence" home with a *grouping* control, not three peer tabs. This executes the long-standing `audit/OPEN_WORK.md:43` follow-up. Timeline / Gaps / Video stay distinct top-level tabs because each answers a genuinely different question (when / what's missing / on camera) over different-shaped data.

**Hierarchy of controls (the key UX decision):**
- **Top switcher (primary)** = the *question* you're asking: Evidence · Timeline · Gaps · Video. Stays the filled segmented control.
- **Sub-toggle (secondary, inside Evidence only)** = *how to arrange* the same evidence: `By type` · `By source` · `Map`. Visually lighter than the top switcher (a labelled pill row, "Arrange:") so it never competes with it — reduces simultaneous density instead of adding a second equal control.

### Implementation
**New component — `EvidenceHome.tsx`** (in `web/components/evidence-views/`):
- Owns grouping state `group ∈ {type, sources, map}` (default `type`).
- Renders the sub-toggle + dispatches to the **existing, unchanged** bodies:
  - `type` → `LibrarianView` (passes `initialRelationships`, `focusElementId`)
  - `sources` → `CorrespondentView`
  - `map` → `CartographerView` (passes `onSwitchToType`)
- Bodies are **not modified** in M2 (their internal controls, per `02_INTERACTIVITY_MAP.md`, ride along untouched). This is the safety property: consolidation is a *re-parenting*, not a rewrite.

**Switcher — `ViewSelector.tsx`:**
- `ALL_TABS` reduced to 4: `EVIDENCE` (value `librarian`, kept for deep-link stability) · `TIMELINE` (chronologist) · `GAPS` (seeker) · `VIDEO` (projectionist). Update `LG_GRID_COLS` usage (already dynamic). Keep the "start" cue on Evidence.

**Dispatch — `check-detail-client.tsx` (`:506-546`) and `public-report-client.tsx` (mirror):**
- Replace the three separate `claimView === 'librarian'|'correspondent'|'cartographer'` blocks with a single `claimView === 'librarian' && <EvidenceHome …/>`.
- Keep `chronologist`, `seeker`, `projectionist` blocks as-is.

**URL-state backward-compatibility (MUST NOT break existing links):**
- Add `?group=type|sources|map` (omitted when `type`). New handler `handleGroupChange` syncs it (mirrors `handleClaimTabChange`).
- **Legacy translation** in the initial-state readers (`check-detail-client.tsx:65-73`, `public-report-client.tsx:31`): `?view=correspondent` → `{view: librarian, group: sources}`; `?view=cartographer` → `{view: librarian, group: map}`. So every old shared/bookmarked link still resolves. Add these two to the `validViews` normalisation, not the tab list.

**Digest deep-links (`ClaimSummaryPanel.tsx` + `handleNavigateFromSummary`):**
- Extend `handleNavigateFromSummary(view, {rel, element, group?})` to carry an optional `group`.
- Remap the digest's existing calls: footer "Map" (`:348`) → `{view: librarian, group: map}`; footer "Sources" (`:352`) → `{view: librarian, group: sources}`; stance-band + strongest-source → `{view: librarian, group: type, rel:[…]}` (unchanged target, now explicit group). The `go('seeker')` gaps link is untouched.

**`onSwitchToLibrarian`** (Cartographer/Chronologist → Evidence) becomes "switch to Evidence, group=type"; rename to `onSwitchToEvidence` for clarity (internal only).

**Analytics:** keep `view_opened` on the 4 tabs; add `group_changed {group}` inside EvidenceHome so we can see whether Sources/Map groupings get used (informs any future cut). Preserve every event in `02_INTERACTIVITY_MAP.md:16`.

### Interactivity parity guard (the verifier's checklist for M2)
Every item below must still work after M2 — this is the `02_INTERACTIVITY_MAP.md` don't-drop contract made concrete:
- [ ] `?view=librarian|correspondent|cartographer` all resolve (last two via legacy→group translation) + `?group=` round-trips.
- [ ] `?rel=` / `?element=` still filter Evidence (type grouping) from a digest click.
- [ ] Librarian internals: heatmap dual-filter, FilterPills, SortControl, ReadingTable, RetrievalFunnel receipts, diagnostic toggle, element-focus badge.
- [ ] Correspondent internals: domain expand/collapse, SourceGaps callouts.
- [ ] Cartographer internals: D3 force map hover/select, ResizeObserver, mobile ElementRoster, onSwitch trigger.
- [ ] All analytics events still fire; new `group_changed` fires.
- [ ] Mobile: sub-toggle is usable and visually subordinate to the top switcher.
- [ ] Public report `/r/[id]` has identical behaviour (read-only).

### Verification
`tsc --noEmit`; vitest on ViewSelector + EvidenceHome + the URL translation; preview environment walk-through of the full parity checklist on desktop + mobile, dashboard + `/r/`, with a legacy `?view=cartographer` link tested explicitly. Independent verifier reports evidence against each checkbox.

### Risk / rollback
Medium — highest-blast-radius phase. Mitigations: bodies untouched (re-parent only); legacy URL translation keeps links alive; whole phase is one PR reviewed in preview before land; single-commit revert restores the 6-tab switcher.

---

## Phase M3 — Elevate the spine + resolve digest-vs-views overlap (decisions E1, D-RESULTS-2)

**Goal:** make the genuinely-distinctive signal — the **element structure + sourcing-integrity notes + gaps** — the headline, and remove the now-triplicate summary strips.

### Approach
After M2, the three groupings share one home, so three tier-count summary strips is indefensible. Keep **one** canonical count surface; make the element roster the spine; decide the digest/view division of labour so the same fact isn't stated at both altitudes.

### Implementation
- **De-dup summary strips:** with `type/sources/map` under one home, show the source-mix count **once** (in the digest footer, already present at `ClaimSummaryPanel.tsx:346`). Slim `LandscapeSummaryStrip` (Map) and `CorrespondentSummary` (Sources) to only their grouping-specific value (e.g. Sources keeps domain-diversity/sole-source flags; Map keeps nothing that the digest already says). Files: `LandscapeSummaryStrip.tsx`, `CorrespondentSummary.tsx`.
- **Elevate the spine (E1):** the "Elements examined" roster + `EvidenceQualityNote` (echo/thin/repetition) + gaps link already sit high in the digest (`ClaimSummaryPanel.tsx:213-248`), but sit *below* the lean and *above* the stance bar. Promote the integrity/gaps signal's prominence (heading weight + spacing) so it reads as the headline of "what we found," not a mid-card block. Presentation-only; no data change.
- **Digest vs views (D-RESULTS-2):** recommended resolution = digest is the *answer*, views are the *depth*. Concretely: keep the digest complete (it's the 1-second read), and rely on M3's strip-slimming to remove the *views'* repetition rather than the digest's. (If you prefer to trim the digest instead, that's the D-RESULTS-2 alternative — a founder call.)

### Verification
`tsc --noEmit`; vitest; preview eyeball — the tier triple now appears at most twice (digest + one heatmap), the element/integrity/gaps signal reads first, no count contradicts another.

### Risk / rollback
Low–medium (presentation reordering + strip edits). Single-commit revert.

---

# ENTRY POINT — 2 phases (lower risk; sequence after the main change, or interleave)

These execute D-ENTRY-1/2/3. They're independent of the results phases and could run in parallel, but per your "main changes first" steer they're planned second.

## Phase E1 — Human-first wayfinding on `/` (decisions D-ENTRY-1, D-ENTRY-2)
**Approach:** make the loudest control start a human; keep a clear (secondary) API path; unify the funnel to one label.
**Implementation:**
- Hero (`stitch-hero.tsx:59`): human "Start in the browser / Open the Research App" becomes the **filled primary**; `Get API Key` becomes secondary. Promote the human path out of the "never a splash" footnote (`:80-90`).
- Nav (`navigation.tsx:84-107`) + mobile (`mobile-nav.tsx:155-174`): filled primary → human start; `Get API Key` → outlined secondary.
- Give `StitchRecord` ("Not a verdict. A structured evidence record.", `stitch-record.tsx:85`) a start CTA — the clearest "what Tru8 does" moment currently has none.
- Pick **one** start-label everywhere ("Open the Research App") and one destination, so the funnel doesn't rename itself at each hop.
- Keep the two-variant front door (`/` + `/research`) — intentional, founder-owned; this phase does **not** merge them.
**Verification:** `tsc --noEmit`; preview — the primary CTA starts a human on `/`, nav/hero consistent, API path still one click away. `verify-ui` skill on the marketing surface.
**Risk:** low (copy/CTA/link). Any wholesale merge of `/` and `/research` is explicitly out of scope (D-ENTRY-2 = keep both).

## Phase E2 — Unify the six-views marketing components + refresh screenshots (decision D-ENTRY-3)
**Approach:** kill the drift between `StitchProductPreview` (screenshots, `/`) and `StitchFeatures` (carousel, `/research`) telling the same story two ways; refresh the stale captures against the shipped results UX.
**Implementation:** consolidate to one component reused on both pages; capture new screenshots of the post-M2 results page (so the marketing matches what ships). **Screenshot refresh depends on M2/M3 being live** — so E2 comes after the main change by construction.
**Verification:** preview — one component, current screenshots, no profession-name leak ("Your Research Team"), the orphan "04 / COMPARE" header resolved.
**Risk:** low.

---

## Sequencing summary

| Order | Phase | What | Depends on | Risk |
|-------|-------|------|-----------|------|
| 0 | **Phase 0** | Preview environment — LOCAL prod-build review on `f8-frontend` branch (DECIDED) | — | — |
| 1 | **M1** | Cut safe scaffolding (CheckMetadataCard, ViewGuide default) | Phase 0 | Low |
| 2 | **M2** | Consolidate Evidence+Sources+Map → one home, 6→4 tabs | M1 | **Medium** |
| 3 | **M3** | Elevate element/integrity/gaps spine; de-dup strips | M2 | Low–Med |
| 4 | **E1** | Human-first CTAs + one funnel label on `/` | Phase 0 | Low |
| 5 | **E2** | Unify six-views components + refresh screenshots | M2/M3 live | Low |

Recommended: **0 → M1 → M2 → M3 → E1 → E2.** (E1 could jump ahead of the M-phases if you want a quick visible win first — it's independent.)

---

## Decisions needed before I build anything

| # | Decision | Status |
|---|----------|--------|
| **D-ENV** | Preview env | ✅ DECIDED — **local prod-build review** on `f8-frontend` branch |
| **D-ENV-2** | Local review mechanics (screenshots vs founder runs branch; in-place vs worktree) | OPEN — asked |
| **D-SEQ** | Order 0 → M1 → M2 → M3 → E1 → E2, main-change-first | ✅ DECIDED — main change first |
| **D-RESULTS-1 shape** | Fold Sources+Map into Evidence w/ subordinate "Arrange: type/source/map" toggle, 6→4 tabs | ✅ DECIDED — as specified |
| **D-RESULTS-2** | Digest vs views: trim the *views* (keep digest complete) | Recommended; confirm at M3 |
| **D-ENTRY confirm** | D-ENTRY-1 (human = primary CTA), D-ENTRY-2 (keep two front doors) | Recommended; confirm at E1 |

I'll build strictly one phase at a time, each reviewed in the preview environment before it merges to `main`.

---

## Session log & pickup point

### 2026-07-09 — PLAN RESHAPED BY FOUNDER: restructure OUT, clarity pass IN ⚠️ (supersedes the phase sequence above)

Founder reviewed the plan in full and redirected. **The M2/M3 consolidation and the Phase 0 preview apparatus are PARKED** — "possibly it goes a bit too far … I did not think we needed a complete restructure, just clarity, DRY attention, clarifying where attention needs to be led, and adding any nice, clever little design improvements." Phase 0 was overkill: the founder only wanted **a basic HTML mockup to react to** before build. Tab consolidation may return later as its own bigger, riskier slice.

**New shape — 4 clarity slices (all founder-stated concerns):**

| # | Slice | Founder's framing | Gate |
|---|-------|-------------------|------|
| **C1** | **Entry-point clarity** | Entry routes awkward; "research app" platformed but it isn't an app; UI still developer-focused; duplicated home pages compete for airtime and confuse. Need: one landing page that succinctly + attractively answers *what Tru8 is / why it exists / what it offers* (what a professional designer/PM and a customer expect to find) + a dedicated, quality `/developers` page platforming the dev product. | HTML mockups → founder reaction → build. |
| **C2** | **Results summary-card review** | The summary content box is busy; several statements say the same thing; section titles easily missed so users hunt. Every element evaluated: says what it should, has a purpose, doesn't just create noise. Adheres to brand/ethos. | Keep/cut/merge/reword table + mockup → sign-off → build. |
| **C3** | **`/compare` correction** | Competitors listed are not our direct competitors. Ground on the recent audit — **founder-confirmed doc: `audit/2026-06-24_pricing_research_plan.md`** (most recent; verified: webcite.co, ~$20/mo cluster, per-call anchors); the 2026-06-15 doc is framing only. No unverified public quality claims (standing gate) — compare shape/features/price. | Content draft → sign-off. |
| **C4** | **Screenshot refresh** | New screenshots after the design changes are complete. Explicitly LAST. | After C1–C2 land. |

**Process:** mockup-first, then small slices on `main` (trunk-based restored). Worktree apparatus dropped for new work.
**Parked (founder, 2026-07-09):** logo polish — the Tru8 mark is "a little rough around the edges, pixelly, not quite perfectly shaped"; a later-date item, NOT part of C1–C4.
**C1 mockup iteration (same day):** Mockup A confirmed as the direction. N4 reworked twice on founder feedback — final shape: section re-titled "Inside a check"; headline **"The summary, then the lenses."** (founder-chosen); the results-summary panel LEADS (labelled THE SUMMARY, unnumbered so it never reads as a seventh view), then LENS 01–04 (Evidence/Map/Gaps/Timeline) in the live section's large alternating clickable-lightbox layout, Sources+Video named in a quiet strip. **MOCKUP SIGNED OFF at rev 4 (2026-07-09).** Artifact: claude.ai/code/artifact/a6a4ea98-595b-467b-b996-83237660445f.

---

## C1 BUILD DESIGN (2026-07-09) — mockup → codebase, three slices

Executes the signed-off rev-4 mockup. Each slice = one commit on `main`, founder-eyeballed on the dev server before the next starts. Verification per slice: `tsc --noEmit` + vitest on touched components + browser walk; independent adversarial verify on S1 (the big one).

### Slice S1 — the landing page (all of Mockup A)

**`web/app/page.tsx`** — new section order: Hero → 00 Why → 01 Record → 02 Inside-a-check → 03 Process → 04 Edges → 05 Developers band → 06 FAQ → Closing CTA. Chrome (accent top rule, spine, frame) unchanged; spine REV bumps to 2026.07.

| File | Change |
|------|--------|
| `stitch-hero.tsx` | Headline → "See the evidence for and against. **Show your working.**" (promoted from `/research`); sub per mockup; CTAs → primary **"Start a check"** (→ `/dashboard`, auth modal intercepts signed-out) + secondary **"See a sample record"**; the "Open the Research App" footnote (`:80-91`) REMOVED; Record fragment panel kept (copy refresh per mockup). |
| `stitch-problem.tsx` + `stitch-compare-teaser.tsx` | MERGED into new **`stitch-why.tsx`** (`00 / WHY TRU8 EXISTS`): "Most tools hand you a conclusion." + the dotted-leader ledger + "See the full comparison →" `/compare` link. Both old components retired (compare-teaser's only other consumer is `/research`, which dies in S2). |
| `stitch-record.tsx` | Kept as `01 / THE RECORD`, moves onto the raised band; artifact simplified to the mockup's single 6-item grid (01 Element decomposition … 06 Signed manifest — replaces the 5-differentiator + 4-register split); gains the quiet **"Start a check and see yours →"** CTA (the finding: strongest moment had no CTA). |
| `stitch-product-preview.tsx` | Reworked to `02 / INSIDE A CHECK` — headline "The summary, **then the lenses.**"; NEW leading panel `THE SUMMARY` (unnumbered) + `LENS 01–04 / 04` (Evidence/Map/Gaps/Timeline); existing lightbox mechanics + `NN` pagination kept; hover accent border + "VIEW FULL SIZE ⤢" chip; lens strip names Sources + Video. Interim screenshots: existing 4 + a fresh capture of the current summary card; ALL refreshed in C4 (post-C2). |
| `stitch-process.tsx` | Kept as `03 / HOW IT WORKS` (copy nudge: step 01 mentions claim selection). |
| NEW `stitch-edges.tsx` | `04 / EDGES` — ports the LIMITS content from `research/page.tsx:71-88` (Not a verdict / Bounded by public / Best on focused claims / Snapshot in time). |
| `stitch-developer-showcase.tsx` | Condensed to the mockup's dark band: headline "The same record, **structured for agents.**", 4 mono chips (claimMap / _manifest / MCP / webhooks), one CTA "Read the docs" → `/developers`, mono price microline "From £0.02 per call · async · batch". Code disclosures + `/compare` link REMOVED from `/` (they live on `/developers` + `/compare`). |
| `stitch-faq.tsx` | 7 → 5 (the 2 API-oriented Q&As move to `DEV_FAQS` in `developers/page.tsx`); FAQPage JSON-LD updated to match. |
| `navigation.tsx` + `mobile-nav.tsx` | Signed-out CTAs → Sign in (modal) + **"Start a check"** filled-primary (→ `/dashboard`); "Research App" + nav "Get API Key" REMOVED (Developers nav link is the dev path). Signed-in unchanged (Dashboard primary). |
| Closing CTA | New small section in `page.tsx`: "See the record for **your claim.**" + Start a check + "or see a sample record first". |
| Analytics | New `start_check_click {surface: nav|hero|record|closing}` (replaces `research_start_click` semantics); `get_api_key_click` unchanged on `/developers`; `view_sample_click` on the sample CTA. |

### Slice S2 — retire `/research`
Permanent redirect `/research` → `/` (`next.config.js` 301 — keeps old links/SEO juice); delete `research/page.tsx` + `research-start-cta.tsx` + `stitch-features.tsx` (the carousel — its story now lives in Inside-a-check); remove `/research` from sitemap; verify no remaining internal links (grep). `StitchCompareTeaser`/`StitchProblem` files deleted here too once nothing imports them.

### Slice S3 — `/developers` top re-platform (Mockup B)
`developers/page.tsx`: hero gains microline ("From £0.02 per call · no subscription required · signed manifests") + secondary "See the response shape" (anchor → existing §12); §02 Quick Start tightened to 3 steps; **§03 Pipeline + §05 Pricing merged** into one "Tiers & pricing — Four depths. One record shape." table (tier / what-runs / per-call GBP); §04 MCP kept; a mono "Full reference below" TOC strip marks the seam; **§06–14 untouched**. Adds the 2 FAQ transplants from S1.

### Build-time decisions (asked 2026-07-09)
- **BD-1 "See a sample record" destination:** (a) public demo `/r/` report in a new tab (real product = strongest proof; demo candidates exist — `scripts/demo_candidates.py`) vs (b) scroll anchor to Inside-a-check. RECOMMEND (a).
- **BD-2 slicing confirm:** S1 → S2 → S3, founder eyeball between each.

### Locks honoured
UK English; no verdict colour/language anywhere new; action names not professions; GBP; PostHog events preserved or superseded 1:1; no `next build/start` against the founder's dev tree (tsc + vitest + dev-server eyeball only). The two-mobile-nav drift (`MobileNav` vs `MobileBottomNav`) stays OUT of scope (logged in the 06-29 review).
**M1 disposition (decided):** `8bb46ff` survives — pure subtraction, fits the new ethos, independently verified. Founder eyeballs the `f8-frontend` branch (`cd C:\Users\projects\Tru8-f8\web && npm run dev`), then **just M1** merges to `main`. M2/M3/E1/E2 sections above are reference material for the parked consolidation, not the active plan.

### C1 — SHIPPED 2026-07-09 (same session)
S1 `742d2ec` (landing rework) · S2 `8b243ca` (/research retired, 301) · S3 `870a224` (/developers top) · hero H1 `d20bd30` **"Evidence, not verdicts."** SUMMARY panel on `/` dormant (`SHOW_SUMMARY_PANEL=false`) until C2+capture.

### C3 — REVIVED + BUILT (2026-07-09, post-retrieval-fixes; awaiting founder eyeball)
Retrieval defects fixed (`c61d9a5`) and verified on live check 6B54C231 → founder called it and revived C3. Built as **cards-first "what comes back" comparison** (tick-matrix avoided per the scrapped-table lesson): NEW `web/app/compare/direct-alternatives.tsx` shortlist module (Webcite/scite/Factiverse cards with output-shape + scope + published price + honest "choose it when"; Tru8 dark record card as payoff; compact 5-row facts table; "as published, checked June–July 2026" footnote), grounding-API assets kept + re-seamed under `#grounding-apis` ("Module — A Different Layer", old H1 demoted to h2), page H1 "The difference is what comes back.", metadata + OG updated, /developers deep-link → `/compare#grounding-apis`. Capture pair NOT published; Webcite-rides-Google-grounding observation omitted (private capture, not vendor-published); qualified "no verdict on the claim" form throughout; vendor prices in their own currency. tsc clean + vitest 68/68. **Founder dev-server eyeball → commit → C4.**

### C3 — /compare correction: PARKED (2026-07-09, capture-tested) [SUPERSEDED by the revival entry above]
Table design scrapped by founder; capture test ran instead (same paragraph → webcite.co playground + Tru8 check TRU-C051-3024, same day). Their output: verdict `partially_false, 57` + a self-refuting correction — the structural no-claim-level-verdict argument stands. But OUR pool underperformed on the specimen (claim 02 = Reddit/TikTok; claim 01 carried WHO indicator noise) → **do not publish the pair; C3 parked.** Two pipeline defects opened (F-R1 WHO adapter noise, F-R2 historical-claim retrieval failure) → **retrieval-quality investigation, own session** — canonical doc `audit/2026-07-09_c3_capture_findings.md`. `/compare` stays as-is. Revival routes in the findings doc §6. Also conceded: marketing copy uses the qualified "no verdict on the claim" form. **C4 (screenshots + wake SHOW_SUMMARY_PANEL) remains queued.**

### C2 — summary-card review: SIGNED OFF + SHIPPED `44172b5` (2026-07-09; R7 fixed separately in `46163a2`)
Deliverable: before/after mockup (artifact 82ed596f — live Trump-claim card re-created vs proposal) + decision table R1–R6. Governing rule: **every fact gets exactly one home** (element count was said 3×, source count 3×, breadth 2 ways, top-sources in 2 sections). Proposals: R1 drop "Submitted Claim" chip on text checks; R2 merge the three grey lines into one ("19 sources · 12 bear directly"; coverage printed only when partial; "broad set" wording cut); R3 diamond+weight section titles + one-line elements explainer; R4 bar titled "Sources mapped", totals move to footer; **R5 section = "Notables" (FOUNDER-NAMED)** — directional cards carry it, unlabelled key-findings rows cut (top-3 fallback when no cards); R6 footer = the single numeric register. **R7 (lean says supports exist while bar shows zero supports — exclusion-filter divergence) is OUT OF SCOPE: founder is resolving it with a SEPARATE agent; C2 build starts only after that lands — RE-PULL AND RE-READ ClaimSummaryPanel.tsx/shared-utils before building (merge-overlap risk).** Both surfaces (dashboard + /r/) share the component; C4 photographs the result. **PAUSED awaiting founder design review of R1–R6.**

---

### 2026-07-08 (evening) — Phase 0 done, M1 built & verified, stopped for the night
**Environment (Phase 0) — DONE.** Git worktree `C:\Users\projects\Tru8-f8` on branch `f8-frontend` (based on `main` @ `5165b65`); `web/node_modules` installed → runnable with `cd C:\Users\projects\Tru8-f8\web && npm run dev` (isolated cache, does not disturb the `main` dev server). Review method = **founder runs the branch** locally.

**Phase M1 — BUILT + VERIFIED + COMMITTED (not merged, not pushed).**
- Commit `8bb46ff` on `f8-frontend`. Files: `web/components/evidence-views/EvidenceMetaStrip.tsx`, `web/components/evidence-views/ViewGuide.tsx`, `web/app/dashboard/check/[id]/check-detail-client.tsx`.
- What it does: on a COMPLETED check, retire the duplicate `CheckMetadataCard` (kept for processing/pending/failed states); fold Credits + Submitted date into `EvidenceMetaStrip`; add a slim "Analysed" input line mirroring `/r/`; make `ViewGuide` collapsed-by-default behind a toggle (both surfaces). Input Type label intentionally dropped.
- `tsc --noEmit` = clean. Independent adversarial verify = **SOUND-WITH-NITS**; the one real finding (Submitted date shown nowhere on completed dashboard) was FIXED in the amend. Second nit (Input Type) = deliberate drop.

**OPEN DECISION (first thing tomorrow):** merge M1 to `main` now, OR keep M1 on the branch and stack M2, then review M1+M2 together and merge as a pair. **Recommendation: stack M2** — M1 alone is a subtle delta; the density win is visible with the consolidation.

**NEXT — Phase M2 (the core consolidation).** Build to the M2 spec above:
1. New `web/components/evidence-views/EvidenceHome.tsx` — owns `group ∈ {type,sources,map}` + a subordinate "Arrange:" toggle; dispatches to the unchanged `LibrarianView` / `CorrespondentView` / `CartographerView` bodies.
2. `ViewSelector.tsx` — `ALL_TABS` 6 → 4 (EVIDENCE · TIMELINE · GAPS · VIDEO).
3. `check-detail-client.tsx` + `public-report-client.tsx` — replace the 3 separate view blocks with one `EvidenceHome`; add `?group=` handler; translate legacy `?view=correspondent|cartographer` → `{view:librarian, group:sources|map}`.
4. `ClaimSummaryPanel.tsx` — remap digest footer "Map"/"Sources" go-calls to `{group:map|sources}`; extend `handleNavigateFromSummary` with optional `group`.
5. Run the **M2 interactivity parity checklist** (in the Phase M2 section) on desktop + mobile, dashboard + `/r/`, incl. a legacy `?view=cartographer` link — via an independent verifier.

Reminders: never run `next build/start` against the founder's `main` tree ([[feedback_next_cache_churn]]) — the worktree has its own cache; prefer `tsc --noEmit` + vitest; the worktree is at `C:\Users\projects\Tru8-f8`.
