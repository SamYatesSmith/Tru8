# Claude Code — Tru8 Report Quality Investigation (Root Cause Research Prompt)

You are Claude Code acting as a senior engineer brought in to investigate a trust/accuracy issue in Tru8’s “Truth Reports”.

## Context
Tru8 generates user-facing verification reports by:
- extracting multiple claims from an article
- retrieving sources
- scoring each claim (Supported / Uncertain / Contradicted / Insufficient)
- rendering a PDF-style report that shows “Evidence Sources” per claim

We recently deployed to family & friends beta testers. Some reports look strong; others show sources that are **topically related but not actually evidential** to the *specific* claim text (e.g., timestamps, numbers, legal references). We need to understand **why** this happens in the current codebase and whether we already have mechanisms intended to prevent it that are failing or misconfigured.

## What was observed (symptoms)
1) “Evidence Sources” sometimes include citations that do not directly support the claim (citation laundering risk).
2) Confidence can appear too high relative to the evidence fit.
3) The system performs much better on “widely reported” claims than on:
   - timestamp/authenticity claims (specific post at a specific time)
   - numeric/stat claims (exact numbers/dates)
   - legal/EO claims (requires primary legal text)
   - publication metadata claims (publisher date/author/page metadata)

## Objective
Run a **root-cause investigation** to answer:
- Do we already compute relevance/similarity and/or entity matching?
- Do we already have gating/filters for “what gets displayed as evidence”?
- Do we already distinguish “context sources” vs “direct evidence” anywhere?
- Are claim typing / retrieval recipes already present?
- If these mechanisms exist, **why are they not working** (bug, thresholds, wrong field used, ordering mistake, display layer ignoring filters, caching, etc.)?
- If they don’t exist, identify the most minimal additions required.

---

# Your tasks (investigation-first)

## 1) Map the current pipeline (high-level, but file-accurate)
Locate and document the exact flow and the files responsible for each stage:
- claim extraction
- retrieval/query building
- source ranking / similarity scoring (if any)
- verdict computation
- confidence computation
- selection of sources for display
- report/PDF rendering

**Deliverable:** `docs/investigations/report_quality_pipeline_map.md`
Include a bullet list of modules/files and a short “data flow” explanation.

## 2) Locate existing “anti-laundering” logic (if present)
Search for any of the following concepts in the codebase and record what you find:
- similarity score / embeddings / cosine / relevance score
- thresholds for inclusion/exclusion
- “top k” selection logic
- entity extraction / NER / keyword overlap
- domain tiering / authority weighting
- source deduplication / canonicalisation
- claim classification / claim types
- logic that labels sources as evidence vs context (or similar)
- any config/env vars controlling thresholds

**Deliverable:** add a section to the same doc listing:
- where each mechanism lives
- what it *intends* to do
- what it actually does (based on code)

## 3) Reproduce the failure mode with a controlled trace
Instrument or simulate one problematic run to see exactly why irrelevant sources are displayed:
- pick one of the “hard” claim types (timestamp / numeric / legal)
- run the pipeline locally (or via test harness)
- dump intermediate artifacts per claim:
  - extracted claim text
  - generated queries
  - retrieved candidates (titles/snippets/urls)
  - similarity/relevance scores (if computed)
  - entity matches (if computed)
  - which sources were selected as “evidence”
  - how the final verdict/confidence was computed
  - what the renderer displays

If no easy harness exists, create a minimal script under `scripts/` that runs a single URL through the pipeline and prints JSON traces.

**Deliverable:** `docs/investigations/report_quality_trace.md` + any script you create.

## 4) Identify the actual causes (not guesses)
Based on (2) and (3), produce a short root-cause list. Examples of what we’re looking for:
- relevance scores exist but renderer ignores them
- thresholds are too low / not applied to display
- scores are computed on the wrong text (article-level not claim-level)
- entity extraction fails on numbers/dates so mismatches slip through
- source ranking uses authority heavily and relevance lightly
- “top-k” always returns something, even if low similarity
- confidence uses candidate count rather than “eligible evidence”
- caching returns stale candidate sets
- claim typing exists but isn’t wired into retrieval

**Deliverable:** `docs/investigations/root_causes.md`
Each cause should include: file/function references + the exact logic that produces the symptom.

## 5) Propose the smallest fixes that address the causes
Only after identifying root causes, propose patches. Keep them minimal and incremental.

Your proposal must include:
- what to change
- where to change it
- why it fixes the root cause
- how to test it
- whether it needs feature flags to avoid disrupting beta

**Deliverable:** `docs/investigations/fix_plan.md` with an ordered list of PR-sized changes.

---

# Investigation guidance (don’t skip)
- Assume the system may already have “relevance” logic; the bug may be *wiring*, *thresholding*, or *presentation*.
- Treat “showing sources” and “using sources for scoring” as two different steps—verify both.
- Pay special attention to claim-level vs article-level operations.

---

# Output format
Keep docs concise and practical. Prefer tables like:

| Stage | File(s) | Key functions | Inputs | Outputs | Notes |
|------|---------|---------------|--------|---------|------|

For traces, include at least one full claim trace end-to-end.

Start by building the pipeline map, then search for existing relevance/gating logic, then run a traced reproduction.
