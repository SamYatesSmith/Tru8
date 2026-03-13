# Track O — Premium Evidence Research Report

## Status: PLANNED
## Date: 2026-03-13

---

## Product Vision

A £5 per-report evidence research product that produces a 6-8 page consulting-quality PDF. Same pipeline, different output tier. The user submits a claim, pays £5 via Stripe, receives a structured evidence landscape report that no competitor produces.

**User flow:**
```
Landing page → Submit claim → Choose: Free check / Full Report (£5)
                                        ↓
               Free: standard pipeline → dashboard access
               Paid: deep pipeline → premium PDF delivered
```

**Revenue model:**
- Cost per report: ~£0.50 (LLM + search API costs)
- Price: £5.00
- Gross margin: 90%
- For £3K/month profit: ~670 reports = ~22/day

---

## Competitive Landscape

### What competitors produce

| Tool | Output | Price | Citation Accuracy |
|------|--------|-------|-------------------|
| ChatGPT Deep Research | 5-14K word prose essay | £1.50/report ($20/mo) | 85% |
| Perplexity Deep Research | ~1,300 word summary | £0.03-1.50/report ($20/mo) | 92% |
| Gemini Deep Research | 12K word report + charts | £1.50/report ($20/mo), charts at $250/mo | Unknown |
| Elicit | PRISMA-style academic review | £4-6/report ($12-79/mo) | High (sentence-level) |
| Grok DeepSearch | Minimal summaries | ~£2/report ($30/mo) | Low |

**Every competitor produces prose essays with inline citations.** None produce structured evidence landscapes.

### What Tru8 uniquely offers

1. **Structured claim decomposition** — claims broken into testable elements
2. **Evidence-to-element mapping** with explicit relationships (supports/challenges/context)
3. **Element states** mechanically derived from evidence, not LLM-opined
4. **Tier and type classification** — classified evidence landscape, not a source list
5. **Receipts** — every exclusion documented, no hidden curation
6. **Zero fabricated citations** — every source was actually fetched, read, classified
7. **Tamper-evident** — manifest signing, verification endpoint
8. **Orientation without verdict** — "we organise; you decide"

### Key competitor weakness

Hallucinated citations are the #1 complaint. 20-55% fabricated in studies. 206+ legal sanctions against attorneys for AI-hallucinated citations (as of July 2025). Tru8's evidence is real URLs, actually fetched — zero hallucination risk on sources.

---

## Report Structure (6-8 Pages)

### Page 1: Cover + Executive Summary

```
┌─────────────────────────────────────────────────────┐
│  TRU8  EVIDENCE RESEARCH REPORT           B794E659  │
│  13 Mar 2026                                        │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ "UK unemployment fell below 4%"                │  │
│  │  Source: User-submitted text                   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  HOW TO READ THIS REPORT                            │
│  This report decomposes claims into testable        │
│  elements and maps evidence by tier                 │
│  (primary/reporting/commentary) and type            │
│  (data/news/analysis/opinion/academic).             │
│  States indicate evidence direction, not truth.     │
│                                                     │
│  AT A GLANCE                                        │
│  2 claims · 4 elements · 17 sources                 │
│  ███████░░░ 7 primary                               │
│  ███████░░░ 7 reporting                             │
│  ███░░░░░░░ 3 commentary                            │
│  Tier × Type mini heatmap                           │
│                                                     │
│  EXECUTIVE SUMMARY (LLM synthesis)                  │
│  3-4 paragraphs: what the evidence shows,           │
│  key findings with citations, where evidence        │
│  conflicts, what's well-covered vs thin.            │
│                                                     │
│  KEY DATA POINTS (extracted table)                  │
│  ┌────────────────────────────────────────────────┐ │
│  │ Metric      │ Value │ Source    │ Date         │ │
│  │ UK unemp.   │ 5.2%  │ ONS [1]  │ Feb 2026     │ │
│  │ Youth rate   │ 14.0% │ ONS [1]  │ Feb 2026     │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Pages 2-5: Claim Sections (one per claim)

For each claim:
- Claim text + type badge
- **Element Analysis** — per-element:
  - Description + state badge + evidence counts
  - Relationship ratio bar (supports vs challenges vs context)
  - **Synthesis paragraph** explaining WHY this state was assigned, citing specific evidence with verbatim quotes
- **Conflicts & Tensions** — where evidence disagrees, both sides presented without resolution
- **Orientation** — existing orientation text
- **Evidence Sources** (full detail):
  - Title, URL, published date
  - Tier badge + Type badge + Content basis badge
  - **Full 1000-char snippet** (not 160-char truncation)
  - Relationship to elements (reasoning text from evidence_refs)
  - Archived URL link if available
  - Classification method indicator (LLM/heuristic)

### Page 6: Methodology + Coverage

- **Evidence Pipeline Funnel** (PRISMA-style, pure CSS):
  ```
  Sources searched:     32
          ↓
  Records identified:   47
          ↓
  Relevance scored:     38  → Excluded: 9 (receipts)
          ↓
  Classified:           29
          ↓
  Mapped to elements:   17  → Excluded: 12
  ```
- **Sources searched**: ONS, GOV.UK, Hansard, BBC, Serper (web), Exa (neural), + N more
- **Models used**: Gemini 2.5 Flash (mapping), GPT-4o (decomposition), Flash Lite (classification)
- **Coverage Assessment** (LLM synthesis): what's well-covered, what's thin, what data would strengthen
- **Known Unknowns**: bounty text / Seeker data if available

### Pages 7-8: Source Appendix

All sources numbered sequentially, grouped by tier:
- **PRIMARY (N)**: Full details — title, domain, type, date, URL, archived URL
- **REPORTING (N)**: Same format
- **COMMENTARY (N)**: Same format

### Footer (every page)

- "TRU8 · We organise; you decide."
- Disclaimer text
- Report ID + generation timestamp
- Pipeline fingerprint
- **Verification link**: "Verify: tru8.app/verify/B794E659"
- **Interactive link**: "Explore: tru8.app/check/B794E659"
- Page X of Y

---

## Synthesis Engine — Technical Design

### Architecture

Single-call per claim using Gemini 2.5 Flash (best grounding-to-cost ratio, 85.3% FACTS score, 1M context window). No map-reduce needed — pipeline caps at ~20 evidence items per claim, well within reliable single-call range.

### Three synthesis calls per report

| Call | Model | Input | Output | Cost |
|------|-------|-------|--------|------|
| Executive synthesis | Gemini 2.5 Flash | All claims + elements + evidence | Executive summary + key data points table | ~$0.02 |
| Per-claim analysis (×N) | Gemini 2.5 Flash | Claim + elements + evidence | Element analysis paragraphs + conflicts | ~$0.01/claim |
| Coverage assessment | Gemini 2.5 Flash | Pipeline metadata + landscape | Coverage narrative + known unknowns | ~$0.01 |

Total synthesis cost: ~$0.05 for a 2-claim report.

### Grounding Strategy

**Verbatim quote anchoring** — every factual claim must cite evidence by number AND include the exact phrase:
```
"All primary sources report unemployment at 5.2% [1,3,8]
("the UK unemployment rate increased by 0.2 percentage points to 5.2%")"
```

**Two-pass verification** for executive synthesis (highest-stakes call):
1. Generate synthesis with grounding rules
2. Self-verify: check each claim against original evidence, flag ungrounded statements

### Key Prompt Techniques

1. **"Synthesis not summary"** — explicitly distinguish in every prompt
2. **Anti-pattern listing** — no conversational markers, no hedging filler, no rhetorical questions
3. **Court reporter pattern** for conflict narration — record what each side says, never rule
4. **Alternating position order** in conflicts to prevent systematic bias
5. **U-shaped evidence ordering** — highest-relevance items at start and end of context
6. **CO-STAR framework** — Context, Objective, Style, Tone, Audience, Response format
7. **Structured data extraction** with verbatim_quote field for grounding verification

### Prompt Templates

#### Executive Synthesis
```
You are a senior research analyst producing a briefing for decision-makers.
You have {n} evidence items across {n_claims} claims.

EVIDENCE:
{evidence_block}

Produce an EXECUTIVE SYNTHESIS with these exact sections:

## Key Finding
One sentence: the single most important thing the evidence reveals.

## Evidence Landscape
- What is well-established (3+ independent sources agree)
- What is contested (sources directly conflict)
- What is thinly evidenced (1 source only)

## Key Data Points
| Metric | Value | Source | Date |
Extract every specific figure, date, statistic from the evidence.

## Conflicts
Where sources disagree, state each position with citations. Do not resolve.

RULES:
- Every factual claim must cite [E1]-[E{n}]
- Do not introduce information not in the evidence
- Formal analytical tone, third person, present tense
- No conversational markers, no hedging filler, no rhetorical questions
```

#### Per-Element Analysis
```
You are writing the analysis for one element of an evidence research report.

ELEMENT: {element_description}
STATE: {state} (derived from evidence mapping)
EVIDENCE MAPPED TO THIS ELEMENT:
{evidence_with_relationships}

Write a 2-3 sentence analytical paragraph explaining WHY this element has
state "{state}". Cite specific evidence items [E1]-[E{n}] and include
verbatim quotes where citing specific figures.

RULES:
- Open with a substantive claim, not a topic sentence
- Use "Source [E1] states..." for attributions
- If disputed, present both sides with equal weight
- Do not use "however" to transition (implies correction)
```

#### Conflict Narration
```
You are narrating a factual disagreement. Your role is that of a court
reporter: record what each side says, never rule.

For each disagreement:
1. STATE THE DISAGREEMENT in one sentence
2. POSITION A: What sources [EX] claim, using their language
3. POSITION B: What sources [EY] claim, using their language
4. FACTUAL DIFFERENCE: What specific fact differs?
5. POSSIBLE EXPLANATIONS: Different time periods, methodologies, definitions?

Present Position A and Position B in alternating order across disagreements.
```

#### Coverage Assessment
```
Assess evidential coverage for: "{claim}"

Elements with evidence counts:
{elements_with_counts}

For each element assess:
- Coverage level: Strong (3+ independent) / Moderate (2) / Thin (1) / Gap (0)
- Are sources independent or citing same origin?
- What specific evidence type would strengthen coverage?

Overall: What aspects have strong primary-source coverage? What relies on
commentary only? What data would a thorough researcher look for next?
```

### New Files

- `backend/app/pipeline/evidence_synthesiser.py` — synthesis logic + prompts
- `backend/app/models/synthesis.py` — ClaimSynthesis data model (or JSONB on Claim)

### Modified Files

- `backend/app/pipeline/runner.py` — insert SYNTHESISE stage after MAP
- `backend/app/models/check.py` — add synthesis JSONB field if needed

---

## Deeper Retrieval — Technical Design

### Exa.ai Integration

Run Exa neural search **in parallel** with existing Serper keyword search:

```
Current:  claim → keyword queries → Serper → fetch page → extract snippet
Deep:     claim → keyword queries → Serper ──────────┐
               → semantic queries → Exa (with content)┤→ merge + dedup → pipeline
```

Exa's `highlights` feature returns semantically relevant snippets + full text in one call. For Exa results, skip `_extract_from_page` entirely.

**Cost:** ~$0.007 per search-with-content. ~40 queries per deep report = ~$0.28.

**Exa strengths for Tru8:**
- Neural search finds semantically relevant content that keyword search misses
- `highlights` = semantic snippets (better than keyword-matched windows)
- `research_paper` category improves academic retrieval
- `auto` mode handles variety of query types (factual, conceptual, question-based)
- 81% accuracy on complex retrieval vs 71% for Tavily

**Exa limitations:**
- Weaker on government sources (.gov.uk) — existing API adapters remain essential
- 5-7x more expensive than Serper per query
- No replacement for specialist API adapters (ONS, FRED, Companies House)

### New File

- `backend/app/services/exa_search.py` — Exa API client

### Modified Files

- `backend/app/core/config.py` — EXA_API_KEY, ENABLE_EXA_SEARCH, EXA_MAX_RESULTS
- `backend/app/pipeline/retrieve.py` — add Exa as parallel search source
- `backend/app/pipeline/runner.py` — DEEP_CONFIG pipeline mode

### DEEP_CONFIG Pipeline Settings

| Setting | Full (current) | Deep (new) |
|---------|---------------|------------|
| max_queries_per_element | 3 | 5 |
| max_sources_per_claim | 20 | 35 |
| MAX_EVIDENCE_PER_DOMAIN | 3 | 5 |
| GLOBAL_MAX_PER_DOMAIN | 3 | 5 |
| LLM_RELEVANCE_MAX_EVIDENCE | 50 | 80 |
| max_wall_time_seconds | 180 | 300 |
| RECOVERY_MAX_CLAIMS | 3 | unlimited |
| RECOVERY_MAX_RESULTS_PER_ELEMENT | 8 | 12 |
| DISTIL_MAX_FACTS_PER_ITEM | 8 | 12 |
| enable_exa_search | false | true |
| enable_synthesis | false | true |

---

## Premium PDF Template — Technical Design

### Rendering

- **Engine:** WeasyPrint (keep existing — superior paged media support vs Playwright)
- **Font:** Inter via `@font-face` with local TTF files (matches web frontend)
- **Monospace:** JetBrains Mono for data elements
- **Page size:** A4 (210mm × 297mm), 2cm top/bottom, 1.8cm sides

### Visual Elements (all pure CSS — no SVG/JS dependency)

**Tier distribution bar (stacked horizontal):**
```css
.tier-dist { width: 100%; height: 8px; overflow: hidden; }
.tier-dist .seg { float: left; height: 8px; }
.seg-primary { background: #18181B; }
.seg-reporting { background: #71717A; }
.seg-commentary { background: #A1A1AA; }
```

**Relationship ratio bar:**
```css
.ratio-bar { width: 100%; height: 5px; overflow: hidden; }
.ratio-s { float: left; height: 5px; background: #16A34A; }
.ratio-c { float: left; height: 5px; background: #D97706; }
.ratio-x { float: left; height: 5px; background: #E2E8F0; }
```

**Tier × Type heatmap (mini):**
```css
.heat-cell { display: inline-block; width: 28px; height: 28px;
             text-align: center; line-height: 28px; font-size: 8px; }
.heat-0 { background: #FAFAFA; color: #D4D4D8; }
.heat-1 { background: #FFF7ED; color: #EA580C; }
.heat-2 { background: #FFEDD5; color: #EA580C; }
.heat-3 { background: #FB923C; color: #FFFFFF; }
```

**Evidence pipeline funnel (PRISMA-style):**
Pure HTML/CSS — stacked divs with connecting border, label left, count right.

### Typography Hierarchy

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Report title | Inter | 18px | 800 |
| Section headers | Inter | 11px | 700, uppercase, letterspaced |
| Claim text | Inter | 10px | 600 |
| Body / synthesis | Inter | 8.5px | 400 |
| Evidence snippets | Inter | 8px | 400 |
| Labels / metadata | Inter | 6.5px | 500, uppercase |

### Page Control

```css
.claim-section { page-break-inside: avoid; }
h2, h3, .section-header { page-break-after: avoid; }
p { orphans: 3; widows: 3; }

@page { @top-left { content: "TRU8"; } }
@page { @bottom-center { content: "Page " counter(page) " of " counter(pages); } }
@page :first { @top-left { content: none; } }
```

### Data Available But Currently Unused in PDF

| Data | Source | Now Rendered |
|------|--------|-------------|
| Full 1000-char snippets | Evidence.snippet | No (truncated to 160) |
| evidence_refs[].reasoning | claim_map | No |
| basis metadata | claim_map elements | No |
| archived_url | Evidence model | No |
| classification_method | Evidence model | No |
| content_basis | Evidence model | No |
| provider_status | Check model | No |
| raw_sources_count | Check model | No |
| bounty_text | claim_map elements | No |
| _compute_landscape() gaps | response_builder | No |
| factcheck_* fields | Evidence model | No |
| manifest / fingerprint | Check model | No |

All of these should be rendered in the premium template.

### New Files

- `backend/app/templates/pdf/premium_report.html` — new Jinja2 template
- `backend/static/fonts/Inter-*.ttf` — Inter font files
- `backend/static/fonts/JetBrainsMono-Regular.ttf` — monospace font

### Modified Files

- `backend/app/api/v1/checks.py` — new endpoint or parameter for premium PDF

---

## Cost Model

| Component | Standard Check | Deep Report |
|-----------|---------------|-------------|
| Serper queries | $0.04 | $0.05 |
| Exa queries | — | $0.28 |
| Decomposition (GPT-4o) | $0.02 | $0.02 |
| Mapping (Gemini Flash) | $0.04 | $0.04 |
| Classification (Flash Lite) | $0.01 | $0.01 |
| Distillation (Flash Lite) | $0.01 | $0.01 |
| Relevance scoring (GPT-4o-mini) | $0.02 | $0.03 |
| Synthesis (Gemini Flash) | — | $0.05 |
| API adapters | $0.00 | $0.00 |
| **Total** | **~$0.14** | **~$0.49** |

---

## Implementation Phases

### Phase 1: "Unlock What You Have" (2-3 days)

New `premium_report.html` template rendering all existing data:
- Full 1000-char snippets (not 160)
- Element reasoning from evidence_refs
- Methodology section from provider_status + raw_sources_count
- Source appendix grouped by tier
- PRISMA-style evidence funnel
- Inter font, improved typography, page break control
- Mini tier × type heatmap
- Verification link + interactive dashboard link
- "How to Read This Report" explainer

**No pipeline changes. Pure presentation. Immediate quality improvement.**

### Phase 2: "Synthesis Layer" (3-4 days)

- New `evidence_synthesiser.py` module
- Executive summary generation (verbatim quote anchoring)
- Per-element analysis paragraphs
- Structured data extraction (figures → table)
- Conflict narration (court reporter pattern)
- Coverage assessment
- Store synthesis output on Claim model (JSONB)
- Wire into premium template

### Phase 3: "Deeper Retrieval" (3-4 days)

- `DEEP_CONFIG` pipeline mode
- Exa.ai search adapter (parallel with Serper)
- Higher caps across retrieval/scoring/recovery
- More aggressive coverage recovery
- `enable_exa_search` flag on PipelineConfig

### Phase 4: "Payment + UX" (2-3 days)

- Stripe one-off payment for £5 report
- "Download Full Report" button on check detail page
- Deep pipeline trigger after payment confirmation
- Email delivery when report ready (deep pipeline ~3-5 min)
- Receipt / invoice generation

---

## Quality Signals to Target

Based on DRACO evaluation framework (Perplexity's benchmark):

1. **Factual accuracy** — zero fabricated citations (structural advantage)
2. **Completeness** — 30+ source categories searched, PRISMA accounting
3. **Objectivity** — conflicts surfaced not resolved, "we organise; you decide"
4. **Citation quality** — every source real, classified, mapped to elements

---

## Research Sources

### Architecture & State of the Art
- Stanford STORM (NAACL 2024) — multi-perspective conversation for research
- DRACO benchmark (arXiv 2602.11685) — evaluation framework for deep research
- Chroma "Context Rot" research — LLM context window degradation patterns
- VeriFact-CoT (arXiv 2509.05741) — citation verification chain
- LLMxMapReduce (arXiv 2410.09342) — structured multi-document processing

### Competitive Intelligence
- ChatGPT Deep Research: $20-200/mo, prose essays, 85% citation accuracy
- Perplexity Deep Research: $20/mo, 92% citation accuracy, no PDF export for Pages
- Gemini Deep Research: $20-250/mo, charts at premium tier, export issues
- Elicit: $12-79/mo, PRISMA-style, academic-focused
- Manus AI: consulting-quality visual reports (the design benchmark)

### Technical Implementation
- WeasyPrint: flexbox supported (v52.5+), custom fonts (TTF/WOFF2), CSS page breaks
- Exa.ai: neural search $5-7/1K queries, `highlights` feature, `auto` mode
- Gemini 2.5 Flash: 85.3% FACTS Grounding score, 1M context, $0.15/$0.60 per M tokens
- Synthesis prompting: anti-pattern listing, verbatim anchoring, U-shaped ordering
