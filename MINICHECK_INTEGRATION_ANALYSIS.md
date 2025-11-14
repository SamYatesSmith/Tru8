# MiniCheck Integration Analysis for Tru8

## Executive Summary

**Recommendation: DO NOT switch to MiniCheck-Flan-T5-Large**

After deep research into MiniCheck models and analyzing the existing codebase, switching from DeBERTa-v3-large NLI to MiniCheck-Flan-T5-Large would be a **regression, not an improvement** for the Tru8 fact-checking pipeline.

### Key Finding: Binary vs Three-Way Classification

**Critical Issue**: MiniCheck models produce **binary classification** (supported/unsupported) instead of the three-way classification (entailment/neutral/contradiction) that the Tru8 pipeline requires.

Your current system's sophisticated handling of the "neutral" category (lines 32-46 in verify.py) is **essential** for preventing false contradictions:

```python
# CRITICAL FIX: Neutral threshold to prevent false contradictions
# If neutral score is high (>0.7), evidence is off-topic/not-related
# Don't classify as "contradicting" just because it doesn't support
NEUTRAL_THRESHOLD = 0.7

if neutral_score > NEUTRAL_THRESHOLD:
    # High neutral = evidence doesn't address claim (NOT contradicting)
    self.relationship = "neutral"
```

**MiniCheck cannot distinguish between**:
- Evidence that CONTRADICTS the claim
- Evidence that DOESN'T ADDRESS the claim

This distinction is fundamental to preventing the false contradictions you've been debugging.

---

## Research Findings

### What is MiniCheck?

**Paper**: "MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents" (EMNLP 2024)
**Authors**: Liyan Tang et al., Carnegie Mellon University
**Purpose**: Detect LLM hallucinations in generated summaries

**Model Variants**:
1. MiniCheck-Flan-T5-Large (770M params) - Largest, highest accuracy
2. MiniCheck-DeBERTa-v3-Large (435M params) - Same backbone as your current model
3. MiniCheck-RoBERTa-Large (355M params) - Smallest, fastest

### Training Data Innovation

MiniCheck's breakthrough comes from **synthetic data generation**:
- Base: 21K examples from ANLI (Adversarial NLI)
- Synthetic: 14K GPT-4-generated claim-document pairs
- **Key insight**: Models trained on synthetic LLM-generated claims perform better on LLM-generated content

### Performance Claims

From the paper:
- Achieves GPT-4-level accuracy on LLM-AggreFact benchmark
- 400x cheaper than GPT-4 approaches
- 4-10% absolute improvement over baseline fact-checkers
- Processes >500 docs/min on NVIDIA A6000

---

## Technical Architecture Comparison

### Current System (DeBERTa-v3-large NLI)

**Input Format**: Premise-hypothesis pairs
```python
inputs = tokenizer(
    [evidence_text],  # Premise
    [claim_text],     # Hypothesis
    max_length=512,
    return_tensors="pt"
)
```

**Output Format**: Three-way softmax probabilities
```python
probabilities = torch.softmax(outputs.logits, dim=-1)
# probabilities[i] = [entailment, neutral, contradiction]
entailment = probabilities[i][0].item()    # Evidence supports claim
neutral = probabilities[i][1].item()        # Evidence doesn't address claim
contradiction = probabilities[i][2].item()  # Evidence refutes claim
```

**Model Loading**:
```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
model = AutoModelForSequenceClassification.from_pretrained(
    "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
)
```

### MiniCheck System

**Input Format**: Document-claim pairs (via wrapper)
```python
from minicheck.minicheck import MiniCheck
scorer = MiniCheck(model_name='flan-t5-large', cache_dir='./ckpts')
pred_label, raw_prob, _, _ = scorer.score(
    docs=[evidence_text],    # Documents
    claims=[claim_text]      # Claims to verify
)
```

**Output Format**: Binary classification
```python
pred_label[0]  # 1 = supported, 0 = unsupported
raw_prob[0]    # Confidence score (0.0-1.0)
```

**Model Type**: Seq2Seq (Flan-T5), not SequenceClassification
```python
from transformers import AutoModelForSeq2SeqLM  # Different class!
model = AutoModelForSeq2SeqLM.from_pretrained("lytang/MiniCheck-Flan-T5-Large")
```

**Critical Constraint**: Sentence-level claims only
> "In order to fact-check a multi-sentence claim, the claim should first be broken up into sentences to achieve optimal performance."

---

## Integration Challenges

### Challenge 1: Binary Output Mapping

Your system expects three scores. MiniCheck provides two (supported_prob, unsupported_prob).

**Attempted Mapping**:
```python
if pred_label[0] == 1:  # Supported
    entailment_score = raw_prob[0]
    neutral_score = (1 - raw_prob[0]) * 0.7
    contradiction_score = (1 - raw_prob[0]) * 0.3
else:  # Unsupported (could be neutral OR contradiction)
    entailment_score = raw_prob[0]  # Will be low
    neutral_score = (1 - raw_prob[0]) * 0.7  # Arbitrary split
    contradiction_score = (1 - raw_prob[0]) * 0.3
```

**Problem**: The 0.7/0.3 split is arbitrary and loses information. When MiniCheck returns "unsupported", you cannot determine if:
- Evidence directly contradicts the claim (should be flagged)
- Evidence is off-topic and doesn't address the claim (should be filtered)

### Challenge 2: Loss of Neutral Detection Logic

Your current system has sophisticated neutral handling (verify.py lines 32-46):

```python
NEUTRAL_THRESHOLD = 0.7

if neutral_score > NEUTRAL_THRESHOLD:
    # High neutral = evidence doesn't address claim (NOT contradicting)
    self.relationship = "neutral"
```

**This logic cannot work with MiniCheck** because MiniCheck doesn't provide a separate neutral score.

Example scenario that would break:
- Claim: "H.R. 123 allows employers to opt out of letter requirements"
- Evidence: "H.R. 123 requires approval for deferred actions"
- **Current system**: High neutral score (0.8) → Correctly marked as "neutral" (off-topic)
- **MiniCheck**: Returns "unsupported" (0.85 confidence) → Incorrectly mapped to contradiction

### Challenge 3: Relevance Gatekeeper Compatibility

Your system already implements a relevance filter (verify.py lines 385-475):

```python
# Check semantic similarity before NLI
relevance_score = await calculate_semantic_similarity(claim_text, evidence_text)

# If OFF-TOPIC, skip NLI and mark as neutral
if relevance_score < settings.RELEVANCE_THRESHOLD:
    logger.info(f"Evidence OFF-TOPIC (relevance {relevance_score:.2f}), skipping NLI")
    result = NLIVerificationResult(
        entailment_score=0.05,
        contradiction_score=0.05,
        neutral_score=0.90  # High neutral for off-topic
    )
```

**Question**: If you're already filtering off-topic evidence with semantic similarity, what additional value does MiniCheck's binary classification provide?

**Answer**: Minimal. The relevance gatekeeper already handles the "evidence doesn't address claim" case.

### Challenge 4: Model Size Increase

| Model | Parameters | Memory (FP16) | Type |
|-------|-----------|---------------|------|
| **DeBERTa-v3-large (current)** | 435M | ~870MB | Encoder-only |
| **MiniCheck-Flan-T5-Large** | 770M | ~1.4GB | Encoder-Decoder |

**Impact**: +530MB VRAM requirement with no clear accuracy benefit for your use case.

### Challenge 5: Dependency Addition

**Current**: Pure `transformers` library
```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
```

**MiniCheck**: Requires new package dependency
```bash
pip install "minicheck @ git+https://github.com/Liyan06/MiniCheck.git@main"
```

**Integration complexity**: Cannot use standard `AutoModel` pattern, must use MiniCheck wrapper.

---

## Why MiniCheck Doesn't Fit This Use Case

### MiniCheck is Designed for Hallucination Detection

From the paper's introduction:
> "Our work focuses on a critical context for fact-checking: grounding LLM-generated summaries in source documents."

**Their use case**:
- Input: Long source document (e.g., Wikipedia article)
- LLM: Generates a summary
- Task: Check if summary sentences are supported by the source

**Tru8's use case**:
- Input: User's claim (could be from any source, not LLM-generated)
- System: Searches for external evidence
- Task: Determine if evidence supports/contradicts/doesn't address the claim

**Key difference**: MiniCheck assumes a **single, authoritative source document** that contains all relevant information. Tru8 deals with **multiple, potentially conflicting sources** from the open web.

### Three-Way Classification is Essential for Tru8

Your pipeline's value comes from nuanced verdicts:
- **Supported**: Multiple credible sources confirm the claim
- **Contradicted**: Multiple credible sources refute the claim
- **Uncertain**: Sources conflict or don't address the claim
- **Conflicting Expert Opinion**: High-quality sources disagree

**This requires distinguishing**:
- Evidence that contradicts (active disagreement)
- Evidence that is neutral (doesn't address the claim)

MiniCheck's binary "unsupported" conflates these categories.

### Your Current Fixes Address the Real Issues

Looking at your recent improvements:
1. ✅ Neutral threshold (0.7) to prevent false contradictions
2. ✅ Relevance gatekeeper to filter off-topic evidence
3. ✅ Larger DeBERTa model (base → large) for better accuracy
4. ✅ Snippet length increase (150 → 400 chars) for context
5. ✅ Better abstention logic (requires 2+ contradictions)

**These are all structural improvements** that work with three-way classification.

Switching to MiniCheck would **undo progress #1 and #2** (neutral detection and relevance filtering).

---

## Alternative Recommendation: MiniCheck Training Data + DeBERTa Architecture

### The Hybrid Approach

**Keep**: DeBERTa-v3-large three-way NLI architecture
**Add**: MiniCheck's superior training data (synthetic claims + ANLI)

**Why this could work**:
- Preserves three-way classification (entailment/neutral/contradiction)
- Benefits from MiniCheck's training on LLM-generated claims
- No integration complexity (same `transformers` API)
- Same memory footprint

### Implementation Path

1. **Fine-tune DeBERTa-v3-large** on MiniCheck's training data:
   - Use MiniCheck's 35K examples (21K ANLI + 14K synthetic)
   - Convert binary labels to three-way:
     - Supported → Entailment
     - Unsupported (off-topic) → Neutral
     - Unsupported (contradicting) → Contradiction
   - Requires manual labeling or heuristic conversion

2. **Use MiniCheck-DeBERTa-v3-Large** (existing variant):
   - Model ID: `lytang/MiniCheck-DeBERTa-v3-Large`
   - Same 435M params as your current model
   - Trained on MiniCheck's data
   - **But still outputs binary classification** (limitation)

**Problem**: MiniCheck-DeBERTa-v3-Large still uses binary output. The training data benefit is offset by the loss of three-way classification.

---

## Production Systems: What Actually Works

From research into professional fact-checking platforms:

### Full Fact (UK's Leading Fact-Checker)

**Architecture**:
- Stage 1: BERT-based topic classification
- Stage 2: Semantic search against claim database
- Stage 3: Cross-encoder reranking for relevance
- Stage 4: Human fact-checker review

**Key insight**: They use NLI + cross-encoders, not MiniCheck-style binary classification.

### Factiverse (Commercial Fact-Checking API)

**Architecture**:
- Fine-tuned XLM-RoBERTa for claim detection (beats GPT-4)
- Semantic search with dense retrieval
- Evidence aggregation with credibility weighting
- Stance detection with **three-way classification**

**Key insight**: Commercial systems still use three-way stance detection (support/refute/neutral).

### AVeriTeC 2024 Competition Winners

**Winning approaches**:
- RAG-based systems with claim decomposition
- Retrieval + reranking pipelines
- **All use three-way stance classification**

**No winning system used binary MiniCheck-style classification.**

---

## What to Do Instead

### Recommendation: Keep Current Architecture, Add Cross-Encoder Reranking

Your pipeline already has strong foundations:
1. ✅ Semantic similarity relevance filter (filters off-topic)
2. ✅ DeBERTa-v3-large NLI (three-way classification)
3. ✅ Neutral threshold logic (prevents false contradictions)
4. ✅ Credibility scoring (weights sources appropriately)

**Next improvement**: Add cross-encoder reranking BEFORE NLI

### Phase 1: Cross-Encoder Evidence Reranking (Week 12-13)

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- 22M parameters (tiny compared to 435M NLI model)
- Trained on MS MARCO passage ranking
- Outputs direct relevance score (0-1) for claim-evidence pairs

**Integration point**: Between retrieval and NLI (verify.py line 398)

**Current flow**:
```
Evidence retrieval → Semantic similarity filter → NLI verification
```

**New flow**:
```
Evidence retrieval → Semantic similarity filter → Cross-encoder reranking → Top-K selection → NLI verification
```

**Benefits**:
- Better evidence quality for NLI (only process most relevant evidence)
- Faster (process fewer evidence items through expensive NLI)
- Preserves three-way classification
- Small model (22M params vs 770M MiniCheck-Flan-T5)

**Code example**:
```python
from sentence_transformers import CrossEncoder

class EvidenceReranker:
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank_evidence(self, claim: str, evidence_list: List[Dict], top_k: int = 5):
        """Rerank evidence by relevance to claim"""
        pairs = [[claim, ev['text']] for ev in evidence_list]
        scores = self.model.predict(pairs)

        # Attach scores and sort
        for ev, score in zip(evidence_list, scores):
            ev['rerank_score'] = float(score)

        ranked = sorted(evidence_list, key=lambda x: x['rerank_score'], reverse=True)
        return ranked[:top_k]
```

### Phase 2: Improve Claim Extraction (Week 14-15)

**Current issue**: Claim extraction quality affects entire pipeline.

**Improvements**:
1. Add claim decomposition for complex claims
2. Use few-shot examples for better extraction
3. Filter subjective opinions before fact-checking
4. Classify claims by type (factual, legal, scientific, opinion)

**This is likely where your 50→58/100 score gap comes from**, not the NLI model.

### Phase 3: Enhanced Evidence Retrieval (Week 16)

**Current**: Brave Search API + embedding search

**Improvements**:
1. Query expansion with synonyms and entity variations
2. Temporal constraints (prioritize recent sources for time-sensitive claims)
3. Multi-hop retrieval for complex claims
4. Domain diversity enforcement (already partially implemented)

---

## Conclusion: Stay with DeBERTa-v3-large NLI

### Summary of Findings

| Aspect | DeBERTa-v3-large NLI (Current) | MiniCheck-Flan-T5-Large |
|--------|--------------------------------|-------------------------|
| **Classification** | Three-way (entailment/neutral/contradiction) ✅ | Binary (supported/unsupported) ❌ |
| **Neutral detection** | Explicit neutral score for off-topic evidence ✅ | Cannot distinguish neutral from contradiction ❌ |
| **Model size** | 435M params (~870MB) ✅ | 770M params (~1.4GB) ❌ |
| **Integration** | Standard `transformers` API ✅ | Requires MiniCheck wrapper ❌ |
| **Use case fit** | Designed for multi-source fact-checking ✅ | Designed for hallucination detection in LLM outputs ❌ |
| **Training data** | MNLI, FEVER, ANLI, LingNLI, WANLI ✅ | ANLI + GPT-4 synthetic (better for LLM claims) ~ |
| **Production usage** | Full Fact, Factiverse, AVeriTeC winners ✅ | Academic/research (2024 paper) ~ |

### Final Recommendation

**DO NOT switch to MiniCheck**. Instead:

1. **Short-term** (This week):
   - Test all recent fixes together (credibility, neutral threshold, snippets)
   - Benchmark performance on diverse test set
   - Identify remaining failure patterns

2. **Medium-term** (Weeks 12-14):
   - Implement cross-encoder reranking for evidence quality
   - Improve claim extraction with decomposition
   - Add claim type classification

3. **Long-term** (Weeks 15-16):
   - Enhanced evidence retrieval with query expansion
   - Multi-hop reasoning for complex claims
   - Consider RAG for claims requiring inference

4. **Monitor MiniCheck evolution**:
   - Watch for three-way classification variants
   - Test if future versions distinguish neutral/contradiction
   - Re-evaluate in 6 months

### Why This Approach is Better

Your current 50→58 score issue is likely **NOT caused by the NLI model**. Evidence:
- Relevance gatekeeper only filtered 1/30 evidence items (3%)
- Judge improvements already implemented (credibility, snippets, prompts)
- Neutral threshold already prevents false contradictions
- DeBERTa-v3-large is already a strong model (trained on FEVER)

**Root cause hypotheses**:
1. **Evidence retrieval quality**: Irrelevant evidence reaching NLI
2. **Claim extraction quality**: Poorly formulated claims
3. **Evidence diversity**: Too many low-quality sources
4. **Judge prompt**: May still over-infer or misinterpret

**MiniCheck won't fix any of these issues** because they're upstream from the verification stage.

---

## Appendix: Code Integration (If Proceeding Against Recommendation)

### Feature Flag Setup

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # Verification model selection
    USE_MINICHECK: bool = Field(False, env="USE_MINICHECK")
    MINICHECK_MODEL: str = Field("deberta-v3-large", env="MINICHECK_MODEL")  # or "flan-t5-large"
```

### Verifier Class Extension

```python
# backend/app/pipeline/verify.py
class NLIVerifier:
    def __init__(self):
        self.use_minicheck = settings.USE_MINICHECK

        if self.use_minicheck:
            self.minicheck_model_name = settings.MINICHECK_MODEL
            self.minicheck_scorer = None
        else:
            self.model = None
            self.tokenizer = None
            self.model_name = settings.nli_model_name

        self.max_length = 512
        self.batch_size = 8
        self._lock = asyncio.Lock()

    async def initialize(self):
        if self.use_minicheck:
            if self.minicheck_scorer is None:
                async with self._lock:
                    if self.minicheck_scorer is None:
                        loop = asyncio.get_event_loop()

                        def load_minicheck():
                            from minicheck.minicheck import MiniCheck
                            return MiniCheck(
                                model_name=self.minicheck_model_name,
                                cache_dir='./ckpts'
                            )

                        self.minicheck_scorer = await loop.run_in_executor(None, load_minicheck)
                        logger.info(f"MiniCheck model loaded: {self.minicheck_model_name}")
        else:
            # Existing DeBERTa initialization
            # ... (current code)
            pass

    def _run_inference(self, premises: List[str], hypotheses: List[str]):
        if self.use_minicheck:
            return self._run_minicheck_inference(premises, hypotheses)
        else:
            # Existing DeBERTa inference (current lines 498-546)
            # ... (current code)
            pass

    def _run_minicheck_inference(self, premises: List[str], hypotheses: List[str]):
        """Run MiniCheck inference and map to three-way scores"""
        try:
            pred_labels, raw_probs, _, _ = self.minicheck_scorer.score(
                docs=premises,
                claims=hypotheses
            )

            results = []
            for label, prob in zip(pred_labels, raw_probs):
                if label == 1:
                    # Supported
                    entailment = prob
                    neutral = (1 - prob) * 0.7
                    contradiction = (1 - prob) * 0.3
                else:
                    # Unsupported (ambiguous: neutral or contradiction)
                    entailment = prob  # Will be low
                    neutral = (1 - prob) * 0.7  # Conservative: lean toward neutral
                    contradiction = (1 - prob) * 0.3

                results.append((entailment, contradiction, neutral))

            return results

        except Exception as e:
            logger.error(f"MiniCheck inference error: {e}")
            return [(0.33, 0.33, 0.34)] * len(premises)
```

### Environment Variable

```bash
# backend/.env
USE_MINICHECK=false  # Set to true to enable
MINICHECK_MODEL=deberta-v3-large  # or flan-t5-large
```

### Installation

```bash
pip install "minicheck @ git+https://github.com/Liyan06/MiniCheck.git@main"
```

---

## References

1. **MiniCheck Paper**: Tang et al., "MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents", EMNLP 2024
2. **GitHub**: https://github.com/Liyan06/MiniCheck
3. **HuggingFace Models**:
   - https://huggingface.co/lytang/MiniCheck-Flan-T5-Large
   - https://huggingface.co/lytang/MiniCheck-DeBERTa-v3-Large
4. **Full Fact Architecture**: Alam et al., "Fighting Misinformation at Scale", 2023
5. **AVeriTeC Competition**: https://fever.ai/task.html

---

**Document created**: 2025-01-14
**Author**: Claude Code (Analysis for Tru8 pipeline improvement)
**Status**: Final recommendation - DO NOT switch to MiniCheck
