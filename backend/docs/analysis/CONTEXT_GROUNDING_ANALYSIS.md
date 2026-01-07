# Context Grounding Analysis - Why Claims Fail Without Article Context

**Date:** 2025-11-19
**Core Issue:** Claims are extracted WITH article context but verified WITHOUT it
**Impact:** Generic queries match wrong events, NLI can't disambiguate similar claims

## User's Insight

> "Shouldn't each claim be presented to the NLI, or Brave, or whichever engine with the **headline as context** for the claim, to offer a grounding of what the claim relates to? A claim made in isolation may be misunderstood."

**This is exactly the problem.**

## Current Context Flow

### ✅ Stage 1: Extraction (CONTEXT USED)

**File:** `backend/app/pipeline/extract.py` (lines 171-175)

```python
user_prompt = ""
if metadata and metadata.get("title"):
    user_prompt += f"Article Title: \"{metadata.get('title')}\"\n"
if metadata and metadata.get("url"):
    user_prompt += f"Source URL: {metadata.get('url')}\n"
user_prompt += f"\nExtract atomic factual claims from this content:\n\n{content}"
```

**Result:**
- GPT-4 sees: `"Article Title: 'Elon Musk returns to White House for state dinner with Saudi Crown Prince Salman'"`
- Extracts claims WITH understanding of the article's topic
- Claims stored with `source_title` and `source_url` (lines 148-149)

### ❌ Stage 2: Query Formulation (CONTEXT IGNORED)

**File:** `backend/app/services/evidence.py` (line 89)

```python
search_query = formulator.formulate_query(
    claim,              # ← Just the claim text
    subject_context,    # ← Generic like "state dinner"
    key_entities,       # ← ["Donald Trump", "state dinner"]
    temporal_analysis   # ← Usually None
)
```

**What's MISSING:**
- ❌ Article title
- ❌ Article date/publish timestamp
- ❌ Sibling claims (other claims from same article)
- ❌ Article-level event identifier (e.g., "Saudi Crown Prince visit November 2025")

**Result:**
- Query: `"Donald Trump state dinner hosted President"`
- Matches: ANY Trump dinner from 2017-2025 ❌

**What SHOULD happen:**
- Query: `"Donald Trump hosted state dinner Saudi Crown Prince Mohammed bin Salman November 2025"`
- Matches: ONLY this specific dinner ✓

### ❌ Stage 3: NLI Verification (CONTEXT IGNORED)

**File:** `backend/app/pipeline/verify.py`

```python
# NLI input:
premise = evidence_text                    # ← Just the evidence snippet
hypothesis = claim["text"]                 # ← Just the claim text
result = nli_model.predict(premise, hypothesis)
```

**What's MISSING:**
- ❌ Article title/headline
- ❌ Temporal context ("this article is from November 2025")
- ❌ Event context ("this article is about the Saudi Crown Prince visit")

**Example of the problem:**

**Claim (isolated):** "The state dinner was hosted by US President Donald Trump"

**Evidence 1:** "Trump hosted a dinner for wealthy donors at the White House" (2018)
- NLI says: ENTAILS (president hosting dinner ✓)
- **But wrong event!**

**Evidence 2:** "Trump hosted Crown Prince Mohammed bin Salman for state dinner" (2025)
- NLI says: ENTAILS (president hosting dinner ✓)
- **Correct event!**

**Problem:** NLI can't distinguish between the two without event context.

## Real-World Impact: Saudi Crown Prince Article

### Article Context
- **Title:** "Elon Musk returns to White House for state dinner with Saudi Crown Prince Salman"
- **Date:** November 19, 2025
- **Event:** Saudi Crown Prince Mohammed bin Salman state visit

### Claim 2: "The state dinner was hosted by US President Donald Trump"

**What happened:**

1. **Extraction (WITH context):**
   - GPT-4 sees headline + article
   - Extracts claim correctly understanding it refers to THIS dinner

2. **Query formulation (WITHOUT context):**
   - Query: `"Donald Trump state dinner hosted President"`
   - **Matches:**
     - "Fact-Checking Trump's Speech at the U.N. General Assembly" (different event)
     - "Trump Hosts Dinner for Wealthy Donors" (2018 event)
     - "PolitiFact | What PolitiFact learned in 1,000 fact-checks" (meta-content)
   - **MISSES:**
     - Actual articles about the Saudi Crown Prince dinner

3. **NLI verification (WITHOUT context):**
   - Premise: "Trump held a dinner at the White House for donors..."
   - Hypothesis: "The state dinner was hosted by US President Donald Trump"
   - NLI: "NEUTRAL - no mention of Crown Prince, but Trump did host a dinner"

4. **Verdict:**
   - Before: "Contradicted" (because evidence is about different dinners)
   - After query expansion: "Uncertain" (mixed signals from multiple dinners)
   - **Should be:** "Supported" (with context: THIS specific dinner)

## Solution: Context Propagation Architecture

### Phase 1: Article-Level Context Injection (Quick Win)

**Add to all stages:**
```python
article_context = {
    "title": metadata.get("title"),
    "publish_date": metadata.get("publish_date"),
    "event_summary": "Saudi Crown Prince Mohammed bin Salman state visit, November 2025"
}
```

**A) Query Formulation (backend/app/utils/query_formulation.py)**

```python
def formulate_query(
    self,
    claim: str,
    subject_context: Optional[str] = None,
    key_entities: Optional[List[str]] = None,
    temporal_analysis: Optional[Dict] = None,
    article_context: Optional[Dict] = None  # ← NEW
) -> str:
    # Extract query terms
    query_terms = self._extract_query_terms(...)

    # Add article-level context
    if article_context:
        if article_context.get("publish_date"):
            # Add year/month for recent articles
            pub_date = article_context["publish_date"]
            if (datetime.now() - pub_date).days < 365:
                query_terms.append(pub_date.strftime("%Y"))

        # Extract key entities from article title
        if article_context.get("title"):
            title_entities = extract_entities_from_title(article_context["title"])
            # Add entities NOT already in claim
            new_entities = [e for e in title_entities if e.lower() not in claim.lower()]
            query_terms.extend(new_entities[:2])

    return " ".join(query_terms)
```

**Expected improvement:**
- Query: `"Donald Trump state dinner hosted Saudi Crown Prince Mohammed bin Salman 2025"`
- Matches: Articles specifically about THIS dinner
- Evidence quality: ⬆️ 80%+

**B) NLI Verification (backend/app/pipeline/verify.py)**

```python
async def verify_claim_with_evidence(
    claim: Dict,
    evidence: List[Dict],
    article_context: Optional[Dict] = None  # ← NEW
) -> Dict:
    # Build context-aware claim text for NLI
    claim_text = claim["text"]

    if article_context and article_context.get("event_summary"):
        # Prepend event context to help NLI understand specificity
        contextualized_claim = f"In an article about '{article_context['event_summary']}', the claim states: {claim_text}"
    else:
        contextualized_claim = claim_text

    # Run NLI with contextualized claim
    for ev in evidence:
        result = nli_model.predict(
            premise=ev["snippet"],
            hypothesis=contextualized_claim  # ← Context-aware
        )
```

**Expected improvement:**
- NLI can distinguish "Trump dinner 2018" vs "Trump dinner 2025"
- Reduces false positives from matching similar but different events
- Verdict accuracy: ⬆️ 30%+

### Phase 2: Cross-Claim Context Sharing (Medium Effort)

**Problem:** Claims from the same article search independently

**Current:**
- Claim 1: "Elon Musk attended dinner" → searches, finds correct sources
- Claim 2: "Trump hosted dinner" → searches AGAIN, finds WRONG sources

**Solution:** Share evidence pool across related claims

```python
def group_claims_by_event(claims: List[Dict], article_context: Dict) -> Dict[str, List[int]]:
    """Group claims that refer to the same event"""
    # Use article context to identify the main event
    event_keywords = extract_keywords(article_context.get("title", ""))

    groups = {}
    for i, claim in enumerate(claims):
        # Check if claim mentions event keywords
        claim_keywords = extract_keywords(claim["text"])
        overlap = set(event_keywords) & set(claim_keywords)

        if len(overlap) >= 2:  # At least 2 shared keywords
            event_id = "_".join(sorted(event_keywords[:3]))
            if event_id not in groups:
                groups[event_id] = []
            groups[event_id].append(i)

    return groups

# In retrieve stage:
claim_groups = group_claims_by_event(claims, article_context)
evidence_pools = {}

for event_id, claim_indices in claim_groups.items():
    # Search ONCE for the event, share evidence across all claims
    event_query = formulate_event_query(claims[claim_indices[0]], article_context)
    event_evidence = search(event_query)
    evidence_pools[event_id] = event_evidence

    # Distribute to all claims in group
    for idx in claim_indices:
        claims[idx]["evidence"] = filter_relevant(event_evidence, claims[idx])
```

**Expected improvement:**
- Reduce search API calls by ~60%
- Ensure consistent evidence across related claims
- Eliminate "Claim 1 correct, Claim 2 wrong" scenarios

### Phase 3: Temporal Context Intelligence (Advanced)

**Add publish date filtering:**
```python
def apply_temporal_filter(evidence: List[Dict], article_date: datetime) -> List[Dict]:
    """Deprioritize evidence far from article date"""
    for ev in evidence:
        if ev.get("published_date"):
            days_apart = abs((article_date - ev["published_date"]).days)

            if days_apart > 365:
                ev["relevance_score"] *= 0.5  # Halve relevance for year-old evidence
            elif days_apart > 90:
                ev["relevance_score"] *= 0.8  # Reduce for 3-month-old evidence

    return sorted(evidence, key=lambda x: x["relevance_score"], reverse=True)
```

## Implementation Priority

### 🔥 TIER 1: Immediate (1-2 hours)
1. **Add article_context parameter to query formulation**
   - Pass title + publish date
   - Extract key entities from title
   - Add year for recent articles

2. **Test on Saudi Crown Prince article**
   - Expected: Claim 2 changes from "Contradicted" → "Supported"
   - Expected: Evidence quality improves (Saudi sources, not 2018 donors)

### ⚡ TIER 2: High Impact (4-6 hours)
3. **Add article_context to NLI verification**
   - Contextualize claims with event summary
   - Improve disambiguation of similar events

4. **Implement cross-claim evidence sharing**
   - Group claims by event
   - Shared evidence pool
   - Consistent verdicts

### 🚀 TIER 3: Future Enhancement
5. **Temporal intelligence filtering**
6. **Event detection and linking**
7. **Multi-article cross-referencing**

## Success Metrics

**Before (current):**
- Query: Generic → matches wrong events
- NLI: Context-free → can't disambiguate
- Verdicts: Inconsistent across related claims
- Score: 62/100 (after broken query expansion)

**After (Tier 1 fixes):**
- Query: Context-aware → matches correct event
- Evidence: Event-specific → all about THIS dinner
- Verdicts: Consistent → all claims reference same event
- Score: 85-90/100 (expected)

**After (Tier 2 fixes):**
- NLI: Event-aware → distinguishes similar events
- Cross-claims: Shared evidence → consistent verdicts
- Score: 90-95/100 (expected)

---

**Priority:** CRITICAL - This is the root cause of the "Trump dinner contradiction" issue
**Effort:** Tier 1 = 2 hours, Tier 2 = 6 hours total
**Impact:** Fixes ambiguous claim verification across ALL articles, not just this one
