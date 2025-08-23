# Tru8 Pipeline Development Rules

## Pipeline Stage Focus

When working on pipeline components, focus memory on:

### Stage Isolation
```yaml
Current Stage Only:
  - Keep: Current stage code + tests
  - Keep: Input/output schemas
  - Discard: Other stage implementations
  - Reference: Stage interfaces only
```

### Pipeline Flow Memory
```
Ingest → Extract → Retrieve → Verify → Judge
  ↓        ↓         ↓          ↓        ↓
Keep active stage + immediate neighbors only
```

## Token Optimization for ML Components

### LLM Calls
- **Claim Extraction**: Max 2.5k input tokens
- **Judge Decision**: Max 1k context per claim
- **Batch Processing**: Group 3-5 claims per call
- **Cache Prompts**: Store templated prompts

### Embedding Operations
```python
# Good: Batch embed
texts = ["claim1", "claim2", "claim3"]
embeddings = model.encode(texts, batch_size=32)

# Bad: Individual embeds
for text in texts:
    embedding = model.encode(text)
```

### NLI Verification
- Preload model once at startup
- Batch premise-hypothesis pairs
- Cache common verdict patterns
- Use ONNX runtime for speed

## Search & Retrieval Optimization

### Search Strategy
1. **Quick Mode**: Max 10 search results
2. **Date Filtering**: Last 2 years only
3. **Source Ranking**: Prioritize trusted domains
4. **Early Stop**: Return on 3 strong sources

### Evidence Caching
```yaml
Cache Hierarchy:
  1. Exact URL match (7 days)
  2. Domain + keywords (1 day)  
  3. Search query (1 hour)
  4. Embedding vectors (permanent)
```

## Development Patterns

### When Building Pipeline Stages

#### ALWAYS:
- Validate input schemas first
- Log stage entry/exit with timing
- Implement timeout handling
- Return structured errors
- Write stage-specific tests

#### NEVER:
- Load all stages in memory
- Process synchronously
- Skip error boundaries
- Ignore rate limits
- Trust external data

### Testing Pipeline Components

```bash
# Test individual stages
pytest backend/tests/pipeline/test_ingest.py -v
pytest backend/tests/pipeline/test_extract.py -v

# Test full pipeline
pytest backend/tests/integration/test_pipeline.py -v

# Test with real data
pytest backend/tests/e2e/ --real-apis -v
```

## Performance Monitoring

### Key Metrics to Track
```python
metrics = {
    "latency": {
        "ingest": "<1s",
        "extract": "<2s",
        "retrieve": "<3s",
        "verify": "<2s",
        "judge": "<2s"
    },
    "token_usage": {
        "extract": "<1k per claim",
        "judge": "<500 per verdict"
    },
    "accuracy": {
        "claim_extraction": ">90%",
        "nli_confidence": ">0.7",
        "source_relevance": ">0.8"
    }
}
```

## Memory Management During Development

### Keep in Context
- Current pipeline stage code
- Pydantic models for data flow
- Error handling patterns
- Performance metrics

### Clear After Use
- Search API responses
- Full article texts
- Embedding computations
- Intermediate results

### Reference Only
- Other stage implementations
- ML model architectures
- API documentation
- Third-party libraries

## Common Pipeline Issues

### Issue: Slow claim extraction
**Solution**: Reduce prompt complexity, use structured output

### Issue: Poor evidence retrieval
**Solution**: Improve search queries, add date filtering

### Issue: Low NLI confidence
**Solution**: Better evidence selection, calibrate thresholds

### Issue: High token costs
**Solution**: Implement caching, reduce context windows

### Issue: Pipeline timeout
**Solution**: Add circuit breakers, parallel processing

## Quick Pipeline Commands

```bash
# Start pipeline worker
cd backend && celery -A workers.pipeline worker --loglevel=info

# Test specific stage
python -m pipeline.extract.test_extractor

# Monitor pipeline metrics
curl http://localhost:8000/metrics | grep pipeline_

# Clear pipeline cache
redis-cli FLUSHDB

# Run pipeline benchmark
python scripts/benchmark_pipeline.py
```

## Pipeline Code Patterns

### Stage Template
```python
class PipelineStage:
    async def process(self, input_data: InputSchema) -> OutputSchema:
        # Validate input
        # Process with timeout
        # Handle errors
        # Return structured output
        pass
```

### Error Handling
```python
try:
    result = await stage.process(data)
except TimeoutError:
    return ErrorResponse(stage="extract", error="timeout")
except ValidationError as e:
    return ErrorResponse(stage="extract", error=str(e))
```

### Caching Pattern
```python
cache_key = f"evidence:{claim_hash}"
if cached := await redis.get(cache_key):
    return cached
result = await retrieve_evidence(claim)
await redis.set(cache_key, result, ex=3600)
```

---
*Optimized for Tru8 pipeline development - focus on <10s latency*