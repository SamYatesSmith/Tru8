# Phase 5: Pricing (Free + Professional Plans)

**Status:** Not Started
**Estimated Time:** 2 hours
**Dependencies:** Phase 2 (Auth modal functional)
**Backend Integration:** Stripe checkout for Professional plan

---

## 🎯 Objectives

1. Create pricing cards component (Free + Professional)
2. Wire up Free plan CTA to auth modal
3. Wire up Professional plan CTA to Stripe checkout
4. Test Stripe checkout session creation
5. Verify payment flow end-to-end

---

## 📋 Task Checklist

- [ ] **Task 5.1:** Create pricing cards component
- [ ] **Task 5.2:** Wire Free plan CTA to auth modal
- [ ] **Task 5.3:** Wire Professional plan CTA to Stripe checkout
- [ ] **Task 5.4:** Test Stripe checkout session creation
- [ ] **Task 5.5:** Test end-to-end payment flow

---

## 🔧 Implementation

### **Task 5.1: Pricing Component**

File: `web/components/marketing/pricing-cards.tsx`

**Free Plan:**
- Price: £0
- Features: "7 day trial / 5 free checks", "Basic source checking", "Standard support", "Web interface access"
- CTA: "START FREE TRIAL" → Opens Clerk auth modal
- Border: slate-700

**Professional Plan:**
- Price: £7/month
- Badge: "Most Popular" (cyan)
- Features: "X40 verifications p/m", "Ability to verify URL's", "Quick & Deep modes", "Export to PDF/JSON/CSV", "Comprehensive sources (10+ citations)", "Priority support"
- CTA: "GET STARTED" → Stripe checkout
- Border: cyan-400 (highlighted)

---

### **Task 5.2: Free Plan Integration**

**Action:** Opens auth modal (from Phase 2)

```typescript
<button onClick={() => setIsAuthModalOpen(true)}>
  START FREE TRIAL
</button>
```

**After auth:**
1. Clerk redirects to `/dashboard`
2. Dashboard calls `GET /api/v1/users/me`
3. Backend auto-creates user with 3 credits
4. User sees dashboard with free tier

---

### **Task 5.3: Professional Plan Integration**

**Backend Endpoint:** `POST /api/v1/payments/create-checkout-session`

**Request:**
```json
{
  "price_id": "price_xxx", // Stripe price ID from env
  "plan": "professional"
}
```

**Response:**
```json
{
  "session_id": "cs_xxx",
  "url": "https://checkout.stripe.com/..."
}
```

**Frontend Flow:**
```typescript
const handleProfessionalPlan = async () => {
  // 1. Check if user is authenticated
  const { isSignedIn } = useAuth();

  if (!isSignedIn) {
    // Open auth modal first
    setIsAuthModalOpen(true);
    return;
  }

  // 2. Create Stripe checkout session
  const session = await apiClient.createCheckoutSession({
    price_id: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO!,
    plan: 'professional'
  });

  // 3. Redirect to Stripe checkout
  window.location.href = session.url;
};
```

**After Payment:**
1. Stripe redirects to success URL: `/account?success=true`
2. Stripe webhook creates Subscription in backend
3. User's account upgraded to Professional tier
4. User sees dashboard with 40 credits/month

---

### **Task 5.4-5.5: Testing**

**Test 1: Free Plan**
1. Click "START FREE TRIAL"
2. Verify auth modal opens
3. Sign up with test account
4. Verify redirect to `/dashboard`
5. Verify 3 credits in database

**Test 2: Professional Plan (Not Authenticated)**
1. Click "GET STARTED"
2. Verify auth modal opens first
3. Sign up, then trigger checkout
4. Verify Stripe checkout URL generated

**Test 3: Professional Plan (Authenticated)**
1. Already signed in
2. Click "GET STARTED"
3. Verify Stripe checkout opens immediately
4. Use test card: `4242 4242 4242 4242`
5. Complete payment
6. Verify redirect to `/account?success=true`
7. Verify Subscription created in database

---

## 🔗 Backend Integration Details

### **POST /api/v1/payments/create-checkout-session**

**Purpose:** Create Stripe checkout session for Professional plan

**Request:**
```http
POST /api/v1/payments/create-checkout-session
Authorization: Bearer <clerk_jwt_token>
Content-Type: application/json

{
  "price_id": "price_1234",
  "plan": "professional"
}
```

**Response (200 OK):**
```json
{
  "session_id": "cs_test_xxx",
  "url": "https://checkout.stripe.com/c/pay/cs_test_xxx"
}
```

**Backend Implementation** (`backend/app/api/v1/payments.py:30-85`):
```python
checkout_session = stripe.checkout.Session.create(
    customer_email=user.email,
    client_reference_id=user.id,
    line_items=[{'price': request.price_id, 'quantity': 1}],
    mode='subscription',
    success_url=f"{FRONTEND_URL}/account?success=true",
    cancel_url=f"{FRONTEND_URL}/account?cancelled=true",
    metadata={'user_id': user.id, 'plan': request.plan}
)
```

**Stripe Webhook Handler:**
- Event: `checkout.session.completed`
- Action: Creates Subscription record in database
- Credits: Sets `credits_per_month=40` for Professional plan

---

## ✅ Definition of Done

- [ ] Pricing component created with both plans
- [ ] Free plan CTA opens auth modal
- [ ] Professional plan CTA creates Stripe checkout (if authenticated)
- [ ] Professional plan CTA opens auth first (if not authenticated)
- [ ] Stripe checkout tested with test card
- [ ] Subscription created in database after payment
- [ ] No console errors
- [ ] Component documented
- [ ] Files committed with detailed message

---

## 📝 Commit Message Template

```
[Phase 5] Add pricing cards with Stripe integration

Pricing Component:
- 2 plans: Free (£0) + Professional (£7/month)
- Free plan: 3 checks, basic features
- Professional plan: 40 checks/month, advanced features
- "Most Popular" badge on Professional plan
- Cyan border highlight on Professional card

Free Plan Integration:
- CTA: "START FREE TRIAL"
- Action: Opens Clerk auth modal
- After auth: User created with 3 credits
- Tested: User receives 3 credits in database

Professional Plan Integration:
- CTA: "GET STARTED"
- Action: Creates Stripe checkout session
- Endpoint: POST /api/v1/payments/create-checkout-session
- Request: {price_id, plan: "professional"}
- Response: {session_id, url}
- Redirect: window.location.href = session.url
- Tested: Stripe checkout opens, payment succeeds

Backend Integration:
- Tested Stripe checkout session creation
- Verified webhook creates Subscription record
- Confirmed user upgraded to Professional tier

Files created:
- components/marketing/pricing-cards.tsx

Files modified:
- app/page.tsx (added pricing section)
- lib/api.ts (added createCheckoutSession method)

Testing performed:
- ✅ Free plan opens auth modal
- ✅ Professional plan creates Stripe checkout
- ✅ Test payment completes successfully
- ✅ Subscription created in database
- ✅ User upgraded to Professional tier
```

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Next Phase:** Phase 6 (Footer)
