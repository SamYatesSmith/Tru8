# ⚠️ TEMPORARY CHANGES & DEFERRED TASKS

**Last Updated:** October 13, 2025
**Status:** Testing Mode Active - DO NOT DEPLOY TO PRODUCTION

---

## 🚨 CRITICAL: TEMPORARY CHANGES FOR TESTING

### **These changes MUST be reverted before production deployment:**

#### 1. **Authentication Disabled** (`web/middleware.ts`)
```typescript
// CURRENT (TESTING):
export default clerkMiddleware((auth, req) => {
  // TEMPORARILY DISABLED FOR TESTING - Re-enable before production!
  // if (isProtectedRoute(req)) auth().protect();
});

// MUST REVERT TO:
export default clerkMiddleware((auth, req) => {
  if (isProtectedRoute(req)) auth().protect();
});
```
**Why:** Dashboard is accessible without authentication for UI testing.
**Risk:** HIGH - Anyone can access protected routes.

---

#### 2. **Mock User Data** (`web/app/dashboard/layout.tsx`)
```typescript
// CURRENT (TESTING): Lines 25-37
if (!userId) {
  // Mock user for testing
  user = {
    id: 'test-user-123',
    name: 'Test User',
    email: 'test@example.com',
    credits: 3,
  };
}

// MUST REVERT TO:
if (!userId) {
  redirect('/?signin=true');
}
const token = await getToken();
const user = await apiClient.getCurrentUser(token) as User;
```
**Why:** Allows viewing dashboard without real user data.
**Risk:** HIGH - No actual user authentication.

---

#### 3. **Mock Dashboard Data** (`web/app/dashboard/page.tsx`)
```typescript
// CURRENT (TESTING): Lines 37-55
if (!userId) {
  // Mock data for testing
  user = { id: 'test-user-123', ... };
  subscription = { hasSubscription: false, ... };
  checksResponse = { checks: [], total: 0 };
}

// MUST REVERT TO:
const { getToken } = auth();
const token = await getToken();
const [user, subscription, checksResponse] = await Promise.all([
  apiClient.getCurrentUser(token) as Promise<User>,
  apiClient.getSubscriptionStatus(token) as Promise<Subscription>,
  apiClient.getChecks(token, 0, 5) as Promise<ChecksResponse>,
]);
```
**Why:** Displays mock subscription and checks data.
**Risk:** HIGH - No real data validation.

---

## 📋 PRODUCTION DEPLOYMENT CHECKLIST

Before deploying to production, complete ALL items:

- [ ] **Revert authentication** in `web/middleware.ts` (line 10)
- [ ] **Remove mock user data** from `web/app/dashboard/layout.tsx` (lines 25-37)
- [ ] **Remove mock dashboard data** from `web/app/dashboard/page.tsx` (lines 37-55)
- [ ] **Restore redirect** on unauthenticated dashboard access
- [ ] **Test authentication flow** end-to-end
- [ ] **Verify Clerk webhooks** are configured
- [ ] **Test with real user accounts**
- [ ] **Run full build**: `npm run build`
- [ ] **Run TypeScript check**: `npm run typecheck`
- [ ] **Run linter**: `npm run lint`

---

## 🔄 DEFERRED TASKS & BACKLOG

### **High Priority - Must Complete Before Launch**

#### **1. Fix Sign-Up Flow from Signed-Out Page**
**Status:** BLOCKED
**Issue:** Users cannot sign up from the homepage
**Location:** `web/components/auth/auth-modal.tsx` or Clerk configuration
**Details:**
- Auth modal opens but sign-up doesn't complete
- Likely Clerk configuration or modal implementation issue
- Prevents new user registration entirely

**Action Required:**
- Debug Clerk modal integration
- Verify Clerk publishable key and environment setup
- Test sign-up flow with network inspector
- Check Clerk dashboard for configuration issues

---

#### **2. Backend Endpoints - Not Yet Implemented**
**Status:** DOCUMENTED, NOT IMPLEMENTED
**Reference:** `docs/plans/BACKEND_ENDPOINTS_REQUIRED.md`

The following endpoints are called by the frontend but **do not exist** in the backend yet:

##### **a) SSE Token Generation** (GAP #16)
```
POST /api/v1/checks/{id}/sse-token
```
**Purpose:** Generate short-lived token for SSE connections
**Frontend Usage:** `apiClient.createSSEToken(checkId, token)`
**Priority:** HIGH (required for real-time check progress)

##### **b) Invoice Retrieval** (GAP #17)
```
GET /api/v1/payments/invoices
```
**Purpose:** Fetch last 5 Stripe invoices
**Frontend Usage:** `apiClient.getInvoices(token)`
**Priority:** MEDIUM (nice-to-have for settings page)

##### **c) User Account Deletion** (GAP #18)
```
DELETE /api/v1/users/me
```
**Purpose:** Delete user account and all data (GDPR compliance)
**Frontend Usage:** `apiClient.deleteUser(userId, token)`
**Priority:** HIGH (legal requirement for GDPR)

##### **d) Subscription Cancellation** (GAP #19)
```
POST /api/v1/payments/cancel-subscription
POST /api/v1/payments/reactivate-subscription
```
**Purpose:** Cancel subscription at end of period / reactivate before end
**Frontend Usage:** `apiClient.cancelSubscription(token)`, `apiClient.reactivateSubscription(token)`
**Priority:** HIGH (required for downgrade flow)

**Action Required:**
- Implement all 5 endpoints in `backend/app/api/v1/`
- Add proper authorization checks
- Test with frontend integration
- Update API documentation

---

### **Medium Priority - Post-Launch Enhancements**

#### **3. Graphics Assets Missing**
**Status:** PLACEHOLDER USED
**Location:** `web/public/imagery/justice-scales.png`
**Details:**
- Currently using placeholder Image component
- Need actual justice scales graphic (300x300px)
- Referenced in: `web/app/dashboard/components/justice-scales-graphic.tsx`

**Action Required:**
- Design or source justice scales graphic
- Export as PNG (300x300px, optimized)
- Add to `web/public/imagery/` folder

---

#### **4. Server-Side Rendering Optimization**
**Status:** DEFERRED
**Location:** All dashboard pages
**Details:**
- Currently using `Promise.all()` for parallel fetching
- Could implement Suspense boundaries for progressive loading
- Would improve perceived performance

**Action Required:**
- Add React Suspense boundaries around slow-loading components
- Implement loading skeletons
- Consider streaming SSR for large data sets

---

#### **5. Mobile Responsiveness Testing**
**Status:** PARTIALLY COMPLETE
**Details:**
- Desktop layout verified
- Mobile breakpoints defined in Tailwind
- Need comprehensive mobile testing on real devices

**Action Required:**
- Test on iOS Safari (iPhone 12, 13, 14)
- Test on Android Chrome (Samsung, Pixel)
- Verify touch interactions work correctly
- Test with slow 3G connection

---

#### **6. Accessibility Audit**
**Status:** BASIC COMPLIANCE ONLY
**Details:**
- ARIA labels added to main components
- Keyboard navigation partially implemented
- Need full WCAG 2.1 AA compliance audit

**Action Required:**
- Run automated accessibility scan (axe DevTools)
- Manual keyboard navigation testing
- Screen reader testing (NVDA, JAWS, VoiceOver)
- Color contrast verification
- Focus indicator audit

---

### **Low Priority - Future Improvements**

#### **7. Performance Monitoring**
**Status:** NOT IMPLEMENTED
**Details:**
- No performance monitoring in place
- Should track Core Web Vitals
- Need error tracking

**Action Required:**
- Integrate Sentry for error tracking
- Add PostHog for analytics
- Monitor API response times
- Set up performance budgets

---

#### **8. Image Optimization**
**Status:** USING NEXT/IMAGE
**Details:**
- Next.js Image component used
- Could implement blur placeholders
- Consider WebP format for all images

**Action Required:**
- Generate blur data URLs for images
- Convert all PNGs to WebP where supported
- Implement responsive image sizes

---

#### **9. Database Performance**
**Status:** NOT OPTIMIZED
**Details:**
- Backend queries not optimized for scale
- No database indexes beyond primary keys
- N+1 query issues in checks list endpoint (now fixed, but could be optimized further)

**Action Required:**
- Add database indexes on frequently queried fields
- Implement database query caching (Redis)
- Analyze slow query logs
- Consider read replicas for scale

---

#### **10. SEO Optimization**
**Status:** BASIC METADATA ONLY
**Details:**
- Missing OpenGraph tags
- No Twitter cards
- No sitemap.xml
- No robots.txt

**Action Required:**
- Add metadata to all pages
- Generate dynamic OG images
- Create sitemap.xml
- Configure robots.txt
- Implement structured data (JSON-LD)

---

## 🛠️ KNOWN TECHNICAL DEBT

### **1. TypeScript Strictness**
**Current:** Using `any` types in some locations
**Example:** `ChecksResponse.checks: any[]` should be properly typed
**Priority:** Medium

### **2. Error Handling**
**Current:** Basic try-catch in some places, none in others
**Example:** API client doesn't have retry logic
**Priority:** High

### **3. Loading States**
**Current:** No loading skeletons implemented
**Example:** Dashboard shows blank screen while fetching
**Priority:** Medium

### **4. Form Validation**
**Current:** Not implemented yet (no forms in current implementation)
**Example:** Will need for new check form, settings form
**Priority:** High (when forms are added)

---

## 📝 NOTES

### **Animation Issues (RESOLVED)**
- **Issue:** Background and navigation animations not working on cold start
- **Root Cause:** Stale `.next` cache with broken CSS
- **Solution:** Clear cache with `npm run dev:clean` before starting
- **Permanent Fix:** Animations properly defined in `globals.css`, will work in production

### **Backend Alignment (COMPLETED)**
- **Issue:** GET `/api/v1/checks` only returned `claimsCount`, not actual claims
- **Solution:** Updated backend to include first claim in array for preview
- **File:** `backend/app/api/v1/checks.py:234-279`
- **Performance:** Adds 1 extra query per check (acceptable for dashboard)

---

## 🎯 NEXT STEPS

1. **Immediate (Before Testing):**
   - Keep temporary changes active
   - Test all dashboard UI components
   - Verify responsive design
   - Check all navigation links work

2. **Before Production:**
   - Complete "Production Deployment Checklist" above
   - Fix sign-up flow
   - Implement missing backend endpoints
   - Revert all temporary changes

3. **Post-Launch:**
   - Address medium priority items
   - Implement monitoring and analytics
   - Conduct accessibility audit
   - Optimize performance

---

**Remember:** This file tracks temporary changes and deferred work. Update it whenever you add temporary code or defer a task!
