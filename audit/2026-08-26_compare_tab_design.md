# COMPARE — replacing the SOURCES tab

**Date:** 2026-08-26
**Status:** DESIGN — approved in principle by the founder, not built
**Supersedes:** `2026-08-26_sources_tab_replacement_design.md` (the INDEPENDENCE
proposal — rejected, see §2; that doc is retained for its measurements)
**Reference sweep:** §9

---

## 1. What it is

A user-driven comparison surface. The reader picks **two** sources from the
claim's evidence, presses **Compare**, and gets one model pass that reads both
articles and returns three things: a short summary of each, and a statement of
where their positions diverge — plus a mechanical, element-aligned breakdown of
exactly which sub-questions they collide on.

**The user's job it serves:** *find an angle.* Not "is this true" — Tru8 never
answers that — but "where is the interesting disagreement in this pile, and what
is it actually about."

**Why it can exist only here:** the collision table is computed from element
decomposition. No competitor decomposes claims into sub-questions, so no
competitor can say *these two pieces disagree specifically on e2 and agree on
e4*. The differentiator falls out of the thing we already uniquely do.

### 1.1 ⚠️ We compare POSITIONS, not articles (founder decision, 2026-08-26)

**The unit of comparison is the position each source takes on this claim, never
the article as a publication.**

An article covers far more than the claim. A Harvard Health piece on alcohol
covers dozens of things; a general summary of it would be mostly irrelevant to
why the reader is on this page, and the divergence field would drift into
differences that have nothing to do with the claim they asked about.

So: **full article text goes in** (the relevant passage may be anywhere in the
piece), **a claim-scoped position comes out.** Scoping is done with the
**element descriptions** — neutral and question-shaped — never the claim text,
which resolves the premise-adoption tension in §10.2.

**Messaging follows from this, and one line is non-negotiable:**

- Say **sources**, not **articles**, throughout the UI and copy.
- Results header reads **"What each says here"**.
- **Required, under the summaries:** *"Compared on the questions in this claim,
  not on the articles as a whole."*

Without that line we print a partial characterisation of a piece **under its
publisher's name** — the same family of defect as a truncated headline that
looks complete (fixed 2026-08-25). It is one cheap sentence and it turns a
hidden limitation into a stated scope.

**Why the user picks, and not us:** an earlier version had Tru8 select the
counter-position article. That is invariant #7 in reverse — structurally
manufacturing two-sidedness, and on a flatly false claim it would be the worst
thing we could ship. **Because the user chooses the pairing, Tru8 remains the
organiser.** This is the load-bearing design decision; do not quietly reverse it
by making the suggestion the default (§5.4).

---

## 2. Why SOURCES goes, and what was rejected first

The cold read (2026-08-25) was *"feels redundant."* Verified: **SOURCES is the
one tab where you cannot open a source** — `SourceCard.tsx:118-124` renders
titles as plain text; the only `Visit source →` is on EVIDENCE
(`ReadingTable.tsx:137-146`). Four of its seven signals duplicate other tabs.

Four replacement ideas were measured and killed **before** being written up. The
numbers are recorded so nobody re-attempts them:

| idea | measured | why killed |
|---|---|---|
| Paper Trail / echo — *"8 sources → 3 originals"* | `originals > 0` on **8%** of evidence sides; repetition clusters **0%**; echo gate **2/10** corpus claims | On ~80% of checks the headline reads *"10 sources → 10 originals"* — a non-statement dressed as an insight |
| Diagnostic value / ACH — *"what would change this"* | top bucket fires on **0%** and **10%** of mapped items | Same failure: blank most of the time |
| Independence / concentration | always populated | It is **already on SOURCES today** (ConcentrationBar + sole-source badges). A cleanup, not a tab |
| Who's saying this / entities | `key_entities` = **2 per claim**, typed `OTHER`, values like *"heart"*, *"red wine"* | No real actors in the data |
| The Working Out (per-ref `reasoning`) | **73/73 refs, 100%, avg 178 chars**, already in the payload, zero readers | **Founder call:** users want the software to work; they do not care how or why. Machinery, not value |

That last rejection generalises into a filter worth keeping: **the tab must give
the user something they want, not prove that we are honest.** It retired the
whole transparency family — working-out, search receipt, scope ledger.

---

## 3. What the data supports

Measured on captured production checks (`backend/scripts/.6b54_capture_artefacts.json`,
`.c051_capture_artefacts.json` — 2 checks, 4 claims, 73 evidence refs).

**Opposing pairs per claim** — two sources addressing the SAME element in
OPPOSITE directions:

| claim | mapped sources | possible pairs | **opposed** |
|---|---|---|---|
| Alcohol protects the heart | 19 | 171 | **50** |
| Physicians advised red wine | 17 | 136 | **0** |
| Alcohol protects against heart disease | 8 | 28 | 4 |
| Doctors recommended red wine | 2 | 1 | 0 |

The collisions are substantive — NIH paper vs Harvard Health vs Heart Foundation
vs Columbia Public Health, all on the same sub-question.

**Relationship mix across all refs:** `context` **33**, `supports` **26**,
`challenges` **14**. **Elements with ≥1 challenging source: 46%.**

Two consequences drive the design:

1. **Half of claims have no opposing pair.** That is a normal outcome, not an
   error state. The suggestion button is simply absent (§5.4).
2. **`context` is the largest bucket** — which is why the second slot must
   accept a *contextualising* source, not only a challenging one. Without that,
   the feature would be dead on half of all claims.

---

## 4. Text availability — the constraint that shapes the build

| what we hold per evidence item | share |
|---|---|
| `distilled` (already LLM-compressed) | 35% |
| `snippet` only | 29% |
| `api` | 18% |
| **`full` article text** | **10%** |

**We do not hold the article for 90% of evidence.** Summarising a stored
~1000-char snippet would produce something shorter than what we already display,
while *looking* like a summary of the piece — the same defect class as the
truncated headlines fixed on 2026-08-25.

**Therefore: fetch at Compare time, not at pipeline time.** Two fetches, in
parallel, for the two articles the user actually chose. This is why the feature
is on-demand rather than precomputed, and it is what keeps the cost near zero
until someone engages.

⚠️ **Fetching will often fail.** Measured 2026-08-25: even with the honest
`Tru8Bot` UA, ~70% of previously-blocked URLs still 403. **Every summary must
declare which text it was built from** (§6.4). Never present a snippet-derived
summary as a summary of the article.

---

## 5. Interaction design

### 5.1 Shape

```
  ┌─────────────────────────┐   ┌─────────────────────────┐
  │        SLOT A           │   │        SLOT B           │
  │   (empty · dashed)      │   │   (empty · dashed)      │
  └─────────────────────────┘   └─────────────────────────┘

        [ COMPARE ]   0 of 3 used      [ SUGGEST A PAIR ]

  ────────────── SOURCES IN THIS CLAIM (17) ──────────────
  ▸ picker rows …
```

### 5.2 Placing a source

**Click-to-place is primary; drag is an enhancement.** Touch drag-and-drop is
fragile, screen readers need a non-drag path, and mobile is a standing concern in
this project (`feedback_mobile_different_ui`). Clicking a picker row fills the
next empty slot; clicking a filled slot's `Remove ×` empties it. Desktop
additionally supports drag onto a slot. Both routes produce identical state.

### 5.3 Slots are A and B — not "supports" and "challenges"

Neither slot constrains what may enter it. Two supporting primaries that
disagree on *magnitude* is an excellent comparison, and a rule that says
"slot 1 = supports" forbids it. Each picker row and filled slot **displays** its
relationship badge; nothing enforces it.

Guards: a source cannot be compared with itself; same-domain pairs are allowed
(two pieces from one outlet can legitimately disagree).

### 5.4 Suggest a pair

A secondary button that fills both slots with the highest-collision pair — most
shared elements in opposite directions, tie-broken toward the higher tier.

- **It is never the default.** Slots start empty.
- **It is absent, not disabled, when no opposing pair exists.** A disabled button
  invites the reader to wonder what they did wrong; absence says nothing is
  there. On the ~50% of claims with no opposition, the tab simply has no
  suggestion.

### 5.4b Pre-flight warning — free, and it protects the budget

Element refs are already on the client, so **before** the user spends a
comparison we know whether the two chosen sources address any of the same
sub-questions. When they share none, show a quiet note above the Compare button
in the `EvidenceQualityNote` idiom:

> *△ These two address different parts of the claim — a comparison may find
> little to say.*

**A second case uses the same strip — syndication.** The same wire story appears
on three sites; comparing two copies of one AP piece yields *"they agree
entirely"*, wastes a comparison and looks foolish. `corroborationGroupId` and
`corroboratingEvidenceIds` already identify these:

> *△ These two appear to carry the same source story — a comparison may find no
> difference.*

**Advisory only — never blocking.** The user may have a good reason. But
spending one of three on a pair with no overlap, and only discovering that after
the call, is a bad experience we can prevent for nothing.

### 5.5 Compare

Disabled until both slots are filled. On press:

1. Both article headers render immediately (favicon, domain, title, date, tier,
   type) so the page is never blank.
2. Two fetches fire in parallel.
3. One model call runs.
4. Results render progressively into the layout beneath each slot.

---

## 6. Visual design

Everything below reuses an idiom already in the codebase. Nothing new is
invented, and no new colour enters the system.

### 6.1 Tokens in play

| use | token / class | source |
|---|---|---|
| Card resting | `border border-zinc-100 hover:border-zinc-300` | `LedgerCard.tsx:60` |
| Card active/filled | `border-zinc-300 bg-[#FAFAF8]` | `SourceCard.tsx:50`, `ReadingTable.tsx:58` |
| Section divider | `flex-1 h-px bg-zinc-200` + centred mono label | `CorrespondentView.tsx` shelf divider |
| Primary button | `bg-zinc-900 text-white border-zinc-900` | active tab, `ViewSelector.tsx:88` |
| Secondary button | `border-zinc-200 text-zinc-400 hover:text-zinc-600` | Diagnostic toggle, `LibrarianView.tsx` |
| Section label | `font-mono text-[9px] font-bold uppercase tracking-[0.25em] text-zinc-500` | `DiagnosticFlag.tsx:11` |
| Quiet receipt line | `font-mono text-[10px] text-zinc-500` + `△` glyph | `EvidenceQualityNote.tsx:23-27` |
| Tier ring on favicon | `w-8 h-8 rounded-full border-2`, tier colour | `SourceCard.tsx:57-62` |
| Tier colours | `#EA580C` / `#3F3F46` / `#A1A1AA` | `--tier1/2/3-accent` |
| Accent (wayfinding only) | `var(--accent)` `#EA580C` | globals.css |

### 6.2 Empty slot

`border border-dashed border-zinc-300`, min-height matching a filled slot so the
layout does not jump. Centred, two lines:

```
        SLOT A
  Click a source below
```

Line 1 `font-mono text-[10px] uppercase tracking-widest text-zinc-400`; line 2
`text-[11px] text-zinc-400`. On drag-over: `border-[var(--accent)]` — the accent
is the wayfinding colour throughout the app and carries no verdict meaning.

### 6.3 Filled slot

Reuses the `SourceCard` header composition exactly: tier-ringed favicon, domain,
title via `cleanTitle` (**which now preserves the trailing ellipsis** — a cut
title must look cut), date with `DateHint`, `TierBadge` + `TypeBadge`, element
chips via `ElementRefs`, and a `Remove ×` in the `ReadingTable` close idiom
(`font-mono text-[10px] text-zinc-400 hover:text-zinc-900`, top-right).

### 6.4 Results

Divider, then two columns aligned under their slots so the eye connects summary
to source, then a full-width divergence block.

```
────────────────── WHAT EACH SAYS HERE ──────────────────
  [summary A prose]              [summary B prose]
  △ READ · full article          △ READ · snippet only
                                   (publisher blocked us)

  Compared on the questions in this claim, not on the
  articles as a whole.

─────────────────── WHERE THEY DIVERGE ──────────────────
  [comparison prose]

  E02  OPPOSED   A supports · B challenges
  E04  ALIGNED   both support
  E01  ONLY A    B does not address this
```

- Summaries: `text-sm text-zinc-700 leading-relaxed` — the `DiagnosticFlag`
  body treatment.
- **The text-basis receipt is required**, in the `EvidenceQualityNote` idiom
  (`△ READ · …`, mono 10px zinc-500). This is the honesty seam that prevents a
  fragment reading as a whole article.
- **The collision table carries NO colour.** Element number via `ElementBadge`;
  `OPPOSED` in `font-mono text-[10px] font-bold text-zinc-900`, `ALIGNED` and
  `ONLY A` in `text-zinc-400`. Weight and case do the work.
  ⚠️ A `--divergence` amber token exists in `globals.css`. **Do not use it
  here.** The no-verdict-colour lock is absolute on this surface, and amber
  reads as a warning about the claim.

### 6.5 Mobile

Slots stack vertically. Picker list below. Click-to-place only — no drag.
Results stack: summary A, summary B, then divergence. The collision table
becomes stacked rows rather than columns.

### 6.6 Guide entry

`ViewGuide.tsx` is keyed by view value and renders nothing for an unrecognised
key, so the new value **needs its own entry** or the guide silently disappears.
Draft: *"Pick two sources and compare them. Tru8 reads both and shows where their
positions differ — and which parts of the claim they disagree on."*

---

## 7. Engineering

### 7.1 One model call, three jobs

One call reads both articles and returns `{summaryA, summaryB, comparison}` via
the flat `responseSchema` path (verified working on Gemini 3.x, 2026-08-01).

**This is not merely cheaper — it is more accurate.** Three separate calls would
leave the comparison step seeing only the two summaries, so every nuance lost in
summarising A is invisible when comparing A to B. One call holds both originals
in context while writing all three fields.

- Model: `GOOGLE_LLM_MODEL` (currently `gemini-3.5-flash-lite`). No new
  integration.
- Size: roughly one distiller-sized task (~15k input tokens). Well inside
  context.
- Output: token-capped per field. Summaries short by construction.
- **Accept the all-or-nothing failure mode.** Rendering the two article headers
  before the call means the page is never blank, and the user pressed a button
  and can retry.

### 7.2 The comparison must not adjudicate

This is a new surface on which the model discusses the claim, so it is a new
sycophancy risk. The prompt is constrained to: what each asserts · where they
diverge · where they agree · what neither addresses. **Never** which is more
convincing, more credible, or correct.

Opinion (grounds-routed) claims are in scope — comparison is arguably *most*
useful there — but orientation is suppressed on those claims and the comparison
must not resolve the opinion either.

**This needs an acceptance test, not prompt wording alone.** Prompt-only fixes
have failed here before (`feedback_nf11_prompt_only_failed`).

### 7.3 ⚠️ The manifest trap

The signed canonical payload includes **per-evidence `content_basis`**
(`manifest_signer.py:108`, built at `:172-174`). If the Compare fetch
helpfully updates that row from `snippet` → `full`, the pipeline fingerprint
changes and **`/verify/{id}` returns `data_modified` for that check forever** —
the same failure class as the migration env-var ordering bug.

**Rule: the comparison writes to its own table and touches nothing the manifest
signs.** No writes to `Evidence`, no writes to `claim_map`.

### 7.4 The cache is the counter

A single `claim_comparisons` table keyed `(claim_id, evidence_a, evidence_b)`
holding the three summaries and the text basis per side. Row count *is* the
spend — no separate counter to drift out of sync.

- Key must be **order-independent** (sort the two ids) or A/B and B/A count
  twice and cache neither.
- Store the text basis per side so a cached comparison never misrepresents what
  it was built from.

⚠️ **STORE PROSE ONLY. Compute `collisions` on READ, never persist them.**
(Design review, 2026-08-26.) Re-search and coverage recovery re-map evidence to
elements, so a stored collision set silently goes stale and starts contradicting
the claim map beside it — **a failure mode we already have in the adjacent
system** (`OPEN_WORK`: *"basis blocks go stale after coverage recovery"*).
Collisions are a cheap pure function of `evidence_refs`; deriving them per
request costs nothing and makes an old comparison's structure self-correct.

⚠️ **Concurrency.** A double-click or a second browser tab fires two identical
comparisons: both run, both charge, and they race on the unique key. Take a
short lock on the sorted pair key, or make the insert an upsert that the loser
reads back as a cache hit.

### 7.5 Budget

**3 comparisons per check, free.** Credits are being de-emphasised generally
(Console is 200/month), so this is a fair-use cap rather than a meter.

**A re-search grants +1, accumulating** (founder, 2026-08-26). So: 3 base, 4
after one re-search, +1 for each further one. Re-search already costs a credit,
so the extra is priced; and the budget follows genuine evidence growth without
compounding.

**`limit = 3 + COUNT(usage_events WHERE kind = 're_search' AND check_id = …)`.**
Verified queryable — `usage_event.py:28` defines `KIND_RE_SEARCH` keyed to the
re-searched check.

**What counts — disambiguated in design review, because "failed" was doing two
jobs:**

| outcome | counts? | why |
|---|---|---|
| Cached pair re-viewed | **No** | No new work done |
| Both fetches blocked, result produced from **stored text** | **Yes** | A real, usable comparison — just on weaker text, and labelled as such (§10.2) |
| No usable text on either side | **No** | Nothing was produced |
| Model call errored or timed out | **No** | Nothing was produced |

The middle row is the one that was ambiguous. A blocked fetch is **not** a failed
comparison — degrading to stored text is a designed path (§4), it consumes real
tokens, and it returns something the reader can use. It must be charged, and it
must say what it read.

### 7.6 Selectable set

**Only evidence with `receiptStatus === 'shown'`.** Letting a user compare an
*excluded* source would re-platform something the pipeline filtered out with a
receipt.

### 7.7 Surfaces

| surface | create | view |
|---|---|---|
| Dashboard (`/dashboard/check/[id]`) | ✅ authenticated | ✅ |
| Public report (`/r/[id]`) | ❌ never | ✅ read-only, cached only |
| Agent API `/agent/*` | ❌ | ❌ |
| MCP (stdio + remote) | ❌ | ❌ |

A shared `/r/` record showing comparisons the owner already ran makes the
distribution unit **richer at zero marginal cost**, while a cold visitor can
never spend tokens. This matters — `/r/` is what gets sent to journalists.

### 7.8 Smaller considerations

- **Paywalled fetches** return a stub. Treat as a fetch failure; never summarise
  a paywall notice.
- **Latency** is realistically 10–25s (two fetches + one call). Progressive
  rendering is required, and the existing 45s calm-stall notice pattern applies.
- **Analytics:** `comparison_run`, `comparison_suggested_used`,
  `comparison_failed` (with reason). Without these we will not know whether the
  best thing on the page is used at all.
- **PDF export:** out of scope for v1. Note it.
- **Publisher relations:** summarising a whole article sits closer to
  substitution than a snippet does. Keep summaries short and always link out.
  Not a blocker; a deliberate choice.
- **Language:** cross-language pairs are possible; the model handles them, but
  the summary should say so.

---

## 8. Build outline

| phase | work |
|---|---|
| 1 | `claim_comparisons` table + migration; order-independent key |
| 2 | Compare endpoint: parallel fetch (reusing `browser_headers`) → one structured call → persist → return |
| 3 | Frontend tab: slots, picker, click-to-place, Compare, budget display |
| 4 | Results rendering + text-basis receipts + collision table |
| 5 | Suggest-a-pair (mechanical, highest collision, tier tie-break) |
| 6 | `/r/` read-only path |
| 7 | Reference cleanup (§9) |
| 8 | Acceptance test for non-adjudication; analytics |

**Cost — MEASURED 2026-08-26 against `cost_constants.py`.** Rates for
`gemini-3.5-flash-lite` are **$0.30/M in, $2.50/M out**, verified against vendor
pages 2026-08-25.

**Superseded by the live measurement in §10.2** — the estimates below were built
on assumed article lengths; the real distribution is now measured.

| | mean cost/comparison | 4-comparison budget |
|---|---|---|
| **Reading whole articles, 32k rail** | **0.262p** | **1.05p** |

A full check costs **~1.18p** (measured 2026-08-12), so a completely exhausted
Compare budget still costs less than the check it sits on.

⚠️ **The 1.18p baseline is itself an undercount.** `cost_constants.py`
accumulates analyzer + classifier + distiller tokens only; extract, the
relevance scorer and the query-answer call are not counted (limitation 1 in that
module). Compare's real share of a check is therefore **smaller** than these
ratios imply — do not quote the ratio as if the baseline were complete.

---

## 9. Reference cleanup (from the codebase sweep)

The swap is far cheaper than expected.

- **Only two files import the view:** `check-detail-client.tsx:24`,
  `public-report-client.tsx:11` — one render line each
  (`:549-551` / `:369-371`).
- **Zero backend involvement.** No API field, no contract, no PDF structure.
- **Zero tests** on any correspondent component. Only guard:
  `ViewSelector.test.tsx:16` asserting the string `SOURCES` renders, and `:12`'s
  "renders all 6 view tabs".
- **A 1-for-1 replacement keeps ~20 "six views" copy claims correct** across
  `tiers.ts`, `stitch-pricing.tsx`, `terms-of-service`, `dashboard-hero`,
  `llms.txt`, `SYNOPSIS.md`, `email_notifications.py:550`. **Replace, do not
  remove.**

**Must change:**

1. `ViewSelector.tsx:6` `ViewTab` union · `:42` `ALL_TABS` entry ·
   `:36` comment.
2. `check-detail-client.tsx:70` and `public-report-client.tsx:25` — hardcoded
   `validViews` arrays.
3. `ViewGuide.tsx:10-11` — new guide entry (§6.6).
4. **`?view=correspondent` deep links are live and shareable.** Both hosts
   validate against the hardcoded array and silently fall back to `librarian` —
   landing the reader on the wrong lens with no explanation. **Needs a
   translation, not just an alias.** `2026-07-08_f8_implementation_plan.md:89`
   proposed exactly this approach.
5. `pricing-faq.tsx:26` — the only user-facing use of a profession name, it
   **breaches the action-names-not-professions lock** *and* describes the old
   Interpreter, not source diversity. Wrong today, independent of this work.
6. `stitch-product-preview.tsx:203-204` — "Sources — outlet by outlet".
7. `ViewSelector.test.tsx:12,16`.
8. `CLAUDE.md:149` — describes Correspondent as "Detail only" with a disposition
   panel. **Stale twice over.**

**Dead code found:** `CorrespondentView`'s `scope="check"` branch — both hosts
only ever pass `scope="claim"`.

---

## 10. Implementation specification

Written to close the five gaps that stood between "shape" and "buildable".

### 10.1 Fetch — what is reusable, and what is not

Checked in code, not assumed.

**Reuse:**
- `app/utils/browser_headers.py::browser_headers()` — the honest `Tru8Bot` UA.
- `EvidenceExtractor._extract_main_content(html, url)` (`app/services/evidence.py`)
  — trafilatura → readability cascade, then `_sanitize_content` (mojibake fix,
  whitespace collapse, nav/footer stripping). **Returns the full article text,
  uncapped.** This is exactly what Compare needs.

**Do NOT reuse `_extract_from_page()`.** It is claim-scoped: it returns an
`EvidenceSnippet` trimmed to a relevance window, not the article. It also
carries side effects Compare must not inherit.

**Therefore:** a small standalone `app/services/article_reader.py` exposing
`fetch_article_text(url) -> (text | None, basis)`, wrapping the two reusable
pieces.

⚠️ **Do not record domain-access telemetry from Compare fetches.**
`_extract_from_page` calls `domain_tracker.record_access_result(...)`. That
table describes *pipeline* domain health; feeding user-driven fetches into it
lets user behaviour distort retrieval statistics.

⚠️ **PDFs: skip in v1.** `pdf_evidence` parses under a **module-wide semaphore
of 1** with a 20MB cap (`df0095f`, added after a 7.8MB treaty PDF OOM-killed the
container). A user-triggered PDF parse would contend with live pipeline parses
for that single slot. v1: a PDF-only source is selectable but falls back to its
stored text, labelled as such.

⚠️ **Text is uncapped, so Compare must cap it** before the model call —
see 10.2.

### 10.2 The model call

**Separation of duties — the design rule for this feature: the model writes
prose, the code computes structure.** The collision table (§6.4) is derived
mechanically from `evidence_refs`; the model never produces element mappings, so
it cannot get them wrong. This keeps the hallucination surface to three prose
fields and keeps the structural claims verifiable.

**Response schema** (flat `responseSchema`, verified working on Gemini 3.x):

```
{
  "summaryA":   string,   // <= 90 words
  "summaryB":   string,   // <= 90 words
  "divergence": string    // <= 120 words
}
```

### ⚠️ WE READ THE WHOLE ARTICLE. Passage selection is REJECTED — measured 2026-08-26.

**Founder objection, upheld by measurement:** summarising selected paragraphs
characterises a source's position from fragments, under that source's name. That
is the truncated-headline defect wearing a different hat, and it would produce
a summary that is worse than useless — confidently wrong about what a piece
argues.

**Cap: 32,000 tokens per article — a safety rail against a pathological input,
not a budget lever.** On a live sample of 88 corpus URLs it never binds.

**The measurement that settles it** (live fetch + trafilatura, 55 articles with
usable text):

| statistic | value |
|---|---|
| median article | **811 words (~1,094 tokens)** |
| p75 | 3,158 words |
| p90 | 7,113 words |
| max | 22,171 words |

| cap | reads whole | mean pence/comparison | 4-comparison budget |
|---|---|---|---|
| 4k | 73% | 0.172 | 0.69p |
| 16k | 95% | 0.244 | 0.98p |
| **32k** | **100%** | **0.262** | **1.05p** |

**Reading everything costs 0.09p more than truncating at 4k**, because cost
scales with *actual* tokens and the median article is tiny — the cap almost
never binds, so raising it is nearly free. The full budget stays under the
~1.18p a check costs.

**And the over-cap tail is not what a cap should be protecting us from.** The ten
longest in the sample were ONS statistical bulletins, PMC papers, a GAO report,
and Wikipedia articles — **not one argumentative news piece among them.**
Selection would only ever have fired on reference documents, and never on the
news articles where the median lives.

**One fallback path, not two.** If we cannot read the article whole — blocked,
non-HTML, or over the 32k rail — we fall back to the **stored** pipeline text
and label it (§6.4). No fragmenting, no second mechanism.

⚠️ **That path is common, not exceptional. Measured fetch rate on corpus URLs:
66% HTTP 200, 62% yielding usable text — so roughly 38% of comparisons will run
on stored text.** The honest-labelling receipt is therefore **load-bearing, not
decorative**: on more than a third of comparisons it is the only thing telling
the reader they are not getting the article. (These URLs are months old, so link
rot inflates the failure rate — treat 66% as a floor.)

**Prompt constraints:**
- Describe what each source says **in its own terms**, attributed
  (*"The Harvard piece argues…"*, never *"studies show…"*).
- State where the two positions differ and where they coincide.
- **Never** say which is more credible, better sourced, more convincing, or
  correct. **Never** resolve the claim.
- If a side's text is a fragment rather than the article, say so and summarise
  only what is present.
- UK English.

⚠️ **Do NOT pass the user's claim text into the prompt.** Pass the **element
descriptions** instead. The claim carries valence, and a model given the claim
tends to frame both articles relative to it — the premise-adoption failure
(PARROT) that keeps mapping on a higher model tier. Element descriptions are
neutral by construction on grounds-routed claims and near-neutral elsewhere.

**Acceptance test = the premise-adoption probe** designed 2026-08-01 and never
built: run an identical pair with and without the claim line, and measure the
delta in how each side is characterised. Invariant #7 as one number.
**Prompt wording alone is not a sufficient control here**
(`feedback_nf11_prompt_only_failed`).

### 10.3 Endpoint contract

```
POST /api/v1/checks/{check_id}/claims/{claim_id}/comparisons
  body    { "evidenceA": "ev-…", "evidenceB": "ev-…" }
  200     { id, summaryA, summaryB, divergence,
            basisA, basisB,            // full | distilled | snippet | failed
            collisions: [ {elementId, a, b, verdict} ],   // computed server-side
            cached: bool,
            budget: { used, limit } }
  409     { error: "budget_exhausted", budget: {…} }
  422     { error: "invalid_pair" }    // same id, or not in the `shown` set
  502     { error: "fetch_failed" | "model_failed" }   // NOT counted

GET  /api/v1/checks/{check_id}/claims/{claim_id}/comparisons
  200     { comparisons: [...], budget: {…} }
```

- `GET` serves both the dashboard tab on load and the `/r/` read-only path.
- **Auth:** Clerk session only. Explicitly rejected under API-key auth, so the
  Agent API and MCP cannot reach it (§7.7).
- `cached: true` returns instantly and does **not** spend budget.

### 10.4 Suggest-a-pair — precise definition

Deterministic, mechanical, no LLM:

1. **Candidates:** both items in the `shown` set, sharing ≥1 element on which
   their relationships are exactly `{supports, challenges}`.
2. Rank by **count of opposed elements**, descending.
3. Tie-break 1: **better combined tier** (primary 0 / reporting 1 / commentary 2;
   lower sum wins).
4. Tie-break 2: **more total shared elements**, descending.
5. Tie-break 3: lexicographic on the sorted `(evidenceA, evidenceB)` pair.

Step 5 exists so the suggestion is **stable across page loads** — a suggestion
that changes on refresh reads as a bug.

**No candidates → the button is absent** (not disabled) — §5.4.

### 10.5 Deep-link translation

`?view=correspondent` links are live and shareable, and today both hosts
silently fall back to `librarian`.

**Translate `correspondent` → `librarian`, with a one-line notice**, rather than
sending the reader to COMPARE. The Evidence ledger absorbed the source-list job;
COMPARE is a different thing, and landing someone there is a wrong answer
delivered confidently. The notice uses the existing dismissible context idiom:

> *The Sources view has been replaced. You're seeing Evidence.*

Silent fallback is not acceptable — it is the same class of defect as a cut
title that looks complete.

---

## 11. Open decisions

1. **Tab label.** `COMPARE` with subtitle *"Where do two sources differ?"* is
   the working assumption. Labels are one-word uppercase across the selector.

**Settled 2026-08-26:** budget is 3 + 1 per re-search (§7.5) · we compare
positions, not articles (§1.1) · per-article cap 4k tokens (§10.2) · cost
measured at 0.16–0.28p per comparison (§8).

---

## 12. Frontend specification

### 12.1 File manifest — new

```
web/components/evidence-views/compare/
  index.ts                 barrel
  CompareView.tsx          container: state machine, data fetch, layout
  ComparisonSlot.tsx       one slot (empty | filled), remove affordance
  SourcePicker.tsx         the selectable list + section divider
  PickerRow.tsx            one selectable source row
  ComparisonResult.tsx     two summaries + divergence prose
  CollisionTable.tsx       mechanical element-by-element rows
  TextBasisReceipt.tsx     what we actually read, per side
```

Reused unchanged: `TierBadge`, `TypeBadge`, `ElementBadge`, `ElementRefs`,
`DateHint`, `cleanTitle` / `getFaviconUrl` from `shared-utils`.

### 12.2 State machine

`CompareView` owns one state value; every transition is explicit.

| state | meaning | UI |
|---|---|---|
| `idle` | 0–1 slots filled | Compare disabled |
| `ready` | both slots filled | Compare enabled |
| `running` | request in flight | headers rendered, summaries skeletal, Compare disabled |
| `done` | result rendered | Compare disabled until a slot changes |
| `error` | fetch/model failed | inline reason, Compare re-enabled, **budget unchanged** |
| `exhausted` | budget spent | Compare replaced by the spent-budget note |

Changing either slot from `done` returns to `ready` and clears the result.

### 12.2b Tab visibility — the tab hides itself

`ViewSelector` already supports `hiddenTabs` (used today to hide VIDEO when a
check has none). COMPARE uses the same mechanism. **Two cases, both found in
design review:**

1. **`/r/` with no stored comparisons → hide the tab.** Otherwise a cold
   recipient of a shared record clicks COMPARE and sees an empty page — on the
   page that *is* the distribution unit. Read-only viewers cannot create, so an
   empty tab there is a dead end, not an invitation.
2. **Fewer than 2 `shown` evidence items on the claim → hide the tab**, on both
   surfaces. You cannot compare with one source. Corpus evidence shows this is
   real: `TRU-C1A0-0004` has 5 shown items but a claim in the capture set had
   only 2 mapped, and one had 1.

An absent tab is correct here for the same reason the suggestion button is
absent rather than disabled (§5.4): nothing to do is not the same as something
you did wrong.

### 12.3 Props

```ts
CompareView({ scope: 'claim', claim, checkId, readOnly, token })
ComparisonSlot({ slot: 'A'|'B', evidence|null, onRemove, onDropTarget })
SourcePicker({ evidence: Evidence[], placed: [idA, idB], onPlace })
PickerRow({ evidence, elementIds, disabled, onClick })
ComparisonResult({ result, evidenceA, evidenceB })
CollisionTable({ rows: CollisionRow[] })
TextBasisReceipt({ basis, words? })   // "full article (1,240 words)" | "stored extract"
```

`readOnly` (the `/r/` path) hides the picker, slots, and Compare entirely and
renders only stored comparisons.

### 12.4 Types — `shared/types/index.ts`

```ts
export type ComparisonBasis = 'full' | 'distilled' | 'snippet' | 'failed';
export type CollisionVerdict = 'opposed' | 'aligned' | 'only_a' | 'only_b';

export interface CollisionRow {
  elementId: string;
  a: EvidenceRelationship | null;
  b: EvidenceRelationship | null;
  verdict: CollisionVerdict;
}

export interface Comparison {
  id: string;
  evidenceA: string;
  evidenceB: string;
  summaryA: string;
  summaryB: string;
  divergence: string;
  basisA: ComparisonBasis;
  basisB: ComparisonBasis;
  collisions: CollisionRow[];   // COMPUTED per request, never stored (§7.4)
  createdAt: string;
}

export interface ComparisonBudget { used: number; limit: number; }
```

**Also add the long-missing field** (needed by nothing here, but it is the
correct home and its absence is why `reasoning` was invisible):
`EvidenceRef.reasoning?: string`.

### 12.5 API client — `web/lib/api.ts`

```ts
getComparisons(checkId, claimId, token?)   // GET  — used on mount and by /r/
createComparison(checkId, claimId, a, b, token)  // POST
```

`409` surfaces as `exhausted`, `422` as a developer error (should be
unreachable — the picker disables placed and non-`shown` items), `502` as
`error` with the reason shown inline.

### 12.6 Accessibility

- **Click-to-place is the primary path**; drag is additive and never the only
  route to any state.
- Slots are `<button>` when empty (`aria-label="Place a source in slot A"`),
  `<section aria-label="Slot A: {domain}">` when filled with a nested
  `Remove` button.
- Picker rows are `<button aria-pressed={placed}>`.
- Result region is `aria-live="polite"` so a screen reader announces arrival.
- `CollisionTable` is a real `<table>` with `<caption>` and scope-d headers —
  it is tabular data, not a layout grid.
- **No colour carries meaning anywhere in this view** (§6.4), so contrast
  requirements are met by weight and text alone.

### 12.7 Responsive

| breakpoint | layout |
|---|---|
| `lg+` | slots side by side; results in two columns beneath their slot |
| `< lg` | slots stacked; results stacked A → B → divergence; collision rows stack label-above-value; click-to-place only, no drag |

### 12.8 Analytics

`comparison_run` `{claimId, suggested: bool, budgetUsed}` ·
`comparison_suggested_used` · `comparison_failed` `{reason}` ·
`comparison_viewed_readonly` (the `/r/` path — tells us whether recipients
engage with it).

---

## 13. Backend file manifest

```
app/models/claim_comparison.py     ClaimComparison (see 7.4)
alembic/versions/xxxx_claim_comparisons.py
app/services/article_reader.py     fetch_article_text(url) -> (text, basis, words)
app/services/comparison.py         orchestration: fetch x2 -> select -> call -> persist
app/prompts/comparison.py          prompt + responseSchema (10.2)
app/api/v1/comparisons.py          GET + POST (10.3)
```

`comparison.py` computes `collisions` **mechanically from `evidence_refs`** —
never from the model (§10.2).

**Tests:** `tests/unit/test_comparison_collisions.py` (pure function, no I/O) ·
`tests/unit/test_comparison_budget.py` (3 + 1 per re-search; cached and failed
runs do not count) · `tests/unit/test_comparison_auth.py` (API-key auth is
rejected) · `tests/integration/test_comparison_endpoint.py` ·
**`tests/unit/test_comparison_no_adjudication.py`** — the premise-adoption probe
(§10.2), which is the acceptance gate, not a nice-to-have.

---

## 14. Removal of the SOURCES tab — file by file

From the codebase sweep. **A 1-for-1 replacement, so the ~20 "six views" copy
claims stay correct and are NOT touched.**

### 14.1 Delete

```
web/components/evidence-views/correspondent/     (6 files, 596 lines)
  index.ts · CorrespondentView.tsx · SourceCard.tsx
  CorrespondentSummary.tsx · ConcentrationBar.tsx · SourceGaps.tsx
```

Nothing else imports them. **Zero tests cover any of them**, so deletion breaks
no CI.

⚠️ `ConcentrationBar.tsx` is the one genuinely good thing on the old tab. It is
deleted here because nothing in COMPARE uses it — **if it is ever wanted back,
it is in git history at this commit**, not lost.

### 14.2 Edit

| file | line | change |
|---|---|---|
| `ViewSelector.tsx` | 6 | `ViewTab` union: `'correspondent'` → `'compare'` |
| `ViewSelector.tsx` | 42 | `ALL_TABS` entry → `{ value: 'compare', label: 'COMPARE', subtitle: 'Where do two sources differ?' }` |
| `ViewSelector.tsx` | 36 | internal profession comment — drop the correspondent mapping |
| `check-detail-client.tsx` | 24 | import → `compare` |
| `check-detail-client.tsx` | 70 | `validViews` array |
| `check-detail-client.tsx` | 549-551 | render `<CompareView …/>` |
| `public-report-client.tsx` | 11 | import |
| `public-report-client.tsx` | 25 | `VALID_DETAIL_VIEWS` array |
| `public-report-client.tsx` | 369-371 | render with `readOnly` |
| `ViewGuide.tsx` | 10-11 | new `compare` entry (§6.6) — **an unrecognised key renders nothing, so omitting this silently removes the guide** |
| `ViewSelector.test.tsx` | 12, 16 | `SOURCES` → `COMPARE` |

### 14.3 Deep-link translation — required, not optional

`?view=correspondent` links are live and shareable. Today both hosts silently
fall back to `librarian`.

Add to both host pages: `correspondent` → `librarian`, **plus a dismissible
notice** in the existing context-strip idiom:

> *The Sources view has been replaced. You're seeing Evidence.*

**Not** a redirect to COMPARE — the ledger absorbed the source-list job; COMPARE
is a different thing, and landing someone there is a wrong answer delivered
confidently. Silent fallback is also not acceptable: it is the same class of
defect as a cut title that looks complete.

### 14.4 Copy that is wrong today, independent of this work

| file | line | problem |
|---|---|---|
| `pricing-faq.tsx` | 26 | *"a Correspondent view for element-by-element analysis"* — the **only** user-facing profession name (breaches the action-names lock) **and** describes the retired Interpreter, not source diversity |
| `stitch-product-preview.tsx` | 203-204 | *"Sources — outlet by outlet"* |
| `stitch-product-preview.tsx` | 17, 47 | comments naming Sources |
| `llms.txt` | 44 | *"source diversity"* in the six-ways list |
| `CLAUDE.md` | 149 | Correspondent row — **stale twice**: says "Detail only" and describes a disposition panel |
| `ClaimSummaryPanel.tsx` | 78 | comment listing lens values |
| `LibrarianView.tsx` | 111 | comment naming Correspondent |

### 14.5 Not touched

The ~20 "six views" claims in `tiers.ts`, `stitch-pricing.tsx`,
`terms-of-service`, `dashboard-hero.tsx`, `ClaimList.tsx:21`, `SYNOPSIS.md`,
`email_notifications.py:550`, `first-public-release`. **The count is unchanged.**

### 14.6 Dead code removed with it

`CorrespondentView`'s `scope="check"` branch — both hosts only ever pass
`scope="claim"`.

---

## 15. Order of operations

Nothing may leave the tree half-swapped.

1. **Backend first, behind nothing.** Model + migration + services + endpoint +
   tests. Ships inert — no UI reaches it.
2. **`shared/types` additions.** Inert.
3. **Build `compare/` alongside `correspondent/`.** Both present; tab still
   says SOURCES. Verify COMPARE in isolation via a temporary route or by
   swapping the `ALL_TABS` value locally.
4. **Swap the tab** (§14.2) in one commit: union, ALL_TABS, both hosts, guide,
   test. Atomic — a partial swap leaves a tab pointing at nothing.
5. **Delete `correspondent/`** (§14.1) in the following commit, so step 4 is
   revertable on its own.
6. **Deep-link translation + notice** (§14.3).
7. **Copy fixes** (§14.4) — independent, can land any time.

---

## 16. Acceptance criteria

**Must all pass before this is called done.**

| # | Criterion | How verified |
|---|---|---|
| 1 | Comparison never adjudicates | premise-adoption probe (§10.2), both valence directions |
| 2 | Collisions match `evidence_refs` exactly | unit test, pure function |
| 3 | Budget is 3, +1 per re-search; cached and failed runs never count | unit test |
| 4 | API-key auth cannot reach either endpoint | unit test |
| 5 | `/verify/{id}` still returns `valid` for a check that has comparisons | live check against a signed check — **the manifest trap, §7.3** |
| 6 | Every summary states what it was built from — article or stored text | live, both paths |
| 7 | A blocked fetch degrades to stored text and says so | live, on a known-403 domain — **~38% of real comparisons take this path** |
| 12 | Collisions are computed per request, not stored | unit test + a re-search that changes the map |
| 13 | Two simultaneous identical requests charge once | concurrency test |
| 8 | `?view=correspondent` lands on Evidence **with the notice** | live |
| 9 | Suggestion is absent (not disabled) on a claim with no opposing pair | live, on a corpus claim measured at 0 opposed |
| 10 | Keyboard-only user can place, compare, and read the result | manual |
| 11 | Replay bench unchanged | `python scripts/replay_bench.py --all` — **this touches no pipeline stage, so any movement is a real regression** |

---

## 17. Next step

**Design review, then build, then verify. Nothing is built.**

Open: tab label confirmation only.
