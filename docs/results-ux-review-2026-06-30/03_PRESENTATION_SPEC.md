# Results presentation — canonical spec (what we present + the rules)

> 2026-06-30 · The single source of truth for the signed-in results experience, consolidating: `00_SYNTHESIS` (competitor review), `01_DESIGN_DIRECTION` (digest + wayfinding), `02_INTERACTIVITY_MAP` (preserve list), and the build + audit on `feat/results-digest`. Read this before building further.

## 0. The goal (what success looks like)
A researcher lands on a result and, in seconds, understands **what was collected, where the evidence leans, and where to click next** — without a verdict, without cross-referencing, without cryptic codes. We win because the three direct rivals can't: **Webcite has no human UI (JSON only), Factiverse gates/blurs its results, scite is academic-only.** Our edge is a public, rendered, legible, no-verdict evidence record — *if* the first glance is visual and the navigation is obvious.

## 1. The Evidence Digest (first-glance answer; doubles as navigation)
Top of every focused claim, shared by `/dashboard/check/[id]` + `/r/[id]` (one component, both surfaces). Order:
1. **Identity** — rank · context (extracted/submitted) · claim type.
2. **Claim restated neutrally** — `claimMap.normalisedClaim || claim.text` (never the article's loaded phrasing).
3. **The lean (BLUF)** — the mechanical `orientation` line. Subject = the evidence, never the claim.
4. **Confidence, shown SEPARATELY** (GRADE) — breadth of set + "N of M elements covered". Stops a thin lean reading as settled.
5. **Distribution bar** — supports / context / challenges, **counted by membership** (an item carrying a relationship is in that band) so a band's count = the filtered Evidence list it links to. Neutral palette + icon + word; click a band → that filtered lens. Tiny bands keep a min-width + tooltip. Header reconciles totals ("N of M sources mapped").
6. **Key findings** — top sources by relevance, favicon + domain, snippet clamped to one–two lines, links out to the source.
7. **Strongest support · strongest challenge** — favicon + title + domain, link into the filtered lens.
8. **Source-quality mix** — tier composition with classification colour (primary orange / reporting dark-grey / commentary grey). Never a single grade.
9. **Gaps** — element description + uncertainty, attributed to our collection; links to the Gaps lens.

## 2. No-verdict wording lock (non-negotiable)
The grammatical subject of any lean sentence is **the evidence / the sources / what we found — never the claim.** Direction is a fact about the collection; certainty is hedged; the claim's truth is never the predicate. **No** rating/badge, **no** 0–100 score, **no** "% likely true" (a % may only describe source distribution), **no** truth-asserting verbs (proves/confirms/debunks).

## 3. Visual + colour language
- **Orange = the app's wayfinding/interaction accent** — active tab, hover, links, click affordances, focus. (De-blands + signals clickability.)
- **Tier/type classification colour is legitimate** (classification ≠ verdict): primary orange, reporting dark-grey, commentary grey.
- **Stance stays neutral** — supports/challenges/context by icon + word + position + tonal weight, **never** green/red/amber.
- Marketing pages stay austere (document brochure); the app may use more accent for QOL.
- **#10 RESOLVED (founder, 2026-06-30): neutralized.** The pressure-test found the emerald/amber `ElementStateBadge` was NOT in fact desaturated at summary altitude — it shipped full-saturation in the overview cards *above* the digest, plus Map + Gaps + the latent ref-chip. All neutralized: state now reads by **icon + tonal weight + filled-vs-outline** (supported = filled dark, disputed = outlined, contextual = light, unresolved = dashed), never green/amber. Collection-qualifier colour (recency / sole-source / save / re-search success) is retained — it qualifies the *collection*, not the claim, so it's not a verdict, and it keeps the surface from going monochrome.

## 4. Navigation model
- **The digest is the launchpad** — its bar bands, key findings, strongest cards, gaps, and tier links all deep-link into the relevant lens via the existing `go(view, {rel, element})` contract.
- **Segmented switcher** (not ghost tabs): connected track, filled active state, inactive tabs visible (not greyed), orange hover, **default = Evidence ("start")**, subtitles = the **question each lens answers**, whole-tab hit area, **mobile caption** carries the active question.
- **Every deep-link (`?view`/`?claim`/`?rel`/`?element`/`?fresh`/`?upgrade`) and analytics event preserved** (see `02_INTERACTIVITY_MAP`). The old Explore rail is gone (switcher replaces it); all destinations still reachable.

## 5. Element legibility
Sub-elements read as their **description** (truncated, full on hover), never the cryptic "E01". Applied on the Evidence ledger cards + Correspondent callouts; the expanded Reading/Timeline cards already show "Element N — description"; Map roster + Gaps already show descriptions.

## 6. The six lenses (the question each answers)
Evidence — *what does the evidence say?* (default) · Sources — *is the full set here?* · Timeline — *when did it appear?* · Gaps — *what don't we know yet?* · Map — *what's the shape of the debate?* · Video — *what's said on camera?* Lens **bodies are unchanged in v1**; the redesign changed the *entry + switcher*, not each lens's internals.

## 7. Carried invariants
No-verdict colour · classify-don't-score (tier+type, no credibility number) · receipts for every exclusion · source-platforming (relevance summaries drive visits; never reproduce article content) · mobile needs a purpose-built UI, not responsive desktop.

## 8. Status — built vs remaining
**BUILT + verified on `feat/results-digest`** (tsc 0, web vitest 26/26): the digest, the segmented switcher, favicons, element descriptions, and 14 audit fixes.

**REMAINING (the build section):**
- Resolve **#10** (in-element colour) — gates the colour model.
- **#14 features:** surface corroboration ("N independent corroborating sources / echo") + Google Fact-Check publisher ratings (stored, unsurfaced).
- Per-lens QOL passes (reflect the active filter in the Evidence FilterPills; promote hover-only affordances; surface keyboard paging; the `ViewGuide` redundancy with question-subtitles).
- **Mobile-native detail views** (separate UI track).
- Merge to `main` (deploy) on founder verification.

## 9. Pressure test (2026-06-30) — outcome
Two adversarial red-teams (no-verdict lock + researcher-buyer). **Result: the CORE holds, execution had gaps — all now fixed.**
- **Holds (verified incl. backend):** no-verdict in WORDS (mechanical `orientation`, evidence-subject), no SCORE on truth, no OVERCLAIM (no tamper-evident/verified/fact-checked), the digest bar palette + caption.
- **Fixed:** #10 verdict colour neutralized (was wider than the spec admitted — overview cards above the digest); "strongest"→"most relevant" (D2); key findings title-not-snippet (D3); the missing disposition-filter banner built (the headline QOL); band-count parity (excluded-evidence); orientation-null + 0-mapped fallbacks; bar flex-grow (no clip on skew) + overlap note; AA contrast (challenges band, rank); footer noun/destination match. `2d8af3c`.

## 10. Remaining (the build section)
1. **#14 corroboration + fact-check** — surface "N independent corroborating sources / echo" + Google Fact-Check publisher ratings (stored, unsurfaced). Next slice or parked — founder call.
2. Small polish: dashboard `ShareSection` missing the verify/signed-record link (only on `/r/`); hover-only affordances on touch; the `ViewGuide` redundancy with question-subtitles; optionally desaturate the collection-qualifier red-600 freshness.
3. **Mobile-native detail views** (separate UI track).
4. Merge timing — verify on the branch then merge to `main` (deploy), or keep iterating on the branch.
