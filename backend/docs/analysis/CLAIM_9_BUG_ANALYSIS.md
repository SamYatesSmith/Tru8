# Claim 9 Logic Bug: Multi-Stage Failure Analysis

**Date**: 2025-11-14
**Report**: 9f71178f (68/100)
**Status**: CRITICAL CODE LOGIC BUG

---

## 🚨 The Problem

**Claim 9**: "House Natural Resources ranking member Jared Huffman and other Democrats sent a letter to Trump requesting documentation on the demolition and plans for the ballroom."

**System Verdict**: **CONTRADICTED 90%** ❌

**Expected Verdict**: **SUPPORTED** ✅ (Huffman's website confirms the letter)

**Judge's Faulty Reasoning**:
> "However, the evidence includes strong contradicting sources indicating that the demolition does not require approval and that the project is being funded privately, which suggests that there may not have been a formal request for documentation as claimed."

---

## 🔍 Root Cause: 3-Stage Logic Failure

### Stage 1: Search Returns Off-Topic Evidence ❌

**What Should Happen**:
```
Claim: "Huffman sent a letter requesting documentation"
Search Query: "Jared Huffman letter Trump White House demolition documentation request"
Expected Results:
  1. Huffman's official letter (huffman.house.gov)
  2. News coverage of the letter (Politico, The Hill, etc.)
  3. Congressional oversight reports
```

**What Actually Happens**:
```
Evidence Retrieved (from PDF):
  1. U.S. Congressman Jared Huffman website (general news page)
  2. PolitiFact article about "Trump flip-flop"
  3. FactCheck.org article about "funding and ethics"
```

**The Bug**: Evidence snippets extracted from these pages **do NOT contain text about the Huffman letter**. They contain text about:
- Whether demolition requires approval (IRRELEVANT to claim)
- Project funding sources (IRRELEVANT to claim)
- Trump's policy changes (IRRELEVANT to claim)

---

### Stage 2: NLI Misinterprets OFF-TOPIC as CONTRADICTING ❌

**NLI's Job**: Compare evidence snippet to claim and determine relationship

**Example of What NLI Sees**:

```python
# Input to NLI Model
premise = "The demolition does not require federal approval and the project is being funded privately through donations from tech companies."
hypothesis = "Jared Huffman and other Democrats sent a letter to Trump requesting documentation on the demolition and plans for the ballroom."

# NLI Output
{
    'entailment': 0.05,      # Low - evidence doesn't support claim
    'neutral': 0.15,         # Low - NLI thinks they're related
    'contradiction': 0.80    # HIGH - NLI treats "off-topic" as "contradicting"
}
```

**The Bug**: NLI model treats **IRRELEVANT** evidence as **CONTRADICTING** instead of **NEUTRAL**.

**Why This Happens**:
- The evidence talks about approval requirements and funding
- The claim talks about a letter being sent
- NLI sees no overlap → scores as CONTRADICTION
- **But these are INDEPENDENT FACTS!** Approval not being required doesn't mean a letter wasn't sent!

**Correct Behavior**:
```python
# When evidence is OFF-TOPIC (mentions completely different aspect)
# NLI should return:
{
    'entailment': 0.05,      # Evidence doesn't support
    'neutral': 0.90,         # ✅ EVIDENCE IS IRRELEVANT - should be NEUTRAL
    'contradiction': 0.05    # Not contradicting, just not related
}
```

---

### Stage 3: Judge Trusts NLI Contradiction Scores ❌

**What Judge Sees** (from `judge.py:330-349`):

```
CLAIM TO JUDGE:
House Natural Resources ranking member Jared Huffman and other Democrats sent a letter to Trump requesting documentation on the demolition and plans for the ballroom.

VERIFICATION METRICS:
Supporting Evidence: 0 pieces
Contradicting Evidence: 3 pieces  ← BUG: These are OFF-TOPIC, not contradicting!
Neutral Evidence: 0 pieces

Max Entailment Score: 0.15
Max Contradiction Score: 0.80

EVIDENCE DETAILS:
Evidence 1:
Source: U.S. Congressman Jared Huffman
Content: [snippet about demolition not requiring approval...]  ← IRRELEVANT!

Evidence 2:
Source: PolitiFact
Content: [snippet about Trump flip-flopping on East Wing...]  ← IRRELEVANT!

Evidence 3:
Source: FactCheck.org
Content: [snippet about private funding sources...]  ← IRRELEVANT!
```

**Judge's Logic** (lines 48-132 in `judge.py`):
1. Sees 3 "contradicting" pieces (from NLI scores)
2. Sees high contradiction score (0.80)
3. Reads snippets that discuss approval/funding (not the letter)
4. **Faulty inference**: "Approval not required → Therefore no letter was sent"
5. Returns: CONTRADICTED 90%

**The Bug**: Judge prompt doesn't instruct the model to detect **IRRELEVANT** evidence. It trusts the NLI scores blindly.

---

## 📊 Why This is a Code Logic Bug (Not External Service Issue)

### Evidence This is Internal Logic, Not API Failures:

1. **Search DID retrieve correct sources**:
   - `huffman.house.gov` ✅ (Congressman's official site - PRIMARY SOURCE!)
   - This source SHOULD contain the letter or reference to it

2. **HTTP requests succeeded**:
   - All 3 sources returned content (no timeouts, no 403 errors)
   - Snippets were successfully extracted

3. **NLI model worked correctly** (technically):
   - Model DID run inference
   - Model DID return scores
   - **But the scores are based on IRRELEVANT snippets!**

4. **Judge followed its programming**:
   - Judge saw "contradicting" signals
   - Judge read snippets about approval/funding
   - Judge made a logical inference (albeit flawed)

---

## 🐛 The Actual Bugs in Code

### Bug #1: Evidence Snippet Extraction (MEDIUM)

**Location**: `backend/app/services/evidence.py:275-334`

**The Issue**: `_find_relevant_snippet()` uses simple word overlap scoring:

```python
# Line 296-298
claim_words = set(claim.lower().split())
sentence_words = set(sentence.lower().split())
word_overlap = len(claim_words & sentence_words) / len(claim_words)
```

**For Claim 9**:
```python
claim_words = {'huffman', 'democrats', 'sent', 'letter', 'requesting', 'documentation', ...}

# Snippet from huffman.house.gov page:
sentence_words = {'demolition', 'white', 'house', 'east', 'wing', 'federal', 'approval', ...}

word_overlap = len({'house'}) / 15 = 0.067  # Only "house" overlaps!
```

**Result**: The function picks sentences that mention "White House demolition" but NOT sentences that mention "Huffman letter documentation request".

**Fix Needed**: Use semantic similarity instead of word overlap, OR prioritize sentences containing claim entities ("Huffman", "letter", "documentation").

---

### Bug #2: NLI Treats Irrelevance as Contradiction (CRITICAL)

**Location**: `backend/app/pipeline/verify.py:382-392` (NLI inference)

**The Issue**: NLI model (DeBERTa-v3-base-mnli-fever-anli) is trained for entailment detection, not relevance filtering.

**Current Behavior**:
```
Input:
  Evidence: "The demolition does not require federal approval."
  Claim: "Huffman sent a letter requesting documentation."

Output:
  entailment: 0.05 (evidence doesn't support claim)
  contradiction: 0.80  ← BUG: Evidence doesn't CONTRADICT claim, it's IRRELEVANT!
  neutral: 0.15
```

**Expected Behavior**:
```
Output:
  entailment: 0.05 (evidence doesn't support claim)
  neutral: 0.90  ← Evidence is OFF-TOPIC, should be neutral
  contradiction: 0.05
```

**Why This Happens**:
- NLI models are trained to classify relationship between two statements
- When statements are about DIFFERENT topics, models often default to "contradiction"
- **Contradiction is being used as "not-entailment" instead of "disproves"**

**Fix Needed**: Add a **relevance pre-filter** before NLI scoring:
1. Check semantic similarity between evidence and claim
2. If similarity < threshold (e.g., 0.4), mark as NEUTRAL and skip NLI
3. Only run NLI on evidence that's actually ABOUT the claim

---

### Bug #3: Judge Doesn't Detect Irrelevant Evidence (HIGH)

**Location**: `backend/app/pipeline/judge.py:48-132` (system prompt)

**The Issue**: Judge prompt has NO instructions for handling irrelevant evidence.

**Current Prompt** (lines 113-117):
```
IMPORTANT - Handling Fact-Check Articles:
- If evidence is from fact-checking sites (Snopes, FactCheck.org, etc.), recognize these are META-CLAIMS
- A fact-check article saying "FALSE - claim X is debunked" means the OPPOSITE claim is supported
- Focus on PRIMARY sources (scientific studies, government data, news reports) over fact-check meta-content
- Do not be confused by double negatives in fact-check headlines
```

**Missing Instruction**:
```
IMPORTANT - Handling Irrelevant Evidence:
- If evidence discusses a DIFFERENT TOPIC than the claim, mark as NEUTRAL (not contradicting)
- Examples of irrelevant evidence:
  - Claim: "Person A sent a letter" + Evidence: "The letter doesn't require approval" → IRRELEVANT (different aspects)
  - Claim: "Event happened on June 5th" + Evidence: "Event didn't require permits" → IRRELEVANT
- Only mark as CONTRADICTING if evidence DIRECTLY DISPROVES the claim
- Example: Claim: "Person A sent a letter" + Evidence: "No letter was ever sent" → CONTRADICTS ✓
```

**Fix Needed**: Add explicit instructions for detecting and handling OFF-TOPIC evidence.

---

### Bug #4: No Relevance Scoring in Verification Stage (MEDIUM)

**Location**: `backend/app/pipeline/verify.py` (entire file)

**The Issue**: Evidence → NLI happens WITHOUT checking if evidence is relevant to the claim.

**Current Flow**:
```
1. Search returns 10 URLs for claim
2. Extract snippets from each URL
3. Run NLI on ALL snippets (no relevance filter)
4. Return all NLI scores to judge
```

**Better Flow**:
```
1. Search returns 10 URLs for claim
2. Extract snippets from each URL
3. ✨ NEW: Calculate semantic similarity(snippet, claim)
4. ✨ NEW: If similarity < 0.4 → Mark as NEUTRAL, skip NLI
5. Run NLI only on relevant snippets (similarity >= 0.4)
6. Return NLI scores + relevance scores to judge
```

**Fix Needed**: Add relevance filter before NLI verification.

---

## 🎯 Recommended Fixes (Priority Order)

### Fix #1: Add Relevance Pre-Filter (IMMEDIATE - Highest Impact)

**File**: `backend/app/pipeline/verify.py`

**Before NLI** (around line 380), add relevance check:

```python
from app.services.embeddings import get_embedding_service, calculate_semantic_similarity

async def verify_evidence_for_claims_batch(self, claims, evidence_by_claim):
    """Verify evidence with relevance filtering"""

    embedding_service = await get_embedding_service()

    for claim_id, evidence_list in evidence_by_claim.items():
        claim_text = claims[claim_id]['text']

        for evidence_item in evidence_list:
            evidence_text = evidence_item.get('text', '')

            # NEW: Check relevance before running NLI
            relevance_score = await calculate_semantic_similarity(claim_text, evidence_text)
            evidence_item['relevance_score'] = relevance_score

            # If evidence is OFF-TOPIC, skip NLI and mark as neutral
            if relevance_score < 0.4:  # Threshold for relevance
                logger.info(f"Evidence irrelevant (similarity {relevance_score:.2f}), skipping NLI")
                evidence_item['nli_entailment'] = 0.05
                evidence_item['nli_neutral'] = 0.90  # HIGH neutral for off-topic
                evidence_item['nli_contradiction'] = 0.05
                evidence_item['nli_stance'] = 'neutral'
                evidence_item['relevance_filtered'] = True
                continue  # Skip NLI for this evidence

            # Run NLI only for relevant evidence
            nli_result = await self._run_nli(claim_text, evidence_text)
            evidence_item.update(nli_result)
            evidence_item['relevance_filtered'] = False
```

**Expected Impact**:
- Claim 9 evidence about "approval not required" will be marked NEUTRAL (not contradicting)
- Judge will see 0 contradicting pieces, 3 neutral pieces
- Verdict will change from CONTRADICTED → UNCERTAIN (appropriate when evidence is off-topic)

---

### Fix #2: Improve Evidence Snippet Extraction (HIGH)

**File**: `backend/app/services/evidence.py:275-334`

**Replace word overlap with semantic similarity**:

```python
def _find_relevant_snippet(self, content: str, claim: str) -> Optional[str]:
    """Find the most relevant snippet using semantic similarity"""
    from app.services.embeddings import get_embedding_service, calculate_semantic_similarity

    if not content or len(content) < 50:
        return None

    # Split into sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]

    if not sentences:
        return None

    # NEW: Use semantic similarity instead of word overlap
    embedding_service = get_embedding_service()  # Initialize once
    scored_sentences = []

    for sentence in sentences:
        if len(sentence) < 20:
            continue

        # Calculate semantic similarity
        similarity_score = calculate_semantic_similarity(claim, sentence)

        # Bonus for fact-indicating phrases
        fact_bonus = sum(1 for indicator in self.fact_indicators if indicator in sentence.lower()) * 0.1

        # Bonus for numbers/dates
        number_bonus = len(re.findall(r'\d+', sentence)) * 0.05

        total_score = similarity_score + fact_bonus + number_bonus
        scored_sentences.append((sentence, total_score))

    if not scored_sentences:
        return None

    # Sort by semantic similarity score
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    # Build snippet from top sentences
    snippet_sentences = []
    total_words = 0

    for sentence, score in scored_sentences[:3]:
        words = sentence.split()
        if total_words + len(words) <= self.max_snippet_words:
            snippet_sentences.append(sentence)
            total_words += len(words)
        else:
            break

    if snippet_sentences:
        return '. '.join(snippet_sentences) + '.'
    else:
        return scored_sentences[0][0][:self.max_snippet_words * 6]
```

**Expected Impact**:
- Snippets from `huffman.house.gov` will contain text about "Huffman", "letter", "documentation request"
- Instead of generic text about "demolition", "approval", "funding"
- Better evidence → Better NLI scores → Better verdicts

---

### Fix #3: Update Judge Prompt (MEDIUM)

**File**: `backend/app/pipeline/judge.py:84-117`

**Add new section to system prompt**:

```python
self.system_prompt = """You are an expert fact-checker making final verdicts on claims based on evidence analysis.

...

CRITICAL - Detecting Irrelevant Evidence:
- Before marking evidence as CONTRADICTING, verify it actually ADDRESSES the claim
- Evidence that discusses a DIFFERENT ASPECT of the topic is IRRELEVANT, not contradicting
- Examples of IRRELEVANT (not contradicting) evidence:
  ❌ Claim: "Person A sent a letter" + Evidence: "Letters don't require approval" → DIFFERENT TOPICS
  ❌ Claim: "Event costs $500M" + Evidence: "Event funded by donations" → DIFFERENT ASPECTS
  ✓  Claim: "Person A sent a letter" + Evidence: "No letter was ever sent" → DIRECT CONTRADICTION
  ✓  Claim: "Event costs $500M" + Evidence: "Event costs $300M" → DIRECT CONTRADICTION

- When evidence is OFF-TOPIC or discusses unrelated aspects, treat as NEUTRAL
- Only mark as CONTRADICTING when evidence DIRECTLY DISPROVES the claim's core assertion

CRITICAL - Logical Fallacies to Avoid:
- Do NOT infer: "Action X doesn't require approval → Therefore action X didn't happen"
- Do NOT infer: "Project funded privately → Therefore no oversight requests were made"
- Do NOT infer: "Law exempts building → Therefore no agencies were consulted"
- Absence of requirement ≠ Absence of action

...
"""
```

**Expected Impact**:
- Judge will better detect when evidence is off-topic
- Reduces false CONTRADICTED verdicts
- Improves reasoning quality

---

## 📊 Expected Outcomes After Fixes

### Claim 9 Behavior:

**Before Fixes**:
```
Evidence: "Demolition doesn't require approval" (OFF-TOPIC)
NLI Score: 0.80 contradiction
Judge Verdict: CONTRADICTED 90%
```

**After Fix #1 (Relevance Filter)**:
```
Evidence: "Demolition doesn't require approval" (OFF-TOPIC)
Relevance Score: 0.25 (below threshold)
NLI Score: SKIPPED (marked as 0.90 neutral)
Judge Verdict: UNCERTAIN 60% (insufficient relevant evidence)
```

**After Fix #2 (Better Snippet Extraction)**:
```
Evidence: "Rep. Jared Huffman sent letter to White House requesting documentation on demolition plans and environmental review" (ON-TOPIC!)
Relevance Score: 0.85
NLI Score: 0.92 entailment
Judge Verdict: SUPPORTED 90% ✅
```

---

## 🚀 Implementation Priority

### Phase 1: Relevance Filter (2-3 hours)
- ✅ Highest impact fix
- ✅ Prevents off-topic evidence from causing false contradictions
- ✅ Relatively simple to implement (add semantic similarity check)

### Phase 2: Snippet Extraction (3-4 hours)
- ✅ Ensures evidence contains relevant text
- ✅ Improves quality upstream (better input → better output)
- ⚠️ Requires embedding service (already available)

### Phase 3: Judge Prompt (30 minutes)
- ✅ Quick win, adds safety net
- ✅ Helps even when relevance filter misses edge cases
- ✅ Improves explainability

---

## 💡 Key Insight: The Real Problem

**The system confuses 3 different relationships**:

1. **SUPPORTING**: Evidence confirms the claim
   - Claim: "It rained in London" + Evidence: "London weather service reports rain" ✓

2. **CONTRADICTING**: Evidence disproves the claim
   - Claim: "It rained in London" + Evidence: "London was dry and sunny" ✓

3. **IRRELEVANT**: Evidence discusses something else
   - Claim: "It rained in London" + Evidence: "Paris had sunshine"
   - **Current system**: Marks as CONTRADICTING ❌
   - **Should be**: Marks as NEUTRAL ✅

**Root Cause**: No relevance filtering before NLI. NLI treats "not-supporting" as "contradicting".

**Solution**: Add explicit relevance check. Only run NLI on evidence that's ABOUT the claim.

---

**Next Step**: Implement Fix #1 (relevance filter) to stop off-topic evidence from causing false contradictions.
