# Gap Resolution Plan - Frontend-Backend Integration

**Created:** October 14, 2025
**Priority:** Address critical issues before MVP launch
**Estimated Time:** 4-6 hours total

---

## 📋 Overview

This plan addresses all gaps identified in `FRONTEND_BACKEND_INTEGRATION.md`. Issues are prioritized by impact and urgency.

### Summary of Gaps
- ✅ **FIXED:** PostgreSQL port mismatch (5433 vs 5432)
- 🔴 **CRITICAL:** Missing Stripe keys (blocks subscription testing)
- 🟡 **HIGH:** Account deletion endpoint (UX issue - button exists but fails)
- 🟢 **MEDIUM:** SSE token security (works but not production-ready)
- 🔵 **LOW:** Invoice history endpoint (not used in UI)
- 🔵 **LOW:** Cancel/reactivate subscription endpoints (handled via Stripe portal)

---

## 🎯 Priority 1: CRITICAL (Must Fix Before Testing)

### GAP-001: Missing Stripe Secret Keys

**Status:** 🔴 CRITICAL
**Impact:** Subscription upgrade/management completely blocked
**Estimated Time:** 15 minutes
**Difficulty:** Easy

#### Problem
Backend `.env` is missing:
- `STRIPE_SECRET_KEY` - Required for Stripe API calls
- `STRIPE_WEBHOOK_SECRET` - Required for webhook verification
- `FRONTEND_URL` - Used for Stripe redirect URLs

#### Current State
```bash
# backend/.env - Missing keys
STRIPE_SECRET_KEY=    # NOT SET
STRIPE_WEBHOOK_SECRET=    # NOT SET
FRONTEND_URL=    # NOT SET (defaults to localhost:3000)
```

#### Solution Steps

**Step 1: Get Stripe Test Keys**
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy "Secret key" (starts with `sk_test_`)
3. Go to https://dashboard.stripe.com/test/webhooks
4. Click "Add endpoint" or view existing endpoint
5. Copy "Signing secret" (starts with `whsec_`)

**Step 2: Update backend/.env**
```bash
# Add to backend/.env
STRIPE_SECRET_KEY=sk_test_your_actual_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_actual_secret_here
FRONTEND_URL=http://localhost:3000
```

**Step 3: Create Test Price ID**
1. Go to https://dashboard.stripe.com/test/products
2. Create product "Tru8 Professional"
3. Add price: £7/month
4. Copy price ID (starts with `price_`)

**Step 4: Update web/.env**
```bash
# Update in web/.env
NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=price_your_actual_price_id_here
```

**Step 5: Restart Backend**
```bash
cd backend
# Press Ctrl+C to stop
.\start-backend.bat    # Windows
# OR
./start-backend.sh     # Linux/macOS
```

#### Verification
1. Navigate to http://localhost:3000/dashboard/settings?tab=subscription
2. Click "Upgrade to Professional"
3. Should redirect to Stripe Checkout (real form, not error)
4. Cancel and return to app
5. Check should NOT show "Failed to start upgrade process"

#### Files to Modify
- `backend/.env` (add 3 environment variables)
- `web/.env` (update 1 environment variable)

#### Dependencies
- Stripe account with test mode enabled
- No code changes required

---

## 🎯 Priority 2: HIGH (Fix Before User Testing)

### GAP-002: Account Deletion Endpoint Not Implemented

**Status:** 🟡 HIGH
**Impact:** Settings page has "Delete Account" button that fails
**Estimated Time:** 2 hours
**Difficulty:** Medium

#### Problem
Frontend has account deletion flow with triple confirmation, but backend endpoint is missing:
- Frontend: `DELETE /api/v1/users/me` (web/lib/api.ts:181-185)
- Backend: Endpoint does not exist
- UX Impact: User clicks "Delete Account", goes through confirmations, then gets error

#### Solution Steps

**Step 1: Create Backend Endpoint**

Create/update `backend/app/api/v1/users.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models import User, Check, Subscription

@router.delete("/me")
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete user account and all associated data

    Deletes:
    - User record
    - All checks and claims/evidence (CASCADE)
    - All subscriptions
    - Cancels active Stripe subscription if exists

    This action is permanent and cannot be undone.
    """
    user_id = current_user["id"]

    try:
        # 1. Get user record
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 2. Cancel active Stripe subscriptions
        subscription_stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        )
        subscription_result = await session.execute(subscription_stmt)
        active_subscriptions = subscription_result.scalars().all()

        for sub in active_subscriptions:
            if sub.stripe_subscription_id:
                try:
                    # Cancel immediately (not at period end)
                    import stripe
                    stripe.Subscription.delete(sub.stripe_subscription_id)
                except Exception as e:
                    # Log but don't block deletion
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to cancel Stripe subscription {sub.stripe_subscription_id}: {e}")

        # 3. Delete all subscriptions (CASCADE will handle checks)
        await session.execute(
            delete(Subscription).where(Subscription.user_id == user_id)
        )

        # 4. Delete all checks (CASCADE will handle claims/evidence)
        await session.execute(
            delete(Check).where(Check.user_id == user_id)
        )

        # 5. Delete user record
        await session.delete(user)
        await session.commit()

        return {
            "message": "Account successfully deleted",
            "userId": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support."
        )
```

**Step 2: Update Database Models (if needed)**

Verify CASCADE is set on foreign keys in `backend/app/models/check.py`:

```python
# Check model should have:
user_id: str = Field(foreign_key="user.id", ondelete="CASCADE")

# Claim model should have:
check_id: str = Field(foreign_key="check.id", ondelete="CASCADE")

# Evidence model should have:
claim_id: str = Field(foreign_key="claim.id", ondelete="CASCADE")
```

**Step 3: Add Import to Router**

Ensure the endpoint is registered in `backend/main.py`:
```python
# Should already exist:
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

**Step 4: Test Backend Endpoint**

```bash
# Start backend
cd backend
.\start-backend.bat

# Test with curl (use real token)
curl -X DELETE http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected response:
# {"message": "Account successfully deleted", "userId": "user_123"}
```

**Step 5: Test Frontend Flow**

1. Navigate to http://localhost:3000/dashboard/settings?tab=account
2. Scroll to "Danger Zone"
3. Click "Delete Account"
4. Confirm all 3 prompts (type "DELETE")
5. Should redirect to homepage as signed-out user
6. Try to sign in with deleted account - should create NEW user

#### Verification Checklist
- [ ] Backend endpoint returns 200 with success message
- [ ] User record deleted from database
- [ ] All checks deleted (CASCADE)
- [ ] All claims deleted (CASCADE)
- [ ] All evidence deleted (CASCADE)
- [ ] Active Stripe subscription cancelled
- [ ] Frontend redirects to homepage
- [ ] Clerk user also deleted
- [ ] Re-signin creates fresh user with 3 credits

#### Files to Modify
- `backend/app/api/v1/users.py` (add delete endpoint, ~60 lines)
- `backend/app/models/check.py` (verify CASCADE, may already be correct)

#### Dependencies
- SQLModel CASCADE support
- Stripe API for subscription cancellation
- No frontend changes needed

#### Risks
- **Data Loss:** This is permanent deletion - ensure triple confirmation works
- **Stripe Sync:** Failed Stripe cancellation should not block account deletion
- **Clerk Sync:** Frontend handles Clerk deletion separately

---

## 🎯 Priority 3: MEDIUM (Security Enhancement)

### GAP-003: SSE Token Security Issue

**Status:** 🟢 MEDIUM
**Impact:** JWT token appears in server logs (security concern)
**Estimated Time:** 1.5 hours
**Difficulty:** Medium

#### Problem
Current SSE implementation passes JWT in query string:
```typescript
// web/hooks/use-check-progress.ts
const url = `${apiUrl}/api/v1/checks/${checkId}/progress?token=${token}`;
const eventSource = new EventSource(url);
```

**Security Issue:** Query parameters are logged by web servers, proxies, and browsers. JWTs should be in headers, but `EventSource` API doesn't support custom headers.

**Current Workaround:** Acceptable for MVP, but not production-ready.

#### Solution: Short-Lived SSE Token Exchange

**Flow:**
1. Frontend requests short-lived token (5 min expiry)
2. Backend generates signed token specific to check_id
3. Frontend passes short-lived token in query string
4. Backend validates short-lived token (not main JWT)

**Step 1: Create Token Generation Endpoint**

Add to `backend/app/api/v1/checks.py`:

```python
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

class SSETokenResponse(BaseModel):
    sse_token: str
    expires_in: int  # seconds

@router.post("/{check_id}/sse-token")
async def create_sse_token(
    check_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate a short-lived token for SSE streaming

    This token:
    - Expires in 5 minutes
    - Is only valid for this specific check_id
    - Is only valid for SSE endpoint (not API calls)
    - Cannot be used for other operations
    """
    # Verify check exists and belongs to user
    stmt = select(Check).where(
        Check.id == check_id,
        Check.user_id == current_user["id"]
    )
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check not found"
        )

    # Create short-lived token
    expires = datetime.utcnow() + timedelta(minutes=5)
    token_payload = {
        "check_id": check_id,
        "user_id": current_user["id"],
        "purpose": "sse",
        "exp": expires,
        "iat": datetime.utcnow()
    }

    sse_token = jwt.encode(
        token_payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return SSETokenResponse(
        sse_token=sse_token,
        expires_in=300  # 5 minutes
    )
```

**Step 2: Update SSE Endpoint to Accept Both Tokens**

Modify `backend/app/api/v1/checks.py` progress endpoint:

```python
from typing import Optional
from jose import jwt, JWTError

async def validate_sse_token(token: str, check_id: str) -> dict:
    """Validate short-lived SSE token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        # Verify purpose
        if payload.get("purpose") != "sse":
            raise HTTPException(status_code=403, detail="Invalid token purpose")

        # Verify check_id
        if payload.get("check_id") != check_id:
            raise HTTPException(status_code=403, detail="Token not valid for this check")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE token")

@router.get("/{check_id}/progress")
async def stream_check_progress(
    check_id: str,
    token: Optional[str] = Query(None),  # Short-lived SSE token
    current_user: Optional[dict] = Depends(get_current_user)  # OR main JWT
):
    """
    Stream real-time progress updates via SSE

    Authentication: Either provide:
    1. Short-lived SSE token in query (?token=xxx) [RECOMMENDED]
    2. Main JWT in Authorization header [LEGACY]
    """
    # Try short-lived token first
    if token:
        user_context = await validate_sse_token(token, check_id)
        user_id = user_context["user_id"]
    elif current_user:
        user_id = current_user["id"]
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Rest of SSE implementation...
```

**Step 3: Update Frontend Hook**

Modify `web/hooks/use-check-progress.ts`:

```typescript
export function useCheckProgress(
  checkId: string,
  token: string | null,
  enabled: boolean
): UseCheckProgressReturn {
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !token) return;

    const setupSSE = async () => {
      try {
        // Step 1: Request short-lived SSE token
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const response = await fetch(
          `${apiUrl}/api/v1/checks/${checkId}/sse-token`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to get SSE token');
        }

        const { sse_token } = await response.json();

        // Step 2: Connect with short-lived token
        const sseUrl = `${apiUrl}/api/v1/checks/${checkId}/progress?token=${sse_token}`;
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => setIsConnected(true);

        eventSource.onmessage = (event) => {
          const data: ProgressData = JSON.parse(event.data);
          // Handle progress events...
        };

        eventSource.onerror = () => {
          setIsConnected(false);
          setError('Connection lost');
          eventSource.close();
        };

      } catch (err) {
        setError('Failed to connect to progress stream');
        console.error('SSE setup error:', err);
      }
    };

    setupSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [checkId, token, enabled]);

  return { progress, currentStage, isConnected, error };
}
```

**Step 4: Test Implementation**

1. Create a check
2. Navigate to check detail page
3. Verify SSE connection works
4. Check browser DevTools Network tab:
   - Should see POST to `/sse-token`
   - Should see EventSource connection with short token
5. Check backend logs:
   - Should NOT see main JWT in logs
   - Should see short-lived token (safe to log)

#### Verification Checklist
- [ ] POST /checks/{id}/sse-token returns short-lived token
- [ ] SSE endpoint accepts short-lived token
- [ ] SSE endpoint still accepts main JWT (backward compatible)
- [ ] Token expires after 5 minutes
- [ ] Token only works for specific check_id
- [ ] Frontend successfully connects with new flow
- [ ] No main JWT visible in server logs

#### Files to Modify
- `backend/app/api/v1/checks.py` (add endpoint + validation, ~80 lines)
- `web/hooks/use-check-progress.ts` (modify connection logic, ~20 lines)

#### Dependencies
- `python-jose` (already in requirements.txt)
- No new dependencies needed

#### Migration Strategy
- Backend supports both authentication methods
- Frontend can deploy new version independently
- Old clients continue working with JWT in query
- New clients use short-lived tokens

---

## 🎯 Priority 4: LOW (Nice to Have)

### GAP-004: Invoice History Endpoint

**Status:** 🔵 LOW
**Impact:** No current UI uses this feature
**Estimated Time:** 1 hour
**Difficulty:** Easy

#### Problem
Frontend has API method but endpoint doesn't exist and no UI uses it:
- Frontend: `GET /api/v1/payments/invoices` (web/lib/api.ts:172-174)
- Backend: Endpoint does not exist
- UI Impact: None (not displayed anywhere)

#### Solution Steps

**Step 1: Add Endpoint to Backend**

Add to `backend/app/api/v1/payments.py`:

```python
@router.get("/invoices")
async def get_invoices(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 5
):
    """
    Fetch user's recent Stripe invoices

    Returns last 5 invoices (or specified limit)
    Only returns invoices if user has active/past subscription
    """
    # Get user's subscription
    stmt = select(Subscription).where(
        Subscription.user_id == current_user["id"]
    ).order_by(desc(Subscription.created_at)).limit(1)
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription or not subscription.stripe_customer_id:
        return {"invoices": []}

    try:
        import stripe

        # Fetch invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=subscription.stripe_customer_id,
            limit=limit
        )

        return {
            "invoices": [
                {
                    "id": inv.id,
                    "number": inv.number,
                    "amount": inv.amount_paid / 100,  # Convert from cents
                    "currency": inv.currency.upper(),
                    "status": inv.status,
                    "date": datetime.fromtimestamp(inv.created).isoformat(),
                    "invoicePdf": inv.invoice_pdf,
                    "hostedInvoiceUrl": inv.hosted_invoice_url,
                }
                for inv in invoices.data
            ]
        }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to fetch invoices for user {current_user['id']}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve invoices"
        )
```

**Step 2: Add to Settings UI (Optional)**

If you want to display invoices, add to `web/app/dashboard/settings/components/subscription-tab.tsx`:

```typescript
// Add after subscription cards
<section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
  <h3 className="text-xl font-bold text-white mb-4">Billing History</h3>
  {/* Fetch and display invoices */}
</section>
```

#### Recommendation
**SKIP FOR NOW** - No UI needs this yet. Implement when building billing history feature.

---

### GAP-005: Cancel/Reactivate Subscription Endpoints

**Status:** 🔵 LOW
**Impact:** Functionality handled via Stripe billing portal
**Estimated Time:** 1.5 hours
**Difficulty:** Medium

#### Problem
Frontend has API methods but endpoints don't exist:
- Frontend: `POST /api/v1/payments/cancel-subscription` (web/lib/api.ts:192-196)
- Frontend: `POST /api/v1/payments/reactivate-subscription` (web/lib/api.ts:199-207)
- Backend: Endpoints do not exist
- Current Solution: Users click "Manage Subscription" → Stripe portal handles cancel/reactivate

#### Solution Steps

**Step 1: Add Cancel Endpoint**

```python
@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel subscription at end of billing period"""
    # Implementation...
```

**Step 2: Add Reactivate Endpoint**

```python
@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Reactivate cancelled subscription before period end"""
    # Implementation...
```

#### Recommendation
**SKIP FOR NOW** - Stripe billing portal already provides this functionality. Only implement if you want custom cancel flow in your app.

---

## 📝 Implementation Order

### Phase 1: Pre-Launch Critical (Must Do)
1. ✅ **DONE:** Fix PostgreSQL port mismatch
2. 🔴 **GAP-001:** Add Stripe keys to backend (15 min)
3. 🟡 **GAP-002:** Implement account deletion endpoint (2 hours)

**Estimated Time:** 2.25 hours
**Blocking:** Subscription testing + Settings page UX

---

### Phase 2: Post-Launch Enhancement (Should Do)
4. 🟢 **GAP-003:** Implement SSE token security (1.5 hours)

**Estimated Time:** 1.5 hours
**Blocking:** Production security requirements

---

### Phase 3: Future Features (Nice to Have)
5. 🔵 **GAP-004:** Invoice history endpoint (1 hour) - When building billing UI
6. 🔵 **GAP-005:** Cancel/reactivate endpoints (1.5 hours) - Only if custom flow needed

**Estimated Time:** 2.5 hours
**Blocking:** Nothing (alternative solutions exist)

---

## ✅ Success Criteria

### After Phase 1 (Critical)
- [ ] Stripe checkout redirects to real payment form
- [ ] Users can upgrade to Professional plan
- [ ] Users can manage subscription via Stripe portal
- [ ] Account deletion works end-to-end
- [ ] No error messages on Settings page

### After Phase 2 (Enhancement)
- [ ] SSE connections use short-lived tokens
- [ ] Main JWT never appears in server logs
- [ ] Real-time progress updates still work

### After Phase 3 (Features)
- [ ] Users can view billing history (if UI built)
- [ ] Users can cancel directly in app (if flow built)

---

## 🚀 Getting Started

### Option A: Fix Everything in Order (Recommended)
```bash
# Work through gaps in priority order
1. Configure Stripe keys (15 min)
2. Implement account deletion (2 hours)
3. Test everything works
4. Deploy to production
5. Later: Add SSE token security
```

### Option B: Parallel Approach (If Multiple Developers)
```bash
Developer 1: GAP-001 (Stripe keys) + testing
Developer 2: GAP-002 (Account deletion endpoint)
Developer 3: GAP-003 (SSE token security)
```

### Option C: MVP Launch Only (Fastest)
```bash
# Minimum to launch
1. Add Stripe keys (15 min)
2. Hide "Delete Account" button temporarily
3. Launch with SSE query param auth
4. Fix GAP-002 and GAP-003 post-launch
```

---

## 📞 Need Help?

### Stripe Configuration
- Docs: https://stripe.com/docs/keys
- Dashboard: https://dashboard.stripe.com/test/apikeys
- Webhooks: https://dashboard.stripe.com/test/webhooks

### Database CASCADE Issues
- Check `backend/app/models/check.py` for foreign key definitions
- Test with: `pytest tests/test_user_deletion.py` (create this test)

### SSE Token Implementation
- Reference: `python-jose` for JWT signing
- Test with: Browser DevTools → Network tab → EventSource

---

**Last Updated:** October 14, 2025
**Next Review:** After completing Phase 1 (Critical fixes)
