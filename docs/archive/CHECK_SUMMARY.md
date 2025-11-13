# Overall Check Summary Feature

## Overview
Add an overall summary section to multi-claim fact-checks that provides:
- Single verdict across all claims
- Narrative summary (2-3 sentences)
- Key sources list showing which sources support/refute which claims
- Verdict distribution breakdown

## Business Case

**User Value**: High
- Gives users a clear "bottom line" conclusion
- Shows which sources informed the overall verdict
- Professional presentation matching industry standards (Snopes, PolitiFact, etc.)

**Cost Impact**: Negligible
- Additional LLM call: ~3000 tokens @ gpt-4o-mini
- Cost per check: +$0.0027 (doubles LLM cost but still only ~$0.006 total)
- Monthly impact (300 checks): +£0.70/month

**Latency Impact**: Acceptable
- Adds 2-3 seconds for summary generation
- Only runs for multi-claim checks (2+ claims)
- Total: 12-18s instead of 10-15s

**Risk**: Low
- No database schema changes (uses existing `decision_trail` JSON field)
- Optional feature - old checks still work
- Isolated implementation

## Technical Design

### Database Storage
**No migration required** - use existing field in Check model:
```python
# backend/app/models/check.py line 23
decision_trail: Optional[str] = Field(default=None, sa_column=Column(JSON))
```

Store summary structure:
```json
{
  "overall_verdict": "supported|contradicted|mixed",
  "confidence": 75,
  "summary_text": "Based on 5 sources including NASA and NOAA, the claims about rising global temperatures are strongly supported by scientific data from 2020-2024.",
  "key_sources": [
    {
      "source": "NASA.gov",
      "url": "https://nasa.gov/...",
      "claims_addressed": [0, 2],
      "stance": "supporting",
      "credibility": 0.95
    },
    {
      "source": "Wikipedia",
      "url": "https://en.wikipedia.org/...",
      "claims_addressed": [1],
      "stance": "mixed",
      "credibility": 0.70
    }
  ],
  "verdict_distribution": {
    "supported": 2,
    "contradicted": 0,
    "uncertain": 1
  }
}
```

### Backend Implementation

#### 1. Add Summary Method to Judge (`backend/app/pipeline/judge.py`)

**Location**: After line 285 (after `judge_all_claims` method)

```python
async def generate_overall_summary(
    self,
    claims: List[Dict[str, Any]],
    claim_results: List[Dict[str, Any]],
    all_evidence: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Generate overall summary after all individual claims judged.
    Aggregates evidence across claims and provides holistic verdict.
    """

    # Aggregate sources across all claims
    source_analysis = self._analyze_sources_across_claims(
        all_evidence, claim_results
    )

    # Prepare context for LLM
    context = self._prepare_summary_context(
        claims, claim_results, source_analysis
    )

    # Call LLM for summary
    if self.openai_api_key:
        summary_data = await self._generate_summary_with_openai(context)
    else:
        # Fallback to rule-based summary
        summary_data = self._generate_simple_summary(
            claims, claim_results, source_analysis
        )

    return summary_data

def _analyze_sources_across_claims(
    self,
    evidence: Dict[str, List[Dict[str, Any]]],
    results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Aggregate sources and determine which claims they addressed.
    Returns list of unique sources with their stances.
    """
    source_map = {}

    for claim_pos, evidence_list in evidence.items():
        claim_verdict = next(
            (r['verdict'] for r in results if str(r.get('position')) == claim_pos),
            'uncertain'
        )

        for ev in evidence_list:
            source = ev.get('source', 'Unknown')
            if source not in source_map:
                source_map[source] = {
                    'source': source,
                    'url': ev.get('url', ''),
                    'claims_addressed': [],
                    'credibility': ev.get('credibility_score', 0.6),
                    'claim_verdicts': []
                }

            source_map[source]['claims_addressed'].append(int(claim_pos))
            source_map[source]['claim_verdicts'].append(claim_verdict)

    # Determine stance for each source
    for source_data in source_map.values():
        verdicts = source_data['claim_verdicts']
        if all(v == 'supported' for v in verdicts):
            source_data['stance'] = 'supporting'
        elif all(v == 'contradicted' for v in verdicts):
            source_data['stance'] = 'refuting'
        else:
            source_data['stance'] = 'mixed'

        # Remove internal tracking field
        del source_data['claim_verdicts']

    # Sort by number of claims addressed (most important first)
    return sorted(
        source_map.values(),
        key=lambda x: len(x['claims_addressed']),
        reverse=True
    )[:5]  # Top 5 sources

def _prepare_summary_context(
    self,
    claims: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    sources: List[Dict[str, Any]]
) -> str:
    """Prepare context for LLM summary generation"""

    claims_summary = "\n".join([
        f"{i+1}. {c['text']} → {r['verdict'].upper()} ({r['confidence']}%)"
        for i, (c, r) in enumerate(zip(claims, results))
    ])

    sources_summary = "\n".join([
        f"- {s['source']} (claims {s['claims_addressed']}, credibility: {s['credibility']:.0%})"
        for s in sources
    ])

    return f"""You have completed fact-checking multiple claims. Now provide an overall summary.

INDIVIDUAL CLAIM RESULTS:
{claims_summary}

KEY SOURCES USED:
{sources_summary}

Provide a holistic assessment:
1. Overall verdict (supported/contradicted/mixed based on majority)
2. 2-3 sentence narrative summary explaining the findings
3. Identify which sources were most important and their stances

Be concise, accurate, and ensure consistency with individual claim verdicts."""

async def _generate_summary_with_openai(
    self,
    context: str
) -> Dict[str, Any]:
    """Generate summary using OpenAI"""

    summary_prompt = """You are summarizing a multi-claim fact-check.

Provide an overall assessment with:
- overall_verdict: "supported" if majority supported, "contradicted" if majority contradicted, "mixed" otherwise
- confidence: Average of individual confidences
- summary_text: 2-3 sentence narrative explaining findings

Return valid JSON matching this structure:
{
  "overall_verdict": "supported|contradicted|mixed",
  "confidence": 75,
  "summary_text": "Your narrative summary here..."
}

Be objective, concise, and consistent with individual verdicts."""

    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini-2024-07-18",
                "messages": [
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": context}
                ],
                "max_tokens": 600,
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            raise Exception(f"OpenAI API error: {response.status_code}")

def _generate_simple_summary(
    self,
    claims: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    sources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Fallback: generate summary without LLM"""
    from collections import Counter

    verdict_counts = Counter(r['verdict'] for r in results)
    most_common = verdict_counts.most_common(1)[0][0]
    avg_confidence = sum(r['confidence'] for r in results) / len(results)

    return {
        "overall_verdict": most_common,
        "confidence": round(avg_confidence, 1),
        "summary_text": f"Checked {len(claims)} claims using {len(sources)} sources. Majority verdict: {most_common}.",
        "verdict_distribution": dict(verdict_counts)
    }
```

#### 2. Integrate in Pipeline (`backend/app/workers/pipeline.py`)

**Location**: After line 336 (after judge stage completes)

```python
# After: stage_timings["judge"] = (datetime.utcnow() - stage_start).total_seconds()

# Stage 6.5: Generate Overall Summary (only for multi-claim checks)
if len(claims) > 1:
    logger.info("Generating overall summary for multi-claim check")
    stage_start = datetime.utcnow()

    try:
        pipeline_judge = await get_pipeline_judge()
        overall_summary = await pipeline_judge.generate_overall_summary(
            claims, results, evidence
        )

        # Add source analysis to summary
        overall_summary["key_sources"] = pipeline_judge._analyze_sources_across_claims(
            evidence, results
        )

        stage_timings["summary"] = (datetime.utcnow() - stage_start).total_seconds()
        logger.info(f"Generated overall summary: {overall_summary['overall_verdict']} ({overall_summary['confidence']}%)")

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        # Continue without summary - not critical
        overall_summary = None
else:
    overall_summary = None
```

**Then update final_result** (around line 393):

```python
# Prepare final result with enhanced metrics
final_result = {
    "check_id": check_id,
    "status": "completed",
    "claims": results,
    "overall_summary": overall_summary,  # ADD THIS LINE
    "processing_time_ms": processing_time_ms,
    # ... rest of fields
}
```

#### 3. Update Save Function (`backend/app/workers/pipeline.py`)

**Location**: Around line 419 in `save_check_results_sync`

```python
# Save overall summary to decision_trail if present
if results.get("overall_summary"):
    if check.decision_trail:
        check.decision_trail["overall_summary"] = results["overall_summary"]
    else:
        check.decision_trail = {"overall_summary": results["overall_summary"]}
```

### Frontend Implementation

#### 1. Create Summary Component (`web/app/dashboard/components/check-summary.tsx`)

```typescript
import { VerdictPill } from './verdict-pill';

interface KeySource {
  source: string;
  url: string;
  claims_addressed: number[];
  stance: 'supporting' | 'refuting' | 'mixed';
  credibility: number;
}

interface OverallSummary {
  overall_verdict: 'supported' | 'contradicted' | 'uncertain' | 'mixed';
  confidence: number;
  summary_text: string;
  key_sources: KeySource[];
  verdict_distribution?: {
    supported: number;
    contradicted: number;
    uncertain: number;
  };
}

interface CheckSummaryProps {
  summary: OverallSummary;
}

export function CheckSummary({ summary }: CheckSummaryProps) {
  return (
    <div className="card p-6 space-y-6">
      {/* Overall Verdict */}
      <div className="text-center space-y-4">
        <h3 className="text-xl font-bold">Overall Assessment</h3>
        <div className="flex justify-center">
          <VerdictPill
            verdict={summary.overall_verdict}
            confidence={summary.confidence}
            size="large"
          />
        </div>
      </div>

      {/* Summary Text */}
      <div className="text-center max-w-2xl mx-auto">
        <p className="text-base text-gray-300 leading-relaxed">
          {summary.summary_text}
        </p>
      </div>

      {/* Verdict Distribution */}
      {summary.verdict_distribution && (
        <div className="flex justify-center gap-4 text-sm">
          <span className="text-emerald-400">
            {summary.verdict_distribution.supported} Supported
          </span>
          <span className="text-red-400">
            {summary.verdict_distribution.contradicted} Contradicted
          </span>
          <span className="text-amber-400">
            {summary.verdict_distribution.uncertain} Uncertain
          </span>
        </div>
      )}

      {/* Key Sources */}
      <div className="space-y-3">
        <h4 className="font-semibold text-sm text-gray-400 uppercase tracking-wide">
          Key Sources ({summary.key_sources.length})
        </h4>
        <div className="space-y-2">
          {summary.key_sources.map((source, idx) => (
            <a
              key={idx}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-4 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium text-gray-200">
                    {source.source}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    Claims {source.claims_addressed.join(', ')} •
                    Credibility: {Math.round(source.credibility * 100)}%
                  </div>
                </div>
                <div className="ml-4">
                  {source.stance === 'supporting' && (
                    <span className="text-emerald-400 text-xl">✓</span>
                  )}
                  {source.stance === 'refuting' && (
                    <span className="text-red-400 text-xl">✗</span>
                  )}
                  {source.stance === 'mixed' && (
                    <span className="text-amber-400 text-xl">?</span>
                  )}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
```

#### 2. Integrate in Check Detail Page (`web/app/dashboard/check/[id]/check-detail-client.tsx`)

Add after claims list rendering:

```typescript
{/* Overall Summary - only for multi-claim checks */}
{checkData.claims && checkData.claims.length > 1 && checkData.decision_trail?.overall_summary && (
  <div className="mt-8">
    <CheckSummary summary={checkData.decision_trail.overall_summary} />
  </div>
)}
```

## Implementation Checklist

### Backend (4-5 hours)
- [ ] Add `generate_overall_summary` method to ClaimJudge class
- [ ] Add `_analyze_sources_across_claims` helper method
- [ ] Add `_prepare_summary_context` helper method
- [ ] Add `_generate_summary_with_openai` method
- [ ] Add `_generate_simple_summary` fallback method
- [ ] Integrate summary generation in pipeline.py (after judge stage)
- [ ] Update final_result to include overall_summary
- [ ] Update save_check_results_sync to store in decision_trail
- [ ] Test with 3-5 multi-claim checks
- [ ] Verify costs (~$0.006 per check)
- [ ] Verify latency (~12-18s total)

### Frontend (2-3 hours)
- [ ] Create CheckSummary component
- [ ] Add TypeScript interface for OverallSummary
- [ ] Style according to DESIGN_SYSTEM.md
- [ ] Integrate in check-detail-client.tsx
- [ ] Test with multi-claim check
- [ ] Test responsive layout (mobile/desktop)
- [ ] Add VerdictPill "large" size variant if needed

### Testing (1-2 hours)
- [ ] Test single-claim check (should not generate summary)
- [ ] Test multi-claim check with mixed verdicts
- [ ] Test multi-claim check with all supported
- [ ] Test error handling (summary generation fails)
- [ ] Verify summary consistency with individual claims
- [ ] Test on mobile/tablet/desktop

## Edge Cases to Handle

1. **Single-claim checks**: Skip summary generation (no value)
2. **Summary generation fails**: Log error, continue without summary
3. **All claims "uncertain"**: Overall verdict = "uncertain"
4. **LLM returns inconsistent verdict**: Log warning, use rule-based fallback
5. **No sources found**: Summary shows "No sources available"

## Success Metrics

- Summary generation succeeds >95% of time for multi-claim checks
- Latency stays under 20s for 3-claim checks
- Cost per check remains <$0.01
- User feedback indicates summary is helpful

## Future Enhancements

- Add "Show/Hide Summary" toggle
- Add timeline visualization of when claims were made
- Add source reliability badges
- Add "Share Summary" feature
- Localize summary text for different languages
