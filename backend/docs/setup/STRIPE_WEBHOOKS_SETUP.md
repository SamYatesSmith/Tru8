# Stripe Webhooks Setup Guide

## Why Webhooks?

Stripe webhooks notify your backend when events occur (payments, renewals, cancellations). Without them:
- Subscription period dates won't update on renewal
- Monthly credits won't reset
- Cancellations won't be tracked

---

## Step 1: Get Your Backend Webhook URL

Your endpoint is:
```
https://<your-backend-domain>/api/v1/payments/webhook
```

Examples:
- Fly.io: `https://tru8-api.fly.dev/api/v1/payments/webhook`
- Railway: `https://tru8-backend.up.railway.app/api/v1/payments/webhook`
- Local (ngrok): `https://abc123.ngrok.io/api/v1/payments/webhook`

---

## Step 2: Create Webhook in Stripe Dashboard

1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Developers** → **Webhooks**
3. Click **"+ Add destination"**

---

## Step 3: Configure the Webhook

### Select Events
Choose these 4 events:

| Event | Purpose |
|-------|---------|
| `checkout.session.completed` | Initial subscription purchase |
| `customer.subscription.updated` | Subscription changes |
| `customer.subscription.deleted` | Cancellation |
| `invoice.paid` | Renewal payments (resets monthly credits) |

### Enter Endpoint URL
Paste your backend webhook URL from Step 1.

### Save
Click **"Add destination"** or **"Create"**

---

## Step 4: Copy Webhook Signing Secret

After creating the webhook:

1. Click on the webhook endpoint you just created
2. Find **"Signing secret"** and click **"Reveal"**
3. Copy the secret (starts with `whsec_...`)
4. Add to your backend `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
   ```

---

## Step 5: Test the Webhook

### Option A: Stripe Dashboard
1. Go to your webhook in Stripe
2. Click **"Send test webhook"**
3. Select `invoice.paid`
4. Check your backend logs for the event

### Option B: Stripe CLI (Local Testing)
```bash
stripe listen --forward-to localhost:8000/api/v1/payments/webhook
```

---

## Troubleshooting

### Webhook not receiving events?
- Check endpoint URL is correct and publicly accessible
- Verify `STRIPE_WEBHOOK_SECRET` in `.env` matches Stripe dashboard
- Check Stripe webhook logs for failed deliveries

### Signature verification failing?
- Ensure you're using the correct signing secret
- Check the secret hasn't been regenerated in Stripe

### Events not being processed?
- Check backend logs for errors
- Verify the event type is handled in `payments.py`

---

## Events Handled by Tru8

| Event | Handler | What it does |
|-------|---------|--------------|
| `checkout.session.completed` | `handle_successful_payment()` | Creates subscription, sets initial credits |
| `customer.subscription.updated` | `handle_subscription_updated()` | Updates status and period dates |
| `customer.subscription.deleted` | `handle_subscription_cancelled()` | Marks subscription as cancelled |
| `invoice.paid` | `handle_invoice_paid()` | Updates period dates, resets monthly credits |

---

## Local Development with ngrok

If testing webhooks locally:

1. Install ngrok: `npm install -g ngrok`
2. Start your backend: `uvicorn main:app --reload`
3. Start ngrok: `ngrok http 8000`
4. Copy the `https://...ngrok.io` URL
5. Add `/api/v1/payments/webhook` to it
6. Use that URL in Stripe webhook settings

Remember: ngrok URLs change each session unless you have a paid plan.
