# 🚨 CRITICAL GAPS & DECISIONS REQUIRED

**Last Updated:** 2025-10-13
**Status:** ✅ ALL 19 GAPS APPROVED - IMPLEMENTATION READY

---

## **GAP #1: Free Plan Credits Mismatch** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** "7 day trial / 5 free checks"
- **Backend provides:** 3 credits on signup (`User.credits = 3`)
- **Location:** Dashboard screenshot, Settings/Subscription screenshot

**DECISION APPROVED:**
✅ Change UI to "3 free checks" (backend is correct, matches User model default)

**Implementation:**
- All UI text must display "3 free checks" instead of "5 free checks"
- Update UsageCard to show correct total
- Update UpgradeBanner to reflect "3 free checks"
- Update Settings/Subscription tab Free plan card

**Impact:**
- Medium priority
- Affects: Dashboard, Settings pages
- File: `backend/app/models/user.py:9`

---

## **GAP #2: Professional Plan Pricing** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** "£7 per month"
- **Backend has:** `plan: 'starter' | 'pro'` but pricing not hardcoded

**DECISION APPROVED:**
✅ £7 is correct price for Professional plan

**Implementation:**
- Display "£7" in all UI references to Professional plan pricing
- Set environment variable: `NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=<stripe_price_id>`
- Ensure Stripe product configured for £7/month
- Update Settings/Subscription tab to show "£7 per month"

**Action Required:**
Set `NEXT_PUBLIC_STRIPE_PRICE_ID_PRO` environment variable before deployment

**Impact:**
- High priority (payment critical)
- Affects: Settings/Subscription tab, UpgradeBanner
- Related: Stripe product configuration

---

## **GAP #3: Subscription Plan Names** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** "Free" and "Professional"
- **Backend uses:** No "free" subscription (just credits), "starter", "pro"

**DECISION APPROVED:**
✅ Professional → "pro" plan (higher tier)
✅ Free → no subscription record, `user.credits` only

**Implementation Mapping:**
```typescript
// Frontend display → Backend plan value
"Free" → No subscription record (hasSubscription: false)
"Professional" → plan: "pro"

// Conditional logic
if (!subscription.hasSubscription) {
  displayPlan = "Free";
  creditsPerMonth = 3;
} else if (subscription.plan === "pro") {
  displayPlan = "Professional";
  creditsPerMonth = subscription.creditsPerMonth;
}
```

**Impact:**
- High priority
- Affects: All subscription-related UI, UpgradeBanner, Settings
- Files: `backend/app/models/user.py:28`

---

## **GAP #4: Usage Display - Monthly Calculation** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** "Checks used this month: 0 / 40"
- **Backend has:**
  - `user.credits` (remaining)
  - `total_credits_used` (all-time)
  - No monthly tracking

**DECISION APPROVED:**
✅ Option 1: Calculate from `checks` table filtered by `createdAt` >= start of month for MVP
✅ Refactor later if performance issues arise

**Implementation:**
```typescript
const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
const monthlyChecks = checks.filter(c => new Date(c.createdAt) >= startOfMonth);
const monthlyUsage = monthlyChecks.reduce((sum, c) => sum + c.creditsUsed, 0);
```

**Impact:**
- Medium priority
- Affects: Dashboard, Settings pages
- Performance: Acceptable for <1000 checks/month per user

---

## **GAP #5: "Most Popular" Badge** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** Cyan "Most Popular" badge on Professional plan
- **Current code:** Pricing cards already use this

**DECISION APPROVED:**
✅ Remove "Most Popular" badge. Await proper sales data before re-adding.

**Implementation:**
- Remove badge from Settings/Subscription tab pricing cards
- Remove badge from marketing pricing cards (if present)
- Can be re-added later once actual sales data justifies it

**Impact:**
- Low priority
- Affects: Settings/Subscription tab, marketing pricing cards
- File: `web/components/marketing/pricing-cards.tsx`

---

## **GAP #6: Social Sharing Icons** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** Facebook, Instagram, Twitter, YouTube, Message icons
- **Backend:** No sharing endpoint exists
- **Location:** New Check page, Dashboard right edge

**DECISION APPROVED:**
✅ Client-side Web Share API + fallback URLs

**Implementation:**
```typescript
const shareCheck = async (checkId: string) => {
  const url = `${window.location.origin}/check/${checkId}`;

  if (navigator.share) {
    await navigator.share({
      title: 'Tru8 Fact-Check Result',
      url: url,
    });
  } else {
    // Fallback URLs
    window.open(`https://twitter.com/intent/tweet?url=${url}`);
  }
};
```

**Impact:**
- Low priority
- Affects: New Check page
- No backend changes required

---

## **GAP #7: Notification Preferences** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** 4 email toggles:
  1. Email Notifications (master toggle)
  2. Check Completion
  3. Weekly Digest
  4. Marketing Emails
- **Backend has:** `push_notifications_enabled` (boolean only)

**DECISION APPROVED:**
✅ Start frontend-only (localStorage), backend enhancement in Phase 2

**Implementation (Frontend-only MVP):**
```typescript
interface NotificationPreferences {
  emailEnabled: boolean;
  checkCompletion: boolean;
  weeklyDigest: boolean;
  marketing: boolean;
}

// Store in localStorage
localStorage.setItem('notificationPrefs', JSON.stringify(prefs));
```

**Future Backend Model:**
```python
class User:
    # Add fields
    email_notifications_enabled: bool = True
    check_completion_emails: bool = True
    weekly_digest_enabled: bool = False
    marketing_emails_enabled: bool = False
```

**Impact:**
- Low priority (Phase 2)
- Affects: Settings/Notifications tab
- Backend changes: Optional

---

## **GAP #8: Verdict Badge Icons** ✅ RESOLVED

**Issue:**
- **Screenshot shows:**
  - SUPPORTED: Green circled check (✓)
  - CONTRADICTED: Red circled X (✗)
  - UNCERTAIN: Amber circled warning (!)
- **Backend:** No icon mapping, just text verdicts

**DECISION APPROVED:**
✅ Use lucide-react icons (already installed)

**Implementation:**
```typescript
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

const verdictConfig = {
  supported: {
    icon: CheckCircle2,
    color: '#059669',
    bgColor: '#059669/10',
  },
  contradicted: {
    icon: XCircle,
    color: '#DC2626',
    bgColor: '#DC2626/10',
  },
  uncertain: {
    icon: AlertCircle,
    color: '#D97706',
    bgColor: '#D97706/10',
  },
};
```

**Impact:**
- Medium priority (visual consistency)
- Affects: All pages displaying checks
- Component: `VerdictPill.tsx`

---

## **GAP #9: Graphics/Illustrations** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** Justice scales, compass, prism, tree graphics
- **Public folder has:** Only `logo.proper.png` and `favicon.proper.png`

**DECISION APPROVED:**
✅ Required images have been added to `web/public/imagery/`

**Available Graphics:**
- Justice scales graphic
- Compass graphic
- Prism graphic
- Tree graphic

**Implementation:**
```typescript
function JusticeScalesPlaceholder() {
  return (
    <div className="w-64 h-64 bg-gradient-to-br from-slate-700 to-slate-900 rounded-2xl flex items-center justify-center">
      <Scale size={120} className="text-slate-400" />
    </div>
  );
}

function CompassPlaceholder() {
  return (
    <div className="w-64 h-64 bg-gradient-to-br from-slate-600 to-slate-800 rounded-full flex items-center justify-center">
      <Compass size={120} className="text-slate-300" />
    </div>
  );
}

// Similar for Prism (Triangle), Tree (Leaf)
```

**Impact:**
- Low priority (cosmetic)
- Affects: All page headers
- Future: Replace with actual graphics

---

## **GAP #10: Check History Pagination** ✅ RESOLVED

**Issue:**
- **Screenshot shows:** Scrollable list, no pagination UI visible
- **Backend supports:** `skip` and `limit` query params

**DECISION APPROVED:**
✅ "Load More" button, 20 per page (simplest for MVP)

**Implementation:**
```typescript
const [checks, setChecks] = useState([]);
const [skip, setSkip] = useState(0);
const [hasMore, setHasMore] = useState(true);

const loadMore = async () => {
  const newChecks = await apiClient.getChecks(token, skip + 20, 20);
  setChecks([...checks, ...newChecks.checks]);
  setSkip(skip + 20);
  setHasMore(newChecks.checks.length === 20);
};
```

**Impact:**
- Medium priority
- Affects: History page
- Alternative: Infinite scroll with IntersectionObserver (Phase 2)

---

---

## **GAP #11: History Search Implementation** ✅ RESOLVED

**Issue:**
- History page requires search functionality (claim text, URL)
- Options: Client-side (filter in browser) vs Backend endpoint

**Source:** PLAN_03_HISTORY_PAGE.md

**DECISION APPROVED:**
✅ Option A: Client-side filtering for MVP

**Implementation:**
```typescript
const filteredChecks = checks.filter(check => {
  return check.claims?.some(claim =>
    claim.text.toLowerCase().includes(searchQuery.toLowerCase())
  );
});
```

**Rationale:**
- Simpler implementation, no backend changes required
- Instant results for better UX
- Acceptable performance for <100 checks per user (MVP scale)
- Can refactor to backend search if users exceed 100 checks

**Impact:**
- Low priority (MVP acceptable with client-side)
- Affects: History page
- Backend changes: None for MVP

---

## **GAP #12: Input Type Support (IMAGE/VIDEO)** ✅ RESOLVED

**Issue:**
- **Backend supports:** 4 input types (url, text, image, video)
- **Screenshot shows:** Only 2 tabs (URL, TEXT)
- **Question:** Should IMAGE and VIDEO tabs be included in MVP?

**Source:** PLAN_04_NEW_CHECK_PAGE.md

**DECISION APPROVED:**
✅ Option A: URL + TEXT only for MVP

**Implementation:**
- New Check page will have 2 tabs: URL and TEXT
- IMAGE and VIDEO tabs deferred to Phase 2
- Backend already supports all 4 types (no changes needed)

**Rationale:**
- Simpler UX for MVP launch
- Faster development cycle
- Focus on core fact-checking functionality
- Can add IMAGE/VIDEO after MVP user validation

**Phase 2 Enhancement:**
- Add IMAGE tab with file upload + preview
- Add VIDEO tab with URL input or file upload
- Implement file validation (size, format)

**Impact:**
- Medium priority
- Affects: New Check page
- Backend: No changes (already supports all types)

---

## **GAP #13: Text Input Length Limits** ✅ RESOLVED

**Issue:**
- TEXT tab needs character limits
- Backend doesn't specify max length in API docs
- Need to define min/max for validation

**Source:** PLAN_04_NEW_CHECK_PAGE.md

**DECISION APPROVED:**
✅ Min: 10 characters, Max: 5,000 characters

**Implementation:**
```typescript
const MAX_LENGTH = 5000;
const MIN_LENGTH = 10;

// Validation
if (textInput.length < MIN_LENGTH) {
  setError(`Minimum ${MIN_LENGTH} characters required`);
}
if (textInput.length > MAX_LENGTH) {
  setError(`Maximum ${MAX_LENGTH} characters exceeded`);
}
```

**UI Display:**
- Character counter: "2,450 / 5,000 characters"
- Real-time validation as user types
- Error message if limits exceeded

**Backend Alignment:**
- Backend should validate same limits (10-5000 chars)
- Return 400 error if limits exceeded

**Impact:**
- Low priority (can adjust later)
- Affects: New Check page TEXT tab
- Backend: Should add validation for same limits

---

## **GAP #14: Public Check Sharing** ✅ RESOLVED

**Issue:**
- Share URLs (`/check/[id]`) require authentication
- Social share recipients can't view shared checks without signing in
- Screenshot shows social sharing, implying public access

**Source:** PLAN_05_CHECK_DETAIL_PAGE.md

**DECISION APPROVED:**
✅ Option C: Authenticated-only check sharing for MVP

**Implementation:**
- All check detail pages require authentication
- Share URLs redirect to signin if user not authenticated
- Social share buttons still functional (share URL, but requires signin to view)
- Route: `/dashboard/check/[id]` (protected route)

**Rationale:**
- Faster MVP launch with simpler privacy model
- No need for public/private toggle complexity
- Reduces abuse potential (spam, misuse)
- Can add public sharing in Phase 2 after user validation

**Phase 2 Enhancement:**
- Add public/private toggle to check settings
- Create public route `/check/[id]` for public checks
- Default to private, user opts in to public sharing
- Public checks shown in search/discovery feed

**Impact:**
- Medium priority (affects viral growth potential)
- Affects: Check Detail page, social sharing
- Backend: No changes for MVP

---

## **GAP #15: Evidence Snippet Truncation** ✅ RESOLVED

**Issue:**
- Evidence snippets vary in length
- Long snippets could break card layout
- Need flexible display that handles variety of lengths from AI

**Source:** PLAN_05_CHECK_DETAIL_PAGE.md

**DECISION APPROVED:**
✅ Flexible text field with generous allocation - NO hard truncation

**Implementation:**
```typescript
// Use line-clamp-4 (4 lines) instead of 2 for more generous display
// Remove character limits - let AI return full snippets
<p className="text-xs text-slate-400 mb-2 line-clamp-4">
  {item.snippet}
</p>
```

**Rationale:**
- Evidence snippets need to be wordy to provide proper context
- AI-generated snippets vary significantly in length
- Must be flexible and versatile to handle variety
- Better UX to show more context than truncate too early

**Alternative Enhancement:**
- Use expandable "Read more" link if snippet exceeds 4 lines
- Accordion pattern: collapsed by default, expand on click
- Preserves layout while allowing full snippet access

**Impact:**
- Low priority (cosmetic)
- Affects: Check Detail page evidence display
- Must accommodate AI-generated content variability

---

## **GAP #16: SSE Token Security** ✅ RESOLVED

**Issue:**
- SSE (Server-Sent Events) doesn't support custom headers
- Must pass JWT token as query parameter
- Security concern: Query params logged by servers/proxies

**Source:** PLAN_05_CHECK_DETAIL_PAGE.md

**DECISION APPROVED:**
✅ Option A: Short-lived SSE tokens (5 min expiry)

**Implementation:**

**Frontend:**
```typescript
// Step 1: Request short-lived SSE token
const sseToken = await apiClient.createSSEToken(checkId, token);

// Step 2: Connect with short-lived token
const url = `${API_URL}/checks/${checkId}/progress?token=${sseToken.token}`;
const eventSource = new EventSource(url);
```

**Backend (New Endpoint Required):**
```python
@router.post("/checks/{check_id}/sse-token")
async def create_sse_token(
    check_id: str,
    current_user: User = Depends(get_current_user)
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

**Rationale:**
- Mitigates security risk of full JWT in query params
- Tokens expire after 5 minutes (short window for exposure)
- Tokens scoped to single check and SSE endpoint only
- Minimal additional complexity vs WebSocket

**Impact:**
- High priority (security)
- Affects: Check Detail page real-time progress
- Backend: New endpoint `/checks/{id}/sse-token` required

---

## **GAP #17: Billing History Data Source** ✅ RESOLVED

**Issue:**
- Settings/Subscription tab shows billing history table
- Need backend endpoint to fetch Stripe invoice data
- Currently placeholder data in plan

**Source:** PLAN_06_SETTINGS_PAGE.md

**DECISION APPROVED:**
✅ Option A: Display billing history on Settings page

**Implementation:**

**Backend (New Endpoint Required):**
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

**Frontend:**
```typescript
// Fetch invoices for Pro users
const invoices = await apiClient.getInvoices(token);

// Display in table
<table>
  <tr>
    <td>{format(new Date(invoice.date * 1000), 'MMM d, yyyy')}</td>
    <td>£{invoice.amount.toFixed(2)}</td>
    <td>{invoice.status}</td>
    <td><a href={invoice.pdf_url} download>Download</a></td>
  </tr>
</table>

// "View All" link to Stripe portal
```

**Rationale:**
- Better UX to show recent invoices on Settings page
- Reduces friction for users checking billing history
- "View All" link provides escape hatch to Stripe portal

**Impact:**
- Low priority (Pro users only)
- Affects: Settings/Subscription tab
- Backend: New endpoint `/api/v1/payments/invoices` required

---

## **GAP #18: Account Deletion Backend Cleanup** ✅ RESOLVED

**Issue:**
- Clerk handles authentication deletion
- Backend database still has User, Checks, Claims, Evidence records
- Need cascade delete for GDPR compliance

**Source:** PLAN_06_SETTINGS_PAGE.md

**DECISION APPROVED:**
✅ Option A: Immediate deletion

**Implementation:**

**Backend (New Endpoint Required):**
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

**Frontend Flow:**
```typescript
const handleDeleteAccount = async () => {
  // Double confirmation
  if (!confirm('Are you absolutely sure? This action cannot be undone.')) {
    return;
  }

  try {
    // 1. Delete backend data
    await apiClient.deleteUser(userId, token);

    // 2. Delete Clerk authentication
    await clerkUser?.delete();

    // 3. Sign out and redirect
    await signOut();
    window.location.href = '/';
  } catch (error) {
    console.error('Failed to delete account:', error);
    alert('Failed to delete account. Please contact support.');
  }
};
```

**Rationale:**
- Simpler implementation for MVP
- Immediate GDPR compliance (right to erasure)
- Clear user expectation (no ambiguity about when data is deleted)
- Can add grace period in Phase 2 if user feedback requests it

**Database Cascade:**
- User deletion → cascades to Checks
- Check deletion → cascades to Claims
- Claim deletion → cascades to Evidence
- Ensure foreign key constraints configured for CASCADE DELETE

**Impact:**
- Medium priority (GDPR compliance)
- Affects: Settings/Account tab
- Backend: New endpoint `/api/v1/users/me` (DELETE) required

---

## **GAP #19: Downgrade Flow (Pro → Free)** ✅ RESOLVED

**Issue:**
- Screenshot doesn't show downgrade UI
- Professional → Free transition needs handling
- Questions: When does downgrade take effect? What happens to excess usage?

**Source:** PLAN_06_SETTINGS_PAGE.md

**DECISION APPROVED:**
✅ Option B: End of period downgrade

**Implementation:**

**Frontend:**
```typescript
const handleDowngrade = async () => {
  if (!confirm('Downgrade to Free plan at end of billing period?')) {
    return;
  }

  try {
    const token = await getToken();
    await apiClient.cancelSubscription(token);

    // Refresh subscription data
    const updated = await apiClient.getSubscriptionStatus(token);
    setSubscriptionData(updated);

    alert(`Your plan will downgrade to Free on ${format(new Date(updated.currentPeriodEnd), 'MMMM d, yyyy')}`);
  } catch (error) {
    console.error('Failed to cancel subscription:', error);
    alert('Failed to cancel subscription. Please try again.');
  }
};
```

**Backend (Stripe Integration):**
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

**UI Display:**
```typescript
// Show cancellation notice in Current Plan card
{subscriptionData.cancelAtPeriodEnd && (
  <div className="mt-4 p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
    <p className="text-sm text-amber-300">
      Your plan will downgrade to Free on{' '}
      {format(new Date(subscriptionData.currentPeriodEnd), 'MMMM d, yyyy')}
    </p>
    <button
      onClick={handleReactivate}
      className="mt-2 text-sm text-amber-400 hover:text-amber-300 underline"
    >
      Reactivate subscription
    </button>
  </div>
)}
```

**Rationale:**
- Fair to user (keeps Pro access until billing period ends)
- Industry standard practice (Netflix, Spotify, etc.)
- User can reactivate before period ends
- Automatic downgrade on period end via Stripe webhook

**Webhook Handling:**
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
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

**Impact:**
- Low priority (Pro users only)
- Affects: Settings/Subscription tab
- Backend: Stripe subscription cancellation + webhook handling

---

## **SUMMARY TABLE**

| Gap # | Title | Priority | Decision Status | Blocking? | Source |
|-------|-------|----------|-----------------|-----------|--------|
| 1 | Credits Mismatch | Medium | ✅ APPROVED | No | Initial |
| 2 | Pricing | High | ✅ APPROVED | No | Initial |
| 3 | Plan Names | High | ✅ APPROVED | No | Initial |
| 4 | Monthly Usage | Medium | ✅ APPROVED | No | Initial |
| 5 | Most Popular Badge | Low | ✅ APPROVED | No | Initial |
| 6 | Social Sharing | Low | ✅ APPROVED | No | Initial |
| 7 | Notifications | Low | ✅ APPROVED | No | Initial |
| 8 | Verdict Icons | Medium | ✅ APPROVED | No | Initial |
| 9 | Graphics | Low | ✅ APPROVED | No | Initial |
| 10 | Pagination | Medium | ✅ APPROVED | No | Initial |
| 11 | History Search | Low | ✅ APPROVED | No | PLAN_03 |
| 12 | Input Types (IMAGE/VIDEO) | Medium | ✅ APPROVED | No | PLAN_04 |
| 13 | Text Length Limits | Low | ✅ APPROVED | No | PLAN_04 |
| 14 | Public Check Sharing | Medium | ✅ APPROVED | No | PLAN_05 |
| 15 | Evidence Snippet Length | Low | ✅ APPROVED | No | PLAN_05 |
| 16 | SSE Token Security | High | ✅ APPROVED | No | PLAN_05 |
| 17 | Billing History | Low | ✅ APPROVED | No | PLAN_06 |
| 18 | Account Deletion | Medium | ✅ APPROVED | No | PLAN_06 |
| 19 | Downgrade Flow | Low | ✅ APPROVED | No | PLAN_06 |

**Status:** ✅ ALL 19 GAPS APPROVED - Implementation Ready
