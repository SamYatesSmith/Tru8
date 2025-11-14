# Judge System & Pipeline Architecture Analysis

**Date**: 2025-11-13
**Purpose**: Deep investigation into judge reasoning issues
**Status**: ANALYSIS COMPLETE - NO EDITS YET

---

## Executive Summary

The judge system has **THREE CRITICAL FAILURE MODES** causing incorrect verdicts:

1. **Credibility Paradox**: Snopes (0.95) has HIGHER credibility than PBS/BBC/NPR (0.90), causing fact-check META-CLAIMS to override PRIMARY sources
2. **Judge Over-Inference**: Judge adds qualifiers not in the claim ("all provisions" when claim just says "provisions"), creating false contradictions
3. **Context Blindness**: Both NLI and Judge fail to distinguish "fake rendering" from "fake project"

---

## Pipeline Architecture

### Flow Diagram

```
Content → INGEST → EXTRACT → RETRIEVE → VERIFY → JUDGE → Final Verdict
                     Claims    Evidence    NLI      LLM
```

### Detailed Pipeline Flow

#### 1. **RETRIEVE** (`retrieve.py`)
- **Input**: Claim text
- **Process**:
  - Web search (Brave/SERP API)
  - Government APIs (if enabled)
  - Fact-check APIs (Google Fact Check)
- **Output**: Evidence list with:
  - `snippet`: Text excerpt (150 chars)
  - `url`: Source URL
  - `published_date`: Publication date
  - `credibility_score`: 0.0-1.0 (from `source_credibility.json`)
  - `source_name`: Publisher name

#### 2. **VERIFY** (`verify.py`)
- **Input**: Claim + Evidence list
- **Process**:
  - NLI model (DeBERTa or BART) scores each evidence
  - For each claim-evidence pair:
    - `entailment_score`: How much evidence supports claim (0-1)
    - `contradiction_score`: How much evidence contradicts claim (0-1)
    - `neutral_score`: How unrelated evidence is (0-1)
  - Relationship determined by max score:
    - `entails` if entailment_score > others
    - `contradicts` if contradiction_score > others
    - `neutral` if neutral_score > others

**CRITICAL: Credibility-Weighted Aggregation**

```python
# From verify.py:544-553
supporting_weight = sum(
    v.get("evidence", {}).get("credibility_score", 0.6)
    for v in verifications
    if v.get("relationship") == "entails"
)

contradicting_weight = sum(
    v.get("evidence", {}).get("credibility_score", 0.6)
    for v in verifications
    if v.get("relationship") == "contradicts"
)
```

**This is where the Snopes problem occurs**:
- Snopes (0.95 credibility) saying "fake" gets 0.95 weight toward "contradicted"
- PBS (0.90) + BBC (0.90) + NPR (0.90) = 2.70 weight toward "supported"
- **BUT** if NLI scores Snopes highly (0.85+ contradiction_score), it can still win!

**Verdict Logic** (verify.py:560-570):
```python
if supporting_weight > contradicting_weight and max_entailment > 0.7:
    verdict = "supported"
elif contradicting_weight > supporting_weight and max_contradiction > 0.7:
    verdict = "contradicted"
else:
    verdict = "uncertain"
```

#### 3. **ABSTENTION LOGIC** (judge.py:447-518)

**Phase 3 Feature**: Judge abstains (refuses to make verdict) if:

1. **Too few sources**: < 3 sources → `insufficient_evidence`
2. **No authoritative sources**: No sources ≥ 0.75 credibility → `insufficient_evidence`
3. **Weak consensus**: < 0.50 consensus strength → `conflicting_expert_opinion`
4. **High-cred conflict**: High-cred sources disagree → `conflicting_expert_opinion`

**Consensus Calculation** (judge.py:520-565):
```python
# Credibility-weighted voting
supporting_weight = sum(cred_scores where stance == 'supporting')
contradicting_weight = sum(cred_scores where stance == 'contradicting')

# Neutral evidence counts as 40% support (not disagreement)
neutral_weight = sum(cred_scores * 0.4 where stance == 'neutral')

consensus_strength = max_weight / total_weight
```

**Problem**: This creates "conflicting_expert_opinion" when 1 high-cred source contradicts + 1 high-cred source supports, even if the contradiction is based on misinterpretation!

#### 4. **JUDGE** (`judge.py`)

**Model**: OpenAI GPT-4o-mini (or Claude Haiku fallback)

**Input Context** (judge.py:276-327):
```
CLAIM TO JUDGE: {claim_text}

EVIDENCE ANALYSIS:
Total Evidence Pieces: 3
Supporting Evidence: 2
Contradicting Evidence: 1

VERIFICATION METRICS:
Overall Verdict Signal: supported
Signal Confidence: 0.75
Max Entailment Score: 0.85
Max Contradiction Score: 0.78

EVIDENCE DETAILS:
[Evidence snippets with source, date, URL]
```

**Judge System Prompt** (judge.py:49-104):

Key sections:
1. **Verdicts**: supported, contradicted, uncertain
2. **Analysis Framework**: Quality, Signal Strength, Consensus, Context
3. **Numerical Tolerance**: ±15-20% for "roughly", exact for "precisely"
4. **Fact-Check Handling** (Lines 85-89):
   ```
   IMPORTANT - Handling Fact-Check Articles:
   - If evidence is from fact-checking sites (Snopes, FactCheck.org, etc.),
     recognize these are META-CLAIMS
   - A fact-check article saying "FALSE - claim X is debunked" means the
     OPPOSITE claim is supported
   - Focus on PRIMARY sources over fact-check meta-content
   - Do not be confused by double negatives
   ```

**Problem**: This guidance exists BUT the judge still gets confused when:
- Snippet is "Fact-check verdict: Fake..." without full context
- The fact-check is about something tangentially related (rendering vs project)

---

## Credibility Score System

**Source**: `backend/app/data/source_credibility.json`

### Tier Structure

| Tier | Credibility | Category | Examples |
|------|-------------|----------|----------|
| **Tier 0** | **0.95-1.00** | Factcheck, Government, Academic | Snopes, PolitiFact, FactCheck.org, .gov domains, .edu |
| **Tier 1** | **0.90** | International News | BBC, Reuters, AP, NPR, PBS |
| **Tier 2** | **0.85** | National Newspapers | NYTimes, WSJ, Guardian, Telegraph |
| **Tier 3** | **0.80** | Business/Tech News | Bloomberg, Financial Times, The Economist |
| **Tier 4** | **0.75** | Mainstream News | CNN, NBC, CBS, ABC, Time, Newsweek |
| **Tier 5** | **0.70** | Regional/Specialty | Local newspapers, trade publications |
| **Default** | **0.60** | Unknown | Any source not in database |

### Problem: Fact-Check Sites Have Highest Credibility

```json
"factcheck": {
  "credibility": 0.95,  // HIGHER than PBS/BBC/NPR (0.90)!
  "domains": [
    "snopes.com",
    "politifact.com",
    "factcheck.org",
    "fullfact.org",
    "apnews.com/ap-fact-check",
    "reuters.com/fact-check"
  ]
}
```

**Why this is a problem**:
- Fact-check sites publish META-CLAIMS about other claims
- Their articles often have headlines like "FALSE", "Fake", "Debunked"
- NLI model reads these headlines and scores them as "contradicting" the claim
- Because fact-checkers have 0.95 credibility, they can override 2-3 news sources at 0.90

---

## Failure Mode Analysis: The Two Problem Claims

### Failure Mode #1: Ballroom Claim (Claim 2)

**Claim**: "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom."

**Evidence Gathered**:
1. **Snopes** (0.95): "Rumored rendering of Trump's planned White House ballroom isn't ... Fact-check verdict: Fake..."
2. **PBS** (0.90): "Trump insists... adding the massive 90,000-square-foot, glass-walled space..."
3. **BBC** (0.90): "critics fear the new 90,000-sq-ft building..."

**What Happened**:

1. **NLI Scoring**:
   - Snopes snippet contains "Fact-check verdict: Fake"
   - NLI model: "Fake" = contradiction → scores Snopes as `contradicts` with high confidence (0.85+)
   - PBS/BBC: Confirmatory text → scores as `entails` with 0.70-0.80

2. **Aggregation**:
   ```
   contradicting_weight = 0.95 (Snopes)
   supporting_weight = 0.90 + 0.90 = 1.80 (PBS + BBC)

   max_contradiction = 0.85 (Snopes)
   max_entailment = 0.75 (PBS/BBC)
   ```

3. **Why "Contradicted" Won**:
   - `supporting_weight (1.80) > contradicting_weight (0.95)` ✓ Should support
   - BUT: `max_contradiction (0.85) > 0.7` ✓ High confidence contradiction exists
   - The algorithm requires BOTH weight advantage AND high max score
   - If Snopes' NLI score was 0.85+, it can flip verdict despite lower weight

4. **Judge Reasoning**:
   > "The highest quality evidence from Snopes indicates the claim is fake"

   **Problem**: Judge doesn't understand that Snopes is saying the RENDERING is fake, not the PROJECT.

**Root Causes**:
1. **Snippet Extraction**: Only extracted "Fact-check verdict: Fake" without context "Rumored RENDERING"
2. **NLI Context Blindness**: Model can't distinguish "fake rendering" from "fake claim"
3. **Credibility Paradox**: Snopes (0.95) beats news sources (0.90) in credibility
4. **Judge Prompt Ignored**: Despite having guidance on fact-check meta-claims, judge still trusted Snopes

---

### Failure Mode #2: Legal Exemption Claim (Claim 4)

**Claim**: "The National Historic Preservation Act of 1966 exempts the White House from its provisions."

**Evidence Gathered**:
1. **Bloomberg** (0.85): "the law doesn't apply to the White House... exempt under the 1966 act"
2. **BBC** (0.90): "three buildings and their grounds are exempt from the Section 106 review process"
3. **PBS** (0.90): "exemption in the Section 106 process of the National Historic Preservation Act of 1966"

**All three sources CONFIRM the exemption exists!**

**What Happened**:

1. **NLI Scoring**:
   - All 3 sources should score as `entails`
   - But judge ended up with `contradicted` verdict

2. **Judge Reasoning** (from PDF):
   > "The claim states that the National Historic Preservation Act of 1966 exempts the White House from its provisions. However, multiple high-quality sources confirm that the White House is indeed exempt from **certain provisions** of the act, particularly the Section 106 review process. This **contradicts** the claim that it is exempt from **all provisions** of the act."

**Problem**: The judge is **hallucinating** a qualifier!

- **Claim says**: "exempts the White House from its provisions"
- **Judge interprets as**: "exempts from ALL provisions"
- **Judge then says**: Evidence shows "certain provisions", so it's contradicted
- **But**: The claim NEVER said "all provisions"!

**Root Causes**:
1. **Judge Over-Inference**: Adding semantic qualifiers not in the text
2. **False Precision**: Treating absence of "certain" as presence of "all"
3. **No Prompt Guidance**: System prompt doesn't warn against adding qualifiers

This is a **REASONING ERROR**, not a credibility or NLI problem.

---

## Current Settings

### Feature Flags (`backend/.env`)

```bash
# Judge Configuration
ENABLE_JUDGE_FEW_SHOT=true          # Uses few-shot examples
JUDGE_MAX_TOKENS=1000
JUDGE_TEMPERATURE=0.3                # Low = more deterministic

# Verification
ENABLE_DEBERTA_NLI=true              # Using DeBERTa model (better than BART)
NLI_CONFIDENCE_THRESHOLD=0.7

# Abstention
ENABLE_ABSTENTION_LOGIC=true
MIN_SOURCES_FOR_VERDICT=3
MIN_CREDIBILITY_THRESHOLD=0.60       # Lowered from 0.75
MIN_CONSENSUS_STRENGTH=0.50          # Lowered from 0.65
```

**Note**: Abstention thresholds were LOWERED in Phase 3 to reduce "fence-sitting". This may have made the problem WORSE by allowing weak evidence to produce verdicts.

---

## Problem Summary

### Issue #1: Credibility Paradox

**Problem**: Fact-check sites (0.95) have higher credibility than primary news sources (0.90).

**Impact**: When fact-check meta-claims are misinterpreted, they override multiple authoritative sources.

**Example**: Snopes "fake rendering" overrides PBS + BBC + NPR about the actual project.

---

### Issue #2: Snippet Context Loss

**Problem**: Evidence snippets are truncated to 150 characters, losing critical context.

**From `retrieve.py:283-294`**:
```python
snippet = ev.get("snippet", ev.get("text", ""))[:150]  # Only 150 chars!
```

**Impact**:
- "Rumored rendering of Trump's planned White House ballroom isn't real. Fact-check verdict: Fake..."
- Becomes: "Fact-check verdict: Fake..."
- NLI sees "Fake" without "rendering" context

---

### Issue #3: Judge Over-Inference

**Problem**: Judge adds qualifiers and semantic interpretations not present in claim.

**Example**:
- Claim: "exempts the White House from its provisions"
- Judge reads: "exempts from ALL provisions"
- Evidence: "exempt from certain provisions"
- Judge concludes: CONTRADICTED (because "all" ≠ "certain")

**Impact**: Creates false contradictions through phantom qualifiers.

---

### Issue #4: NLI Context Blindness

**Problem**: NLI model can't distinguish between:
- "The claim about a rendering is fake" (meta-claim)
- "The claim about the project is fake" (direct claim)

**Impact**: Model scores fact-check META-CLAIMS as if they're about the PRIMARY claim.

---

### Issue #5: Abstention Logic Creates False "Conflicting Opinion"

**Problem**: When 1 high-cred source contradicts (even if misinterpreted) + 1 high-cred source supports, system marks as "conflicting_expert_opinion".

**From `judge.py:500-506`**:
```python
if high_cred_supporting > 0 and high_cred_contradicting > 0:
    return (
        "conflicting_expert_opinion",
        f"High-credibility sources conflict: {high_cred_supporting} support, "
        f"{high_cred_contradicting} contradict. Expert opinion divided.",
        consensus_strength
    )
```

**Impact**: System abstains from verdict even when the "conflict" is due to misinterpretation.

---

## Recommendations (For Discussion)

### Short-Term Fixes (High Impact, Low Risk)

#### 1. **Adjust Fact-Check Credibility**
**Current**: Snopes/PolitiFact = 0.95
**Proposed**: 0.85-0.88 (below BBC/PBS/NPR)

**Rationale**: Fact-check sites publish meta-analysis, not primary evidence. Should not override multiple primary sources.

#### 2. **Increase Evidence Snippet Length**
**Current**: 150 chars
**Proposed**: 300-400 chars

**Rationale**: Capture more context to distinguish "fake rendering" from "fake project".

#### 3. **Improve Judge Prompt**
Add explicit instructions:
```
CRITICAL - Do NOT Add Qualifiers:
- If claim says "exempts from provisions", do NOT interpret as "all provisions"
- If claim says "roughly $350M", do NOT require exactly $350M
- Judge ONLY what the claim explicitly states
- Do NOT infer semantic qualifiers (all, some, certain, etc.) unless present
```

#### 4. **Add Evidence Relevance Pre-Filter**
Before sending to judge, score each evidence for relevance:
- "Fake rendering" article → LOW relevance to "ballroom project" claim
- Direct confirmation → HIGH relevance

### Medium-Term Fixes (Higher Impact, Moderate Risk)

#### 5. **Implement Fact-Check Detection**
- Detect when evidence is from fact-check site
- Parse fact-check target (what claim are they checking?)
- Only use if target matches our claim
- Otherwise, discount credibility

#### 6. **Enhance NLI with Context Window**
- Pass more context to NLI model (currently 512 tokens)
- Include article title + snippet (not just snippet)
- Helps model understand "fake rendering" vs "fake project"

#### 7. **Add Judge Self-Critique Step**
- After generating verdict, ask judge: "Did you add any qualifiers not in the claim?"
- If yes, regenerate without adding qualifiers
- Two-pass judgment system

### Long-Term Fixes (Highest Impact, Highest Risk)

#### 8. **Multi-Stage Evidence Routing**
```
Evidence → Relevance Filter → NLI Verification → Judge
           ↓
    Discard low-relevance
    (e.g., tangential fact-checks)
```

#### 9. **Ensemble Verification**
- Run multiple NLI models (DeBERTa + BART + custom fine-tuned)
- Average scores to reduce single-model bias
- Particularly important for nuanced cases

#### 10. **Judge Fine-Tuning**
- Collect examples of judge failures (like these)
- Fine-tune judge model to:
  - Not add qualifiers
  - Better understand fact-check meta-claims
  - Better handle numerical tolerance

---

## Test Cases to Validate Fixes

### Test Case 1: Ballroom Project
**Claim**: "The East Wing demolition project is part of plans to construct a 90,000-square-foot ballroom."
**Expected**: SUPPORTED (PBS + BBC + NPR confirm)
**Current**: contradicted (Snopes "fake rendering" overrides)

### Test Case 2: Legal Exemption
**Claim**: "The National Historic Preservation Act of 1966 exempts the White House from its provisions."
**Expected**: SUPPORTED (all sources confirm exemption)
**Current**: contradicted (judge adds "all provisions" qualifier)

### Test Case 3: Numerical Tolerance
**Claim**: "The project received roughly $350 million in donations."
**Expected**: SUPPORTED with tolerance (actual = $320M, "roughly" allows ±15%)
**Current**: To be tested

### Test Case 4: Fact-Check Meta-Claim
**Claim**: "Tesla delivered 1.3 million vehicles in 2022."
**Evidence**: Snopes article "FALSE: Claim that Tesla delivered 2 million vehicles is fake"
**Expected**: SUPPORTED (Snopes contradicts a DIFFERENT claim)
**Current**: Unknown (needs testing)

---

## Next Steps

**For Discussion**:
1. Which fixes should we prioritize?
2. Should we adjust credibility scores first (easiest) or judge prompt (more impactful)?
3. Do you want to see the judge prompt rewritten before implementation?
4. Should we add evidence relevance scoring as a pre-filter?

**No code changes have been made yet** - waiting for your direction on which approach to take.

---

## Files Referenced

- `backend/app/pipeline/judge.py` - Judge logic and prompt (710 lines)
- `backend/app/pipeline/verify.py` - NLI verification and aggregation (617 lines)
- `backend/app/pipeline/retrieve.py` - Evidence retrieval (1000+ lines)
- `backend/app/data/source_credibility.json` - Credibility scores
- `backend/app/core/config.py` - Feature flags and settings

---

**Analysis Complete**: 2025-11-13 15:00 UTC
