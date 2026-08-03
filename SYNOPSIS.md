# Tru8 — Product & Pipeline Synopsis

*For external review. Updated 2026-03-09.*

---

## 1. What Tru8 Is

Tru8 is an evidence research platform. A user submits a URL or a plain-text claim. The system extracts verifiable assertions, retrieves evidence from the open web and specialist APIs (web search, government APIs, academic databases, fact-check registries), classifies each piece by proximity and content type, maps evidence to sub-components of each claim, and presents the result through six specialised views.

**The core philosophy: "We organise; you decide."** Tru8 does not render verdicts. It does not score source credibility. It classifies sources by **Tier** (primary / reporting / commentary) and **Type** (data / official / news / analysis / opinion / academic), maps their relationship to each claim element (supports / challenges / context), and shows everything it excluded and why (receipts). The user draws their own conclusions.

---

## 2. Who Buys It

### Human Market

| Segment | Use Case | Price Point |
|---------|----------|-------------|
| Journalists / researchers | Pre-publication evidence mapping — "what's the full landscape on this claim?" | $7/mo (40 checks) |
| Policy analysts / legal teams | Regulatory claim verification, legislative evidence trails | $29/mo (200 checks) |
| Enterprises (newsrooms, compliance) | Bulk evidence research with SLA | Custom |
| Casual users | Trial exploration | Free (3 lifetime checks) |

The human product is a dashboard with six evidence views (see §5). Value proposition: what would take a researcher hours of source-hunting is returned in 60–120 seconds, structured and classified.

### Agent Market

| Segment | Use Case | Payment Rail |
|---------|----------|-------------|
| AI agent developers | Evidence retrieval as a tool call — agents building on Claude/GPT/Gemini that need grounded evidence | API key + prepaid credits |
| MCP-connected models | Claude Desktop / any MCP host discovers Tru8 as a tool, calls it autonomously | API key via MCP config |
| Crypto-native autonomous agents | Fully permissionless evidence lookup — wallet is identity, USDC is payment | HTTP 402 (x402 protocol) |

**Agent pricing is per-request micro-payments:**

| Tier | Price | Speed | What It Does |
|------|-------|-------|-------------|
| Lookup | $0.02 | Instant | Returns a cached prior analysis (exact claim match) |
| Quick | $0.07 | ~15s | Web search only, heuristic classification (93.7% accuracy), no API adapters |
| Full | $0.15 | ~90s | Complete pipeline — web + specialist APIs, LLM classification, element decomposition, coverage recovery |

The MCP server auto-escalates: lookup → quick → full, charging only for the tier actually executed.

### Quality Expectations by Market

**Human users** care about comprehensiveness and presentation. They want to see the full landscape — all sides, properly classified, with nothing hidden. Missing a key government dataset or academic paper is a failure. They tolerate 60–120s wait times.

**Agent users** care about structured accuracy and speed. They consume JSON, not views. A misclassified tier or a hallucinated evidence-to-element mapping corrupts their downstream reasoning. Quick-mode agents need reliable results in <15s. Full-mode agents need the same comprehensiveness humans expect, but in machine-readable form.

---

## 3. Pipeline Architecture

Two-phase pipeline with an optional user gate between phases:

```
Phase 1 (user submits URL or claim):
  INGEST       → Fetch page / OCR image / process transcript
  EXTRACT      → LLM atomises content into ≤12 verifiable claims
  RANK         → Classify article domain + rank claims by significance
  [PAUSE]      → Article mode: user selects which claims to investigate

Phase 2 (per selected claim):
  FACTCHECK    → Google Fact-Check API lookup
  DECOMPOSE    → LLM breaks each claim into 1–5 testable elements
  RETRIEVE     → Parallel multi-source evidence retrieval
  SCORE        → LLM relevance scoring (topical only, 1–5 scale)
  CLASSIFY     → LLM assigns Tier + Type to each evidence item
  MAP          → LLM maps evidence → elements (supports/challenges/context)
  ORIENT       → Mechanical derivation of claim orientation from element states
  RECOVER      → Targeted re-search for unresolved elements

Post-pipeline (fire-and-forget):
  - YouTube video recommendations (max 5/claim)
  - Wayback Machine archiving of all evidence URLs
```

### LLM Call Inventory (per full-mode check)

| Stage | Primary Model | Fallback | Temp | Purpose |
|-------|--------------|----------|------|---------|
| Extract | Gemini 2.5 Flash Lite | GPT-4o-mini | 0.1 | Atomise content → claims (questions accepted via implicit claim extraction) |
| Rank | Gemini 2.5 Flash Lite | GPT-4o-mini | — | Claim significance ordering |
| Query Plan | Gemini 2.5 Flash Lite | GPT-4o-mini | — | Generate per-element search queries |
| Decompose | Gemini 2.5 Flash Lite | GPT-4o | 0.2 | Claim → 1–5 elements |
| Score | Gemini 2.5 Flash Lite | GPT-4o-mini | 0.1 | Topical relevance 1–5 |
| Classify | Gemini 2.5 Flash Lite | GPT-4o-mini | 0.1 | Tier + Type labels |
| Map | Gemini 2.5 Flash (thinking) | GPT-4o | 0.2 | Evidence → element mapping (1000-char snippets) |
| Query (optional) | Gemini 2.5 Flash Lite | GPT-4o-mini | 0.2 | Answer user's specific question |

**Total: 6–10 LLM calls per check.** Most stages use Gemini Flash Lite (cost/speed optimisation). The highest-stakes call — mapping — uses Gemini 2.5 Flash (thinking model) with GPT-4o fallback. Mapping operates on 1000-character evidence snippets with tier/type/content_basis metadata.

### Evidence Sources (30+)

**Web search** (fallback chain): Serper.dev → Brave Search → SerpAPI

**Structured API adapters** (priority-tiered, domain-routed):

| Domain | Sources |
|--------|---------|
| Government | GOV.UK, Hansard, GovInfo, Companies House, ONS |
| Legal | UK Legislation (legislation.gov.uk), GovInfo |
| Economic | FRED, Marketaux, World Bank |
| Academic | Semantic Scholar, OpenAlex, PubMed |
| Health | WHO, PubMed |
| Climate | NOAA, WeatherAPI, Open-Meteo, GBIF |
| Archives | Wikipedia, Library of Congress, Internet Archive |
| Business | Companies House, Wikidata |
| Sports | Transfermarkt, Football-Data.org |
| Video | YouTube Data API |
| Fact-check | Google Fact-Check Explorer |

Adapters are selected via a 3-tier priority system: T1 domain specialists, T2 cross-domain academic, T3 general reference. Wikipedia results trigger **reference mining** — following citations to their original authority sources.

---

## 4. Data Model (What Gets Stored)

```
Check
 ├── status: pending → processing → waiting_for_selection → completed
 ├── entry_mode: focused (single claim) | article (URL with multiple claims)
 ├── initiated_via: dashboard | api_key | agent_x402 | agent_skyfire | agent_credit
 ├── executed_tier: quick | full (agent checks only)
 └── Claims[] (up to 12)
      ├── claim_text, claim_type (5 taxonomy), significance_rank
      ├── claim_text_hash (SHA256 fingerprint for cross-check matching)
      ├── ClaimMap
      │    ├── normalised_claim
      │    ├── claim_type: empirical | definitional | causal | predictive | normative
      │    ├── elements[] (1–5)
      │    │    ├── element_id, description
      │    │    ├── evidence_refs[] ← SOURCE OF TRUTH
      │    │    │    ├── evidence_id, relationship (supports/challenges/context)
      │    │    │    └── reasoning
      │    │    ├── state: supported | disputed | unresolved
      │    │    ├── basis (evidence_count, tier/relationship/classification/content_basis breakdowns)
      │    │    ├── uncertainty (text)
      │    │    └── bounty_text (research brief for unknowns)
      │    ├── orientation (mechanical: derived from element states, evidence-centred language)
      │    └── orientation_basis (total_elements, state_distribution)
      └── Evidence[]
           ├── source, url, title, snippet, published_date
           ├── evidence_id (SHA256 hash, stable cross-ref key)
           ├── tier: primary | reporting | commentary
           ├── evidence_type: data | official | news | analysis | opinion | academic
           ├── content_basis: full | snippet | api | pdf
           ├── classification_method: llm | heuristic | llm+override
           ├── llm_relevance_score, llm_relevance_rationale
           ├── receipt_status: found → extracted → classified → excluded | shown
           ├── exclusion_reason (if excluded)
           ├── archived_url (Wayback Machine)
           └── external_source_provider (which API adapter produced this)
```

Every piece of evidence that was considered but excluded is stored in a `RawEvidence` table with `filter_stage` and `filter_reason` — full audit trail.

---

## 5. The Six Views (What Users See)

| View | Metaphor | Question It Answers | Level |
|------|----------|-------------------|-------|
| **Cartographer** | Citation Cascade | What shape is the evidence landscape? | Overview + Detail |
| **Librarian** | Tier×Type Heatmap + Ledger | What's the full set, properly labelled? | Overview + Detail |
| **Interpreter** | Disposition Panel | What does the evidence say about this element? | Detail only |
| **Projectionist** | Video Grid | What's been said on camera? | Overview + Detail |
| **Chronologist** | Timeline | When did the evidence appear? | Overview + Detail |
| **Seeker** | Unknowns Ledger | What don't we know yet? | Detail only |

Cross-cutting features: Diagnostic Value Highlighter (Analysis of Competing Hypotheses toggle), URL-persisted view state, auto-archive links, receipt disclosure on every view.

---

## 6. Known Quality Bottlenecks

These are the points in the pipeline where quality of return is most at risk, ranked by impact:

### A. Content Truncation at Extraction

**The problem:** Input content is truncated to **2,500 words** before the extraction LLM call. A 5,000-word article loses its entire second half. Claims from the bottom of a long article are never extracted.

**Impact:** Unrecoverable. Claims that aren't extracted can't be investigated. For long-form journalism, investigative reports, and legal documents, this is a significant blind spot.

### B. Relevance Scoring Cap

**The problem:** The LLM relevance scorer processes a maximum of **50 evidence items** across all claims. A check with 5 claims averaging 15 items each = 75 items. The excess 25 pass through **unscored** and proceed to the mapper regardless of relevance.

**Impact:** The mapper receives a mix of relevant and potentially irrelevant evidence, increasing noise and potentially crowding out better items within the per-claim cap (20 items).

### C. Timeout Cascade

**The problem:** Three independent hard timeouts can each truncate results:
- 45s per-claim retrieval timeout (partial evidence if exceeded)
- 180s total retrieval wall time
- 45s analyze/mapping timeout (check fails entirely if exceeded)
- 20s coverage recovery timeout

**Impact:** Checks about obscure or complex topics — which need the most evidence — are the most likely to hit timeouts and get the least evidence.

### D. Content Extraction Failures

**The problem:** 2,778 tracked domains show 538 bot-blocked, 15 paywalled, 15 JS-required. When full content extraction fails, the system falls back to **search snippets** (typically 150–200 characters). The `content_basis` field now tracks this (full/snippet/api/pdf), but the mapper still processes all evidence identically regardless of content quality.

**Impact:** Evidence from major paywalled sources (NYT, FT, WSJ, Bloomberg) is represented by search snippets only. The `content_basis` metadata is available for downstream consumers to weight accordingly.

### E. Orientation Has No Quality Weighting

**The problem:** The orientation line is derived by counting element states (supported / disputed / unresolved). A claim with 2 supported elements and 1 disputed element gets the same orientation formula regardless of whether the supporting evidence is Tier 1 government data or Tier 3 blog commentary. The `orientation_basis` dict and per-element `basis` metadata are now exposed, enabling consumers to make their own assessments.

**Impact:** The orientation is a headline signal for both human and agent users. Without evidence-quality weighting, it can be misleading — but the structured basis metadata allows sophisticated consumers to re-derive.

---

## 7. Architecture Strengths

To be clear about what's working well:

- **Receipt system** — full audit trail of every exclusion, visible to users. Rare in the industry.
- **Element decomposition** — breaking claims into testable sub-assertions is a genuine differentiator. Most competitors treat claims as monolithic.
- **Element basis metadata** — per-element transparency on evidence count, tier/relationship/classification/content_basis breakdowns. Agents can assess determination quality programmatically.
- **Source diversity** — web search plus priority-tiered, domain-routed API adapters. Not just web search.
- **Six views** — each answers a different analytical question. Not just a list of links.
- **Dual-market architecture** — same pipeline serves both human dashboard and agent API with appropriate pricing and auth for each.
- **Three-tier agent commerce** — lookup (instant, $0.02), quick (~15s, $0.07), full (~90s, $0.15) with three payment rails.
- **Pipeline break** — article mode pauses for user claim selection. Respects user agency.
- **Cross-claim URL dedup** — prevents the same source appearing against every claim.
- **Coverage recovery** — automatic re-search when elements remain unresolved, with cross-element mapping.
- **Content basis tracking** — end-to-end transparency on what the pipeline actually obtained per evidence item.
- **Provenance persistence** — classification method, LLM relevance scores, and content basis stored to DB.
- **Fire-and-forget archiving** — Wayback Machine preservation of evidence URLs.
- **Idempotent stages** — pipeline can resume/replay without side effects.
- **Heuristic classifier accuracy** — 93.7% tier+type accuracy on URL patterns alone (Quick mode).

---

## 8. Remaining Quality Investigation Areas

Areas where further improvement could increase output reliability:

1. **Extraction window** — Would a smarter truncation strategy (e.g., extract from beginning + end, or chunk-and-merge) capture claims from long articles without doubling the LLM call?

2. **Relevance scoring threshold** — Currently only score-1 items are excluded. Would raising the threshold to exclude score-2 items (same general domain, different specific topic) reduce noise for the mapper?

3. **Orientation weighting** — Would incorporating evidence tier into the orientation derivation (e.g., a Tier 1 challenge outweighs three Tier 3 supports) produce a more reliable headline signal? The `basis` metadata already exposes the data needed — this is a formula change in one function. Counter-argument: this introduces Tru8's judgement about source weight, which may conflict with "we organise; you decide."

4. **Batch mapping token budget** — Would splitting the batch mapping into per-claim calls by default (accepting the latency cost) reduce output truncation and improve mapping completeness?

5. **Content-basis-aware mapping** — Would the mapper benefit from weighting full-content evidence more heavily than snippet-only evidence? The `[Content: ...]` tag is already in the prompt, but the mapper doesn't explicitly differentiate.

---

*Document generated from codebase analysis. All constants, architecture claims, and model references verified against source as of 2026-03-09.*
