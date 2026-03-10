# Celery Worker Scaling - Known Issues & Production Considerations

> **NOTICE (2026-03-10):** This document references `fly.toml` and Fly.io scaling
> commands. Update to match the chosen deployment platform before production release.

**Status:** Partially addressed for beta, requires review before production
**Last Updated:** January 2026

---

## Summary

The Celery worker configuration has a critical limitation that was discovered during deployment planning. This document explains the issue, the current fix, and what needs to be addressed for production.

---

## The Problem

### Original Configuration
```python
worker_pool="solo"  # Sequential processing - ONE task at a time globally
```

### Impact
With the `solo` pool, **all users share a single queue** processed one task at a time:

| Concurrent Users | Max Wait Time |
|------------------|---------------|
| 1 | 0 min |
| 5 | 12 min |
| 10 | 27 min |
| 20 | 57 min |

This is **unacceptable for production** with multiple simultaneous users.

### Why Solo Pool Was Used
- Windows compatibility (prefork has permission issues on Windows)
- Simpler debugging during development
- Avoided memory issues from too many concurrent ML models

---

## Current Fix (Beta)

### Code Change
**File:** `backend/app/workers/__init__.py`

```python
import platform

# Platform-specific worker pool
WORKER_POOL = "solo" if platform.system() == "Windows" else "prefork"

celery_app.conf.update(
    worker_pool=WORKER_POOL,
    worker_concurrency=2,  # 2 concurrent tasks on Linux
    ...
)
```

### Fly.io Configuration
**File:** `backend/fly.toml`

Separate processes for API and worker:
```toml
[processes]
  web = "uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"
  worker = "celery -A app.workers worker --loglevel=info --concurrency=2"

# Web VM (API server)
[[vm]]
  memory = "512mb"
  processes = ["web"]

# Worker VM (Celery - needs memory for ML models)
[[vm]]
  memory = "2gb"
  processes = ["worker"]
```

### Result
- **Beta:** 2 concurrent checks (vs 1 before)
- **Windows development:** Still uses solo pool (1 at a time)
- **Linux/Fly.io:** Uses prefork pool (true concurrency)

---

## Production Considerations

### 1. Memory Requirements

Each concurrent task needs ~800MB for ML models:
- NLI model (DeBERTa): ~400MB
- Embedding model (MiniLM): ~90MB
- Python + dependencies: ~200MB
- Task overhead: ~100MB

| Concurrency | Required RAM |
|-------------|--------------|
| 1 | 1GB |
| 2 | 1.5GB |
| 4 | 2.5GB |

**Recommendation:** Start with 2GB worker VM, scale up if needed.

### 2. Scaling Options

#### Option A: Increase Concurrency
```bash
# In fly.toml or via CLI
worker = "celery -A app.workers worker --concurrency=4"
```
Requires more RAM per worker.

#### Option B: Add More Workers
```bash
fly scale count worker=2
```
Runs 2 worker machines, each with concurrency=2 = 4 total concurrent tasks.

#### Option C: Horizontal + Vertical
- 2 worker machines
- 4 concurrency each
- = 8 concurrent checks

### 3. Monitoring

Watch for:
- Task queue length: `redis-cli LLEN celery`
- Worker memory usage: Fly.io dashboard
- Task completion times: Application logs

### 4. Cost Implications

| Configuration | Monthly Cost (est.) |
|---------------|---------------------|
| 1 worker, 2GB | ~$14 |
| 2 workers, 2GB each | ~$28 |
| 1 worker, 4GB | ~$28 |

---

## Alternative: Remove Celery Entirely

### Pros
- Simpler architecture (no Redis queue dependency)
- One process to deploy
- Lower infrastructure cost

### Cons
- No automatic retries
- Harder to track failed tasks
- Can't scale workers independently
- Long tasks may affect API responsiveness

### Migration Effort
- ~100 lines of code to change
- Replace `.delay()` calls with `asyncio.create_task()`
- Add manual error handling and retry logic
- 3-4 hours estimated work

**Recommendation:** Keep Celery for now, consider removal only if infrastructure complexity becomes a burden.

---

## Pre-Production Checklist

Before going to production, verify:

- [ ] Worker concurrency matches expected user load
- [ ] Worker VM has sufficient memory (monitor during beta)
- [ ] Redis connection is stable under load
- [ ] Task timeout (180s) is appropriate
- [ ] Error handling and credit refunds work correctly
- [ ] Worker auto-restarts on failure
- [ ] Monitoring/alerting for queue backlog

---

## Files Involved

| File | Purpose |
|------|---------|
| `backend/app/workers/__init__.py` | Celery app configuration |
| `backend/app/workers/pipeline.py` | Pipeline task definition |
| `backend/app/api/v1/checks.py` | Task dispatch via `.delay()` |
| `backend/fly.toml` | Fly.io process configuration |

---

## History

| Date | Change |
|------|--------|
| Jan 2026 | Discovered solo pool limitation during Fly.io deployment planning |
| Jan 2026 | Added platform detection for worker pool (solo on Windows, prefork on Linux) |
| Jan 2026 | Added separate worker process to fly.toml with 2GB RAM |

---

*This document should be reviewed before production launch to ensure scaling is appropriate for expected user load.*
