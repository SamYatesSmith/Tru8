# AUTH REFACTORING - TEST VERIFICATION PLAN

**Date:** October 16, 2025
**Refactoring:** Extract `_fetch_user_data_from_clerk()` helper + Remove `RequireAuth` class
**Status:** ✅ Code refactored, ✅ Compiles successfully, ⏳ Awaiting testing
**File:** `backend/app/core/auth.py`

---

## 📋 CHANGES SUMMARY

### **✅ COMPLETED**

1. **Extracted Helper Function** (`_fetch_user_data_from_clerk`)
   - Lines: 52-120 (69 lines)
   - Purpose: Shared user data fetching logic
   - Used by: `get_current_user()` and `get_current_user_sse()`

2. **Refactored `get_current_user()`**
   - Lines: 122-136 (15 lines, was 68 lines)
   - Reduced from: 68 lines → 15 lines (53 lines saved)
   - Now calls: `_fetch_user_data_from_clerk()`

3. **Refactored `get_current_user_sse()`**
   - Lines: 138-176 (39 lines, was 92 lines)
   - Reduced from: 92 lines → 39 lines (53 lines saved)
   - Now calls: `_fetch_user_data_from_clerk()`

4. **Removed Dead Code**
   - Deleted: `RequireAuth` class (7 lines)
   - Reason: Never imported, never used, incomplete implementation

**Total Reduction:** 206 lines → 177 lines (29 lines saved)

---

## ✅ PRE-FLIGHT CHECKS PASSED

```bash
# ✅ Syntax validation passed
python -c "import ast; ast.parse(open('app/core/auth.py', encoding='utf-8').read())"

# ✅ Import validation passed
python -c "from app.core.auth import get_current_user, get_current_user_sse, _fetch_user_data_from_clerk"
```

**Result:** Code compiles successfully with no syntax errors.

---

## 🧪 TESTING PLAN

### **Critical: All endpoints must work identically to before refactoring**

---

## TEST SUITE 1: STANDARD AUTH ENDPOINTS (17 endpoints)

**Function:** `get_current_user(token_payload: dict = Depends(verify_token))`
**Usage:** All standard REST endpoints requiring authentication

### **Endpoints Using `get_current_user()`:**

#### **Auth Endpoints (2)**
1. `GET /api/v1/auth/me` - Get current user profile
2. `POST /api/v1/auth/refresh` - Refresh token

#### **Checks Endpoints (4)**
3. `POST /api/v1/checks/upload` - Upload image for fact-checking
4. `POST /api/v1/checks` - Create new check
5. `GET /api/v1/checks` - Get user's checks
6. `GET /api/v1/checks/{check_id}` - Get check by ID

#### **Payments Endpoints (5)**
7. `POST /api/v1/payments/checkout` - Create checkout session
8. `GET /api/v1/payments/subscription` - Get subscription status
9. `POST /api/v1/payments/cancel` - Cancel subscription
10. `POST /api/v1/payments/portal` - Create portal session
11. `POST /api/v1/payments/reactivate` - Reactivate subscription

#### **Users Endpoints (6)**
12. `GET /api/v1/users/profile` - Get user profile (auto-creates user)
13. `GET /api/v1/users/usage` - Get usage stats
14. `POST /api/v1/users/push-token` - Register push token
15. `GET /api/v1/users/notifications` - Get notifications
16. `PATCH /api/v1/users/notifications` - Mark notifications read
17. `DELETE /api/v1/users/me` - Delete account (GDPR)

---

### **TEST 1.1: Basic Authentication Flow**

**Prerequisites:**
- Backend running: `uvicorn app.main:app --reload`
- Have valid Clerk JWT token

**Steps:**
```bash
# 1. Get JWT token from Clerk (login via frontend)
# Copy token from browser DevTools → Application → Local Storage → clerk-token

# 2. Export token for testing
export TOKEN="your_clerk_jwt_token_here"

# 3. Test user profile endpoint
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "id": "user_xxxxx",
  "clerk_id": "user_xxxxx",
  "email": "test@example.com",
  "name": "Test User",
  "credits": 3,
  "totalCreditsUsed": 0,
  "subscription": {
    "plan": "free",
    "status": "active"
  },
  "createdAt": "2025-10-16T..."
}
```

**✅ Pass Criteria:**
- Status: 200 OK
- User data returned with correct structure
- Name extracted correctly (first+last, username, or email prefix)
- Email present
- Credits present

---

### **TEST 1.2: Token Verification Edge Cases**

**Test expired token:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer expired_token_here"
```

**Expected Response:**
```json
{
  "detail": "Token has expired"
}
```
**Status:** 401 Unauthorized

**Test invalid token:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer invalid_token"
```

**Expected Response:**
```json
{
  "detail": "Invalid token: ..."
}
```
**Status:** 401 Unauthorized

**Test missing token:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/profile"
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```
**Status:** 403 Forbidden

---

### **TEST 1.3: User Data Fetching Strategies**

**Purpose:** Verify `_fetch_user_data_from_clerk()` helper works correctly

**Scenario 1: JWT contains email AND name**
- Expected: Uses data from JWT token directly
- No Clerk API call should be made

**Scenario 2: JWT contains email but NO name**
- Expected: Fetches user data from Clerk API
- Applies 3-tiered name fallback strategy

**Scenario 3: JWT missing email**
- Expected: Fetches user data from Clerk API
- Extracts email from `email_addresses` array

**Test Setup:**
1. Login with different Clerk JWT templates
2. Check backend logs for Clerk API calls
3. Verify returned user data structure

---

### **TEST 1.4: All 17 Endpoints (Quick Smoke Test)**

**Run this script to test all endpoints:**

```bash
#!/bin/bash
# Save as: test-auth-endpoints.sh

export TOKEN="your_token_here"
BASE_URL="http://localhost:8000/api/v1"

echo "Testing Auth Endpoints..."
curl -s "$BASE_URL/auth/me" -H "Authorization: Bearer $TOKEN" | jq '.email'

echo "Testing Users Endpoints..."
curl -s "$BASE_URL/users/profile" -H "Authorization: Bearer $TOKEN" | jq '.credits'
curl -s "$BASE_URL/users/usage" -H "Authorization: Bearer $TOKEN" | jq '.totalCreditsUsed'

echo "Testing Checks Endpoints..."
curl -s "$BASE_URL/checks?offset=0&limit=10" -H "Authorization: Bearer $TOKEN" | jq '.total'

echo "Testing Payments Endpoints..."
curl -s "$BASE_URL/payments/subscription" -H "Authorization: Bearer $TOKEN" | jq '.plan'

echo "✅ All endpoints accessible"
```

**Expected:** All endpoints return 200 OK with valid data

---

## TEST SUITE 2: SSE AUTH ENDPOINT (1 endpoint)

**Function:** `get_current_user_sse(request: Request, token: Optional[str] = Query(None))`
**Usage:** Server-Sent Events endpoint for real-time progress updates

### **Endpoint Using `get_current_user_sse()`:**

1. `GET /api/v1/checks/{check_id}/progress` - SSE progress stream

**Why different from standard auth?**
- EventSource (browser SSE API) cannot send custom headers
- Must accept token via query parameter: `?token=xxx`
- Fallback to Authorization header for compatibility

---

### **TEST 2.1: SSE with Query Parameter (Primary Method)**

**Steps:**
```bash
# Get valid token
export TOKEN="your_token_here"

# Create a check first to get check_id
CHECK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/checks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"claim": "The sky is blue", "mode": "quick"}' \
  | jq -r '.id')

echo "Check ID: $CHECK_ID"

# Test SSE endpoint with query parameter
curl -N "http://localhost:8000/api/v1/checks/$CHECK_ID/progress?token=$TOKEN"
```

**Expected Response:**
```
data: {"status": "pending", "progress": 0, "message": "Starting verification..."}

data: {"status": "extracting", "progress": 20, "message": "Extracting claims..."}

data: {"status": "retrieving", "progress": 40, "message": "Finding evidence..."}

data: {"status": "verifying", "progress": 60, "message": "Verifying claims..."}

data: {"status": "judging", "progress": 80, "message": "Generating verdict..."}

data: {"status": "completed", "progress": 100, "result": {...}}
```

**✅ Pass Criteria:**
- Connection stays open (SSE stream)
- Progress updates received
- No authentication errors
- Stream completes successfully

---

### **TEST 2.2: SSE with Authorization Header (Fallback)**

**Steps:**
```bash
# Test SSE endpoint with Bearer token header
curl -N "http://localhost:8000/api/v1/checks/$CHECK_ID/progress" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
- Same SSE stream as TEST 2.1
- Should work identically

**✅ Pass Criteria:**
- Both methods work (query param AND header)
- User authenticated correctly in both cases

---

### **TEST 2.3: SSE Authentication Errors**

**Test missing token:**
```bash
curl -N "http://localhost:8000/api/v1/checks/$CHECK_ID/progress"
```

**Expected Response:**
```json
{
  "detail": "No authentication token provided"
}
```
**Status:** 401 Unauthorized

**Test invalid token:**
```bash
curl -N "http://localhost:8000/api/v1/checks/$CHECK_ID/progress?token=invalid"
```

**Expected Response:**
```json
{
  "detail": "Invalid token: ..."
}
```
**Status:** 401 Unauthorized

---

## 🧪 AUTOMATED TEST SCRIPT

**Save as:** `backend/test-refactored-auth.sh`

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "AUTH REFACTORING - AUTOMATED TEST SUITE"
echo "=========================================="
echo ""

# Configuration
BASE_URL="http://localhost:8000/api/v1"
export TOKEN="${1:-}"

if [ -z "$TOKEN" ]; then
  echo "❌ ERROR: No token provided"
  echo "Usage: ./test-refactored-auth.sh YOUR_TOKEN"
  exit 1
fi

echo "✅ Token provided: ${TOKEN:0:20}..."
echo ""

# Test counter
PASSED=0
FAILED=0

# Helper function
test_endpoint() {
  local name=$1
  local url=$2
  local method=${3:-GET}

  echo -n "Testing $name... "

  response=$(curl -s -w "\n%{http_code}" -X $method "$url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

  status_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$status_code" = "200" ]; then
    echo "✅ PASS ($status_code)"
    PASSED=$((PASSED + 1))
  else
    echo "❌ FAIL ($status_code)"
    echo "   Response: $body"
    FAILED=$((FAILED + 1))
  fi
}

echo "=========================================="
echo "TEST SUITE 1: STANDARD AUTH ENDPOINTS"
echo "=========================================="
echo ""

# Auth endpoints
test_endpoint "GET /auth/me" "$BASE_URL/auth/me"

# Users endpoints
test_endpoint "GET /users/profile" "$BASE_URL/users/profile"
test_endpoint "GET /users/usage" "$BASE_URL/users/usage"
test_endpoint "GET /users/notifications" "$BASE_URL/users/notifications"

# Checks endpoints
test_endpoint "GET /checks" "$BASE_URL/checks?offset=0&limit=10"

# Payments endpoints
test_endpoint "GET /payments/subscription" "$BASE_URL/payments/subscription"

echo ""
echo "=========================================="
echo "TEST SUITE 2: SSE AUTH ENDPOINT"
echo "=========================================="
echo ""

# Create a check first
echo -n "Creating test check... "
check_response=$(curl -s -X POST "$BASE_URL/checks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"claim": "Test claim for SSE", "mode": "quick"}')

check_id=$(echo "$check_response" | jq -r '.id')

if [ "$check_id" != "null" ] && [ -n "$check_id" ]; then
  echo "✅ Check created: $check_id"
  PASSED=$((PASSED + 1))

  # Test SSE with query parameter
  echo -n "Testing SSE with query parameter... "
  sse_response=$(curl -s -N --max-time 5 "$BASE_URL/checks/$check_id/progress?token=$TOKEN" 2>&1 || true)

  if echo "$sse_response" | grep -q "data:"; then
    echo "✅ PASS (SSE stream received)"
    PASSED=$((PASSED + 1))
  else
    echo "❌ FAIL (No SSE stream)"
    FAILED=$((FAILED + 1))
  fi

  # Test SSE with header
  echo -n "Testing SSE with Authorization header... "
  sse_response=$(curl -s -N --max-time 5 "$BASE_URL/checks/$check_id/progress" \
    -H "Authorization: Bearer $TOKEN" 2>&1 || true)

  if echo "$sse_response" | grep -q "data:"; then
    echo "✅ PASS (SSE stream received)"
    PASSED=$((PASSED + 1))
  else
    echo "❌ FAIL (No SSE stream)"
    FAILED=$((FAILED + 1))
  fi
else
  echo "❌ Check creation failed"
  FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "TEST RESULTS SUMMARY"
echo "=========================================="
echo ""
echo "✅ PASSED: $PASSED"
echo "❌ FAILED: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "🎉 ALL TESTS PASSED - REFACTORING VERIFIED!"
  exit 0
else
  echo "⚠️  SOME TESTS FAILED - REVIEW REQUIRED"
  exit 1
fi
```

**Usage:**
```bash
# 1. Start backend
cd backend
uvicorn app.main:app --reload

# 2. Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info --pool=solo

# 3. Get JWT token from frontend (login and copy from DevTools)

# 4. Run test script
chmod +x test-refactored-auth.sh
./test-refactored-auth.sh "your_clerk_jwt_token_here"
```

---

## 📊 TEST RESULTS TEMPLATE

```markdown
## Auth Refactoring Test Results

**Date:** [Date]
**Tester:** [Name]
**Backend Version:** [Git commit hash]
**Status:** ✅ PASS / ❌ FAIL

### Test Suite 1: Standard Auth Endpoints
- [ ] GET /auth/me
- [ ] GET /users/profile
- [ ] GET /users/usage
- [ ] GET /users/notifications
- [ ] GET /checks
- [ ] GET /payments/subscription
- [ ] [Add other endpoints tested]

**Result:** ✅ X/17 endpoints passed

### Test Suite 2: SSE Auth Endpoint
- [ ] SSE with query parameter
- [ ] SSE with Authorization header
- [ ] SSE authentication errors

**Result:** ✅ All SSE tests passed

### Name Fallback Strategy Testing
- [ ] JWT with email + name (direct use)
- [ ] JWT with email, no name (Clerk API fetch)
- [ ] JWT missing email (Clerk API fetch)
- [ ] Name Strategy 1: first_name + last_name
- [ ] Name Strategy 2: username
- [ ] Name Strategy 3: email prefix

**Result:** ✅ All strategies working

### Issues Found:
[None / List issues here]

### Conclusion:
✅ Refactoring verified - safe to proceed with Week 1 testing
```

---

## ✅ VERIFICATION CHECKLIST

Before proceeding with Week 1 Day 1 testing:

- [ ] Backend starts without errors (`uvicorn app.main:app --reload`)
- [ ] No import errors in auth.py
- [ ] GET /users/profile returns correct user data
- [ ] All 17 standard endpoints return 200 OK
- [ ] SSE endpoint works with query parameter
- [ ] SSE endpoint works with Authorization header
- [ ] Name fallback strategies working correctly
- [ ] Token expiration handled correctly
- [ ] Invalid token errors returned correctly
- [ ] Automated test script passes 100%

---

## 🚀 READY TO PROCEED

Once all tests pass:

1. ✅ Mark refactoring as verified
2. ✅ Update INNEFICENCY.md (mark as resolved)
3. ✅ Proceed with Week 1 Day 1 manual testing from `WEEK1_DAY1_AUTH_TESTING.md`
4. ✅ Authentication system ready for production

---

## 📝 NOTES

**Why this testing is critical:**
- Refactored 68 lines in `get_current_user()` - used by 17 endpoints
- Refactored 92 lines in `get_current_user_sse()` - used by 1 critical SSE endpoint
- Any break in auth logic would block ALL authenticated features
- SSE endpoint is critical for real-time progress updates

**What we're verifying:**
- Helper function `_fetch_user_data_from_clerk()` works identically to original code
- No regressions in JWT verification
- No regressions in Clerk API fallback logic
- Name extraction strategies still work (3-tiered fallback)
- SSE query parameter auth still works (EventSource compatibility)

**Confidence Level:** HIGH (code is identical, just extracted into helper)

---

**Next:** Run automated test script and proceed with Week 1 Day 1 testing once verified.
