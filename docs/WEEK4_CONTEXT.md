# Week 4 Implementation Context - Judge & Optimize

## 🎯 Week 4 Objectives (from DEVELOPMENT_PLAN.md)
- [ ] Judge LLM prompts implementation
- [ ] Result aggregation logic
- [ ] Caching layer optimization
- [ ] Performance optimization (<10s target)
- [ ] Error recovery mechanisms
- [ ] SSE progress updates
- **Integration Point:** Full pipeline E2E

## 📁 Current Pipeline Architecture

### Existing Components (Week 1-3)
```
backend/app/pipeline/
├── ingest.py       ✅ (URL, Image, Video ingestion)
├── extract.py      ✅ (LLM claim extraction with OpenAI/Anthropic)
├── retrieve.py     ✅ (Evidence retrieval with search & embeddings)
├── verify.py       ❌ (Needs implementation)
└── judge.py        ❌ (Needs implementation)
```

### Services Layer
```
backend/app/services/
├── cache.py        ✅ (Redis caching with TTL strategies)
├── search.py       ✅ (Brave & SerpAPI integration)
├── embeddings.py   ✅ (Sentence-Transformers, all-MiniLM-L6-v2)
├── vector_store.py ✅ (Qdrant for semantic search)
├── evidence.py     ✅ (Evidence extraction & ranking)
└── nli.py          ❌ (Needs implementation for NLI verification)
```

## 🔄 Current Pipeline Flow (workers/pipeline.py)

### Stage Flow with Progress Updates:
1. **Ingest** (10%) → Real implementation ✅
2. **Extract** (25%) → Real LLM extraction ✅
3. **Retrieve** (40%) → Real search + embeddings ✅
4. **Verify** (60%) → Mock implementation (lines 256-271)
5. **Judge** (80%) → Mock implementation (lines 273-296)

### Key Integration Points:
- `process_check()` - Main pipeline orchestrator (line 22)
- Celery task state updates for progress (lines 41, 48, 57, 61, 65)
- Cache service integration throughout
- Mock functions that need real implementation:
  - `verify_claims()` - line 256
  - `judge_claims()` - line 273

## 📊 Data Models (models/check.py)

### Database Schema:
```python
Check:
  - id, user_id, input_type, input_content, input_url
  - status: 'pending' | 'processing' | 'completed' | 'failed'
  - credits_used, processing_time_ms, error_message
  - Relations: claims[]

Claim:
  - id, check_id, text, position
  - verdict: 'supported' | 'contradicted' | 'uncertain'
  - confidence: 0-100
  - rationale: string
  - Relations: evidence[]

Evidence:
  - id, claim_id, source, url, title, snippet
  - published_date, relevance_score (0-1)
```

## 🌐 API Endpoints (api/v1/checks.py)

### Current Endpoints:
- `POST /api/v1/checks/` - Create check (line 21)
- `GET /api/v1/checks/` - List checks (line 97)
- `GET /api/v1/checks/{check_id}` - Get check details (line 132)
- `GET /api/v1/checks/{check_id}/progress` - Progress stub (line 199) ⚠️

### SSE Implementation Needed:
- Line 201: "TODO: Implement SSE for real-time updates"
- Currently returns static mock progress

## 🔧 Week 4 Implementation Requirements

### 1. NLI Verification Component (`app/services/nli.py`)
```python
class NLIVerifier:
    - Load DeBERTa ONNX model
    - Batch premise-hypothesis pairs
    - Calculate entailment/contradiction scores
    - Calibrate confidence thresholds
    - Cache verification results
```

### 2. Judge Component (`app/pipeline/judge.py`)
```python
class ClaimJudge:
    - Aggregate evidence signals
    - Apply credibility weighting
    - Generate final verdicts
    - Create explanatory rationales
    - Handle conflicting evidence
```

### 3. SSE Progress Updates (`app/api/v1/checks.py`)
```python
@router.get("/{check_id}/progress")
async def stream_progress():
    - Connect to Redis pubsub
    - Stream Celery task updates
    - Format SSE events
    - Handle client disconnections
```

### 4. Performance Optimizations
- Parallel processing in verify stage
- Batch NLI inference
- Optimize Judge LLM prompts (< 1k tokens)
- Circuit breakers for external services
- Connection pooling for databases

### 5. Error Recovery
- Implement retry logic with exponential backoff
- Fallback strategies for each stage
- Graceful degradation
- Update check status on failures

## 🔗 Key Dependencies & Imports

### For NLI Implementation:
```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import onnxruntime as ort
import numpy as np
```

### For SSE Implementation:
```python
from fastapi import Response
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis
```

### For Judge Implementation:
```python
from app.pipeline.extract import ClaimExtractor  # Reuse LLM setup
from app.services.cache import get_cache_service
from typing import List, Dict, Any
```

## 📈 Performance Targets

### Current Latencies (from WEEK3_COMPLETE.md):
- LLM extraction: <2s with caching
- Search: <1s for 10 results
- Embeddings: <100ms per batch
- Vector search: <50ms

### Week 4 Targets:
- NLI verification: <1s per claim batch
- Judge LLM: <1.5s per check
- **Total pipeline: <10s end-to-end**

## 🚀 Implementation Order

1. **Create `app/pipeline/verify.py`**
   - Implement NLI verification with ONNX
   - Integrate with existing evidence from retrieve.py

2. **Create `app/pipeline/judge.py`**
   - Aggregate signals from verify stage
   - Generate final verdicts with rationales

3. **Update `app/workers/pipeline.py`**
   - Replace mock functions with real implementations
   - Add error handling and retries

4. **Implement SSE in `app/api/v1/checks.py`**
   - Real-time progress streaming
   - Connect to Celery task updates

5. **Optimize Performance**
   - Add parallel processing
   - Implement circuit breakers
   - Fine-tune caching strategies

## 🔑 Configuration Updates Needed

### Add to `.env`:
```env
# NLI Model
NLI_MODEL_PATH=./models/deberta-v3-base-nli.onnx
NLI_CONFIDENCE_THRESHOLD=0.7

# Judge LLM
JUDGE_MAX_TOKENS=1000
JUDGE_TEMPERATURE=0.3

# Performance
MAX_CONCURRENT_VERIFICATIONS=5
VERIFICATION_TIMEOUT_SECONDS=5
```

### Add to `config.py`:
```python
NLI_MODEL_PATH: str = Field("./models/deberta-v3-base-nli.onnx", env="NLI_MODEL_PATH")
NLI_CONFIDENCE_THRESHOLD: float = Field(0.7, env="NLI_CONFIDENCE_THRESHOLD")
JUDGE_MAX_TOKENS: int = Field(1000, env="JUDGE_MAX_TOKENS")
```

## ✅ Ready for Week 4 Implementation

All context gathered. The pipeline foundation is solid with:
- Real LLM extraction (OpenAI/Anthropic)
- Real search (Brave/SerpAPI)
- Real embeddings (Sentence-Transformers)
- Real vector store (Qdrant)
- Comprehensive caching (Redis)

**Next steps:** Implement verify.py → judge.py → SSE updates → Performance optimization