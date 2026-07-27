# Evidence Philosophy: LOCKED

**Date:** 2026-02-16
**Status:** LOCKED (amended 2026-02-17: added Principle 5 + Navigation section). Canonical reference for all pipeline and frontend decisions.

---

## Mission

> "Tru8 gathers broad evidence around a claim, labels it transparently, and lets you view it four ways: the Cartographer, the Librarian, the Interpreter, and the Projectionist. We don't silently bury sources or score outlets into invisibility. We organise; you decide."

---

## Principles

### 1. No hidden curation.

Tru8 will deduplicate, drop pages that return zero content, and classify sources. That is curation. The rule is: **nothing happens silently.** Every decision has a receipt. Every excluded item has a reason. The user can always ask "what didn't I see?" and get an answer.

### 2. Classify, don't score.

The 50-tier credibility scoring system is **deleted.** No outlet gets a numerical authority score. Sources are classified on two descriptive axes — tier (proximity to the original information) and type (nature of the content). These are descriptions, not judgments. The user decides what to trust.

### 3. Show everything we find.

"As much relevant evidence as we can find, with transparent logging of what we did and didn't include." Not "every piece" — that's a promise we'd break daily. We cast a wide net, we show what we catch, and we're honest about how we fished.

### 4. The user controls the view.

Same evidence corpus, four views. Three for text evidence (Cartographer, Librarian, Interpreter), plus the Projectionist for video context. The user moves between them depending on what they need.

### 5. The user decides what to investigate.

When a URL produces multiple claims, the pipeline pauses and presents them. The user selects which claims to research. We don't silently decide for them.

**Entry mode branching:**
- **URL / article input:** Pipeline extracts claims, presents them, pauses. User selects. Pipeline resumes with selected claims only.
- **Text input:** The user wrote the claims themselves. No pause, no selection gate. All claims proceed.

This extends Principle 4: the user controls not just how results are displayed, but what gets investigated in the first place.

---

## Four Views

### The Cartographer

> "What's the shape of the conversation?"

**Output: Citation Cascade.** A tiered visualisation flowing top-to-bottom: primary sources at the apex, reporting in the middle, commentary at the base. Connection lines show derivation — when 5 articles all cite one dataset, the user sees ONE node connected to 5 below. The apparent breadth reveals itself as narrow.

- Convergence zones — multiple sources confirming the same facts (orange diamond)
- Divergence points — sources directly contradicting each other (amber, dashed)
- Lone signals — uncorroborated claims from a single source
- The gaps — elements where no source has anything to say (dotted outline)
- Derivation chains — 7 articles all citing one primary dataset is one data point, not 7

This is the **landing view** — the first thing the user sees when a check completes.

### The Librarian

> "Show me the full set, clearly labelled."

**Output: Tier x Type Heatmap + Evidence Ledger.** A 3x6 grid (tiers x types) where cell intensity shows evidence density — the "fingerprint" of the evidence landscape. Below it, a filterable ledger of every source with tier badge, type badge, title, metadata, and excerpt. Nothing hidden by default. The receipt disclosure section ("What we didn't include") lives here.

### The Interpreter

> "Answer this specific sub-question."

**Output: Evidence Disposition Panel.** Element-level focus. Pick one element of the claim. The Disposition Bar — a horizontal bar split proportionally between supports (emerald), challenges (amber), and context (slate) — shows the weight of evidence at a glance. Below it, evidence grouped into three columns by relationship. The bar is a count, not a score.

### The Projectionist

> "What's being said about this on camera?"

**Output: Video Context.** A capped, classified selection of YouTube videos providing context for the claim in a different medium. Max 5 videos per claim. Not part of the evidence pipeline — a standalone recommendation feature that runs as a parallel task once claims are known. Videos are retrieved via YouTube Data API based on claim text, not through the evidence retrieval pipeline.

The Projectionist uses the same visual classification language (tier + type badges) but classification is a lightweight heuristic based on channel metadata, not the pipeline's LLM classifier. A Reuters YouTube explainer is labelled T2/News. A government press conference upload is labelled T1/Official. The labels describe what the content IS — same principle as text evidence, different execution path.

**Why this is separate from the pipeline:** Text evidence goes through retrieval → filtering → classification → mapping. Video recommendations serve a different purpose — they provide multimedia context, not source material for claim analysis. They don't participate in the Cartographer's citation cascade, the Librarian's ledger, or the Interpreter's disposition panel. They have their own view.

### ~~The Jeweller (Detail Panel)~~ — DROPPED (2026-02-23)

*Feature dropped. Evidence clicks open the source URL directly. All relevant metadata (tier, type, elements, dates) is already visible on evidence cards across all views.*

---

## Navigation: Overview → Detail

One check may contain multiple claims. The results are structured in two levels.

### Overview (Level 1)

The landing page after analysis completes. Shows all claims from this check:
- **Claim cards:** Each claim's normalised text, type badge, element count, orientation summary. The claim card IS the selector — click to drill in.
- **Check-wide Cartographer:** All evidence across all claims, visualised as a single Citation Cascade. The "shape of the whole conversation."
- **Check-wide Librarian:** All evidence pooled, one Tier × Type heatmap, one ledger. "Everything we found."
- **Check-wide Projectionist:** Video context across all claims. Up to 5 videos total.

### Detail (Level 2)

Per-claim focus. Four views — Cartographer, Librarian, Interpreter (all scoped to one claim's evidence), and Projectionist (videos for this claim). This is where the user does deep work on a specific sub-question.

Back button returns to Overview. The user moves between claims freely.

### Why This Structure

A single-claim check lands directly at Detail. A multi-claim check lands at Overview. The overview prevents the "first claim gets all the attention" problem — every claim is visible and equally accessible. The overview also doubles as the claim selector, eliminating the need for a separate navigation widget.

---

## Classification System

### Tier: Proximity to the Original Information

Not reputation. Not popularity. Not editorial quality. How close is this source to the thing being claimed?

| Tier | Definition | Examples |
|------|-----------|----------|
| **1: Primary** | The thing itself. The data, the statement, the filing, the dataset. The source that other sources cite. | Government data, official statements, court filings, original research, raw statistics, primary documents |
| **2: Reporting** | Someone investigated, interviewed, verified. Journalism. | News organisations, investigative outlets, specialist correspondents, field reporting |
| **3: Commentary** | Interpretation of primary sources or reporting. Valuable context, further from the raw evidence. | Op-eds, analysis, editorials, blog posts, think-tank output |

A Tier 1 government dataset from a questionable government is still Tier 1. A BBC opinion column is still Tier 3. The tier describes proximity, not quality.

### Type: Nature of the Content

| Type | What It Is |
|------|-----------|
| **Data / Statistics** | Numbers, datasets, measurements |
| **Official Statement** | Press releases, government communications |
| **News Reporting** | Event coverage, investigation |
| **Analysis / Explainer** | In-depth contextual pieces |
| **Opinion / Editorial** | Stated perspective |
| **Academic / Research** | Peer-reviewed, studies |

### The Grid

Every evidence item gets a position. The position is a description, not a judgment.

| Example | Tier | Type |
|---------|------|------|
| ONS employment statistics | 1 | Data |
| Downing Street press release | 1 | Official Statement |
| Reuters breaking news report | 2 | News Reporting |
| Guardian long-read investigation | 2 | Analysis |
| Nature peer-reviewed study | 1 | Academic |
| Think-tank policy paper | 3 | Analysis |
| Blogger's reaction piece | 3 | Opinion |
| Daily Mail news article | 2 | News Reporting |

The Daily Mail reporting on a government announcement is Tier 2 / News Reporting — same classification as Reuters reporting on the same announcement. The tier and type describe what the content IS, not who published it.

---

## The Trust Engine: Receipts

Every evidence item that enters the pipeline gets a status:

```
found → extracted → deduped → relevance-checked → excluded (with reason) → shown
```

Exclusion reasons are mechanical or factual, never editorial:
- **Extraction failed:** Page returned no readable text
- **Duplicate:** Identical content already included from another URL
- **Satire:** Source is intentionally fictional (The Onion, Babylon Bee)
- **Irrelevant:** Content is not about this claim or its elements (with explanation)

That's the complete exclusion list. No outlet-level blocking. No credibility thresholds. No domain caps that silently remove sources.

**The irrelevant exclusion** requires explanation. A 2018 paper on atmospheric chemistry is not relevant to a specific Feb 2026 executive order. Excluding it is not editorial — it's the basic job of a search engine. The distinction:
- "This source is untrustworthy" → editorial judgment → **never excluded for this reason**
- "This source is not about this claim" → factual assessment → **excluded with receipt**

Irrelevant exclusions appear in the receipt disclosure alongside all other exclusions. The user sees what was found and why it was set aside. They can always review the excluded items and disagree with the relevance judgment. Nothing is hidden.

---

## Intelligence vs Editorial

Two layers operate on evidence in the pipeline. They are different things and must not be confused.

### Editorial layer (DELETE)

Decisions about **who** published something. Outlet reputation scores, domain blacklists, credibility tiers based on the publisher's name. These are value judgments. Tru8 does not make them. The user does.

### Intelligence layer (FIX and KEEP)

Decisions about **what** was published and whether it relates to the claim being researched. Relevance filtering ("is this about this topic?"), temporal relevance ("is a 2018 paper relevant to a 2026 event?"), deduplication ("is this the same article from another URL?"), and text extraction quality ("did we actually get the content?"). These are factual assessments, not value judgments.

The current pipeline conflates these two layers. The credibility score influences which evidence survives the per-claim cap. The LLM relevance scorer prompt judges "source authority" alongside topical relevance. The auto-exclude list blocks entire outlet categories. All of this must be untangled:

- **Editorial decisions → deleted.** No exceptions.
- **Relevance decisions → fixed and kept.** The relevance scorer must work (it currently returns nothing), must judge topical relevance only (not source quality), and must produce a receipt for every exclusion.
- **Retrieval quality → improved.** Query planner generates less noise. Academic APIs filter by date proximity. FactCheck API results get their text extracted. Less garbage in = less garbage to filter out.

---

## What Gets Deleted

| Component | Status | Reason |
|-----------|--------|--------|
| `source_credibility.json` (50 tiers, 2,340 domains) | **DELETE** | Replaced by Tier + Type classification |
| `_get_credibility_score()` in retrieve.py | **DELETE** | No more numerical outlet scoring |
| `credibility_score` field on evidence | **DELETE** | Replaced by `tier` and `type` fields |
| `final_score = base × credibility × recency` formula | **DELETE** | No more credibility-weighted ranking |
| Auto-exclude list (social media, state media, tabloids) | **DELETE** | Only satire excluded |
| Global domain cap (max 3 per domain) | **DELETE** | No more hidden caps |
| Per-claim credibility-weighted cap (top 20 by final_score) | **REDESIGN** | Cap by count if needed, but not by credibility ranking |
| LLM relevance scorer prompt | **REWRITE** | Currently judges "source authority" (editorial). Rewrite to pure topical relevance only. Must actually return scores (currently broken — returns nothing). |
| `domain_status.json` (2,340 domains) | **KEEP** | Useful for extraction success/failure tracking, not for editorial scoring |
| Content deduplication | **KEEP** | Mechanical, not editorial |
| Corroboration detection | **KEEP** | Convergence/divergence is a landscape signal, not an editorial judgment |

---

## What Gets Built

| Component | Purpose |
|-----------|---------|
| **Tier classifier** | LLM assigns Tier 1/2/3 to each evidence item based on content proximity |
| **Type classifier** | LLM assigns content type (Data, Official, News, Analysis, Opinion, Academic) |
| **Receipt log** | User-visible audit trail: found → extracted → deduped → excluded (reason) → shown |
| **The Cartographer** | Citation Cascade — tiered derivation visualisation (Dagre layout engine + custom SVG) |
| **The Librarian** | Tier x Type Heatmap + Evidence Ledger — filterable collection with receipt disclosure |
| **The Interpreter** | Evidence Disposition Panel — element-level focus with disposition bar + grouped evidence |
| **The Projectionist** | YouTube video context — standalone recommendation feature, max 5 videos per claim, lightweight classification by channel metadata |
| ~~**The Jeweller**~~ | ~~Slide-in detail panel for any evidence item~~ — DROPPED (2026-02-23) |
| **Relevance scorer (rewritten)** | Pure topical relevance: "Is this evidence about this claim?" No source quality judgment. Exclusions produce receipts. |
| **Query planner (tightened)** | 1-2 queries per element (down from 2-4). Less noise at source, less redundancy. |
| **Academic API temporal filter** | CrossRef/SemanticScholar/OpenAlex results filtered by date proximity to claim. A 2018 paper is not relevant to a 2026 event. |
| **FactCheck text extraction** | When Google Fact-Check API returns a URL, fetch and extract the article content. No more evidence with zero text. |

---

## The Decision Test

Every engineering decision gets tested against this:

1. **Does this hide something from the user without telling them?** Don't do it.
2. **Does this classify or does this judge?** If it judges, rethink it.
3. **Does this help the Cartographer, the Librarian, the Interpreter, or the Projectionist?** If none, why are we building it?
4. **Would this survive the question "what didn't I see?"** If not, add a receipt.

---

## What This Document Is Not

This is not a design spec, a technical plan, or a sprint backlog. This is the **why.** The engineering tracks that follow will define the how and the when. But every decision in those tracks must pass the tests above.

The pipeline as it exists today was built for a verdict platform. Tru8 is not a verdict platform. The pipeline must be rebuilt for what Tru8 actually is: an evidence landscape that the user navigates, not a curated list that Tru8 controls.
