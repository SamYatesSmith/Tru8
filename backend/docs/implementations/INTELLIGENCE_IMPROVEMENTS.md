# Intelligence Improvements to Prevent Illogical Verdicts

**Date:** 2025-11-19
**Issue:** Claim 2 marked "contradicted" despite obvious logical truth
**Example:** "The state dinner was hosted by US President Donald Trump" → contradicted (but he's literally the president hosting at the White House!)

## Root Cause Analysis

### Claim 2 Error Breakdown
**Claim:** "The state dinner was hosted by US President Donald Trump"
**Verdict:** Contradicted (90% confidence)
**Evidence Used:**
- ABC News: "Donald Trump's royal banquet dinner" (2018 UK state visit)
- NYTimes: "Trump Hosts Dinner for Wealthy Donors" (different event)
- PolitiFact: "Latest Fact-checks on Donald Trump" (generic page)

**Meanwhile, Claim 1 evidence included:**
- Forbes: "**Trump Hosts Saudi Leader For White House Dinner**"
- NYTimes: "**Trump's Dinner** for the Saudi Crown Prince"
- The Hill: "**President Trump's black tie dinner**"

### Why This Happened

1. **Query Expansion Disabled**
   - Setting: `ENABLE_QUERY_EXPANSION=False` (default)
   - Result: Search query = just the claim text
   - Problem: "Trump hosts dinner" matches ANY Trump dinner from any year

2. **No Temporal Context**
   - Article date: November 19, 2025
   - Evidence retrieved: Includes articles from 2014, 2018 (7+ years old)
   - Problem: Old "Trump dinners" ranked as highly as recent ones

3. **No Cross-Claim Evidence Sharing**
   - Claim 1 and Claim 2 are about THE SAME EVENT
   - Evidence for Claim 1: Correct (Forbes, NYT, Hill about Saudi dinner)
   - Evidence for Claim 2: Wrong (ABC UK visit, wealthy donors)
   - Problem: Each claim searches independently, no shared context

4. **Query Formulator Issues** (when enabled)
   - Line 88: `query += ' (site:.gov OR site:.edu OR site:.org ...)'`
   - Problem: EXCLUDES news sources (NYT, BBC, Reuters, etc.)
   - Result: Forces searches to match .gov archives with old Trump dinners

5. **No Common Sense Verification**
   - NLI model correctly identifies evidence doesn't support claim
   - Judge accepts "contradicted" verdict without logical check
   - Problem: Doesn't ask "Could a US President NOT host a White House state dinner?"

## Proposed Solutions (Tiered)

### 🔥 TIER 1: Quick Wins (Enable Now)

#### 1.1 Enable Query Expansion with Fixes
**File:** `backend/.env`
```env
ENABLE_QUERY_EXPANSION=True  # Currently False
```

**File:** `backend/app/utils/query_formulation.py` (line 88)
```python
# BEFORE:
query += ' (site:.gov OR site:.edu OR site:.org OR "study" OR "research")'

# AFTER:
# REMOVED - Don't filter out news sources for news-based claims
```

**Expected Impact:**
- Queries will include key entities + temporal context
- Won't exclude news sources
- Better match specificity

#### 1.2 Add Article Date Context to Queries
**File:** `backend/app/pipeline/retrieve.py`

Add article publish date to claim context:
```python
article_date = check.get("article_date")  # From ingest stage
temporal_context = {
    "article_date": article_date,
    "is_recent": (datetime.now() - article_date).days < 90  # 3 months
}
```

Pass to query formulator to add "2025" or "November 2025" to queries.

**Expected Impact:**
- Queries for recent events will include year/month
- Old articles will be deprioritized

### ⚡ TIER 2: Medium Effort (Implement Next)

#### 2.1 Cross-Claim Evidence Pool
**File:** `backend/app/pipeline/retrieve.py`

When multiple claims are about the same event:
1. Extract "article_subject" during extraction (e.g., "Trump Saudi Crown Prince dinner November 2025")
2. Group claims with high semantic similarity (>0.8)
3. Share evidence pool between grouped claims
4. Deduplicate at the end

**Implementation:**
```python
def group_related_claims(claims: List[Dict]) -> Dict[int, List[int]]:
    """Group semantically similar claims that likely refer to same event"""
    # Use sentence-transformers to compute claim embeddings
    # Cluster claims with similarity > 0.8
    # Return {group_id: [claim_indices]}

def retrieve_with_shared_evidence(claims, groups):
    # For each group, merge search results
    # Share evidence pool across all claims in group
```

**Expected Impact:**
- Claims about same event use same evidence
- No more "Claim 1 has correct evidence, Claim 2 has wrong evidence"

#### 2.2 Temporal Evidence Filtering
**File:** `backend/app/services/evidence.py`

After retrieving evidence, apply temporal filtering:
```python
def apply_temporal_filter(evidence, claim_temporal_context):
    if claim_temporal_context.get("is_recent"):
        # For recent claims, deprioritize evidence older than 1 year
        for ev in evidence:
            if ev.published_date and (datetime.now() - ev.published_date).days > 365:
                ev.relevance_score *= 0.5  # Halve relevance for old articles
```

**Expected Impact:**
- Recent claims won't match articles from 2014-2018
- Old "Trump dinner" articles won't contaminate recent events

#### 2.3 Common Sense Reasoning Layer
**File:** `backend/app/pipeline/judge.py`

Before finalizing "contradicted" verdicts, apply logic checks:
```python
def validate_contradiction(claim: str, verdict: str, evidence: List) -> bool:
    """Check if contradiction makes logical sense"""

    # Pattern 1: Role-based hosting
    if "hosted by" in claim.lower() and verdict == "contradicted":
        # Extract: "X hosted Y at Z"
        # If X = president and Z = White House, hosting is automatic
        if any(role in claim.lower() for role in ["president", "prime minister", "chancellor"]):
            if any(venue in claim.lower() for venue in ["white house", "downing street", "chancellery"]):
                logger.warning(f"⚠️ LOGIC CHECK: President hosting at official venue - likely NOT contradicted")
                return False  # Reject contradiction

    # Pattern 2: Obvious temporal facts
    # ... more patterns

    return True  # Accept verdict
```

**Expected Impact:**
- Catch illogical contradictions before finalizing
- Maintain "uncertain" instead of "contradicted" for edge cases

### 🚀 TIER 3: Advanced (Future Enhancement)

#### 3.1 LLM-Based Query Reformulation
Use GPT-4 to reformulate queries with full article context:
```
Prompt: "Given this article about X, formulate an optimal search query for the claim Y.
Include key entities, temporal context, and exclude off-topic terms."
```

#### 3.2 Evidence Deduplication Across Claims
Build a check-level evidence cache:
- First claim searches normally
- Subsequent claims check cache first
- Only search if cache has <3 relevant pieces

#### 3.3 Fact-Check Source Exclusion
Currently excludes Snopes/FactCheck during search. Extend to:
- Detect if retrieved evidence is ABOUT fact-checking (meta-content)
- Filter out "X fact-checked" articles that don't contain primary evidence

## Recommended Implementation Order

1. **Enable query expansion** + **Remove restrictive site filters** (5 min)
2. **Add temporal filtering** (1 hour)
3. **Add common sense reasoning layer** (2 hours)
4. **Implement cross-claim evidence sharing** (4 hours)
5. **Test on 10+ articles** (1 hour)

## Success Metrics

**Before (Current State):**
- Claim 2: Contradicted (90%) with wrong evidence
- User sees illogical verdict
- Trust in system ↓

**After (Expected):**
- Claim 2: Supported (85%) with correct evidence from Claim 1 pool
- OR: Supported (90%) with query expansion finding correct articles
- Logical verdicts across all claims
- Trust in system ↑

## Testing Protocol

1. **Test article:** Saudi Crown Prince dinner (current failure case)
2. **Expected results:**
   - All claims about the dinner use shared evidence pool
   - Trump as host: Supported (90%+)
   - No articles from 2014-2018 in evidence
   - All evidence explicitly mentions "Saudi Crown Prince" + "November 2025"

3. **Control test:** Re-run previous US articles (rollcall, etc.)
   - Ensure 90/100 scores maintained
   - No regression in quality

---

**Priority:** HIGH - Affects user trust in verdict accuracy
**Effort:** TIER 1 (5 min) → TIER 2 (7 hours total)
**Impact:** Prevents obviously wrong "contradicted" verdicts
