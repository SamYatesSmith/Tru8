# MVP WEEK 1: TESTING & POLISH

**Project:** Tru8 MVP Launch Preparation
**Week:** 1 of 2
**Duration:** October 17-21, 2025 (5 days)
**Status:** Ready to Start
**Goal:** Comprehensive testing, bug fixes, and polish of all implemented features

---

## 📋 WEEK 1 OVERVIEW

This week focuses on **validating everything that's been built**. With 95% of features already implemented, the priority is ensuring quality, fixing edge cases, and polishing the user experience.

### Key Objectives:
1. ✅ Test complete user journeys end-to-end
2. ✅ Verify all API integrations work correctly
3. ✅ Fix any bugs or edge cases discovered
4. ✅ Polish UI/UX based on testing feedback
5. ✅ Ensure mobile responsiveness
6. ✅ Performance optimization

---

## 🗓️ DAY-BY-DAY BREAKDOWN

### **DAY 1: Authentication & User Management Testing**

#### Morning Session (3-4 hours)

**1.1 Sign-Up Flow Testing**
- [ ] Test sign-up from marketing page "Start Verifying Free" button
- [ ] Verify Clerk modal opens with Sign Up tab
- [ ] Test email/password sign-up
- [ ] Test Google OAuth sign-up
- [ ] Verify redirect to `/dashboard` after sign-up
- [ ] Check backend creates user with 3 free credits
- [ ] Verify user data in database: `SELECT * FROM users WHERE id = '[clerk_user_id]'`

**1.2 Sign-In Flow Testing**
- [ ] Test sign-in from marketing page "Sign In" button
- [ ] Test sign-in from `/dashboard` redirect when not authenticated
- [ ] Verify Clerk modal opens with Sign In tab
- [ ] Test email/password sign-in
- [ ] Test Google OAuth sign-in
- [ ] Verify redirect to `/dashboard` after sign-in

**1.3 Middleware & Route Protection**
- [ ] Access `/dashboard` without auth → should redirect to `/?signin=true`
- [ ] Access `/dashboard/history` without auth → should redirect
- [ ] Access `/dashboard/settings` without auth → should redirect
- [ ] Access `/dashboard/new-check` without auth → should redirect
- [ ] Access `/dashboard/check/[id]` without auth → should redirect
- [ ] Verify `web/middleware.ts:10` has `if (isProtectedRoute(req)) auth().protect();` (no mock data)

#### Afternoon Session (3-4 hours)

**1.4 User Profile & Data Fetching**
- [ ] Dashboard home loads with correct user name
- [ ] Dashboard shows correct credit count (3 for new free users)
- [ ] User menu dropdown shows correct email
- [ ] User avatar displays (initials or Clerk profile image)
- [ ] Test API: `GET /api/v1/users/profile` returns correct data
- [ ] Verify no console errors on dashboard load

**1.5 Account Deletion Testing** (GDPR Compliance)
- [ ] Navigate to Settings → Account tab
- [ ] Scroll to "Danger Zone"
- [ ] Click "Delete Account" button
- [ ] Verify confirmation modal appears
- [ ] Type confirmation text and submit
- [ ] Verify account deletion succeeds
- [ ] Check database: User, Checks, Claims, Evidence all deleted
- [ ] Test API: `DELETE /api/v1/users/me`
- [ ] Verify Stripe subscription cancelled (if user had Pro plan)

**Testing Checklist Template:**
```markdown
## Day 1 Results

### Sign-Up Flow
- ✅/❌ Sign-up button works
- ✅/❌ Clerk modal opens
- ✅/❌ User created with 3 credits
- ✅/❌ Redirect to dashboard works
- Issues found: [list any issues]

### Account Deletion
- ✅/❌ Delete button accessible
- ✅/❌ Confirmation required
- ✅/❌ Database cleaned up
- ✅/❌ Stripe subscription cancelled
- Issues found: [list any issues]
```

---

### **DAY 2: Check Creation & Pipeline Testing**

#### Morning Session (3-4 hours)

**2.1 URL Check Creation**
- [ ] Navigate to `/dashboard/new-check`
- [ ] Verify "URL" tab is active by default
- [ ] Test valid URL: `https://www.bbc.com/news/example`
- [ ] Verify URL validation works (rejects `invalid-url`, `example.com` without protocol)
- [ ] Submit URL check
- [ ] Verify redirect to `/dashboard/check/[id]`
- [ ] Verify credit deduction (user credits: 3 → 2)
- [ ] Check database: `SELECT * FROM checks ORDER BY created_at DESC LIMIT 1`
- [ ] Verify check status: `pending` → `processing` → `completed`

**2.2 TEXT Check Creation**
- [ ] Switch to "TEXT" tab
- [ ] Test validation:
  - [ ] Less than 10 characters → error message
  - [ ] More than 5000 characters → error message
  - [ ] Valid text (10-5000 chars) → success
- [ ] Submit text check: "The unemployment rate decreased to 3.7% in October 2024."
- [ ] Verify redirect to check detail page
- [ ] Verify credit deduction (user credits: 2 → 1)

**2.3 Character Counter Testing**
- [ ] Type in TEXT textarea
- [ ] Verify character counter updates: "X / 5000"
- [ ] Verify counter color changes when near limit
- [ ] Test paste operation with long text
- [ ] Verify validation on submit

#### Afternoon Session (3-4 hours)

**2.4 Real-Time Progress (SSE) Testing**
- [ ] Create new URL check
- [ ] Watch progress bar on check detail page
- [ ] Verify SSE events received: `connected`, `progress`, `completed`
- [ ] Check browser DevTools → Network → EventSource connection
- [ ] Verify progress stages appear:
  - [ ] "Ingesting content..." (10%)
  - [ ] "Extracting claims..." (25%)
  - [ ] "Retrieving evidence..." (40%)
  - [ ] "Verifying claims..." (60%)
  - [ ] "Finalizing judgment..." (80%)
  - [ ] "Check completed" (100%)
- [ ] Test API: `GET /api/v1/checks/{id}/progress`
- [ ] Verify `get_current_user_sse()` auth works (query param token)

**2.5 Pipeline Performance Testing**
- [ ] Create 3 different checks (URL, TEXT, URL)
- [ ] Measure time to completion for each
- [ ] Verify <10s completion time (Quick mode target)
- [ ] Check backend logs for stage timings
- [ ] Verify no pipeline failures in logs
- [ ] Test Celery worker processing: `celery -A app.workers.celery_app inspect active`

**2.6 Error Handling**
- [ ] Test invalid URL that returns 404
- [ ] Test URL behind paywall
- [ ] Test URL that times out
- [ ] Verify check status changes to `failed`
- [ ] Verify error message displayed on check detail page
- [ ] Verify credits NOT refunded (expected behavior)

---

### **DAY 3: Dashboard & History Testing**

#### Morning Session (3-4 hours)

**3.1 Dashboard Home Page**
- [ ] Navigate to `/dashboard`
- [ ] Verify hero section displays with JusticeScalesGraphic
- [ ] Verify welcome message: "Welcome back, [User Name]"
- [ ] Check upgrade banner (should appear for free users)
- [ ] Verify usage card displays correctly:
  - [ ] "Checks used this month: X / 3" (or X / 40 for Pro)
  - [ ] Progress bar fills correctly
  - [ ] Color changes based on usage (green → amber → red)
- [ ] Verify "Quick Action" card displays
- [ ] Click "New Check" button → redirects to `/dashboard/new-check`

**3.2 Recent Checks List**
- [ ] Verify "Recent Checks" section displays
- [ ] Check shows last 5 checks (or fewer if user has less)
- [ ] Verify each check card displays:
  - [ ] Input type badge (URL, TEXT)
  - [ ] Created date (relative: "2 hours ago")
  - [ ] Status badge (Completed, Processing, Failed)
  - [ ] First claim text preview
  - [ ] Verdict pill (Supported/Contradicted/Uncertain)
  - [ ] Confidence bar
- [ ] Click check card → redirects to `/dashboard/check/[id]`

**3.3 Upgrade Banner Testing**
- [ ] Verify banner displays for free users
- [ ] Check content: "Unlock Premium Features", "Current Plan: Free"
- [ ] List features: "Unlimited fact-checks", "Advanced source analysis", etc.
- [ ] Click "Upgrade Now" → redirects to Settings → Subscription tab
- [ ] Verify banner does NOT display for Pro users

#### Afternoon Session (3-4 hours)

**3.4 History Page Testing**
- [ ] Navigate to `/dashboard/history`
- [ ] Verify page header with CompassGraphic
- [ ] Check "New Check" CTA button in header
- [ ] Verify all checks display (20 per page)

**3.5 Search Functionality (Client-Side)**
- [ ] Type in search box: "unemployment"
- [ ] Verify only checks with claims containing "unemployment" display
- [ ] Test search: "rate" → verify matching checks appear
- [ ] Clear search → verify all checks return
- [ ] Test case-insensitive search
- [ ] Test with special characters

**3.6 Filter Functionality**
- [ ] Verdict filter:
  - [ ] Click "Supported" → only supported checks display
  - [ ] Click "Contradicted" → only contradicted checks display
  - [ ] Click "Uncertain" → only uncertain checks display
  - [ ] Click "All" → all checks display
- [ ] Status filter:
  - [ ] Click "Completed" → only completed checks display
  - [ ] Click "Processing" → only processing checks display
  - [ ] Click "Failed" → only failed checks display
  - [ ] Click "All" → all checks display
- [ ] Test combined filters (e.g., Supported + Completed)

**3.7 Pagination Testing**
- [ ] Create 25+ checks (if needed for testing)
- [ ] Verify first 20 display
- [ ] Click "Load More" button
- [ ] Verify next 20 checks append (not replace)
- [ ] Scroll down, verify infinite load works
- [ ] Test API: `GET /api/v1/checks?skip=20&limit=20`

**3.8 Empty States**
- [ ] Create new user account with 0 checks
- [ ] Navigate to `/dashboard/history`
- [ ] Verify empty state displays: "No checks yet"
- [ ] Verify CTA button: "Create Your First Check"

---

### **DAY 4: Check Detail & Stripe Integration**

#### Morning Session (3-4 hours)

**4.1 Check Detail Page - Metadata**
- [ ] Navigate to completed check: `/dashboard/check/[id]`
- [ ] Verify page header with CompassGraphic
- [ ] Verify "Check Metadata Card" displays:
  - [ ] Input type (URL or TEXT)
  - [ ] URL (if URL check) or text preview (if TEXT check)
  - [ ] Status badge with color coding
  - [ ] Credits used: 1
  - [ ] Created date
  - [ ] Completed date (if completed)
  - [ ] Processing time (if completed)

**4.2 Claims Section**
- [ ] Verify all extracted claims display
- [ ] Each claim card shows:
  - [ ] Claim text
  - [ ] Verdict pill (Supported/Contradicted/Uncertain) with color
  - [ ] Confidence bar (0-100%) with animation
  - [ ] Rationale text (2-3 sentences)
  - [ ] Evidence accordion (collapsed by default)
- [ ] Click evidence accordion → expands
- [ ] Each evidence item shows:
  - [ ] Source name (e.g., "Bureau of Labor Statistics")
  - [ ] Title (clickable link to source)
  - [ ] Snippet text
  - [ ] Published date (formatted: "Jan 15, 2024")
  - [ ] Relevance score badge
  - [ ] Credibility score badge

**4.3 Share Section**
- [ ] Scroll to "Share" section
- [ ] Test Web Share API (on mobile or supported browser):
  - [ ] Click "Share" button
  - [ ] Verify native share sheet appears
  - [ ] Share to Twitter (test link format)
- [ ] Test fallback (on desktop):
  - [ ] Click "Copy Link" → verify "Link copied!" toast
  - [ ] Paste link → verify format: `https://tru8.com/dashboard/check/[id]`
  - [ ] Click Twitter icon → opens Twitter intent URL
  - [ ] Click Facebook icon → opens Facebook sharer

#### Afternoon Session (3-4 hours)

**4.4 Settings Page - Account Tab**
- [ ] Navigate to `/dashboard/settings`
- [ ] Verify "Account" tab active by default
- [ ] Check profile info section:
  - [ ] Email displays (from Clerk)
  - [ ] Name displays (from Clerk)
  - [ ] User ID displays
  - [ ] Joined date displays
- [ ] Security section:
  - [ ] "Change Password" button → opens Clerk modal
  - [ ] "Enable 2FA" button → opens Clerk modal
  - [ ] Test Clerk modal interactions

**4.5 Stripe Checkout Testing (CRITICAL)**
- [ ] Navigate to Settings → Subscription tab
- [ ] Verify "Current Plan: Free" displays
- [ ] Verify usage summary: "X / 3 checks this month"
- [ ] Scroll to "Professional" plan card
- [ ] Verify pricing: "£7 / month"
- [ ] Verify features list: "40 checks per month", etc.
- [ ] Click "Upgrade to Professional" button
- [ ] Verify redirect to Stripe Checkout:
  - [ ] URL contains `checkout.stripe.com`
  - [ ] Line item: "Tru8 Professional - £7.00 / month"
  - [ ] Email pre-filled
  - [ ] Payment form displays
- [ ] Test with Stripe test card: `4242 4242 4242 4242`
- [ ] Complete checkout
- [ ] Verify redirect to `/dashboard?upgraded=true`
- [ ] Verify success message displays
- [ ] Check database: `SELECT * FROM subscriptions WHERE user_id = '[user_id]'`
  - [ ] Subscription created with status: "active"
  - [ ] Plan: "pro"
  - [ ] credits_per_month: 40
  - [ ] stripe_subscription_id populated
- [ ] Verify user credits updated: 40

**4.6 Stripe Webhook Testing**
- [ ] Use Stripe CLI to forward webhooks: `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`
- [ ] Complete another checkout
- [ ] Verify webhook event received: `checkout.session.completed`
- [ ] Check backend logs for webhook processing
- [ ] Test `customer.subscription.updated` event:
  - [ ] Use Stripe Dashboard to update subscription
  - [ ] Verify database subscription record updates
- [ ] Test `customer.subscription.deleted` event:
  - [ ] Cancel subscription in Stripe Dashboard
  - [ ] Verify user downgraded to Free plan
  - [ ] Verify credits reset to 3

**4.7 Subscription Management**
- [ ] As Pro user, navigate to Settings → Subscription tab
- [ ] Verify "Current Plan: Professional" displays
- [ ] Verify usage: "X / 40 checks this month"
- [ ] Verify "Next billing date" displays
- [ ] Click "Manage Billing" button
- [ ] Verify redirect to Stripe Customer Portal
- [ ] Test updating payment method
- [ ] Test viewing invoices
- [ ] Return to Settings

**4.8 Subscription Cancellation**
- [ ] Settings → Subscription tab (as Pro user)
- [ ] Click "Cancel Subscription" button
- [ ] Verify confirmation modal: "Cancel at end of billing period?"
- [ ] Confirm cancellation
- [ ] Verify success message
- [ ] Verify banner: "Your subscription will end on [date]"
- [ ] Verify "Reactivate Subscription" button appears
- [ ] Test API: `POST /api/v1/payments/cancel-subscription`
- [ ] Check Stripe Dashboard: subscription has `cancel_at_period_end: true`

**4.9 Subscription Reactivation**
- [ ] With cancelled subscription, click "Reactivate Subscription"
- [ ] Verify confirmation modal
- [ ] Confirm reactivation
- [ ] Verify success message
- [ ] Verify cancellation banner disappears
- [ ] Test API: `POST /api/v1/payments/reactivate-subscription`
- [ ] Check Stripe Dashboard: subscription has `cancel_at_period_end: false`

---

### **DAY 5: Mobile, Performance & Polish**

#### Morning Session (3-4 hours)

**5.1 Mobile Responsiveness - Marketing Page**
- [ ] Open on mobile (or resize browser to 375px width)
- [ ] Test animated background (should work with reduced motion)
- [ ] Test desktop navigation (should hide on mobile)
- [ ] Test mobile bottom nav (should show on mobile):
  - [ ] Features, How It Works, Pricing, Sign In icons
  - [ ] Tap each icon → smooth scrolls to section
  - [ ] Active state highlighting works
- [ ] Hero section:
  - [ ] Text stacks vertically
  - [ ] CTAs stack vertically
  - [ ] Trust indicators stack
- [ ] Feature carousel:
  - [ ] Shows 1 card at a time
  - [ ] Swipeable on touch
  - [ ] Dots navigation visible
- [ ] Pricing cards:
  - [ ] Stack vertically on mobile
  - [ ] All content readable
- [ ] Footer:
  - [ ] Links stack vertically
  - [ ] All links clickable

**5.2 Mobile Responsiveness - Dashboard**
- [ ] Dashboard home:
  - [ ] Hero section stacks
  - [ ] Usage card full width
  - [ ] Quick action card full width
  - [ ] Recent checks list scrolls
- [ ] History page:
  - [ ] Search input full width
  - [ ] Filter chips wrap
  - [ ] Check cards full width
- [ ] New Check page:
  - [ ] Tabs display correctly
  - [ ] Form inputs full width
  - [ ] Character counter visible
  - [ ] Submit button full width
- [ ] Check Detail page:
  - [ ] Metadata card readable
  - [ ] Claims cards full width
  - [ ] Evidence accordion scrolls
  - [ ] Share buttons stack
- [ ] Settings page:
  - [ ] Tabs scroll horizontally if needed
  - [ ] All forms full width
  - [ ] Stripe buttons full width

**5.3 Mobile Device Testing (Real Devices)**
- [ ] iOS Safari (iPhone 12+):
  - [ ] Sign-up flow works
  - [ ] Dashboard navigation works
  - [ ] Check creation works
  - [ ] SSE progress works
  - [ ] Stripe checkout works
- [ ] Android Chrome (Samsung/Pixel):
  - [ ] Sign-up flow works
  - [ ] Dashboard navigation works
  - [ ] Check creation works
  - [ ] SSE progress works
  - [ ] Stripe checkout works

#### Afternoon Session (3-4 hours)

**5.4 Performance Testing - Lighthouse Audit**
- [ ] Run Lighthouse on marketing page (`/`)
  - [ ] Performance > 90
  - [ ] Accessibility > 95
  - [ ] Best Practices > 90
  - [ ] SEO > 90
- [ ] Run Lighthouse on dashboard home (`/dashboard`)
  - [ ] Performance > 85 (server-rendered)
  - [ ] Accessibility > 95
- [ ] Run Lighthouse on check detail page
  - [ ] Performance > 85
  - [ ] Accessibility > 95

**5.5 Performance Optimization (if needed)**
- [ ] Review Next.js build output: `npm run build`
- [ ] Check bundle sizes (aim for <200KB first load JS)
- [ ] Optimize images (use WebP where possible)
- [ ] Review API response times (aim for <200ms p95)
- [ ] Check database query performance
- [ ] Review Celery task execution times

**5.6 Accessibility Testing**
- [ ] Keyboard navigation:
  - [ ] Tab through all interactive elements
  - [ ] Focus states visible
  - [ ] Enter/Space activates buttons
  - [ ] Escape closes modals
- [ ] Screen reader testing (NVDA/JAWS/VoiceOver):
  - [ ] All sections announced
  - [ ] Buttons have labels
  - [ ] Form inputs have labels
  - [ ] Error messages announced
- [ ] Color contrast:
  - [ ] Run axe DevTools scan
  - [ ] Verify no contrast issues
  - [ ] Check verdict pill colors (Supported/Contradicted/Uncertain)

**5.7 Cross-Browser Testing**
- [ ] Chrome (latest):
  - [ ] Marketing page renders
  - [ ] Dashboard works
  - [ ] Stripe checkout works
- [ ] Firefox (latest):
  - [ ] Marketing page renders
  - [ ] Dashboard works
  - [ ] Stripe checkout works
- [ ] Safari (latest):
  - [ ] Marketing page renders
  - [ ] Dashboard works
  - [ ] Stripe checkout works
- [ ] Edge (latest):
  - [ ] Marketing page renders
  - [ ] Dashboard works
  - [ ] Stripe checkout works

**5.8 Error Handling & Edge Cases**
- [ ] Test with no internet connection
- [ ] Test with slow 3G connection
- [ ] Test with network errors (disable backend)
- [ ] Test with invalid API responses
- [ ] Test with expired auth tokens
- [ ] Test with CORS errors
- [ ] Verify error messages user-friendly
- [ ] Verify no sensitive data in error messages

**5.9 Final Polish**
- [ ] Review all copy for typos
- [ ] Check all links work
- [ ] Verify loading states display correctly
- [ ] Test all toast notifications
- [ ] Verify all modals work correctly
- [ ] Check favicon displays
- [ ] Test meta tags (Open Graph, Twitter Cards)

---

## 🐛 BUG TRACKING TEMPLATE

Create a `WEEK1_BUGS.md` file to track issues found during testing:

```markdown
# Week 1 Testing - Bugs Found

## Critical (P0) - Must Fix Before Launch
- [ ] **Bug #1**: [Description]
  - **Steps to Reproduce**:
  - **Expected**:
  - **Actual**:
  - **File**:
  - **Fix**:

## High Priority (P1) - Should Fix Before Launch
- [ ] **Bug #2**: [Description]

## Medium Priority (P2) - Can Fix Post-Launch
- [ ] **Bug #3**: [Description]

## Low Priority (P3) - Nice to Have
- [ ] **Bug #4**: [Description]
```

---

## ✅ WEEK 1 SUCCESS CRITERIA

By end of Week 1, the following must be verified:

### Authentication
- [x] Sign-up and sign-in work flawlessly
- [x] Route protection works correctly
- [x] User data loads correctly
- [x] Account deletion works

### Check Creation
- [x] URL checks work
- [x] TEXT checks work
- [x] Validation works correctly
- [x] Credits deducted correctly
- [x] SSE progress works

### Dashboard Pages
- [x] All 5 pages load correctly
- [x] All components display correctly
- [x] All interactions work
- [x] Search and filters work

### Stripe Integration
- [x] Checkout works
- [x] Webhooks process correctly
- [x] Subscription management works
- [x] Cancellation/reactivation work

### Quality
- [x] Mobile responsive
- [x] Performance targets met
- [x] Accessibility standards met
- [x] Cross-browser compatible
- [x] No critical bugs

---

## 📊 WEEK 1 DAILY STANDUP TEMPLATE

Use this template for daily progress tracking:

```markdown
## Day X Standup - [Date]

### ✅ Completed Today
- [List completed tasks]

### 🐛 Bugs Found
- [List bugs with severity]

### 🚧 In Progress
- [Current task]

### ⏭️ Next
- [Tomorrow's priority]

### 🚨 Blockers
- [Any blockers or concerns]
```

---

## 🎯 WEEK 1 COMPLETION CHECKLIST

**End of week review:**

- [ ] All Day 1-5 tasks completed
- [ ] All critical (P0) bugs fixed
- [ ] All high priority (P1) bugs fixed
- [ ] Bug list documented for Week 2
- [ ] Performance benchmarks met
- [ ] Accessibility audit passed
- [ ] Mobile testing completed
- [ ] Cross-browser testing completed
- [ ] Documentation updated with any changes
- [ ] Ready to proceed to Week 2 (Production Deployment)

---

**Next:** [MVP_WEEK2_PRODUCTION_DEPLOYMENT.md](./MVP_WEEK2_PRODUCTION_DEPLOYMENT.md)
