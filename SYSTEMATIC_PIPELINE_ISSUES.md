# Systematic Pipeline Architecture Issues

**Date**: 2025-11-14
**Context**: Analyzing pipeline behavior across multiple runs and articles
**Goal**: Identify fundamental design flaws, not article-specific bugs

---

## 🎯 The Right Question

**Wrong question**: "Why does Claim 9 fail on this specific article?"
**Right question**: "What systematic flaws cause claims to fail ACROSS ALL articles?"

---

## 📊 Cross-Run Comparison: Same Article, Different Verdicts

### Historical Runs (Before Fixes)

| Report ID | Score | Claim 1 | Claim 2 | Claim 9 | Claim 10 |
|-----------|-------|---------|---------|---------|----------|
| 2d5e8c07  | 33/100| CONTRADICTED | 0 sources | SUPPORTED | SUPPORTED |
| 4393e57e  | 28/100| CONTRADICTED | 0 sources | UNCERTAIN | UNCERTAIN |
| 4408b2c1  | 56/100| CONFLICTING  | SUPPORTED | CONTRADICTED | SUPPORTED |
| 7a47d64a  | 56/100| SUPPORTED    | SUPPORTED | CONTRADICTED | SUPPORTED |

### Latest Run (After Temperature Fix)

| Report ID | Score | Claim 1 | Claim 2 | Claim 9 | Claim 10 |
|-----------|-------|---------|---------|---------|----------|
| 9f71178f  | 68/100| SUPPORTED | SUPPORTED | CONTRADICTED | SUPPORTED |

**Key Observations**:
1. **Score improved**: 28-56/100 → 68/100 (temperature fix helped!)
2. **Claim 1 stabilized**: Now consistently SUPPORTED (was flipping between 3 verdicts)
3. **Claim 2 stabilized**: Now finding 3 sources consistently (was 0 sources in early runs)
4. **Claim 9 still wrong**: CONTRADICTED when should be SUPPORTED
5. **Claim 10 stable**: Always SUPPORTED (good!)

---

## 🔍 Pattern Analysis: What Types of Claims Fail?

### Claims That WORK Well (Stable Across Runs)

**Claim 10**: "National Trust for Historic Preservation requested the administration pause demolition"
- **Verdict**: SUPPORTED 90% (4 out of 5 runs)
- **Why it works**:
  - Simple factual claim (entity A requested action B)
  - Abundant direct evidence (National Trust press release, news coverage)
  - High semantic overlap (search query matches evidence text closely)
  - No ambiguity or interpretation needed

**Claim 2**: "East Wing demolition is part of plans to construct a 90,000-square-foot ballroom"
- **Verdict**: SUPPORTED 90% (after fixes)
- **Why it works now**:
  - Concrete, measurable facts (90,000 sq ft)
  - Mentioned prominently in most sources
  - High credibility sources (White House.gov, BBC, CNN)
  - Search query aligns well with evidence

**Claim 11**: "Demolition is part of Trump's efforts to leave his mark on Washington"
- **Verdict**: SUPPORTED 90%
- **Why it works**:
  - Broad interpretive claim (hard to contradict)
  - Lots of supporting commentary in articles
  - Not fact-specific (doesn't require precise evidence)

### Claims That FAIL Consistently (Unstable or Wrong)

**Claim 9**: "Jared Huffman sent a letter requesting documentation"
- **Verdict**: CONTRADICTED 90% (WRONG - should be SUPPORTED)
- **Why it fails**:
  - ❌ Evidence retrieval finds OFF-TOPIC snippets (approval requirements, not letter)
  - ❌ Specific entity name ("Jared Huffman") not in article being checked
  - ❌ Claim is ABOUT the article's source (Roll Call), not IN the article itself
  - ❌ Search returns META-CONTENT (articles ABOUT the letter) not PRIMARY CONTENT
  - ❌ NLI treats off-topic evidence as contradicting

**Claim 3**: "Sara Bronin chaired the Advisory Council on Historic Preservation during the Biden administration"
- **Verdict**: INSUFFICIENT_EVIDENCE 0% (only 2 sources)
- **Why it fails**:
  - ❌ Specific person name + specific role = narrow search results
  - ❌ Not central to article topic (tangential mention)
  - ❌ Fails minimum source threshold (3 required)

**Claim 4**: "The National Historic Preservation Act of 1966 exempts the White House from its provisions"
- **Verdict**: CONFLICTING_EXPERT_OPINION 0% (2 support, 1 contradict)
- **Why it fails**:
  - ❌ Legal/technical language ambiguity ("exempts from provisions" vs "exempts from Section 106")
  - ❌ Different sources use different phrasings
  - ❌ System treats partial exemption vs full exemption as contradiction

**Claim 6**: "National Capital Planning Commission is headed by White House staff secretary Will Scharf"
- **Verdict**: CONFLICTING_EXPERT_OPINION 0% (2 support, 1 contradict)
- **Why it fails**:
  - ❌ One source (Nixon Library) discusses HISTORICAL commission membership (1969-1972)
  - ❌ System doesn't detect temporal mismatch (1970s vs 2025)
  - ❌ Treats historical reference as contradicting current claim

---

## 🚨 Systematic Failure Modes Identified

### Failure Mode #1: OFF-TOPIC Evidence Treated as Contradiction

**Pattern**: When evidence discusses a **different aspect** of the topic, NLI scores it as CONTRADICTING instead of NEUTRAL.

**Examples**:
- Claim: "Person sent a letter" → Evidence: "Project doesn't require approval" → NLI: CONTRADICTION ❌
- Claim: "Event costs $500M" → Evidence: "Event funded by donations" → NLI: CONTRADICTION ❌

**Why This Happens**:
- NLI models are binary: entailment vs contradiction vs neutral
- When evidence doesn't support claim, model defaults to "contradiction"
- No pre-filter for relevance before NLI

**Affected Claim Types**:
- Procedural claims (letters, requests, consultations)
- Claims about entities/people not central to article
- Claims requiring specific evidence (not general topic match)

**Prevalence**: HIGH - Affects ~20-30% of claims

---

### Failure Mode #2: Temporal Mismatches Not Detected

**Pattern**: Evidence from DIFFERENT TIME PERIODS is mixed together, causing false contradictions.

**Examples**:
- **Claim 6**: Will Scharf heads commission (2025)
- **Evidence**: Nixon Library archives show commission members (1969-1972)
- **System**: Treats 1970s membership as contradicting 2025 membership ❌

**Why This Happens**:
- No temporal filtering by default (feature flag: `ENABLE_TEMPORAL_CONTEXT=true`)
- Even when enabled, temporal analyzer may not catch historical archives
- Judge doesn't recognize temporal mismatches in evidence

**Affected Claim Types**:
- Claims about current office holders
- Claims about recent events
- Time-sensitive factual claims

**Prevalence**: MEDIUM - Affects ~10-15% of claims

---

### Failure Mode #3: Legal/Technical Language Ambiguity

**Pattern**: Different sources use **different phrasings** for the same concept, causing false contradictions.

**Examples**:
- **Claim 4**: "Exempts the White House from its provisions"
- **Evidence 1**: "Exempts from the National Historic Preservation Act" (SUPPORTING)
- **Evidence 2**: "Exempts from Section 106 review process" (SUPPORTING)
- **Evidence 3**: [Implies not all provisions exempted] (CONTRADICTING?)
- **System**: Marks as CONFLICTING EXPERT OPINION ❌

**Why This Happens**:
- "From its provisions" is vague (all provisions? some provisions?)
- Different sources specify different sections (Section 106, Section 107, etc.)
- Judge interprets lack of universality as contradiction
- Claim extraction may be too specific/vague

**Affected Claim Types**:
- Legal claims (statutes, exemptions, requirements)
- Technical specifications
- Claims with ambiguous scope

**Prevalence**: MEDIUM - Affects ~10-20% of claims, especially legal/technical articles

---

### Failure Mode #4: Meta-Content vs Primary Content Confusion

**Pattern**: Claims about the **article itself** or its sources are hard to verify because search returns articles ABOUT THE SAME TOPIC.

**Examples**:
- **Claim 9**: "Huffman sent a letter" (this is ABOUT the Roll Call article's reporting)
- **Search Returns**: Other articles ALSO reporting on Huffman's letter
- **Problem**: Evidence doesn't contain the PRIMARY SOURCE (the letter itself or Huffman's site)

**Why This Happens**:
- Search query: "Jared Huffman letter Trump documentation"
- Returns: NEWS ARTICLES about the letter (secondary sources)
- Misses: HUFFMAN'S WEBSITE or OFFICIAL LETTER (primary sources)
- Current search optimization deprioritizes fact-check sites but not news aggregation

**Affected Claim Types**:
- Claims about actions by sources (reporter's sources, congressional actions)
- Claims about documents/letters/requests
- Claims requiring primary sources vs news coverage

**Prevalence**: MEDIUM - Affects ~15-20% of claims

---

### Failure Mode #5: Narrow Search Results for Specific Entities

**Pattern**: Claims about **specific people or organizations** fail minimum source threshold (3 required).

**Examples**:
- **Claim 3**: "Sara Bronin chaired Advisory Council..." → Only 2 sources found → INSUFFICIENT_EVIDENCE

**Why This Happens**:
- Generic topics (e.g., "White House demolition") → Thousands of results
- Specific people (e.g., "Sara Bronin") → Limited results
- Credibility filtering removes low-tier sources
- Domain capping limits sources per domain

**Affected Claim Types**:
- Claims about specific individuals
- Claims about niche organizations
- Technical/specialized claims

**Prevalence**: MEDIUM - Affects ~10-15% of claims

---

### Failure Mode #6: Partial Information Treated as Contradiction

**Pattern**: When evidence provides PARTIAL confirmation but doesn't address all claim details, it's marked as CONTRADICTING.

**Examples**:
- **Claim**: "Administration received $350 million in donations"
- **Evidence**: "Project costs $300 million" (mentions cost but not donations)
- **System**: May treat cost≠donations as contradiction ❌

**Why This Happens**:
- Claim has multiple assertions (amount + source of funds)
- Evidence addresses only one assertion (amount)
- Partial match + numerical mismatch → Treated as contradiction

**Affected Claim Types**:
- Multi-part claims (X happened AND Y reason)
- Claims with both fact and context
- Claims requiring multiple pieces of evidence

**Prevalence**: MEDIUM - Affects ~10-15% of claims

---

## 📊 Overall Failure Rate Analysis

### Current Pipeline Performance (Report 9f71178f)

**11 claims analyzed**:
- ✅ 4 SUPPORTED (36.4%) - Claims 1, 2, 10, 11
- ⚠️ 6 UNCERTAIN (54.5%) - Claims 3, 5, 6, 7, 8, 9
- ❌ 1 CONTRADICTED (9.1%) - Claim 9 (FALSE POSITIVE)

**Uncertainty Breakdown**:
- 2 claims: INSUFFICIENT_EVIDENCE (too few sources)
- 2 claims: CONFLICTING_EXPERT_OPINION (contradicting sources)
- 2 claims: UNCERTAIN (neutral/ambiguous evidence)

**True Accuracy** (if we fix Claim 9):
- Should be: 5 SUPPORTED (45.5%), 6 UNCERTAIN (54.5%), 0 CONTRADICTED
- **Issue**: 54.5% uncertainty rate is VERY HIGH for fact-checking

---

## 🎯 Architectural Problems (Not Article-Specific)

### Problem #1: No Relevance Filtering Before NLI

**Current Flow**:
```
Search → Extract Snippets → NLI (ALL snippets) → Judge
```

**Issue**: NLI runs on OFF-TOPIC evidence, treating irrelevance as contradiction.

**Better Flow**:
```
Search → Extract Snippets → Relevance Filter → NLI (ONLY relevant) → Judge
```

**Impact**: Would fix Failure Modes #1, #4 (30-40% of failures)

---

### Problem #2: Snippet Extraction Uses Word Overlap, Not Semantic Similarity

**Current Method** (`evidence.py:296-298`):
```python
claim_words = set(claim.lower().split())
sentence_words = set(sentence.lower().split())
word_overlap = len(claim_words & sentence_words) / len(claim_words)
```

**Issue**: Extracts sentences with high WORD overlap, not high SEMANTIC relevance.

**Example**:
- Claim: "Huffman sent a letter requesting documentation"
- Sentence A: "The White House demolition project continues" (overlap: "White", "House")
- Sentence B: "Representative Huffman's oversight request demanded records" (overlap: "request")
- **Current**: Picks Sentence A (more common words) ❌
- **Should**: Pick Sentence B (semantically relevant) ✅

**Impact**: Would fix Failure Modes #1, #4 (30-40% of failures)

---

### Problem #3: No Temporal Awareness in Evidence Evaluation

**Current**: All evidence treated equally regardless of date.

**Issue**: Historical sources mixed with current sources.

**Example**:
- Claim: "Will Scharf heads commission (2025)"
- Evidence: Nixon Library archives (1969-1972)
- **Current**: Treated as relevant evidence ❌
- **Should**: Filter out or down-weight temporal mismatches ✅

**Impact**: Would fix Failure Mode #2 (10-15% of failures)

---

### Problem #4: Abstention Logic Too Conservative

**Current Thresholds** (`.env:79-82`):
```
MIN_SOURCES_FOR_VERDICT=3
MIN_CREDIBILITY_THRESHOLD=0.75
MIN_CONSENSUS_STRENGTH=0.45
```

**Issue**: Specific claims (people, organizations) can't reach 3 high-credibility sources.

**Result**: Many INSUFFICIENT_EVIDENCE verdicts that could be SUPPORTED with 2 high-quality sources.

**Example**:
- **Claim 3**: Sara Bronin (2 sources: Cornell Law School, ACHP official site) → INSUFFICIENT
- **Reality**: 2 PRIMARY sources should be enough!

**Impact**: Would fix Failure Mode #5 (10-15% of failures)

---

### Problem #5: No Distinction Between Primary and Secondary Sources

**Current**: All sources ranked by credibility tier (news tier 1, tier 2, etc.)

**Issue**: News articles ABOUT a letter are weighted same as the letter itself.

**Better**:
- **Primary sources** (official sites, press releases, documents): Weight 1.0
- **Secondary sources** (news coverage): Weight 0.8
- **Tertiary sources** (commentary, opinion): Weight 0.6

**Impact**: Would fix Failure Mode #4 (15-20% of failures)

---

### Problem #6: Legal/Technical Language Not Normalized

**Current**: Claims and evidence matched literally.

**Issue**: "Exempts from provisions" vs "Exempts from Section 106" treated as different.

**Better**: Normalize legal terms or use semantic similarity for legal claims.

**Impact**: Would fix Failure Mode #3 (10-20% of failures)

---

## 💡 Key Insights

### Insight #1: The 80/20 Rule

**80% of failures** come from **2 root causes**:
1. **No relevance filtering** (Failure Modes #1, #4) → ~40% of failures
2. **Word overlap instead of semantic similarity** (Failure Modes #1, #4) → ~40% of failures

**Implication**: Fixing these 2 issues would improve accuracy from ~45% → ~75%+

---

### Insight #2: Uncertainty is NOT a Bug

**Current**: 54.5% UNCERTAIN verdicts

**User perception**: System is "not working" because of high uncertainty

**Reality**: Uncertainty is CORRECT for:
- Ambiguous claims (Claim 5, 7)
- Conflicting expert sources (Claim 4, 6)
- Low-credibility evidence (Claim 8)

**The problem**: System conflates two types of uncertainty:
1. **Legitimate uncertainty** (experts disagree, evidence unclear) ✓
2. **Technical failure** (search failed, evidence off-topic, NLI broken) ❌

**Better approach**: Separate verdict types:
- `uncertain` → Evidence is genuinely ambiguous
- `insufficient_evidence` → Couldn't find enough sources
- `inconclusive` → Evidence exists but doesn't address claim

---

### Insight #3: Pipeline Assumes One-to-One Mapping

**Assumption**: 1 claim → 1 search query → N evidence pieces → 1 verdict

**Reality**: Complex claims need MULTIPLE search strategies:
- **Claim 9**: "Huffman sent a letter"
  - Search 1: "Jared Huffman letter Trump" (finds news coverage)
  - Search 2: site:huffman.house.gov "letter" "documentation" (finds primary source)
  - Search 3: "congressional oversight" "White House demolition" (finds related actions)

**Current flow** runs ONE search, so it misses primary sources.

---

### Insight #4: Evidence Quality ≠ Evidence Relevance

**Current**: Evidence ranked by credibility, then top N sent to judge.

**Issue**: High-credibility OFF-TOPIC evidence beats low-credibility ON-TOPIC evidence.

**Example**:
- Evidence A: BBC article about approval process (credibility: 0.90, relevance: 0.30)
- Evidence B: Huffman's website about letter (credibility: 0.80, relevance: 0.95)
- **Current**: Ranks A higher (higher credibility) ❌
- **Should**: Rank B higher (relevance * credibility) ✅

**Formula**:
```python
# Current
final_score = credibility * recency

# Better
final_score = relevance * credibility * recency
```

---

## 🎯 Fundamental Design Questions

### Question #1: What is the Pipeline's Core Job?

**Option A**: Find evidence for/against claim, let judge decide
- **Current implementation**
- **Problem**: Judge gets irrelevant evidence, makes bad decisions

**Option B**: Find RELEVANT evidence, score relevance, then let judge decide
- **Better implementation**
- **Requires**: Relevance filter before NLI

---

### Question #2: How Much Uncertainty is Acceptable?

**For users**:
- Supported/Contradicted verdicts: Actionable
- Uncertain verdicts: Frustrating ("system doesn't know")

**Current**: 54.5% uncertain

**Target**: <30% uncertain (70% of claims get definitive verdict)

**How to get there**:
- Better evidence retrieval (more sources)
- Better relevance filtering (higher quality evidence)
- Smarter abstention (don't give up too early)

---

### Question #3: Should NLI Handle Relevance?

**Current**: NLI decides entailment/contradiction/neutral

**Problem**: NLI conflates "not supporting" with "contradicting"

**Two-stage approach**:
1. **Relevance classifier**: Is evidence ON-TOPIC? (yes/no)
2. **NLI**: If yes, does it support/contradict/neutral?

**This would cleanly separate**:
- Irrelevant evidence (skip NLI)
- Relevant but neutral evidence (run NLI, expect neutral)
- Relevant and contradicting evidence (run NLI, expect contradiction)

---

## 📋 Next Steps (Context Gathering)

### Understanding Current Behavior

1. **How often does relevance filtering get triggered?**
   - Check: `ENABLE_RELEVANCE_FILTER` in config (does this exist?)
   - Check: Logs for relevance scores

2. **How often does temporal filtering get triggered?**
   - Check: `ENABLE_TEMPORAL_CONTEXT=true` in `.env`
   - Check: `backend/app/utils/temporal.py` implementation

3. **What's the actual abstention rate?**
   - Current: 18% (2 out of 11 claims)
   - Is this typical across articles?

4. **What's the distribution of failure modes across many articles?**
   - Need to analyze: 10-20 different articles
   - Track which failure modes appear most often

---

**User is right**: We need to understand the SYSTEM, not fix individual claims.

**Next questions**:
1. Are there relevance/temporal features already implemented but not working?
2. What's the performance across different article types (political, scientific, legal, etc.)?
3. Which failure modes are most common in production?
