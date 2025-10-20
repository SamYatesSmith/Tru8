# AUTH CODE DUPLICATION - DETAILED ANALYSIS

**File:** `backend/app/core/auth.py`
**Issue:** Duplicated user data fetching logic in two functions
**Status:** SAFE TO REFACTOR WITH CAUTION
**Risk Level:** LOW (with proper testing)

---

## 📊 USAGE ANALYSIS

### **Function 1: `get_current_user()`**
**Used in:** 17 endpoints across 4 files
- `auth.py` - 2 usages (get current user, refresh token)
- `checks.py` - 4 usages (upload, create, get checks, get check by ID)
- `payments.py` - 5 usages (checkout, subscription status, cancel, portal, reactivate)
- `users.py` - 6 usages (profile, usage, push token, notifications, delete account)

**Authentication Method:** Bearer token from `Authorization` header via FastAPI `HTTPBearer`

### **Function 2: `get_current_user_sse()`**
**Used in:** 1 endpoint in 1 file
- `checks.py` - 1 usage (SSE progress streaming endpoint line 352)

**Authentication Method:** JWT token from query parameter OR Authorization header

---

## 🔍 DIFFERENCES BETWEEN FUNCTIONS

### **Key Difference: Token Extraction**

**`get_current_user()`:**
```python
async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    # Token already extracted and verified by verify_token()
    # verify_token() uses HTTPBearer security scheme
    user_id = token_payload.get("sub")
    ...
```

**`get_current_user_sse()`:**
```python
async def get_current_user_sse(request: Request, token: Optional[str] = Query(None)) -> dict:
    # Manually extract token from query param OR header
    jwt_token = None

    if token:  # Query parameter (for EventSource)
        jwt_token = token
    else:  # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]

    # Manually verify token
    payload = await _verify_jwt_token(jwt_token)
    user_id = payload.get("sub")
    ...
```

**Why the difference exists:**
- EventSource (browser's SSE API) **cannot send custom headers**
- Therefore, SSE endpoint must accept token via query parameter
- Standard REST endpoints use standard Bearer token authentication

### **Identical Part: User Data Fetching (53 lines)**

After getting the `user_id` from the token, **both functions have EXACTLY the same code** (lines 60-112 and 146-198):

```python
# Try to get email and name from token
email = payload.get("email")
name = payload.get("name")

# If email or name is missing from JWT, fetch from Clerk's API
if not email or not name:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}", ...}
            )
            if response.status_code == 200:
                user_data = response.json()

                # Get email if missing
                if not email:
                    email = user_data.get("email_addresses", [{}])[0].get("email_address")

                # Get name with 3-tiered fallback strategy
                if not name:
                    # Strategy 1: first_name + last_name
                    first_name = user_data.get('first_name', '').strip()
                    last_name = user_data.get('last_name', '').strip()
                    if first_name or last_name:
                        name = f"{first_name} {last_name}".strip()

                    # Strategy 2: username
                    if not name:
                        username = user_data.get('username')
                        if username:
                            name = username

                    # Strategy 3: email prefix
                    if not name and email:
                        name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
    except Exception as e:
        pass

return {
    "id": user_id,
    "email": email,
    "name": name,
}
```

**This exact code appears twice** - 53 lines duplicated.

---

## ✅ SAFE REFACTORING APPROACH

### **Proposed Solution:**

Extract the duplicated user data fetching logic into a shared helper function:

```python
async def _fetch_user_data_from_clerk(user_id: str, token_payload: dict) -> dict:
    """
    Shared helper to fetch user email and name from JWT or Clerk API.

    Args:
        user_id: Clerk user ID from JWT 'sub' claim
        token_payload: Decoded JWT payload (may contain email/name)

    Returns:
        Dict with id, email, name
    """
    email = token_payload.get("email")
    name = token_payload.get("name")

    # If email or name is missing from JWT, fetch from Clerk's API
    if not email or not name:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    user_data = response.json()

                    # Get email if missing
                    if not email:
                        email = user_data.get("email_addresses", [{}])[0].get("email_address")

                    # Get name if missing - try multiple fallback strategies
                    if not name:
                        first_name = user_data.get('first_name', '').strip() if user_data.get('first_name') else ''
                        last_name = user_data.get('last_name', '').strip() if user_data.get('last_name') else ''

                        # Strategy 1: Use first_name + last_name
                        if first_name or last_name:
                            name = f"{first_name} {last_name}".strip()

                        # Strategy 2: Use username if available
                        if not name:
                            username = user_data.get('username')
                            if username:
                                name = username

                        # Strategy 3: Use email prefix (part before @)
                        if not name and email:
                            name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        except Exception as e:
            # Error fetching from Clerk API, continue with what we have
            pass

    return {
        "id": user_id,
        "email": email,
        "name": name,
    }


async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    """Get current user from JWT token (standard Bearer auth)"""
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return await _fetch_user_data_from_clerk(user_id, token_payload)


async def get_current_user_sse(request: Request, token: Optional[str] = Query(None)) -> dict:
    """
    Get current user for SSE endpoints that support both header and query param auth.
    EventSource doesn't support custom headers, so we allow token via query parameter.
    """
    jwt_token = None

    # Try to get token from query parameter first (for SSE)
    if token:
        jwt_token = token
    else:
        # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]  # Remove "Bearer " prefix

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )

    # Verify the token using shared logic
    payload = await _verify_jwt_token(jwt_token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return await _fetch_user_data_from_clerk(user_id, payload)
```

---

## 🎯 REFACTORING BENEFITS

### **Before:**
- 206 lines total in `auth.py`
- 53 lines duplicated (25% of file)
- Changes need to be made in 2 places
- Higher risk of bugs if one function updated but not the other

### **After:**
- ~160 lines total (estimated)
- 0 duplicated lines
- Changes made in 1 place
- Lower maintenance burden

**Lines saved:** ~46 lines
**Maintenance burden:** Reduced significantly

---

## ⚠️ RISKS & MITIGATION

### **Risk 1: Breaking Existing Endpoints**
**Likelihood:** LOW
**Impact:** HIGH (authentication broken)

**Mitigation:**
- Test ALL 18 endpoints that use these functions
- Verify both functions return identical data structure
- Test SSE endpoint specifically (only user of `get_current_user_sse`)

### **Risk 2: Subtle Behavioral Difference**
**Likelihood:** VERY LOW (code is identical)
**Impact:** MEDIUM

**Mitigation:**
- Line-by-line code review confirms exact duplication
- Return value structure is identical
- Exception handling is identical

### **Risk 3: Import or Dependency Issues**
**Likelihood:** VERY LOW
**Impact:** LOW

**Mitigation:**
- No new imports needed
- All dependencies already available
- Helper function is private (underscore prefix)

---

## ✅ TESTING PLAN

After refactoring, test these scenarios:

### **1. Standard Auth Endpoints (17 endpoints)**
```bash
# Test with valid token
curl -H "Authorization: Bearer {valid_token}" http://localhost:8000/api/v1/users/profile

# Expected: 200 OK, user data returned
```

### **2. SSE Endpoint (1 endpoint)**
```bash
# Test with query param (EventSource pattern)
curl "http://localhost:8000/api/v1/checks/{check_id}/progress?token={valid_token}"

# Test with header (fallback)
curl -H "Authorization: Bearer {valid_token}" http://localhost:8000/api/v1/checks/{check_id}/progress

# Expected: Both return SSE stream, user authenticated correctly
```

### **3. User Data Fetching**
Test with different JWT scenarios:
- JWT with email AND name → should use from token
- JWT with email but NO name → should fetch from Clerk API
- JWT with NO email → should fetch from Clerk API

### **4. Name Fallback Strategies**
Test all 3 fallback strategies:
1. User with first_name + last_name → should combine
2. User with username but no name → should use username
3. User with only email → should extract from email prefix

---

## 🚦 RECOMMENDATION

### **Should we proceed with refactoring?**

**YES - WITH CAUTION**

**Reasons:**
✅ Code is proven identical (53 lines exact match)
✅ Clear separation of concerns (token extraction vs user data fetching)
✅ Only 1 SSE endpoint to test for regressions
✅ Helper function is straightforward and well-scoped
✅ Significant maintenance burden reduction

**Conditions:**
⚠️ Must test all 18 endpoints after refactoring
⚠️ Must specifically test SSE endpoint with both auth methods
⚠️ Should be done BEFORE Week 1 testing continues (avoid confusion)
⚠️ Must verify in staging/dev before production

---

## 📋 QUESTIONS FOR YOU

Before I proceed with the refactoring, please confirm:

### **1. Timing Question:**
Should we do this refactoring:
- **Option A:** NOW (before continuing Week 1 testing) - Clean codebase for testing
- **Option B:** AFTER Week 1 testing complete - Avoid changing code during testing
- **Option C:** POST-LAUNCH - Minimize risk, defer to refactoring sprint

**My recommendation:** Option A (NOW) - The code is identical, risk is very low, and cleaner code makes testing easier.

### **2. Testing Question:**
Do you want me to:
- **Option A:** Make the change and provide you manual test steps
- **Option B:** Create a test branch first for you to review
- **Option C:** Skip this refactoring for MVP (defer post-launch)

**My recommendation:** Option A - I'm confident the change is safe.

### **3. Scope Question:**
Should I also fix while I'm in the file:
- **Option A:** ONLY fix the duplication
- **Option B:** Also fix the other minor issues (unused RequireAuth class, etc.)
- **Option C:** Also update the API client comments (medium priority items)

**My recommendation:** Option A - Stay focused, one change at a time.

---

## 🎯 MY ASSESSMENT

**Confidence Level:** 95%
**Safe to refactor:** YES
**Recommendation:** Proceed with refactoring NOW

The duplication is clear, the solution is straightforward, and the risk is minimal. The only real risk is breaking the SSE endpoint (1 endpoint), which is easily testable.

**What do you want me to do?**
