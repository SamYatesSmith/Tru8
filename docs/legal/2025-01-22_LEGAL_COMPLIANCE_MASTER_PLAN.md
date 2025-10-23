# TRU8 LEGAL COMPLIANCE MASTER PLAN
**Document Date:** 2025-01-22
**Status:** Pre-MVP Implementation Required
**Target:** UK GDPR & Data Protection Act 2018 Compliance

---

## EXECUTIVE SUMMARY

This document outlines all legal compliance requirements for Tru8's MVP launch in the UK market. Tru8 is a SaaS fact-checking platform that processes user data, requires payment processing, and will implement analytics tracking.

**Key Compliance Areas:**
1. ✅ ICO Registration (Required)
2. ✅ Privacy Policy (Required)
3. ✅ Terms of Service (Required)
4. ✅ Cookie Consent Banner (Required - PostHog & Sentry planned)
5. ✅ GDPR User Rights Implementation (Required)
6. ⚠️ Online Safety Act Considerations (Content moderation)
7. ✅ Data Processing Records (Required)

**Estimated Implementation Time:** 5-7 days
**Legal Risk Level:** HIGH (non-negotiable for launch)

---

## PART 1: ICO REGISTRATION

### Status: ❌ NOT COMPLETED

### Requirement
All UK businesses processing personal data must register with the Information Commissioner's Office (ICO) unless specifically exempted.

### Tru8's Data Processing Activities
You process:
- ✅ User account data (name, email, authentication)
- ✅ Payment information (via Stripe - processed by third party)
- ✅ User-generated content (fact-check submissions)
- ✅ Usage analytics (PostHog planned)
- ✅ Error tracking data (Sentry planned)

**Result:** ICO registration is MANDATORY

### Fee Structure
Based on your MVP stage (likely <10 employees, <£632k turnover):
- **Tier 1 (Most Likely):** £40/year
- **Tier 2 (If scaling quickly):** £60/year

### Registration Process
1. **Self-Assessment Tool:** https://ico.org.uk/for-organisations/data-protection-fee/self-assessment/
2. **Complete Online Registration:** ~15 minutes
3. **Payment:** Credit/debit card
4. **Certificate:** Receive confirmation within 24 hours

### Penalty for Non-Compliance
Up to £4,350 fine

### Action Items
- [ ] Complete ICO self-assessment
- [ ] Register organization (provide: business name, address, DPO if applicable, data processing activities)
- [ ] Pay annual fee (£40 or £60)
- [ ] Add ICO registration number to Privacy Policy footer
- [ ] Set calendar reminder for annual renewal

**Priority:** 🔴 CRITICAL - Complete within 1 week
**Owner:** [Business Owner]
**Estimated Time:** 1 hour

---

## PART 2: PRIVACY POLICY

### Status: ⚠️ DRAFT EXISTS (User mentioned - location unknown)

### Legal Requirement
UK GDPR Article 13 & 14 require transparent information about data processing.

### What Your Privacy Policy Must Include

#### 2.1 Data Controller Information
```
Tru8 Limited [or your legal entity name]
[Registered address]
[Contact email]
ICO Registration Number: [To be added after registration]
```

#### 2.2 Data We Collect

**Account Data:**
- Email address (authentication via Clerk)
- Name (optional, for personalization)
- Hashed password (managed by Clerk)
- Account creation date

**Usage Data:**
- Fact-checks submitted (URLs, text, images, videos)
- Check results and history
- Credits usage tracking
- Dashboard interactions

**Payment Data:**
- Processed by Stripe (PCI DSS compliant)
- We store: subscription status, plan type, billing cycle
- We DO NOT store: card numbers, CVV, full card details

**Analytics Data (PostHog):**
- Page views
- Button clicks
- User journey tracking
- Device/browser information
- IP address (anonymized option available)

**Error Tracking Data (Sentry):**
- Error logs
- Stack traces
- Browser/device information
- User ID (for authenticated errors)

**Cookies:**
- Authentication cookies (Clerk - essential)
- Analytics cookies (PostHog - requires consent)
- Error tracking cookies (Sentry - requires consent)

#### 2.3 Legal Basis for Processing

| Data Type | Legal Basis | Purpose |
|-----------|-------------|---------|
| Account Data | Contract | Provide fact-checking service |
| Payment Data | Contract | Process subscriptions |
| Usage Data | Legitimate Interest | Service improvement, fraud prevention |
| Analytics Data | Consent | Understand user behavior |
| Error Tracking | Legitimate Interest | Fix bugs, improve stability |

#### 2.4 Data Retention

**Account Data:** Retained until account deletion requested
**Check History:** Retained for 2 years or until account deletion
**Payment Records:** 7 years (UK tax law requirement)
**Analytics Data:** 12 months (PostHog default)
**Error Logs:** 90 days (Sentry default)

#### 2.5 Third-Party Data Processors

**We share data with:**
- **Clerk (clerk.com):** Authentication services (US-based, Standard Contractual Clauses)
- **Stripe (stripe.com):** Payment processing (Ireland entity, UK GDPR compliant)
- **PostHog (posthog.com):** Analytics (EU hosting option available)
- **Sentry (sentry.io):** Error tracking (EU hosting option available)
- **Evidence Sources:** URLs you submit are fetched from public sources

**We do NOT sell data to third parties.**

#### 2.6 International Data Transfers

- Clerk (US): Standard Contractual Clauses (SCCs)
- Stripe (Ireland): UK GDPR adequate
- PostHog: EU hosting recommended
- Sentry: EU hosting recommended

#### 2.7 User Rights (GDPR Chapter 3)

You have the right to:
1. **Access:** Request copy of your data (dashboard export + email support)
2. **Rectification:** Update your account information (settings page)
3. **Erasure:** Delete your account (settings → delete account)
4. **Restrict Processing:** Limit how we use your data
5. **Data Portability:** Export your check history as JSON
6. **Object:** Opt out of non-essential processing
7. **Withdraw Consent:** Revoke analytics cookies anytime

**How to Exercise Rights:**
- Account management: Dashboard → Settings
- Data export: [To be implemented]
- Account deletion: Settings → Account → Delete Account
- Other requests: privacy@tru8.com [or your email]

**Response Time:** Within 30 days

#### 2.8 Data Security Measures

- HTTPS encryption (TLS 1.3)
- Password hashing via Clerk (industry standard)
- Database encryption at rest
- Regular security updates
- Access controls (role-based)
- Backup encryption

#### 2.9 Breach Notification

If a data breach affects you, we will:
- Notify ICO within 72 hours
- Notify affected users without undue delay
- Provide guidance on protective measures

#### 2.10 Children's Privacy

Tru8 is not intended for users under 18. If you become aware a child has provided data, contact us for immediate deletion.

#### 2.11 Changes to Privacy Policy

We will notify you via:
- Email (to registered address)
- Banner notification on dashboard
- Version history maintained

#### 2.12 Contact & Complaints

**Data Protection Queries:**
privacy@tru8.com

**ICO Complaints:**
Information Commissioner's Office
Wycliffe House, Water Lane, Wilmslow, Cheshire, SK9 5AF
https://ico.org.uk/make-a-complaint/

### Action Items
- [ ] Locate draft privacy policy (user mentioned it exists)
- [ ] Review draft against this checklist
- [ ] Add ICO registration number
- [ ] Verify all third-party processors listed
- [ ] Add last updated date
- [ ] Have lawyer review (recommended)
- [ ] Create `/privacy-policy` page in Next.js
- [ ] Link from footer on all pages

**Priority:** 🔴 CRITICAL - Complete within 1 week
**Owner:** [Business Owner/Developer]
**Estimated Time:** 4-6 hours (draft review + implementation)

---

## PART 3: TERMS OF SERVICE

### Status: ❌ NOT CREATED

### Legal Requirement
Protects your business and sets user expectations. Not legally required, but strongly recommended for SaaS.

### What Your ToS Must Include

#### 3.1 Service Description
- Tru8 provides AI-powered fact-checking services
- Evidence retrieval from public sources
- Claim analysis and verdict generation
- NOT a substitute for professional verification
- Results are probabilistic, not absolute

#### 3.2 Account Terms
- Must be 18+ to create account
- One account per person
- Accurate information required
- Responsible for account security
- Notify us of unauthorized access

#### 3.3 Acceptable Use Policy

**You may:**
- Submit factual claims for verification
- Use results for personal/commercial purposes with attribution
- Share check results publicly

**You may NOT:**
- Submit illegal, defamatory, or harmful content
- Abuse the service (spam, DDoS attempts)
- Reverse engineer the platform
- Use for automated/high-volume scraping without permission
- Violate any applicable laws

#### 3.4 Content & Intellectual Property

**Your Content:**
- You retain ownership of submitted content
- Grant us license to process for fact-checking
- You're responsible for content legality
- We may remove content violating ToS

**Our Content:**
- Tru8 platform, code, algorithms are our IP
- Check results are provided under limited license
- Attribution required for public sharing

#### 3.5 Payment Terms

**Free Plan:**
- 3 checks per month
- No payment required
- Credit resets monthly

**Professional Plan:**
- 40 checks per month
- £[X]/month via Stripe
- Auto-renewal
- Cancel anytime (applies next billing cycle)
- No refunds for partial months
- Unused credits don't roll over

**Payment Failures:**
- Service suspended after 3 failed attempts
- Account deletion after 60 days non-payment

#### 3.6 Service Availability

- Target: 99% uptime (no SLA guarantee at MVP stage)
- Scheduled maintenance communicated via email
- Emergency downtime may occur
- No liability for service interruptions
- Beta/experimental features may be unstable

#### 3.7 Disclaimers & Limitations

**Important Disclaimers:**
- Results are AI-generated, may contain errors
- Not a substitute for expert verification
- Fact-checking is subjective by nature
- Evidence sources are third-party, unverified by us
- No warranty of accuracy, completeness, or fitness

**Limitation of Liability:**
- Liability capped at amount paid in last 12 months (or £100 for free users)
- No liability for indirect, consequential damages
- UK law governs disputes
- Jurisdiction: England & Wales courts

#### 3.8 Termination

**We may suspend/terminate for:**
- ToS violation
- Payment failure
- Illegal activity
- Abusive behavior

**You may terminate by:**
- Deleting your account (Settings → Delete Account)
- Cancelling subscription (Settings → Subscription → Cancel)

**Effect of Termination:**
- Account data deleted within 30 days
- Payment records retained 7 years (tax law)
- No refunds for early termination

#### 3.9 Changes to Terms

- We may update ToS with 30 days notice
- Continued use = acceptance
- Material changes require explicit consent

#### 3.10 Governing Law

- UK law applies
- England & Wales jurisdiction
- EU users: Consumer protection rights apply

### Action Items
- [ ] Draft Terms of Service using template (Termly.io recommended)
- [ ] Add pricing details once finalized
- [ ] Have lawyer review
- [ ] Create `/terms-of-service` page in Next.js
- [ ] Require acceptance during sign-up (Clerk custom flow)
- [ ] Link from footer on all pages

**Priority:** 🔴 CRITICAL - Complete within 1 week
**Owner:** [Business Owner]
**Estimated Time:** 4-6 hours

---

## PART 4: COOKIE CONSENT BANNER

### Status: ❌ NOT IMPLEMENTED

### Legal Requirement
UK GDPR requires informed consent for non-essential cookies before they're set.

### Your Cookie Categories

#### Essential Cookies (No Consent Required)
- **Clerk authentication:** `__session` (7-day session)
- **CSRF protection:** `__Host-csrf`
- Purpose: Service functionality

#### Analytics Cookies (Consent Required)
- **PostHog:** `ph_*` cookies
- Purpose: User behavior tracking, product improvement
- Duration: 12 months

#### Error Tracking Cookies (Consent Required)
- **Sentry:** `sentry-*` cookies
- Purpose: Error monitoring, bug fixing
- Duration: 90 days

### Recommended Solution: **CookieYes**

**Why CookieYes:**
1. ✅ GDPR & CCPA compliant out-of-box
2. ✅ Next.js 14/15 compatible
3. ✅ Free tier available (up to 10,000 pageviews/month)
4. ✅ Automatic cookie scanning
5. ✅ Geo-location targeting (show banner only to EU/UK users)
6. ✅ Multi-language support
7. ✅ Google Consent Mode v2 compatible
8. ✅ Easy integration

**Pricing:**
- **Free:** 10k pageviews/month
- **Basic:** $10/month - 100k pageviews
- **Pro:** $25/month - 500k pageviews

**Alternative (Custom Build):**
- `react-cookie-consent` package (open source)
- More control, more maintenance
- Requires manual cookie categorization

### Implementation Steps (CookieYes)

#### Step 1: Create Account
1. Sign up at cookieyes.com
2. Add domain: `tru8.com` (or your production domain)
3. Configure cookie categories
4. Customize banner design (match Tru8 branding)

#### Step 2: Install in Next.js

**File:** `web/app/layout.tsx`

```tsx
import Script from 'next/script';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* CookieYes Banner Script */}
        <Script
          id="cookieyes"
          src="https://cdn-cookieyes.com/client_data/[YOUR_ID]/script.js"
          strategy="beforeInteractive"
        />
      </head>
      <body>
        <ClerkProvider>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}
```

#### Step 3: Configure Cookie Blocking

**PostHog Integration:**
```typescript
// Only initialize if consent given
if (window.CookieYes?.getConsent('analytics')) {
  posthog.init('[YOUR_API_KEY]', {
    api_host: 'https://eu.posthog.com', // Use EU hosting
  });
}

// Listen for consent changes
window.addEventListener('cookieyes_consent_update', (event) => {
  if (event.detail.accepted.includes('analytics')) {
    // User accepted - initialize PostHog
    posthog.init('[YOUR_API_KEY]');
  } else {
    // User rejected - disable PostHog
    posthog.opt_out_capturing();
  }
});
```

**Sentry Integration:**
```typescript
// Only initialize if consent given
if (window.CookieYes?.getConsent('analytics')) {
  Sentry.init({
    dsn: '[YOUR_DSN]',
    environment: process.env.NODE_ENV,
  });
}
```

#### Step 4: Cookie Policy Page

CookieYes auto-generates a cookie policy. Link to it:
- Footer: "Cookie Policy" link
- Privacy Policy: Reference cookie usage section

### Action Items
- [ ] Decide: CookieYes (recommended) vs custom build
- [ ] Create CookieYes account (free tier)
- [ ] Configure cookie categories
- [ ] Customize banner to match Tru8 design (#f57a07 orange, dark theme)
- [ ] Install script in `web/app/layout.tsx`
- [ ] Implement PostHog consent check
- [ ] Implement Sentry consent check
- [ ] Test: banner appears on first visit
- [ ] Test: preferences persist across sessions
- [ ] Test: PostHog doesn't load without consent
- [ ] Add cookie policy link to footer

**Priority:** 🔴 CRITICAL - Complete before analytics implementation
**Owner:** [Developer]
**Estimated Time:** 4-6 hours

---

## PART 5: GDPR USER RIGHTS IMPLEMENTATION

### Status: ⚠️ PARTIAL (Deletion exists, export missing)

### Required Rights & Current Implementation Status

#### 5.1 Right to Access
**Status:** ⚠️ PARTIAL

**User Request:** "Give me a copy of my data"

**Current Implementation:**
- ✅ User can view data in dashboard (checks, account info)
- ❌ No structured export functionality

**Required Implementation:**
- [ ] Create `/api/v1/users/me/export` endpoint
- [ ] Export format: JSON (machine-readable) + PDF (human-readable)
- [ ] Include: account data, check history, subscription details, usage logs
- [ ] Deliver via: download link + email
- [ ] Implement in Settings → Privacy → "Download My Data"

**Code Location:** `backend/app/api/v1/users.py`

```python
@router.get("/me/export")
async def export_user_data(user_id: str = Depends(require_auth)):
    """
    GDPR Article 15 - Right to Access
    Returns all user data in structured format
    """
    # Gather all data
    user = db.get_user(user_id)
    checks = db.get_user_checks(user_id)
    subscription = stripe.get_subscription(user_id)

    export_data = {
        "export_date": datetime.now().isoformat(),
        "account": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at,
            "credits": user.credits
        },
        "checks": [serialize_check(c) for c in checks],
        "subscription": serialize_subscription(subscription)
    }

    return JSONResponse(export_data)
```

#### 5.2 Right to Rectification
**Status:** ✅ IMPLEMENTED

- ✅ Settings → Account → Update name/email
- ✅ Clerk handles email verification

#### 5.3 Right to Erasure (Right to be Forgotten)
**Status:** ✅ IMPLEMENTED

**Current Implementation:**
- ✅ Settings → Account → Delete Account
- ✅ Confirms via double-check prompts
- ✅ Deletes user from Clerk
- ✅ Deletes user from Tru8 database

**Code Location:** `web/app/dashboard/settings/components/account-tab.tsx:32-61`

**⚠️ Gap:** Payment records must be retained 7 years (UK tax law) - document this exception in Privacy Policy

#### 5.4 Right to Restrict Processing
**Status:** ❌ NOT IMPLEMENTED (Low Priority)

**User Request:** "Stop using my data but don't delete it"

**Implementation (if needed post-MVP):**
- Account suspension state
- Stops analytics tracking
- Preserves data for restoration

#### 5.5 Right to Data Portability
**Status:** ❌ NOT IMPLEMENTED

**Same as Right to Access** - covered by export functionality above

#### 5.6 Right to Object
**Status:** ⚠️ PARTIAL

**Current Implementation:**
- ✅ Cookie banner allows objecting to analytics
- ❌ No mechanism to object to legitimate interest processing (usage tracking)

**Implementation:**
- [ ] Settings → Privacy → "Opt out of usage analytics"
- [ ] Disable PostHog for this user specifically
- [ ] Add to privacy preferences table

#### 5.7 Rights Related to Automated Decision Making
**Status:** ✅ N/A (No automated decisions affecting user rights/contracts)

Tru8's AI provides information, doesn't make automated decisions about:
- Account approval/suspension (manual)
- Payment processing (Stripe handles, manual review available)
- Service access (based on subscription, not profiling)

### Action Items
- [ ] Implement data export endpoint (backend)
- [ ] Add "Download My Data" button (Settings → Privacy)
- [ ] Test export includes all user data
- [ ] Add "Opt out of analytics" toggle (Settings → Privacy)
- [ ] Document payment record retention exception in Privacy Policy
- [ ] Create support email for rights requests: privacy@tru8.com

**Priority:** 🟡 HIGH - Complete within 2 weeks
**Owner:** [Developer]
**Estimated Time:** 6-8 hours

---

## PART 6: DATA PROCESSING RECORDS (Article 30)

### Status: ❌ NOT CREATED

### Legal Requirement
Organizations must maintain records of processing activities (GDPR Article 30).

### What to Document

#### Processing Activity Record Template

**Activity 1: User Account Management**
- **Purpose:** Provide authentication and service access
- **Legal Basis:** Contract
- **Data Categories:** Email, name, password hash, user ID
- **Data Subjects:** All registered users
- **Recipients:** Clerk (authentication service)
- **Transfers:** US (Clerk) via Standard Contractual Clauses
- **Retention:** Until account deletion + 30 days
- **Security:** HTTPS, password hashing, encrypted database

**Activity 2: Fact-Check Processing**
- **Purpose:** Provide core fact-checking service
- **Legal Basis:** Contract
- **Data Categories:** Submitted URLs/text, check results, timestamps
- **Data Subjects:** Registered users
- **Recipients:** None (internal processing)
- **Transfers:** None
- **Retention:** 2 years or until account deletion
- **Security:** Database encryption, access controls

**Activity 3: Payment Processing**
- **Purpose:** Handle subscriptions and billing
- **Legal Basis:** Contract
- **Data Categories:** Subscription status, plan type, billing cycle
- **Data Subjects:** Paying subscribers
- **Recipients:** Stripe (payment processor)
- **Transfers:** Ireland (Stripe) - UK GDPR adequate
- **Retention:** 7 years (UK tax law)
- **Security:** Stripe PCI DSS Level 1, no card data stored locally

**Activity 4: Usage Analytics**
- **Purpose:** Product improvement, user behavior understanding
- **Legal Basis:** Consent (via cookie banner)
- **Data Categories:** Page views, interactions, device info, IP (anonymized)
- **Data Subjects:** Users who consented
- **Recipients:** PostHog (analytics platform)
- **Transfers:** EU hosting (configure PostHog for EU data residency)
- **Retention:** 12 months
- **Security:** Anonymized IPs, aggregated data

**Activity 5: Error Tracking**
- **Purpose:** Bug detection and service stability
- **Legal Basis:** Legitimate interest
- **Data Categories:** Error logs, stack traces, user ID (for authenticated users)
- **Data Subjects:** All users
- **Recipients:** Sentry (error monitoring)
- **Transfers:** EU hosting (configure Sentry for EU data residency)
- **Retention:** 90 days
- **Security:** Sensitive data scrubbing, access controls

### Action Items
- [ ] Create document: `docs/legal/DATA_PROCESSING_RECORDS.md`
- [ ] Complete template for all 5 activities
- [ ] Review annually (or when processing changes)
- [ ] Make available to ICO upon request

**Priority:** 🟡 MEDIUM - Complete within 2 weeks
**Owner:** [Business Owner/DPO]
**Estimated Time:** 2-3 hours

---

## PART 7: ONLINE SAFETY ACT CONSIDERATIONS

### Status: ⚠️ TO BE ASSESSED

### Does Tru8 Fall Under Online Safety Act?

The UK Online Safety Act applies to services that:
1. Host user-generated content, OR
2. Facilitate user interaction (comments, messaging)

**Tru8's Content:**
- Users submit URLs/text for fact-checking
- Results are displayed back to user
- **No public user-generated content**
- **No user-to-user communication**
- **No comments or social features**

**Initial Assessment:** Likely NOT in scope for Online Safety Act Phase 1

**However, if you plan to add:**
- Public check sharing (others can comment)
- User profiles with public content
- Discussion forums
- User ratings/reviews

**Then:** Online Safety Act compliance required (risk assessments, content moderation policies)

### Recommended Action

**For MVP:**
- ❌ Do NOT add public user content features
- ❌ Do NOT add commenting
- ✅ Keep checks private to user (with shareable links)

**Post-MVP:**
- If adding social features, consult lawyer on OSA compliance
- Implement content moderation tools
- Create Community Guidelines
- Conduct risk assessment

### Action Items
- [ ] Document content model (private checks only)
- [ ] Add to ToS: "Checks are private unless you share the link"
- [ ] If adding social features post-MVP, consult OSA expert

**Priority:** 🟢 LOW (for MVP) - Monitor if features change
**Owner:** [Business Owner]
**Estimated Time:** 1 hour (documentation)

---

## PART 8: ADDITIONAL LEGAL PAGES REQUIRED

### 8.1 Acceptable Use Policy (AUP)
**Status:** ❌ NOT CREATED
**Required:** Yes (part of ToS or separate page)

**Content:**
- Prohibited content (illegal, harmful, spam)
- Abuse consequences (account suspension/termination)
- Reporting mechanism for violations

**Action:** Include in Terms of Service (Section 3.3 above)

### 8.2 Refund Policy
**Status:** ❌ NOT CREATED
**Required:** Yes (consumer protection)

**UK Consumer Rights:**
- 14-day cooling-off period for digital services
- Right to refund if service not as described
- No refund for used services (checks consumed)

**Recommended Policy:**
```
Refunds:
- Pro-rated refunds available within 14 days of subscription start
- If you've used >10% of monthly checks, refund reduced proportionally
- Technical issues: Full refund if service unavailable >48 hours
- Contact: refunds@tru8.com within 14 days
```

**Action:** Create `/refund-policy` page, link from pricing and footer

### 8.3 Contact Page
**Status:** ❌ NOT CREATED
**Required:** Yes (GDPR transparency requirement)

**Must Include:**
- Business address (registered office)
- Contact email
- Privacy queries email
- Support email
- ICO registration number

**Action:** Create `/contact` page

---

## PART 9: FOOTER COMPLIANCE

### Current Footer Status
**Review Needed:** Check if footer has all required links

### Required Footer Links (All Pages)
- [ ] Privacy Policy
- [ ] Terms of Service
- [ ] Cookie Policy
- [ ] Contact Us
- [ ] Refund Policy
- [ ] ICO Registration: [Number]

**Optional but Recommended:**
- [ ] About Us
- [ ] FAQ
- [ ] Acceptable Use Policy
- [ ] Accessibility Statement

### Action Items
- [ ] Audit current footer in `web/components/layout/footer.tsx` (if exists)
- [ ] Add missing links
- [ ] Ensure links work on all pages (marketing + dashboard)

**Priority:** 🟡 HIGH - Complete with other legal pages
**Owner:** [Developer]
**Estimated Time:** 1-2 hours

---

## PART 10: INTERNATIONAL CONSIDERATIONS

### 10.1 EU Data Transfers
**Tru8 → Clerk (US):** Standard Contractual Clauses (SCCs) in place ✅
**Tru8 → Stripe (Ireland):** UK GDPR adequate ✅
**Tru8 → PostHog:** Use EU hosting option ⚠️
**Tru8 → Sentry:** Use EU hosting option ⚠️

### 10.2 CCPA (California Consumer Privacy Act)
**Applies If:** You have California users

**Requirements:**
- Privacy policy disclosure
- Right to deletion
- Right to opt-out of data sale (you don't sell data - easy compliance)
- "Do Not Sell My Personal Information" link

**Action:** Add CCPA section to privacy policy if targeting US users

### 10.3 Other Jurisdictions
- **Canada (PIPEDA):** Similar to GDPR, largely compatible
- **Australia (Privacy Act):** Privacy policy required
- **Rest of world:** Generally GDPR compliance covers most requirements

**Recommendation:** Focus on UK GDPR for MVP, expand as userbase grows internationally

---

## PART 11: IMPLEMENTATION TIMELINE

### Week 1: Foundation (5 days)
**Priority: Critical blockers**

**Day 1: ICO Registration**
- [ ] Complete self-assessment
- [ ] Register organization
- [ ] Pay fee
- [ ] Receive registration number
- **Owner:** Business Owner
- **Time:** 1-2 hours

**Day 2-3: Privacy Policy**
- [ ] Locate draft privacy policy
- [ ] Review against Part 2 checklist
- [ ] Add ICO number
- [ ] Add all third-party processors
- [ ] Legal review (recommended)
- [ ] Create `/privacy-policy` page
- **Owner:** Business Owner + Developer
- **Time:** 6-8 hours

**Day 4-5: Terms of Service**
- [ ] Draft ToS from template
- [ ] Customize for Tru8 (pricing, acceptable use)
- [ ] Legal review (recommended)
- [ ] Create `/terms-of-service` page
- [ ] Require acceptance during sign-up
- **Owner:** Business Owner + Developer
- **Time:** 6-8 hours

### Week 2: User Rights & Consent (5 days)

**Day 6-7: Cookie Consent**
- [ ] Set up CookieYes account
- [ ] Configure categories
- [ ] Customize banner design
- [ ] Install in Next.js
- [ ] Implement consent checks (PostHog, Sentry)
- [ ] Test functionality
- **Owner:** Developer
- **Time:** 4-6 hours

**Day 8-9: GDPR Rights**
- [ ] Implement data export endpoint
- [ ] Add "Download My Data" button
- [ ] Implement analytics opt-out
- [ ] Test export includes all data
- **Owner:** Developer
- **Time:** 6-8 hours

**Day 10: Documentation & Polish**
- [ ] Create data processing records
- [ ] Add footer links
- [ ] Create contact page
- [ ] Create refund policy
- [ ] Final review
- **Owner:** Business Owner + Developer
- **Time:** 4-6 hours

### Post-Week 2: Ongoing Compliance
- [ ] Set calendar reminder: ICO renewal (annual)
- [ ] Set calendar reminder: Privacy policy review (quarterly)
- [ ] Set calendar reminder: ToS review (annual)
- [ ] Set calendar reminder: Data processing records review (annual)
- [ ] Monitor for legal changes (UK GDPR updates)

---

## PART 12: COST BREAKDOWN

| Item | Provider | Cost | Frequency |
|------|----------|------|-----------|
| ICO Registration | UK ICO | £40-60 | Annual |
| Cookie Consent (CookieYes) | CookieYes | Free - $10 | Monthly |
| Privacy Policy Generator (optional) | Termly | Free - $15 | One-time |
| Legal Review (recommended) | Lawyer | £200-500 | One-time |
| **Total Year 1** | | **£240-570** | |
| **Total Ongoing (Annual)** | | **£40-180** | |

**Recommendation:** Budget £500 for legal compliance setup, £100/year ongoing

---

## PART 13: RISK ASSESSMENT

### High Risk - Launch Blockers
1. **No ICO Registration** → £4,350 fine
2. **No Privacy Policy** → ICO enforcement action
3. **No Cookie Consent** → GDPR violation (up to 4% revenue or €20M)

**Mitigation:** Complete Parts 1-4 before MVP launch

### Medium Risk - Post-Launch Required
4. **No Data Export** → GDPR complaint upheld by ICO
5. **No Refund Policy** → Consumer protection complaint

**Mitigation:** Complete within 2 weeks of launch

### Low Risk - Best Practice
6. **No Data Processing Records** → ICO audit finding (administrative)
7. **No dedicated DPO** → Not required at MVP scale

**Mitigation:** Complete within 1 month of launch

---

## PART 14: CHECKLIST FOR LAUNCH

### CRITICAL (Must complete before launch)
- [ ] ICO registration completed
- [ ] Privacy policy live at `/privacy-policy`
- [ ] Terms of service live at `/terms-of-service`
- [ ] Cookie consent banner implemented and tested
- [ ] Footer links added to all pages
- [ ] Sign-up requires ToS acceptance
- [ ] Account deletion functionality working

### HIGH PRIORITY (Complete within 2 weeks of launch)
- [ ] Data export functionality implemented
- [ ] Refund policy created
- [ ] Contact page created
- [ ] Analytics opt-out implemented
- [ ] Data processing records documented

### MEDIUM PRIORITY (Complete within 1 month)
- [ ] Privacy policy reviewed by lawyer
- [ ] Terms of service reviewed by lawyer
- [ ] Data processing records filed
- [ ] Internal GDPR training for team
- [ ] Privacy@tru8.com email set up and monitored

---

## PART 15: RESOURCES & TEMPLATES

### Official Guidance
- **ICO Guidance:** https://ico.org.uk/for-organisations/
- **UK GDPR Full Text:** https://www.legislation.gov.uk/uksi/2019/419/contents
- **DPA 2018:** https://www.legislation.gov.uk/ukpga/2018/12/contents

### Template Generators
- **Privacy Policy:** https://termly.io/products/privacy-policy-generator/ (Free)
- **Terms of Service:** https://termly.io/products/terms-and-conditions-generator/ (Free)
- **Cookie Policy:** CookieYes auto-generates (Free with account)

### Cookie Consent Solutions
- **CookieYes (Recommended):** https://www.cookieyes.com/
- **Alternative:** react-cookie-consent (Open source)

### Legal Review Services
- **UK Tech Lawyers:** Search "SaaS lawyer UK" on Google
- **Typical Cost:** £200-500 for document review
- **Recommended:** Yes, for peace of mind

### GDPR Compliance Tools
- **Iubenda:** Privacy policy + cookie consent (€27/month)
- **CookiePro by OneTrust:** Enterprise option (expensive)
- **Termly:** All-in-one compliance ($15/month)

---

## PART 16: QUESTIONS TO RESOLVE

Before finalizing legal compliance, clarify:

1. **Legal Entity Details:**
   - [ ] Company name: Tru8 Limited? [Confirm]
   - [ ] Registered address: [Provide]
   - [ ] Company number: [Provide]
   - [ ] VAT number (if applicable): [Provide]

2. **Pricing Confirmation:**
   - [ ] Professional plan price: £[X]/month
   - [ ] Credit allocations: 3 free, 40 pro [Confirm]
   - [ ] Refund policy details [Define]

3. **Contact Details:**
   - [ ] Support email: support@tru8.com? [Confirm]
   - [ ] Privacy email: privacy@tru8.com? [Set up]
   - [ ] Refunds email: refunds@tru8.com? [Set up]

4. **Data Residency:**
   - [ ] PostHog: Use EU hosting? [Decide]
   - [ ] Sentry: Use EU hosting? [Decide]
   - [ ] Backend hosting location: [Confirm - currently?]

5. **Legal Review:**
   - [ ] Budget available for lawyer review? [Decide]
   - [ ] Timeline for legal review? [If yes]

---

## NEXT STEPS

**Immediate Actions (This Week):**
1. ✅ Read this entire document
2. ⚠️ Locate draft privacy policy mentioned by user
3. ✅ Complete ICO registration (1 hour)
4. ✅ Start drafting Terms of Service
5. ✅ Set up CookieYes account

**Developer Handoff (Next Week):**
1. Implement legal pages (`/privacy-policy`, `/terms-of-service`, `/contact`)
2. Integrate cookie consent banner
3. Add footer compliance links
4. Implement data export endpoint

**Business Owner Tasks (Next Week):**
1. Answer "Questions to Resolve" (Part 16)
2. Review/finalize privacy policy
3. Review/finalize terms of service
4. Consider legal review budget

**Final Pre-Launch:**
1. Test all legal pages load correctly
2. Test cookie banner functionality
3. Test account deletion flow
4. Verify all footer links work
5. Document completion in launch checklist

---

## DOCUMENT CONTROL

**Version:** 1.0
**Date:** 2025-01-22
**Author:** AI Legal Compliance Review
**Next Review:** Before MVP Launch
**Status:** DRAFT - Awaiting User Input

**Change Log:**
- 2025-01-22: Initial comprehensive compliance plan created

---

**END OF LEGAL COMPLIANCE MASTER PLAN**

For questions or clarifications, add comments or create issues in project tracker.
