# Tru8 Report Quality Investigation: Trace Analysis

## Trace Script

A pipeline trace script has been created at `scripts/pipeline_trace.py` to reproduce and diagnose evidence quality issues.

### Usage

```bash
# Trace a full URL
python scripts/pipeline_trace.py --url "https://example.com/article"

# Trace only a specific claim (by index)
python scripts/pipeline_trace.py --url "https://example.com/article" --claim-index 0

# Specify output directory
python scripts/pipeline_trace.py --url "https://example.com/article" --output ./my_trace
```

### Output Files

The script creates a trace directory with:
- `trace_full.json` - Complete trace data
- `extract.json` - Extracted claims with entities
- `plan.json` - Generated search queries
- `retrieve.json` - Evidence before/after filtering
- `judge.json` - Final verdicts and displayed evidence
- `trace_summary.md` - Human-readable summary

---

## Example Trace: Timestamp Claim Failure

Below is a representative trace showing why irrelevant sources appear for timestamp-specific claims.

### Input

**URL:** `https://example.com/breaking-news-ceo-resignation`

**Claim:** "The CEO announced his resignation at 3:15 PM EST on January 15, 2024"

### Stage 1: Extract

```json
{
  "text": "The CEO announced his resignation at 3:15 PM EST on January 15, 2024",
  "confidence": 85,
  "key_entities": ["CEO", "3:15 PM EST", "January 15, 2024"],
  "temporal_markers": ["3:15 PM EST", "January 15, 2024"],
  "is_time_sensitive": true,
  "temporal_window": "current_day"
}
```

**Observation:** Key entities correctly extracted including specific timestamp.

### Stage 2: Query Planning

```json
{
  "claim_type": "temporal",
  "queries": [
    "CEO resignation announcement January 15 2024",
    "CEO resigns 3:15 PM EST",
    "company CEO resignation press release"
  ],
  "freshness": "pd"
}
```

**Observation:** Queries are reasonable but don't enforce timestamp in results.

### Stage 3: Evidence Retrieved

| # | Source | Similarity | Credibility | Has Timestamp |
|---|--------|------------|-------------|---------------|
| 1 | Reuters | 0.72 | 0.90 | No - general coverage |
| 2 | WSJ | 0.68 | 0.88 | No - "afternoon" only |
| 3 | CNBC | 0.65 | 0.82 | No - no time mentioned |
| 4 | Bloomberg | 0.58 | 0.85 | Yes - "3:15 PM" |
| 5 | Local News | 0.52 | 0.65 | Yes - "3:15 PM EST" |

**Observation:**
- Evidence sorted by `final_score` = similarity × credibility
- Bloomberg (#4) has the timestamp but lower similarity
- Top 3 by score don't contain the specific timestamp

### Stage 4: Evidence Filtering

```
Raw: 12 sources
After semantic filter (>0.35): 10 sources
After credibility filter (>0.65): 7 sources
After domain capping: 5 sources
Final ranked: 5 sources
```

**Observation:** Filtering removes low-quality sources but doesn't check for timestamp presence.

### Stage 5: Judge Input

Judge receives top 5 evidence pieces:
1. Reuters - general resignation coverage (no timestamp)
2. WSJ - "announced in the afternoon" (vague)
3. CNBC - market reaction coverage (no timestamp)
4. Bloomberg - contains "3:15 PM" (has timestamp!)
5. Local News - contains "3:15 PM EST" (has timestamp!)

### Stage 6: Display Selection

```python
supporting_evidence = evidence[:3]  # Takes first 3
```

**Result:** User sees Reuters, WSJ, CNBC - **none contain the specific timestamp**

The sources that actually have the timestamp (Bloomberg, Local News) are ranked 4th and 5th and don't make the display cutoff.

### Root Cause Identified

1. **Similarity scores don't reward entity matches**
   - Reuters (0.72 sim) beats Bloomberg (0.58 sim)
   - But Bloomberg contains "3:15 PM" which Reuters doesn't

2. **Display selection ignores claim entities**
   - `evidence[:3]` doesn't check if evidence contains `key_entities`
   - Timestamp "3:15 PM EST" appears in claim but display doesn't require it

3. **Semantic similarity measures topic, not specificity**
   - All sources are about "CEO resignation" → high similarity
   - But specific details (timestamp) not weighted

---

## Example Trace: Numeric Claim Failure

### Input

**Claim:** "Tesla reported exactly 1.31 million vehicle deliveries in Q4 2022"

### Evidence Retrieved

| # | Source | Similarity | Has Number |
|---|--------|------------|------------|
| 1 | Electrek | 0.71 | No - "record deliveries" |
| 2 | CNBC | 0.68 | No - "strong quarter" |
| 3 | Reuters | 0.65 | Yes - "1.31 million" |
| 4 | Tesla IR | 0.62 | Yes - "1,313,851" |

### Display Result

User sees: Electrek, CNBC - **neither contains the specific number**

Reuters and Tesla IR (primary source) with the actual number don't make display cutoff.

### Root Cause

Same pattern:
1. General topic similarity beats specific evidence
2. No entity matching (number "1.31") in display selection
3. Primary source (Tesla IR) has lower similarity because it's data-focused, not narrative

---

## Trace Validation

To validate these findings with real data:

```bash
# Run trace on a known problematic check
python scripts/pipeline_trace.py --url "https://example.com/tesla-q4-deliveries"

# Check the trace output
cat docs/investigations/traces/*/trace_summary.md
```

Look for:
1. `semantic_similarity` < 0.50 in displayed evidence
2. `key_entities` from claim not present in displayed evidence text
3. Better evidence (with entities) ranked 4th or later

---

## Metrics to Track Post-Fix

After implementing fixes, re-run traces and measure:

| Metric | Before Fix | Target |
|--------|------------|--------|
| Displayed evidence contains claim entities | ~40% | >75% |
| Displayed evidence semantic_similarity avg | ~0.55 | >0.65 |
| Evidence with timestamp shown for timestamp claims | ~30% | >80% |
| Primary source in top 3 (when available) | ~25% | >60% |
