# Enabling Paid Subscriptions

**Purpose:** Checklist for transitioning from beta (free) to production (paid subscriptions)

**Current State:** Beta testing with subscriptions disabled

---

## Quick Summary

When ready to accept payments, you need to:

1. Set `SUBSCRIPTIONS_ENABLED=true` (backend)
2. Set `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true` (frontend)
3. Configure production Stripe keys
4. Remove beta testers from unlimited access (optional)

---

## Pre-Launch Checklist

### 1. Stripe Configuration

| Task | Status | Notes |
|------|--------|-------|
| Create production Stripe account | [ ] | https://dashboard.stripe.com |
| Create Pro plan product + price | [ ] | £7/month, 40 checks |
| Get live API keys (`sk_live_*`, `pk_live_*`) | [ ] | Settings → API Keys |
| Configure webhook endpoint | [ ] | `https://api.trueight.com/api/v1/payments/webhook` |
| Get webhook signing secret (`whsec_*`) | [ ] | Webhooks → Add endpoint → Signing secret |
| Test webhook locally with Stripe CLI | [ ] | `stripe listen --forward-to localhost:8000/api/v1/payments/webhook` |

### 2. Backend Environment Variables

Update in Railway variables (or your hosting provider):

```bash
# Enable subscriptions
SUBSCRIPTIONS_ENABLED=true

# Stripe Production Keys
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
STRIPE_PRICE_ID_PRO=price_xxxxxxxxxxxx  # Your live price ID

# Optional: Remove beta testers (or keep for continued free access)
BETA_TESTER_EMAILS=[]  # Empty array to disable beta access
```

**Commands:**
```bash
# Railway
railway variables set SUBSCRIPTIONS_ENABLED=true
railway variables set STRIPE_SECRET_KEY=sk_live_xxx
railway variables set STRIPE_WEBHOOK_SECRET=whsec_xxx
railway variables set STRIPE_PRICE_ID_PRO=price_xxx

# To remove beta testers
railway variables set BETA_TESTER_EMAILS='[]'
```

### 3. Frontend Environment Variables

Update in Railway (web service):

```bash
# Enable subscriptions UI
railway variables set NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true --service web

# Stripe Production Keys
railway variables set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxx --service web
railway variables set NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=price_xxxxxxxxxxxx --service web
```

**Railway Dashboard:**
1. Go to Project → Web Service → Variables tab
2. Update the variables above
3. Redeploy triggers automatically on variable change

### 4. Webhook Events to Handle

Ensure your Stripe webhook is configured to receive these events:

| Event | Purpose |
|-------|---------|
| `checkout.session.completed` | New subscription created |
| `customer.subscription.updated` | Plan changed, renewed, etc. |
| `customer.subscription.deleted` | Subscription cancelled |
| `invoice.paid` | Monthly renewal successful |
| `invoice.payment_failed` | Payment failed (optional) |

---

## What Changes When Enabled

### Pricing Page (`/` landing page)

| Element | Beta (disabled) | Production (enabled) |
|---------|-----------------|----------------------|
| Pro badge | "Coming Soon" (amber) | "Most Popular" (cyan) |
| Pro CTA button | "JOIN WAITLIST" | "GET STARTED" |
| Click action | Shows waitlist modal | Redirects to Stripe Checkout |

### Settings Page (`/dashboard/settings`)

| Element | Beta (disabled) | Production (enabled) |
|---------|-----------------|----------------------|
| Subscription tab | Shows "Coming Soon" + waitlist form | Shows upgrade button + plan comparison |
| Upgrade button | "Join Waitlist" | "Upgrade to Professional" |

### Upgrade Prompts (banners, modals)

| Element | Beta (disabled) | Production (enabled) |
|---------|-----------------|----------------------|
| Banner text | "Pro Features Coming Soon" | "Unlock Premium Features" |
| CTA | "Join Waitlist" | "Upgrade Now" |
| Badge | "Beta" indicator | None |

### API Behavior

| Endpoint | Beta (disabled) | Production (enabled) |
|----------|-----------------|----------------------|
| `POST /payments/create-checkout-session` | Returns 503 "Coming Soon" | Creates Stripe session |
| `GET /payments/subscription-status` | Returns `subscriptionsEnabled: false` | Returns `subscriptionsEnabled: true` |

---

## Beta Tester Handling

### Current Beta Configuration

Beta testers are defined by email in:
```bash
BETA_TESTER_EMAILS=["tester1@example.com","tester2@example.com"]
```

**Beta testers get:**
- Unlimited checks (no monthly limit)
- No credit deductions

### Options When Launching Paid Subscriptions

**Option A: Remove all beta access**
```bash
BETA_TESTER_EMAILS=[]
```
All users now subject to normal limits (3 free checks/month).

**Option B: Keep beta testers with free access**
```bash
BETA_TESTER_EMAILS=["loyal-tester@example.com"]
```
Listed users continue to have unlimited access, everyone else pays.

**Option C: Convert beta testers to Pro subscriptions**
1. Remove from `BETA_TESTER_EMAILS`
2. Manually create subscription records in database, or
3. Give them a 100% off Stripe coupon

### Notifying Beta Testers

Before removing beta access:
1. Email beta testers thanking them
2. Give advance notice (e.g., "Free access ends [date]")
3. Offer a discount code for their first month (Stripe coupon)

---

## Testing Before Launch

### 1. Test with Stripe Test Mode First

Before switching to live keys:

```bash
# Backend (test keys)
SUBSCRIPTIONS_ENABLED=true
STRIPE_SECRET_KEY=sk_test_xxxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxxx

# Frontend (test keys)
NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxx
```

### 2. Test Scenarios

| Scenario | How to Test | Expected Result |
|----------|-------------|-----------------|
| New subscription | Click "Get Started" on Pro plan | Redirects to Stripe, subscription created |
| Successful payment | Complete Stripe checkout | User upgraded, credits = 40 |
| Subscription renewal | Use Stripe CLI to trigger `invoice.paid` | Credits reset to 40 |
| Cancellation | Cancel via settings or Stripe portal | Status = cancelled, access until period end |
| Failed payment | Use Stripe test card `4000000000000341` | Webhook receives `invoice.payment_failed` |

### 3. Stripe Test Cards

| Card Number | Result |
|-------------|--------|
| `4242424242424242` | Success |
| `4000000000000002` | Declined |
| `4000000000000341` | Attaches but fails on charge |
| `4000002500003155` | Requires 3D Secure |

---

## Launch Day Checklist

### Morning of Launch

- [ ] Take database backup
- [ ] Verify Stripe live webhook is active
- [ ] Set backend `SUBSCRIPTIONS_ENABLED=true`
- [ ] Set frontend `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=true`
- [ ] Redeploy backend
- [ ] Redeploy frontend
- [ ] Test one real subscription (use a real card, refund after)

### Post-Launch Monitoring

- [ ] Check Stripe dashboard for successful payments
- [ ] Monitor Sentry for errors
- [ ] Check webhook delivery in Stripe dashboard
- [ ] Verify user credits are updated correctly
- [ ] Respond to any customer support inquiries

---

## Rollback Plan

If issues arise, you can instantly disable subscriptions:

```bash
# Backend
railway variables set SUBSCRIPTIONS_ENABLED=false

# Frontend
# Update NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=false in Railway web service and redeploy
railway variables set NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=false --service web
```

This will:
- Show "Coming Soon" on pricing page again
- Block new subscription attempts
- Existing subscribers continue to work (Stripe webhooks still process)

---

## Environment Variable Reference

### Backend (`SUBSCRIPTIONS_ENABLED`)

| Value | Effect |
|-------|--------|
| `false` (default) | `/payments/create-checkout-session` returns 503 |
| `true` | Stripe checkout flow works normally |

### Backend (`BETA_TESTER_EMAILS`)

| Value | Effect |
|-------|--------|
| `[]` (empty) | No beta testers, normal limits apply |
| `["email@example.com"]` | Listed emails get unlimited checks |

### Frontend (`NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED`)

| Value | Effect |
|-------|--------|
| `false` (default) | Shows "Coming Soon" badge, "Join Waitlist" buttons |
| `true` | Shows "Most Popular" badge, "Get Started" buttons |

---

## Files Involved

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | `SUBSCRIPTIONS_ENABLED`, `BETA_TESTER_EMAILS` definitions |
| `backend/app/api/v1/payments.py` | Subscription gate check |
| `backend/app/api/v1/checks.py` | Beta tester credit bypass |
| `web/.env` | `NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED` |
| `web/components/marketing/pricing-cards.tsx` | Pricing page UI |
| `web/components/subscriptions/coming-soon.tsx` | Waitlist modal |
| `web/app/dashboard/settings/components/subscription-tab.tsx` | Settings page subscription UI |
| `web/app/dashboard/components/upgrade-banner.tsx` | Upgrade banner UI |

---

## Support Contacts

| Role | Contact |
|------|---------|
| Stripe Support | https://support.stripe.com |
| Stripe Status | https://status.stripe.com |

---

*Document created for Tru8 beta → production transition*
