# 🔌 BACKEND API ENDPOINTS REQUIRED

**Purpose:** Complete list of all backend endpoints referenced in dashboard implementation plans
**Last Updated:** 2025-10-13
**Status:** Ready for Backend Implementation

---

## **EXISTING ENDPOINTS (Already Implemented)**

### **User Management**
✅ `GET /api/v1/users/me`
- **Purpose:** Fetch current user data
- **Auth:** Bearer token (Clerk JWT)
- **Response:**
```json
{
  "id": "string",
  "email": "string",
  "name": "string | null",
  "credits": 3,
  "totalCreditsUsed": 0,
  "hasSubscription": false,
  "createdAt": "2024-01-01T00:00:00Z"
}
```
- **Used In:** All dashboard pages (layout fetch)
- **File:** `backend/app/api/v1/users.py:10-31`

---

### **Check Management**
✅ `POST /api/v1/checks`
- **Purpose:** Create new fact-check
- **Auth:** Bearer token
- **Request:**
```json
{
  "input_type": "url" | "text" | "image" | "video",
  "url": "string (optional)",
  "content": "string (optional)"
}
```
- **Response:**
```json
{
  "check": {
    "id": "string",
    "user_id": "string",
    "input_type": "url",
    "status": "pending",
    "credits_used": 1,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```
- **Used In:** New Check page
- **File:** `backend/app/api/v1/checks.py:23-44`

---

✅ `GET /api/v1/checks`
- **Purpose:** Get user's check history (paginated)
- **Auth:** Bearer token
- **Query Params:**
  - `skip`: number (default 0)
  - `limit`: number (default 20)
- **Response:**
```json
{
  "checks": [
    {
      "id": "string",
      "input_type": "url",
      "url": "string | null",
      "content": "string | null",
      "status": "completed",
      "credits_used": 1,
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:05:00Z",
      "claims": [
        {
          "id": "string",
          "text": "string",
          "verdict": "supported" | "contradicted" | "uncertain",
          "confidence": 87.5
        }
      ]
    }
  ],
  "total": 100
}
```
- **Used In:** Dashboard home, History page
- **File:** `backend/app/api/v1/checks.py:47-71`

---

✅ `GET /api/v1/checks/{check_id}`
- **Purpose:** Get single check with full details
- **Auth:** Bearer token
- **Response:**
```json
{
  "check": {
    "id": "string",
    "user_id": "string",
    "input_type": "url",
    "url": "string | null",
    "content": "string | null",
    "status": "completed",
    "error_message": "string | null",
    "credits_used": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z",
    "completed_at": "2024-01-01T00:05:00Z"
  },
  "claims": [
    {
      "id": "string",
      "check_id": "string",
      "text": "The unemployment rate decreased to 3.7%",
      "verdict": "supported",
      "confidence": 87.5,
      "reasoning": "Multiple credible sources confirm...",
      "order_index": 0
    }
  ],
  "evidence": [
    {
      "id": "string",
      "claim_id": "string",
      "source": "Bureau of Labor Statistics",
      "url": "https://bls.gov/news/...",
      "title": "Employment Situation Summary",
      "snippet": "The unemployment rate edged down to 3.7 percent...",
      "published_date": "2024-01-05T00:00:00Z",
      "credibility_score": 9.2,
      "relevance_score": 8.8
    }
  ]
}
```
- **Used In:** Check Detail page
- **File:** `backend/app/api/v1/checks.py:74-112`

---

✅ `GET /api/v1/checks/{check_id}/progress`
- **Purpose:** Server-Sent Events (SSE) for real-time progress
- **Auth:** Short-lived SSE token (query param)
- **Query Params:**
  - `token`: string (short-lived SSE token)
- **SSE Events:**
```
data: {"stage": "ingest", "status": "completed", "message": "Content ingested"}
data: {"stage": "extract", "status": "processing", "message": "Extracting claims..."}
data: {"progress": 40}
```
- **Stages:** ingest, extract, retrieve, verify, judge
- **Used In:** Check Detail page (real-time progress)
- **File:** `backend/app/api/v1/checks.py:129-161`

---

### **Payment Management**
✅ `GET /api/v1/payments/subscription-status`
- **Purpose:** Get current subscription details
- **Auth:** Bearer token
- **Response:**
```json
{
  "hasSubscription": true,
  "plan": "pro",
  "status": "active",
  "creditsPerMonth": 100,
  "creditsRemaining": 75,
  "currentPeriodStart": "2024-01-01T00:00:00Z",
  "currentPeriodEnd": "2024-02-01T00:00:00Z",
  "cancelAtPeriodEnd": false
}
```
- **Used In:** Dashboard, Settings
- **File:** `backend/app/api/v1/payments.py:10-45`

---

✅ `POST /api/v1/payments/create-checkout-session`
- **Purpose:** Create Stripe checkout session for upgrade
- **Auth:** Bearer token
- **Request:**
```json
{
  "priceId": "price_xxxxx",
  "successUrl": "https://app.tru8.com/dashboard/settings?tab=subscription&success=true",
  "cancelUrl": "https://app.tru8.com/dashboard/settings?tab=subscription"
}
```
- **Response:**
```json
{
  "url": "https://checkout.stripe.com/pay/cs_xxxxx"
}
```
- **Used In:** Settings page (upgrade flow)
- **File:** `backend/app/api/v1/payments.py:48-78`

---

✅ `POST /api/v1/payments/create-portal-session`
- **Purpose:** Create Stripe billing portal session
- **Auth:** Bearer token
- **Response:**
```json
{
  "url": "https://billing.stripe.com/session/xxxxx"
}
```
- **Used In:** Settings page (manage subscription)
- **File:** `backend/app/api/v1/payments.py:81-102`

---

## **NEW ENDPOINTS REQUIRED**

### **SSE Token Security (GAP #16)**
🆕 `POST /api/v1/checks/{check_id}/sse-token`
- **Purpose:** Generate short-lived token for SSE connection
- **Auth:** Bearer token (Clerk JWT)
- **Request:** None (check_id in path)
- **Response:**
```json
{
  "token": "eyJhbGc...",
  "expires_in": 300
}
```
- **Implementation:**
```python
@router.post("/checks/{check_id}/sse-token")
async def create_sse_token(
    check_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user owns the check
    check = db.query(Check).filter(
        Check.id == check_id,
        Check.user_id == current_user.id
    ).first()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Create short-lived token (5 min expiry)
    token = create_jwt_token(
        user_id=current_user.id,
        check_id=check_id,
        exp=300,  # 5 minutes
        scope="sse_only"
    )

    return {"token": token, "expires_in": 300}
```
- **Used In:** Check Detail page (before opening SSE connection)
- **Priority:** HIGH (security)
- **Source:** GAP #16, PLAN_05

---

### **Billing History (GAP #17)**
🆕 `GET /api/v1/payments/invoices`
- **Purpose:** Fetch last 5 Stripe invoices
- **Auth:** Bearer token
- **Response:**
```json
{
  "invoices": [
    {
      "id": "in_xxxxx",
      "date": 1704067200,
      "amount": 7.00,
      "currency": "gbp",
      "status": "paid",
      "pdf_url": "https://pay.stripe.com/invoice/xxxxx/pdf"
    }
  ]
}
```
- **Implementation:**
```python
@router.get("/invoices")
async def get_invoices(current_user: User = Depends(get_current_user)):
    # Only for Pro users with Stripe customer ID
    if not current_user.stripe_customer_id:
        return {"invoices": []}

    stripe_customer_id = current_user.stripe_customer_id
    invoices = stripe.Invoice.list(customer=stripe_customer_id, limit=5)

    return {
        "invoices": [
            {
                "id": inv.id,
                "date": inv.created,
                "amount": inv.amount_paid / 100,
                "currency": inv.currency,
                "status": inv.status,
                "pdf_url": inv.invoice_pdf
            }
            for inv in invoices.data
        ]
    }
```
- **Used In:** Settings page (Subscription tab, Pro users only)
- **Priority:** LOW (nice-to-have)
- **Source:** GAP #17, PLAN_06

---

### **Account Deletion (GAP #18)**
🆕 `DELETE /api/v1/users/me`
- **Purpose:** Delete user account and all associated data (GDPR compliance)
- **Auth:** Bearer token
- **Response:**
```json
{
  "message": "User deleted successfully"
}
```
- **Implementation:**
```python
@router.delete("/users/me")
async def delete_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Delete all checks (cascade deletes claims and evidence via foreign key)
    db.query(Check).filter(Check.user_id == current_user.id).delete()

    # Delete subscription records
    db.query(Subscription).filter(Subscription.user_id == current_user.id).delete()

    # Delete user
    db.delete(current_user)
    db.commit()

    return {"message": "User deleted successfully"}
```
- **Database Cascade Requirements:**
  - User deletion → cascades to Checks
  - Check deletion → cascades to Claims
  - Claim deletion → cascades to Evidence
  - Ensure foreign key constraints: `ON DELETE CASCADE`
- **Used In:** Settings page (Account tab, Danger Zone)
- **Priority:** MEDIUM (GDPR compliance)
- **Source:** GAP #18, PLAN_06

---

### **Subscription Cancellation (GAP #19)**
🆕 `POST /api/v1/payments/cancel-subscription`
- **Purpose:** Cancel subscription at end of billing period
- **Auth:** Bearer token
- **Response:**
```json
{
  "message": "Subscription will cancel at period end",
  "cancel_at": 1706745600
}
```
- **Implementation:**
```python
@router.post("/payments/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Set Stripe subscription to cancel at period end
    subscription = stripe.Subscription.modify(
        current_user.stripe_subscription_id,
        cancel_at_period_end=True
    )

    return {
        "message": "Subscription will cancel at period end",
        "cancel_at": subscription.current_period_end
    }
```
- **Webhook Handling Required:**
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    event = stripe.Webhook.construct_event(
        await request.body(),
        request.headers.get("stripe-signature"),
        STRIPE_WEBHOOK_SECRET
    )

    if event.type == "customer.subscription.deleted":
        # Subscription ended - downgrade user to Free
        subscription = event.data.object
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription.id
        ).first()

        if user:
            # Reset to free plan
            user.stripe_subscription_id = None
            user.credits = 3
            db.commit()

    return {"status": "success"}
```
- **Used In:** Settings page (Subscription tab, downgrade flow)
- **Priority:** LOW (Pro users only)
- **Source:** GAP #19, PLAN_06

---

### **Subscription Reactivation (GAP #19 - Optional)**
🆕 `POST /api/v1/payments/reactivate-subscription`
- **Purpose:** Reactivate subscription before period end
- **Auth:** Bearer token
- **Response:**
```json
{
  "message": "Subscription reactivated",
  "next_billing_date": 1706745600
}
```
- **Implementation:**
```python
@router.post("/payments/reactivate-subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user)
):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Remove cancel_at_period_end flag
    subscription = stripe.Subscription.modify(
        current_user.stripe_subscription_id,
        cancel_at_period_end=False
    )

    return {
        "message": "Subscription reactivated",
        "next_billing_date": subscription.current_period_end
    }
```
- **Used In:** Settings page (when user has pending cancellation)
- **Priority:** LOW (nice-to-have)
- **Source:** GAP #19, PLAN_06

---

## **VALIDATION REQUIREMENTS**

### **Text Input Validation (GAP #13)**
Backend should validate text input on `POST /api/v1/checks`:
```python
@router.post("/checks")
async def create_check(request: CheckCreateRequest, ...):
    if request.input_type == "text":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content required for text input")

        if len(request.content) < 10:
            raise HTTPException(status_code=400, detail="Minimum 10 characters required")

        if len(request.content) > 5000:
            raise HTTPException(status_code=400, detail="Maximum 5000 characters exceeded")

    # Continue processing...
```
- **Min:** 10 characters
- **Max:** 5,000 characters
- **Source:** GAP #13, PLAN_04

---

## **SUMMARY**

### **Existing Endpoints:** 8
- User management: 1
- Check management: 4
- Payment management: 3

### **New Endpoints Required:** 5
- SSE token generation: 1 (HIGH priority)
- Billing history: 1 (LOW priority)
- Account deletion: 1 (MEDIUM priority)
- Subscription cancellation: 1 (LOW priority)
- Subscription reactivation: 1 (OPTIONAL)

### **Validation Updates:** 1
- Text input length validation (PLAN_04)

### **Database Schema Updates Required:**
- None (all use existing models)
- Ensure CASCADE DELETE foreign keys configured

### **Environment Variables Required:**
- `NEXT_PUBLIC_STRIPE_PRICE_ID_PRO` (frontend)
- `STRIPE_WEBHOOK_SECRET` (backend)

---

**Status:** All endpoints documented and implementation-ready
