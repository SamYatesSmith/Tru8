# Check Endpoint Hanging Issue - Diagnostic Report

**Date:** October 16, 2025
**Issue:** POST /checks endpoint hangs/times out during Week 1 Day 2 testing

---

## Current Status

**✅ Working:**
- Backend API server running (uvicorn on localhost:8000)
- Database connectivity verified (PostgreSQL on localhost:5433)
- Auth system working (GET /users/profile successful)
- GET /checks working (logs show successful queries at 16:14:29)
- Celery worker running (confirmed by user)
- Redis configured at localhost:6379

**❌ Not Working:**
- POST /checks - Request hangs with no output
- No visible error messages in backend logs
- Curl command times out after waiting

---

## Configuration Review

### Redis Configuration
**File:** `backend/.env`
```
REDIS_URL=redis://localhost:6379/0
```

### Celery Configuration
**File:** `backend/app/workers/__init__.py`
```python
celery_app = Celery(
    "tru8",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.pipeline"]
)
```
- Task timeout: 180 seconds (PIPELINE_TIMEOUT_SECONDS)
- Worker pool: solo (Windows compatibility)
- Worker concurrency: 2
- Prefetch multiplier: 1

### Check Creation Endpoint
**File:** `backend/app/api/v1/checks.py:97-214`

**Critical Section (lines 158-202):**
```python
try:
    logger.info(f"Attempting to dispatch task for check {check.id}")
    logger.info(f"Redis URL: {settings.REDIS_URL}")

    # Test Redis connection first
    import redis
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()  # <-- POTENTIAL HANG POINT #1
        logger.info("Redis connection successful")
    except Exception as redis_error:
        logger.error(f"Redis connection failed: {redis_error}")
        raise redis_error

    task = process_check.delay(  # <-- POTENTIAL HANG POINT #2
        check_id=check.id,
        user_id=user.id,
        input_data={...}
    )
    logger.info(f"Task dispatched successfully: {task.id}")

    # Store task ID mapping in Redis
    r.set(f"check-task:{check.id}", task.id, ex=300)  # <-- POTENTIAL HANG POINT #3

    # Verify task is in Redis queue
    queue_length = r.llen("celery")  # <-- POTENTIAL HANG POINT #4
    logger.info(f"Queue length after dispatch: {queue_length}")
```

---

## Hypothesis: Why It's Hanging

### Most Likely Causes (in order):

1. **Redis Connection Timeout (Line 166)**
   - `r.ping()` is a **synchronous blocking call** in an **async endpoint**
   - If Redis is not responding, it will hang until timeout
   - No async/await used, so entire request blocks

2. **Celery Task Dispatch Blocking (Line 172)**
   - `process_check.delay()` is synchronous
   - If Celery worker not properly connected, it may hang
   - No timeout on the `.delay()` call

3. **Redis Operations After Dispatch (Lines 186, 190)**
   - `r.set()` and `r.llen()` are synchronous blocking calls
   - If Redis connection issues occur mid-request, hangs here

4. **Missing Exception Handling**
   - If Redis hangs on `.ping()`, no timeout mechanism
   - FastAPI request will wait indefinitely (or until uvicorn timeout)

---

## What We Know From Logs

**From ERROR.md (lines 233-333):**
```
2025-10-16 16:14:29 - GET /checks successful
- Auth verified (Clerk API calls successful)
- Database queries executed successfully
- Subscription queries working
- Claims data retrieved correctly
```

**What's Missing:**
- No logs from POST /checks attempt
- No "Attempting to dispatch task" message
- No "Redis URL" log message
- No "Redis connection successful" message
- **This suggests the request is hanging BEFORE line 159**

---

## Revised Hypothesis

Given that NO logs appear from the POST /checks endpoint, the hang is likely occurring **before** the try block at line 158.

**Most Likely Culprit:**
- **Lines 104-117:** User credit check and database query
- **Lines 119-133:** Input validation
- **Lines 136-155:** Check record creation and credit deduction

**Specific Suspects:**
```python
# Line 154: await session.commit() - Could hang if DB transaction lock
await session.commit()

# Line 155: await session.refresh(check) - Could hang if DB connection issues
await session.refresh(check)
```

---

## Recommended Testing Approach

### Test 1: Use the Diagnostic Script
```bash
cd backend
test-check-creation.bat YOUR_JWT_TOKEN
```

This will:
1. Verify auth still works
2. Test GET /checks (should work)
3. Test POST /checks with verbose output and 10s timeout

### Test 2: Check Backend Logs During POST Request
Watch for these log messages (or lack thereof):
- ✅ "Attempting to dispatch task for check..."
- ✅ "Redis URL: redis://localhost:6379/0"
- ✅ "Redis connection successful"
- ✅ "Task dispatched successfully: ..."

**If NONE of these appear:** Hang is in database operations (lines 104-155)
**If "Attempting to dispatch" appears but nothing after:** Hang is in Redis connection (line 166)
**If "Redis connection successful" appears:** Hang is in task dispatch or queue operations

### Test 3: Check Redis Directly
```bash
redis-cli ping
# Expected: PONG

redis-cli llen celery
# Expected: 0 or positive number
```

### Test 4: Check Celery Worker Logs
```bash
# Look in celery-worker.log for task registration
# Should see: [tasks] . app.workers.pipeline.process_check
```

---

## Potential Fixes

### Fix 1: Add Timeout to Redis Operations
Replace synchronous Redis with async Redis or add timeout:

```python
# Option A: Use async Redis
import redis.asyncio as aioredis

r = await aioredis.from_url(settings.REDIS_URL)
await r.ping()  # async version

# Option B: Add timeout to sync Redis
r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=5)
r.ping()  # Will timeout after 5 seconds
```

### Fix 2: Move Redis Connection Test Outside Endpoint
- Redis connection should be tested at startup, not per-request
- Remove lines 163-170 (redundant check)
- Rely on Celery's built-in connection handling

### Fix 3: Add Request Timeout
Add timeout to the entire endpoint using asyncio:

```python
try:
    # Wrap everything in timeout
    async with asyncio.timeout(10):  # 10 second timeout
        task = process_check.delay(...)
        # ... rest of code
except asyncio.TimeoutError:
    logger.error("Task dispatch timed out")
    raise HTTPException(status_code=504, detail="Request timed out")
```

### Fix 4: Check Database Connection Pool
Verify PostgreSQL connection pool not exhausted:
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'tru8_dev';
```

---

## Next Steps

1. **Run diagnostic script** to get verbose output
2. **Check backend terminal** for any log messages during POST request
3. **Verify Redis is running:** `redis-cli ping`
4. **Check Celery worker logs** for task registration
5. **Test with timeout:** Add `--max-time 10` to curl (already in script)

Once we identify WHERE the hang occurs (database vs Redis vs Celery), we can apply the appropriate fix.

---

## Expected Behavior

**Successful Request Should:**
1. Authenticate user (~200ms)
2. Query user credits from DB (~50ms)
3. Validate input (<1ms)
4. Create check record in DB (~100ms)
5. Commit transaction (~50ms)
6. Test Redis connection (<50ms)
7. Dispatch Celery task (~100ms)
8. Store task mapping in Redis (~50ms)
9. Return response (~10ms)

**Total Expected Time:** <1 second

**Current Behavior:** Hangs indefinitely (>60 seconds)

---

## User Confirmation Needed

Please run the diagnostic script and provide:
1. Full terminal output from the script
2. Backend server logs during the POST request
3. Redis CLI test results: `redis-cli ping`

This will help us pinpoint the exact hanging location.
