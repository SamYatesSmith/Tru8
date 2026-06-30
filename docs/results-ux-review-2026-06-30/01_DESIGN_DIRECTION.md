# Signed-in results redesign — design direction (for discussion)

> 2026-06-30 · Built from the competitor results-UX review (`00_SYNTHESIS.md`) + two follow-up research threads (evidence-digest UX; multi-view wayfinding) + founder user-feedback (users want an evidence summary; users don't know what to click; profession tabs don't read as clickable).
> **Status: DISCUSSION / not approved, not built.** Next step is founder decisions → a rendered sample → phased-build-loop.

---

## The core insight

The two user complaints have **one shared solution**: an **evidence digest at the top of the result that doubles as the navigation.** Users get the quick-reference summary they asked for, and because every line of that digest links into the relevant lens, they always know where to click and where the value is. The summary *is* the map (NN/g "local navigation / summary-as-launchpad").

This is an evolution of the existing `ClaimSummaryPanel`, not a new surface — it gets richer, more visual, and becomes the primary entry into the six lenses.

---

## Part A — The Evidence Digest (the "summary users asked for")

Ordered contents for a one-screen, scannable digest (each part grounded in the research):

1. **Claim restated neutrally** — one line (BLUF: subject up front).
2. **One-line lean sentence** — evidential, attributed to the evidence: *"Of 21 sources gathered, the evidence leans toward support."* This is the BLUF + Consensus-Meter-as-a-sentence. **Subject is the evidence, never the claim.**
3. **The visual distribution bar** — supports / context / challenges as one **100%-stacked proportional bar** (Datawrapper: stacked beats diverging for shares; better on mobile). True skew preserved (no false balance). Neutral palette + icon + count; **never green/red**.
4. **Confidence-in-the-lean / coverage — shown SEPARATELY from direction.** *"Based on a moderate set · 4 of 5 elements covered."* This is the GRADE/Cochrane move: report the lean and your confidence in the lean as two different things. Stops a 3-source lean from masquerading as settled.
5. **Key findings (3–5)** — the notable facts the evidence offers, each one line, each linking to its source (Elicit cite-back).
6. **Strongest support · strongest challenge** — side by side, labelled by direction, not by right/wrong (scite split).
7. **Source-quality mix** — tier/type spread as composition (*6 primary · 9 reporting · 6 commentary*), never a single grade.
8. **Gaps** — elements with no/one-sided evidence, attributed to our collection: *"No source we found addresses [element]."* (Seeker / Ground News blindspot.)
9. **Expand to detail** — the digest's links + the lens switcher drop into the full views beneath.

### Sketch
```
┌─ EVIDENCE DIGEST ───────────────────────────────── TRU-XXXX ─┐
│ [Claim restated neutrally, one line]                          │
│                                                               │
│ Of 21 sources gathered, the evidence leans toward support.    │  BLUF · evidential
│ Based on a moderate set · 4 of 5 elements covered.            │  confidence (separate)
│                                                               │
│ ┌────────────────────────────┬────────┬───────────────┐      │
│ │ ⊕ Supports 12              │ ◦ Ctx 4│ ⊖ Challenges 5 │  ◀── click a band → that lens
│ └────────────────────────────┴────────┴───────────────┘      │
│                                                               │
│ KEY FINDINGS                                                  │
│ • [one-line fact] → source                                    │
│ • [one-line fact] → source                                    │
│                                                               │
│ Strongest support ⊕ […] →     Strongest challenge ⊖ […] →     │
│                                                               │
│ Sources  6 primary · 9 reporting · 6 commentary               │
│ Gaps     no source addresses [element 3] →                    │
│                                                               │
│ READ IN DETAIL                                                │
│ ▣ Evidence  ·  Sources  ·  Timeline  ·  Gaps  ·  Map  ·  Video │  segmented · default Evidence
└───────────────────────────────────────────────────────────────┘
```

---

## Part B — The no-verdict wording lock (non-negotiable)

The digest gives users the "position" they want **without** ever ruling on the claim. The discipline:

**Golden rule:** the grammatical subject of any lean sentence is *the evidence / the sources / what we found* — **never the claim.** Direction is a fact *about the collection*; certainty is hedged; the claim's truth is never the predicate.

**DO:** "Of N sources, X support, Y challenge." · "The evidence collected leans toward support." · "Sources are mixed on this." · "The gathered evidence suggests / appears to / points toward…" · "No source we found addresses X." · pair lean with reach ("leans support, but on a thin set of 3").

**DON'T:** "This claim is true/false/mostly-true." · a rating badge or 0–100 score. · "proves / confirms / debunks." · "73% likely true" (a % may only describe *source distribution*, never the claim's truth). · green/red on stance. · render a lopsided split as visually even (false balance). · hide the dominant context/neutral mass.

This lock should be written into CLAUDE.md / memory alongside the existing no-verdict-colours invariant.

---

## Part C — Wayfinding fixes ("I don't know what to click")

1. **Summary-as-launchpad** (the core insight) — digest lines link into lenses; the summary carries the discovery.
2. **Default into one recommended lens** — land on **Evidence** ("Start here"), pre-selected and visibly active, not six equal options.
3. **Segmented control, not ghost tabs** — one bordered/filled connected track with a sliding active indicator. Signals "same analysis, different views" (the correct mental model for our six lenses). Single row, 1–2 word labels + icon.
4. **Fix the clickability signifiers** — active item gets ≥2 cues (fill + bold + underline); **inactive items stay visible, not greyed** (greyed reads as disabled); hover background + `cursor:pointer`; whole-tab hit area.
5. **Label lenses by the question they answer** (subtitle/tooltip) — our six professions already *are* six questions:
   - Evidence → "What does the evidence say?"
   - Sources → "Is the full set here, clearly labelled?"
   - Timeline → "When did the evidence appear?"
   - Gaps → "What don't we know yet?"
   - Map → "What's the shape of the debate?"
   - Video → "What's said on camera?"
   (NN/g flags our bare **"Video"** format-label as the weak pattern — the question fixes it.)
6. **Progressive disclosure** — collapse secondary filters/deep-links so they don't compete on first glance (the "too many buttons" overload).
7. **In-context teaching** — a one-time inline hint ("Six ways to read this — start with Evidence") + per-lens empty states; no heavy modal tour.

---

## Decisions needed before designing the build

1. **Bar treatment** — confirm the **100%-stacked proportional bar + clickable bands** (research-preferred over a tally-cells row or a position spectrum; the spectrum reads too close to a verdict).
2. **Digest replaces/absorbs `ClaimSummaryPanel`** as the top-of-result, and **the digest's links become the primary way into the lenses** — yes? (The lens switcher stays, improved, for free browsing.)
3. **Adopt direction-vs-confidence separation** (GRADE) — show "lean" and "how well-evidenced" as two distinct things — yes?
4. **Per-element strength label (#8 from the review)** — keep (as evidence-strength, carefully worded) or drop (verdict-adjacency risk)?
5. **Scope of first slice** — recommend: build the **digest + bar + improved segmented switcher** as one rendered sample first (sandbox, not wired into live), evaluate visually, then phased-build-loop into `/dashboard/check/[id]` + `/r/[id]`.

---

## Sequencing (proposed, post-decisions)
1. Rendered **sample** of the digest + bar + switcher (sandbox route) → founder visual eval.
2. Phase 1: digest + distribution bar + wording lock → live (claim altitude).
3. Phase 2: segmented switcher + default lens + question-labels + clickability fixes.
4. Phase 3: key-findings cite-back + gaps glanceable + tier-mix composition.
5. Phase 4: export (RIS/BibTeX), per-element label (if kept), live pipeline steps.
6. Track: mobile-native detail views (separate UI).

---

## Part D — Feasibility (code-grounded, 2026-06-30)

**Verdict: frontend-only. No pipeline change, no LLM change, no backend change for v1.**

- **Pipeline: unchanged.** Everything the digest shows is already produced + already in the API payload (proven — the live `ClaimSummaryPanel` consumes it): stance on `claimMap.elements[].evidenceRefs[].relationship` (the locked source-of-truth); the lean line = `claimMap.orientation` (mechanical, no LLM); tier/type/`relevanceScore`/`snippet`/`archivedUrl` on each `Evidence`; gaps = elements with `state ∈ {null, unresolved}`.
- **LLM calls: untouched.** Stance taxonomy is unchanged and produced upstream in the MAP stage; orientation is mechanical. The digest only re-presents it — no mapper-prompt edit, no new map/decompose call. The ONLY possible new LLM is "Key findings" — and v1 does it **mechanically** (top-N evidence by `relevanceScore`, show existing snippet) = **zero new LLM**. Optional v2 = one cheap Flash-Lite rewrite of those snippets (additive, avoidable).
- **Load-bearing code touched:** two **shared** frontend components — `ClaimSummaryPanel.tsx` (→ digest) and `ViewSelector.tsx` (→ segmented switcher). Both are single-source shared by `/dashboard/check/[id]` AND `/r/[id]`, so one change updates both surfaces together (benefit, not risk). The relationship→evidence join the bar needs already exists (Librarian view + the panel's `rel:['challenges']` deep-links).
- **One open data decision (no code cost):** the distribution-bar denominator — **element-state distribution** (what the panel counts today) vs **evidence-stance distribution** (tally `evidenceRefs` by relationship). They answer slightly different questions; pick one or show both.

**Difficulty: low–moderate, frontend-only.** No migrations, no pipeline risk, no new LLM spend in v1.

---

## Part E — Visual language / colour (open founder decision)

Founder critique 2026-06-30: the results page reads "a bit bland / like a black-and-white newspaper." Honest diagnosis: grey comes from two *deliberate* constraints — the document-grammar restraint (orange = precision mark only) + the no-verdict colour lock (no green/red on stance) — BUT the sandbox **over-rotated**, greying out things allowed to carry colour.

**Resolution (adds life, keeps both locks):**
- **Orange = the app's wayfinding/interaction accent** (active tab, hover, links, click affordances, focus) — de-blands AND fixes "tabs don't look clickable". (Orange = interaction, never stance.)
- **Restore tier/type classification colour** (classification ≠ verdict — legitimate).
- **More surface warmth + stronger type hierarchy** → "refined document", not "grey wall".
- **Stance stays neutral** (icon + word + position, no hue).
- Distinction held: *marketing pages* stay austere (document brochure); the *app* may use more accent for interactivity/QOL.

Next: apply a "warmth + orange-wayfinding" pass to the sandbox for side-by-side comparison before locking the palette.

---

## Part F — Broader scope: the linked results surface (to plan next)

The digest is the entry point; the redesign must keep + improve the *whole* interactive surface it links into. Scope to plan (maintain interactivity + QOL, improve flow):
- **The six lens views** (profession tabs): Evidence/Librarian, Sources/Correspondent, Timeline/Chronologist, Gaps/Seeker, Map/Cartographer, Video/Projectionist — each with its own internal interactivity (filters, sorts, diagnostic toggle, Seeker re-search, Cartographer map interactions, expand cards).
- **The switcher** (ViewSelector) + the deep-link state (`?view=`, `?claim=`, `?rel=`, `?element=`).
- **Multi-claim paging** (prev/next, claim grid).
- **Share / export** (social, copy link, PDF), `/verify` link, archived links, re-check, re-search.
- **Pre-result states** (processing/progress, claim selection).

Plan step: a grounded inventory of every interactive element + link across the results surface → a per-area maintain/improve plan, so nothing interactive is lost and QOL rises. (Survey launched 2026-06-30.)

