# Tru8 Legal Compliance UI Implementation Guide
**Date:** 2025-01-22
**Status:** Planning - Pre-Implementation
**Scope:** Web application only (mobile app planned 3 months post-web release)

---

## 📋 OVERVIEW

This document provides comprehensive UI implementation guidance for integrating legal compliance documents into the Tru8 web application. All component paths, routes, and design patterns are based on actual codebase analysis.

**Related Documents:**
- `docs/legal/2025-01-22_LEGAL_COMPLIANCE_MASTER_PLAN.md` - Legal requirements and templates
- `docs/DESIGN_SYSTEM.md` - Design standards to follow

**Key Principle:** All UI implementations MUST follow the design system specifications in `docs/DESIGN_SYSTEM.md` including 4pt grid, container max-width, color system, and component standards.

---

## 🎯 UI TOUCHPOINTS SUMMARY

| Touchpoint | Component/Route | Action Required | Priority |
|------------|----------------|-----------------|----------|
| **Footer Links** | `web/components/layout/footer.tsx` | Update routes, add missing links | 🔴 CRITICAL |
| **Legal Pages** | Create: `web/app/privacy-policy/page.tsx` etc. | Build 5 new pages with templates | 🔴 CRITICAL |
| **Cookie Banner** | `web/app/layout.tsx` | Integrate CookieYes script | 🔴 CRITICAL |
| **Auth Modal ToS** | `web/components/auth/auth-modal.tsx` | Add ToS checkbox & link | 🔴 CRITICAL |
| **Settings Privacy Tab** | `web/app/dashboard/settings/` | Create new privacy tab | 🟡 HIGH |
| **Data Export Button** | `web/app/dashboard/settings/components/account-tab.tsx` | Add download data button | 🟡 HIGH |
| **Cookie Preferences Link** | Footer + Settings | Persistent access to manage cookies | 🟢 MEDIUM |

---

## PART 1: FOOTER COMPONENT UPDATES

### Current State Analysis

**File:** `web/components/layout/footer.tsx`

**Current Legal Links (Lines 26-30):**
```tsx
const legalLinks = [
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Terms of Service', href: '/terms' },
  { label: 'Cookie Policy', href: '/cookies' },
];
```

**Issue:** Routes don't match recommended structure from legal compliance plan.

### Required Changes

#### ✅ Update 1: Correct Legal Routes

**Change:** Update `legalLinks` array to match legal page routes

**Before:**
```tsx
const legalLinks = [
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Terms of Service', href: '/terms' },
  { label: 'Cookie Policy', href: '/cookies' },
];
```

**After:**
```tsx
const legalLinks = [
  { label: 'Privacy Policy', href: '/privacy-policy' },
  { label: 'Terms of Service', href: '/terms-of-service' },
  { label: 'Cookie Policy', href: '/cookie-policy' },
  { label: 'Refund Policy', href: '/refund-policy' },
  { label: 'Contact', href: '/contact' },
];
```

**Why:** Consistency with legal page naming convention, adds missing required links.

#### ✅ Update 2: Add ICO Registration Number

**Add After Legal Links Section (After Line 103):**
```tsx
{/* ICO Registration */}
<div className="col-span-2 md:col-span-1">
  <h3 className="text-white font-semibold mb-3 text-sm">Compliance</h3>
  <p className="text-slate-400 text-xs">
    ICO Registration: <span className="text-slate-300 font-mono">[ZA123456]</span>
  </p>
  <p className="text-slate-400 text-xs mt-2">
    Data Controller: Tru8 Ltd
  </p>
</div>
```

**Note:** Replace `[ZA123456]` with actual ICO registration number once obtained.

#### ✅ Update 3: Add Cookie Preferences Button

**Add to Legal Links (Line 101):**
```tsx
<li key="cookie-preferences">
  <button
    onClick={() => {
      // CookieYes API to reopen banner
      if (typeof window !== 'undefined' && (window as any).cookieyes) {
        (window as any).cookieyes.showBanner();
      }
    }}
    className="text-slate-400 hover:text-[#f57a07] transition-colors text-sm"
  >
    Manage Cookie Preferences
  </button>
</li>
```

### Implementation Checklist

- [ ] Update `legalLinks` array with correct routes
- [ ] Add Refund Policy link
- [ ] Add Contact link
- [ ] Add ICO Registration section
- [ ] Add Cookie Preferences button
- [ ] Test all footer links work on both marketing and dashboard pages
- [ ] Verify responsive layout still works on mobile

**Estimated Time:** 30 minutes

---

## PART 2: LEGAL PAGE TEMPLATES

### Pages to Create

All pages will be created under `web/app/` directory:

1. `privacy-policy/page.tsx` - Privacy Policy
2. `terms-of-service/page.tsx` - Terms of Service
3. `cookie-policy/page.tsx` - Cookie Policy
4. `refund-policy/page.tsx` - Refund Policy
5. `contact/page.tsx` - Contact Information

### Design System Requirements

**CRITICAL:** All legal pages MUST follow these standards from `docs/DESIGN_SYSTEM.md`:

- **Container:** `max-width: var(--container-lg)` (1024px), centered
- **Spacing:** 4pt grid system (`var(--space-4)`, `var(--space-6)`, etc.)
- **Typography:** Responsive scale, bold headings
- **Colors:** Dark background `#0f1419`, white text, `#f57a07` accents
- **Radius:** Cards use `var(--radius-lg)` (12px)

### Shared Legal Page Template Component

**Create:** `web/components/legal/legal-page-layout.tsx`

```tsx
'use client';

import { Navigation } from '@/components/layout/navigation';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  return (
    <>
      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="min-h-screen bg-[#0f1419] pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Page Header */}
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-black text-white mb-4">
              {title}
            </h1>
            <p className="text-slate-400 text-sm">
              Last Updated: <span className="text-slate-300">{lastUpdated}</span>
            </p>
          </div>

          {/* Content Container */}
          <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-8 md:p-12">
            <div className="prose prose-invert prose-slate max-w-none">
              {children}
            </div>
          </div>

          {/* Contact Footer */}
          <div className="mt-12 text-center">
            <p className="text-slate-400 text-sm mb-4">
              Have questions about this policy?
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-medium transition-colors"
            >
              Contact Us
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
```

**Design Notes:**
- Uses `container mx-auto max-w-4xl` for optimal reading width
- Prose styling for legal text readability
- Consistent header pattern across all legal pages
- Dark theme matching dashboard aesthetic

### Custom Prose Styles

**Add to:** `web/app/globals.css`

```css
/* Legal Document Prose Styles */
.prose-legal {
  @apply text-slate-300 leading-relaxed;
}

.prose-legal h2 {
  @apply text-3xl font-bold text-white mt-12 mb-6 first:mt-0;
}

.prose-legal h3 {
  @apply text-2xl font-semibold text-white mt-8 mb-4;
}

.prose-legal h4 {
  @apply text-xl font-semibold text-slate-200 mt-6 mb-3;
}

.prose-legal p {
  @apply mb-4 text-slate-300;
}

.prose-legal ul, .prose-legal ol {
  @apply mb-6 pl-6;
}

.prose-legal li {
  @apply mb-2 text-slate-300;
}

.prose-legal a {
  @apply text-[#f57a07] hover:text-[#e06a00] underline transition-colors;
}

.prose-legal strong {
  @apply text-white font-semibold;
}

.prose-legal code {
  @apply bg-slate-900 text-slate-300 px-2 py-1 rounded text-sm font-mono;
}

.prose-legal table {
  @apply w-full border-collapse border border-slate-700 my-6;
}

.prose-legal th {
  @apply bg-slate-800 text-white font-semibold p-3 border border-slate-700;
}

.prose-legal td {
  @apply p-3 border border-slate-700 text-slate-300;
}
```

### Page 1: Privacy Policy

**Create:** `web/app/privacy-policy/page.tsx`

```tsx
import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Privacy Policy | Tru8',
  description: 'Tru8 privacy policy - How we collect, use, and protect your data',
};

export default function PrivacyPolicyPage() {
  return (
    <LegalPageLayout
      title="Privacy Policy"
      lastUpdated="22 January 2025"
    >
      <div className="prose-legal">
        {/* Use template from Part 2 of 2025-01-22_LEGAL_COMPLIANCE_MASTER_PLAN.md */}

        <h2>1. Introduction</h2>
        <p>
          Tru8 Ltd ("we," "our," or "us") operates the Tru8 fact-checking platform.
          This Privacy Policy explains how we collect, use, disclose, and safeguard
          your information when you use our services.
        </p>

        <h2>2. Information We Collect</h2>

        <h3>2.1 Account Information</h3>
        <ul>
          <li><strong>Email address:</strong> For authentication and communication</li>
          <li><strong>Name:</strong> Display name for your account</li>
          <li><strong>Authentication data:</strong> Managed by Clerk (our authentication provider)</li>
        </ul>

        <h3>2.2 Usage Data</h3>
        <ul>
          <li><strong>Fact-check submissions:</strong> Text, URLs, images, or videos you submit</li>
          <li><strong>Check history:</strong> Your past fact-checking requests and results</li>
          <li><strong>Credits usage:</strong> Tracking your subscription usage</li>
        </ul>

        <h3>2.3 Payment Information</h3>
        <ul>
          <li><strong>Billing details:</strong> Processed securely by Stripe (we don't store card numbers)</li>
          <li><strong>Subscription status:</strong> Plan type, renewal dates, payment history</li>
        </ul>

        <h3>2.4 Analytics & Error Tracking</h3>
        <ul>
          <li><strong>PostHog:</strong> Anonymous usage analytics (optional, requires cookie consent)</li>
          <li><strong>Sentry:</strong> Error monitoring for bug fixes (anonymized)</li>
        </ul>

        <h2>3. Legal Basis for Processing (UK GDPR)</h2>

        <table>
          <thead>
            <tr>
              <th>Data Type</th>
              <th>Legal Basis</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Account Information</td>
              <td>Contract Performance (Art. 6(1)(b))</td>
            </tr>
            <tr>
              <td>Payment Data</td>
              <td>Contract Performance + Legal Obligation (Art. 6(1)(b)(c))</td>
            </tr>
            <tr>
              <td>Usage Analytics</td>
              <td>Consent (Art. 6(1)(a))</td>
            </tr>
            <tr>
              <td>Service Improvement</td>
              <td>Legitimate Interest (Art. 6(1)(f))</td>
            </tr>
          </tbody>
        </table>

        <h2>4. How We Use Your Information</h2>
        <ul>
          <li>Provide fact-checking services</li>
          <li>Manage your account and subscription</li>
          <li>Process payments</li>
          <li>Send service updates and notifications</li>
          <li>Improve our AI models and service quality</li>
          <li>Detect and prevent fraud</li>
        </ul>

        <h2>5. Third-Party Services</h2>

        <h3>5.1 Authentication</h3>
        <p><strong>Clerk:</strong> Manages user authentication and sessions</p>
        <p>Privacy Policy: <a href="https://clerk.com/privacy" target="_blank" rel="noopener">clerk.com/privacy</a></p>

        <h3>5.2 Payment Processing</h3>
        <p><strong>Stripe:</strong> Handles all payment transactions</p>
        <p>Privacy Policy: <a href="https://stripe.com/privacy" target="_blank" rel="noopener">stripe.com/privacy</a></p>

        <h3>5.3 Analytics (Optional)</h3>
        <p><strong>PostHog:</strong> Product analytics (requires cookie consent)</p>
        <p>Privacy Policy: <a href="https://posthog.com/privacy" target="_blank" rel="noopener">posthog.com/privacy</a></p>

        <h3>5.4 Error Monitoring</h3>
        <p><strong>Sentry:</strong> Application error tracking</p>
        <p>Privacy Policy: <a href="https://sentry.io/privacy" target="_blank" rel="noopener">sentry.io/privacy</a></p>

        <h2>6. Data Retention</h2>
        <ul>
          <li><strong>Account data:</strong> Retained while account is active + 2 years</li>
          <li><strong>Fact-check history:</strong> Retained for 2 years</li>
          <li><strong>Payment records:</strong> Retained for 7 years (UK tax law requirement)</li>
          <li><strong>Error logs:</strong> Retained for 90 days</li>
        </ul>

        <h2>7. Your Rights (UK GDPR)</h2>

        <p>You have the following rights regarding your personal data:</p>

        <h3>7.1 Right to Access</h3>
        <p>Download all your data from Settings → Privacy → Download My Data</p>

        <h3>7.2 Right to Rectification</h3>
        <p>Update your name/email in Settings → Account → Update Profile</p>

        <h3>7.3 Right to Erasure ("Right to be Forgotten")</h3>
        <p>Delete your account in Settings → Account → Delete Account</p>
        <p><em>Note: Payment records retained 7 years for legal compliance</em></p>

        <h3>7.4 Right to Object</h3>
        <p>Opt out of analytics in Settings → Privacy → Cookie Preferences</p>

        <h3>7.5 Right to Data Portability</h3>
        <p>Export your data in JSON format via Settings → Privacy</p>

        <h2>8. Data Security</h2>
        <ul>
          <li>Industry-standard encryption (TLS 1.3)</li>
          <li>Secure authentication via Clerk</li>
          <li>Regular security audits</li>
          <li>Limited employee access to data</li>
        </ul>

        <h2>9. International Transfers</h2>
        <p>
          Our services use cloud infrastructure that may process data outside the UK.
          We ensure adequate safeguards through Standard Contractual Clauses (SCCs)
          approved by the UK ICO.
        </p>

        <h2>10. Cookies</h2>
        <p>
          We use cookies for authentication and analytics. See our{' '}
          <a href="/cookie-policy">Cookie Policy</a> for details.
        </p>
        <p>
          Manage your cookie preferences via our{' '}
          <button
            onClick={() => {
              if (typeof window !== 'undefined' && (window as any).cookieyes) {
                (window as any).cookieyes.showBanner();
              }
            }}
            className="text-[#f57a07] hover:text-[#e06a00] underline"
          >
            Cookie Consent Banner
          </button>
        </p>

        <h2>11. Children's Privacy</h2>
        <p>
          Tru8 is not intended for users under 13. We do not knowingly collect
          data from children.
        </p>

        <h2>12. Changes to This Policy</h2>
        <p>
          We may update this policy periodically. Material changes will be communicated
          via email 30 days before taking effect.
        </p>

        <h2>13. Contact Us</h2>
        <p>
          <strong>Data Controller:</strong> Tru8 Ltd<br />
          <strong>ICO Registration:</strong> [ZA123456]<br />
          <strong>Email:</strong> <a href="mailto:hello@tru8.com">hello@tru8.com</a><br />
          <strong>Address:</strong> [Business Address]
        </p>

        <p>
          To exercise your data rights or submit complaints:<br />
          Email: <a href="mailto:hello@tru8.com">hello@tru8.com</a><br />
          Response time: Within 30 days
        </p>

        <p>
          <strong>Complaints to ICO:</strong><br />
          Information Commissioner's Office<br />
          Wycliffe House, Water Lane<br />
          Wilmslow, Cheshire SK9 5AF<br />
          Website: <a href="https://ico.org.uk" target="_blank" rel="noopener">ico.org.uk</a>
        </p>
      </div>
    </LegalPageLayout>
  );
}
```

### Page 2: Terms of Service

**Create:** `web/app/terms-of-service/page.tsx`

```tsx
import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Terms of Service | Tru8',
  description: 'Tru8 terms of service - User agreements and conditions',
};

export default function TermsOfServicePage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      lastUpdated="22 January 2025"
    >
      <div className="prose-legal">
        <h2>1. Agreement to Terms</h2>
        <p>
          By accessing Tru8, you agree to these Terms of Service. If you disagree,
          do not use our services.
        </p>

        <h2>2. Service Description</h2>
        <p>
          Tru8 provides AI-powered fact-checking services to verify claims using
          publicly available sources. Our service:
        </p>
        <ul>
          <li>Analyzes text, URLs, images, and videos for factual claims</li>
          <li>Searches credible sources for supporting or contradicting evidence</li>
          <li>Provides dated citations and confidence scores</li>
          <li>Offers Quick and Deep verification modes (paid plans)</li>
        </ul>

        <h2>3. User Accounts</h2>

        <h3>3.1 Account Creation</h3>
        <ul>
          <li>You must be 13+ years old</li>
          <li>Provide accurate email and authentication details</li>
          <li>Maintain account security (strong password, 2FA recommended)</li>
        </ul>

        <h3>3.2 Account Responsibilities</h3>
        <ul>
          <li>You are responsible for all activity under your account</li>
          <li>Notify us immediately of unauthorized access</li>
          <li>Do not share login credentials</li>
        </ul>

        <h2>4. Subscription Plans</h2>

        <h3>4.1 Free Plan</h3>
        <ul>
          <li>3 free fact-checks upon signup</li>
          <li>Basic verification features</li>
          <li>Standard support</li>
        </ul>

        <h3>4.2 Professional Plan (£7/month)</h3>
        <ul>
          <li>40 fact-checks per month</li>
          <li>URL verification</li>
          <li>Quick & Deep modes</li>
          <li>Export to PDF/JSON/CSV</li>
          <li>Priority support</li>
        </ul>

        <h3>4.3 Billing</h3>
        <ul>
          <li>Monthly subscriptions auto-renew until cancelled</li>
          <li>Payment processed via Stripe</li>
          <li>Prices in GBP, inclusive of VAT where applicable</li>
          <li>Unused credits do not roll over</li>
        </ul>

        <h2>5. Acceptable Use Policy</h2>

        <h3>5.1 Permitted Use</h3>
        <ul>
          <li>Verify factual claims for personal or professional use</li>
          <li>Research and journalism</li>
          <li>Educational purposes</li>
        </ul>

        <h3>5.2 Prohibited Activities</h3>
        <ul>
          <li>Submitting illegal, defamatory, or harmful content</li>
          <li>Attempting to reverse-engineer or bypass our systems</li>
          <li>Automated abuse or scraping</li>
          <li>Reselling or redistributing our services</li>
          <li>Violating others' intellectual property rights</li>
        </ul>

        <h2>6. Service Limitations & Disclaimers</h2>

        <h3>6.1 AI Limitations</h3>
        <p>
          <strong>IMPORTANT:</strong> Tru8 uses AI and automated systems which may:
        </p>
        <ul>
          <li>Produce inaccurate or incomplete results</li>
          <li>Miss relevant sources or evidence</li>
          <li>Misinterpret context or nuance</li>
        </ul>
        <p>
          <strong>Always verify critical information through independent research.</strong>
        </p>

        <h3>6.2 No Warranty</h3>
        <p>
          Services provided "AS IS" without warranties of:
        </p>
        <ul>
          <li>Accuracy or completeness</li>
          <li>Fitness for particular purpose</li>
          <li>Uninterrupted availability</li>
        </ul>

        <h2>7. Intellectual Property</h2>

        <h3>7.1 Our IP</h3>
        <ul>
          <li>Tru8 platform, code, design, and branding remain our property</li>
          <li>AI models and algorithms are proprietary</li>
        </ul>

        <h3>7.2 Your Content</h3>
        <ul>
          <li>You retain ownership of content you submit</li>
          <li>You grant us license to process content for fact-checking</li>
          <li>We may use anonymized data to improve our services</li>
        </ul>

        <h3>7.3 Fact-Check Results</h3>
        <ul>
          <li>You may use results for personal/professional purposes</li>
          <li>Attribute Tru8 when sharing results publicly</li>
        </ul>

        <h2>8. Liability Limitations</h2>

        <p>
          To the maximum extent permitted by law:
        </p>
        <ul>
          <li>We are not liable for decisions made based on our results</li>
          <li>Total liability limited to fees paid in past 12 months</li>
          <li>No liability for indirect, consequential, or punitive damages</li>
        </ul>

        <h2>9. Indemnification</h2>
        <p>
          You agree to indemnify Tru8 from claims arising from:
        </p>
        <ul>
          <li>Your use of the service</li>
          <li>Violation of these terms</li>
          <li>Content you submit</li>
        </ul>

        <h2>10. Termination</h2>

        <h3>10.1 By You</h3>
        <ul>
          <li>Cancel subscription anytime in Settings</li>
          <li>Delete account in Settings → Account</li>
          <li>No refunds for partial months (see Refund Policy)</li>
        </ul>

        <h3>10.2 By Us</h3>
        <p>We may suspend or terminate accounts for:</p>
        <ul>
          <li>Violation of these terms</li>
          <li>Fraudulent payment activity</li>
          <li>Abuse of service</li>
        </ul>

        <h2>11. Dispute Resolution</h2>

        <h3>11.1 Governing Law</h3>
        <p>These terms are governed by the laws of England and Wales</p>

        <h3>11.2 Jurisdiction</h3>
        <p>Disputes will be resolved in the courts of England and Wales</p>

        <h3>11.3 EU Consumer Rights</h3>
        <p>EU users retain statutory consumer protection rights</p>

        <h2>12. Changes to Terms</h2>
        <p>
          We may update these terms with 30 days notice via email.
          Continued use constitutes acceptance.
        </p>

        <h2>13. Contact</h2>
        <p>
          <strong>Company:</strong> Tru8 Ltd<br />
          <strong>Email:</strong> <a href="mailto:hello@tru8.com">hello@tru8.com</a>
        </p>
      </div>
    </LegalPageLayout>
  );
}
```

### Page 3: Cookie Policy

**Create:** `web/app/cookie-policy/page.tsx`

```tsx
import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Cookie Policy | Tru8',
  description: 'How Tru8 uses cookies and similar technologies',
};

export default function CookiePolicyPage() {
  return (
    <LegalPageLayout
      title="Cookie Policy"
      lastUpdated="22 January 2025"
    >
      <div className="prose-legal">
        <h2>1. What Are Cookies?</h2>
        <p>
          Cookies are small text files stored on your device when you visit websites.
          They help us provide core functionality and improve your experience.
        </p>

        <h2>2. Cookies We Use</h2>

        <h3>2.1 Essential Cookies (No Consent Required)</h3>
        <p>These cookies are necessary for the service to function:</p>

        <table>
          <thead>
            <tr>
              <th>Cookie Name</th>
              <th>Provider</th>
              <th>Purpose</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>__session</code></td>
              <td>Clerk</td>
              <td>User authentication and session management</td>
              <td>7 days</td>
            </tr>
            <tr>
              <td><code>__Host-csrf</code></td>
              <td>Clerk</td>
              <td>Security (CSRF protection)</td>
              <td>Session</td>
            </tr>
            <tr>
              <td><code>cookieyes-consent</code></td>
              <td>CookieYes</td>
              <td>Stores your cookie preferences</td>
              <td>1 year</td>
            </tr>
          </tbody>
        </table>

        <h3>2.2 Analytics Cookies (Requires Consent)</h3>
        <p>Help us understand how users interact with Tru8:</p>

        <table>
          <thead>
            <tr>
              <th>Cookie Name</th>
              <th>Provider</th>
              <th>Purpose</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>ph_*</code></td>
              <td>PostHog</td>
              <td>Anonymous usage analytics, feature tracking</td>
              <td>12 months</td>
            </tr>
            <tr>
              <td><code>ph_phc_*</code></td>
              <td>PostHog</td>
              <td>Session identification</td>
              <td>12 months</td>
            </tr>
          </tbody>
        </table>

        <h3>2.3 Error Tracking Cookies (Requires Consent)</h3>
        <p>Help us identify and fix bugs:</p>

        <table>
          <thead>
            <tr>
              <th>Cookie Name</th>
              <th>Provider</th>
              <th>Purpose</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>sentry-*</code></td>
              <td>Sentry</td>
              <td>Error monitoring and debugging</td>
              <td>90 days</td>
            </tr>
          </tbody>
        </table>

        <h2>3. Managing Cookies</h2>

        <h3>3.1 Cookie Consent Banner</h3>
        <p>
          On your first visit, you'll see our cookie consent banner. Choose:
        </p>
        <ul>
          <li><strong>Accept All:</strong> Essential + Analytics + Error Tracking</li>
          <li><strong>Reject Non-Essential:</strong> Essential cookies only</li>
          <li><strong>Customize:</strong> Select specific cookie categories</li>
        </ul>

        <h3>3.2 Change Preferences Anytime</h3>
        <p>Update your cookie settings by:</p>
        <ul>
          <li>
            Clicking{' '}
            <button
              onClick={() => {
                if (typeof window !== 'undefined' && (window as any).cookieyes) {
                  (window as any).cookieyes.showBanner();
                }
              }}
              className="text-[#f57a07] hover:text-[#e06a00] underline"
            >
              "Cookie Preferences"
            </button>
            {' '}in the footer
          </li>
          <li>Visiting Settings → Privacy → Cookie Preferences (when logged in)</li>
        </ul>

        <h3>3.3 Browser Controls</h3>
        <p>
          You can also manage cookies via your browser settings:
        </p>
        <ul>
          <li><strong>Chrome:</strong> Settings → Privacy → Cookies</li>
          <li><strong>Firefox:</strong> Settings → Privacy & Security → Cookies</li>
          <li><strong>Safari:</strong> Preferences → Privacy → Cookies</li>
          <li><strong>Edge:</strong> Settings → Privacy → Cookies</li>
        </ul>
        <p>
          <em>Note: Blocking essential cookies will prevent you from signing in.</em>
        </p>

        <h2>4. Third-Party Services</h2>

        <p>Our third-party providers may set cookies subject to their policies:</p>
        <ul>
          <li><strong>Clerk:</strong> <a href="https://clerk.com/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
          <li><strong>Stripe:</strong> <a href="https://stripe.com/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
          <li><strong>PostHog:</strong> <a href="https://posthog.com/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
          <li><strong>Sentry:</strong> <a href="https://sentry.io/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
        </ul>

        <h2>5. Do Not Track</h2>
        <p>
          We respect Do Not Track (DNT) browser signals. When DNT is enabled,
          we do not load analytics cookies.
        </p>

        <h2>6. Updates</h2>
        <p>
          We may update this policy to reflect new cookies or technologies.
          Changes will be posted on this page with an updated "Last Updated" date.
        </p>

        <h2>7. Contact</h2>
        <p>
          Questions about our cookie usage?<br />
          Email: <a href="mailto:hello@tru8.com">hello@tru8.com</a>
        </p>
      </div>
    </LegalPageLayout>
  );
}
```

### Page 4: Refund Policy

**Create:** `web/app/refund-policy/page.tsx`

```tsx
import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Refund Policy | Tru8',
  description: 'Tru8 refund policy and cancellation terms',
};

export default function RefundPolicyPage() {
  return (
    <LegalPageLayout
      title="Refund Policy"
      lastUpdated="22 January 2025"
    >
      <div className="prose-legal">
        <h2>1. Subscription Cancellation</h2>
        <p>
          You may cancel your Tru8 Professional subscription at any time:
        </p>
        <ul>
          <li>Go to Settings → Subscription</li>
          <li>Click "Cancel Subscription"</li>
          <li>Access continues until the end of your current billing period</li>
          <li>No charges after cancellation</li>
        </ul>

        <h2>2. Refund Eligibility</h2>

        <h3>2.1 14-Day Money-Back Guarantee</h3>
        <p>
          <strong>NEW CUSTOMERS:</strong> If you're not satisfied within 14 days of your
          first subscription payment, we'll provide a full refund.
        </p>

        <h3>2.2 How to Request</h3>
        <ol>
          <li>Email <a href="mailto:hello@tru8.com">hello@tru8.com</a> within 14 days of payment</li>
          <li>Include your account email and reason for refund</li>
          <li>We'll process your request within 5 business days</li>
          <li>Refunds issued to original payment method within 7-10 business days</li>
        </ol>

        <h2>3. Non-Refundable Situations</h2>
        <p>
          Refunds are <strong>NOT</strong> available for:
        </p>
        <ul>
          <li>Partial months (prorated refunds not offered)</li>
          <li>Renewal payments beyond 14 days</li>
          <li>Unused credits (credits don't roll over)</li>
          <li>Service dissatisfaction after 14-day period</li>
          <li>Account termination due to Terms of Service violations</li>
        </ul>

        <h2>4. Billing Errors</h2>
        <p>
          If you believe you were charged in error:
        </p>
        <ul>
          <li>Contact <a href="mailto:hello@tru8.com">hello@tru8.com</a> immediately</li>
          <li>Provide transaction details (date, amount, payment method)</li>
          <li>We'll investigate and resolve within 7 business days</li>
        </ul>

        <h2>5. EU Consumer Rights</h2>
        <p>
          <strong>EU Customers:</strong> You have the right to withdraw from your subscription
          within 14 days under the EU Consumer Rights Directive, regardless of reason.
        </p>

        <h2>6. Free Plan</h2>
        <p>
          The Free Plan has no charges and therefore no refunds apply. Free credits
          are provided as-is with no cash value.
        </p>

        <h2>7. Contact</h2>
        <p>
          <strong>For refund requests and billing questions:</strong> <a href="mailto:hello@tru8.com">hello@tru8.com</a><br />
          <strong>Response Time:</strong> Within 5 business days
        </p>
      </div>
    </LegalPageLayout>
  );
}
```

### Page 5: Contact

**Create:** `web/app/contact/page.tsx`

```tsx
import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { Mail } from 'lucide-react';

export const metadata = {
  title: 'Contact Us | Tru8',
  description: 'Get in touch with Tru8 for all support and inquiries',
};

export default function ContactPage() {
  return (
    <LegalPageLayout
      title="Contact Us"
      lastUpdated="22 January 2025"
    >
      <div className="prose-legal">
        <p className="text-lg text-slate-200 mb-12">
          We're here to help. Contact us for any inquiry related to your account, privacy, billing, or legal matters.
        </p>

        {/* Single Contact Email */}
        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-8 not-prose mb-12">
          <div className="flex items-start gap-6">
            <div className="bg-[#f57a07] rounded-lg p-4">
              <Mail className="text-white" size={32} />
            </div>
            <div className="flex-1">
              <h3 className="text-2xl font-bold text-white mb-3">Get in Touch</h3>
              <p className="text-slate-300 mb-4">
                For all inquiries including general support, privacy/GDPR requests, billing issues, refunds, and legal matters:
              </p>
              <a
                href="mailto:hello@tru8.com"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-medium transition-colors text-lg"
              >
                <Mail size={20} />
                hello@tru8.com
              </a>
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-slate-400 text-sm">
                    <strong className="text-white">General Inquiries:</strong> 24-48 hours
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">
                    <strong className="text-white">GDPR Requests:</strong> Within 30 days
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <h2>Business Information</h2>
        <div className="bg-slate-900/30 border border-slate-700 rounded-lg p-6 not-prose">
          <p className="text-slate-300 mb-2">
            <strong className="text-white">Company Name:</strong> Tru8 Ltd
          </p>
          <p className="text-slate-300 mb-2">
            <strong className="text-white">ICO Registration:</strong> [ZA123456]
          </p>
          <p className="text-slate-300 mb-2">
            <strong className="text-white">Business Address:</strong> [Full Business Address]
          </p>
          <p className="text-slate-300">
            <strong className="text-white">VAT Number:</strong> [VAT Number if applicable]
          </p>
        </div>

        <h2>Office Hours</h2>
        <p>
          Our support team operates Monday-Friday, 9:00 AM - 5:00 PM GMT (UK time).
        </p>
        <p>
          <em>Urgent privacy requests are monitored outside business hours.</em>
        </p>

        <h2>Complaints Escalation</h2>
        <p>
          If you're not satisfied with our response:
        </p>
        <ol>
          <li>Reply to the original support email requesting escalation</li>
          <li>Your case will be reviewed by a senior team member</li>
          <li>You'll receive a response within 7 business days</li>
        </ol>

        <h2>Regulatory Authority</h2>
        <p>
          For data protection complaints, you may contact the UK Information Commissioner's Office:
        </p>
        <div className="bg-slate-900/30 border border-slate-700 rounded-lg p-6 not-prose">
          <p className="text-slate-300 mb-2">
            <strong className="text-white">ICO</strong>
          </p>
          <p className="text-slate-300 mb-2">
            Wycliffe House, Water Lane<br />
            Wilmslow, Cheshire SK9 5AF
          </p>
          <p className="text-slate-300 mb-2">
            <strong className="text-white">Helpline:</strong> 0303 123 1113
          </p>
          <p className="text-slate-300">
            <strong className="text-white">Website:</strong>{' '}
            <a href="https://ico.org.uk" target="_blank" rel="noopener" className="text-[#f57a07]">
              ico.org.uk
            </a>
          </p>
        </div>
      </div>
    </LegalPageLayout>
  );
}
```

### Implementation Checklist

- [ ] Create shared component: `web/components/legal/legal-page-layout.tsx`
- [ ] Add prose styles to `web/app/globals.css`
- [ ] Create `web/app/privacy-policy/page.tsx`
- [ ] Create `web/app/terms-of-service/page.tsx`
- [ ] Create `web/app/cookie-policy/page.tsx`
- [ ] Create `web/app/refund-policy/page.tsx`
- [ ] Create `web/app/contact/page.tsx`
- [ ] Replace placeholder `[ZA123456]` with actual ICO number
- [ ] Replace `[Business Address]` with actual address
- [ ] Replace `[VAT Number]` with actual VAT number (if applicable)
- [ ] Test all pages render correctly
- [ ] Test responsive layout on mobile
- [ ] Test footer links navigate to correct pages
- [ ] Verify design system compliance (container width, spacing, colors)

**Estimated Time:** 4-6 hours

---

## PART 3: COOKIE CONSENT BANNER INTEGRATION

### CookieYes Setup

**File to Modify:** `web/app/layout.tsx`

### Step 1: Get CookieYes Account ID

1. Sign up at [https://www.cookieyes.com](https://www.cookieyes.com)
2. Create a new website project
3. Select "Next.js" as platform
4. Copy your unique banner ID (format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)

### Step 2: Add CookieYes Script

**Current `web/app/layout.tsx` (Lines 13-30):**
```tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider
      dynamic
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
    >
      <html lang="en" suppressHydrationWarning>
        <body className="bg-[#0f1419] text-white antialiased" suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
```

**Updated `web/app/layout.tsx`:**
```tsx
import Script from 'next/script';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider
      dynamic
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
    >
      <html lang="en" suppressHydrationWarning>
        <head>
          {/* CookieYes Cookie Consent Banner */}
          <Script
            id="cookieyes"
            src={`https://cdn-cookieyes.com/client_data/${process.env.NEXT_PUBLIC_COOKIEYES_ID}/script.js`}
            strategy="beforeInteractive"
          />
        </head>
        <body className="bg-[#0f1419] text-white antialiased" suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
```

### Step 3: Add Environment Variable

**Add to:** `web/.env.local`

```bash
# CookieYes Cookie Consent
NEXT_PUBLIC_COOKIEYES_ID="your-cookieyes-banner-id-here"
```

### Step 4: Configure CookieYes Banner (In Dashboard)

**Cookie Categories to Enable:**
1. **Essential Cookies** (Always Active)
   - Clerk authentication cookies
   - CSRF protection

2. **Analytics Cookies** (Opt-in)
   - PostHog tracking

3. **Performance Cookies** (Opt-in)
   - Sentry error tracking

**Banner Customization:**
- **Primary Color:** `#f57a07` (Tru8 orange)
- **Button Style:** Rounded
- **Position:** Bottom banner
- **Layout:** Horizontal
- **Language:** English (UK)

### Step 5: Conditional PostHog Loading

**File:** `web/app/layout.tsx` (if PostHog is integrated)

```tsx
// Only load PostHog if user has consented
useEffect(() => {
  // Check for CookieYes consent cookie
  const checkConsent = () => {
    if (typeof window !== 'undefined' && (window as any).cookieyes) {
      const consent = (window as any).cookieyes.getConsent();

      if (consent && consent.analytics) {
        // User consented to analytics - load PostHog
        posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
          api_host: 'https://app.posthog.com'
        });
      }
    }
  };

  // Check on mount and when consent changes
  checkConsent();
  window.addEventListener('cookieyes_consent_update', checkConsent);

  return () => window.removeEventListener('cookieyes_consent_update', checkConsent);
}, []);
```

### Implementation Checklist

- [ ] Sign up for CookieYes account
- [ ] Configure banner in CookieYes dashboard
- [ ] Copy banner ID
- [ ] Add `NEXT_PUBLIC_COOKIEYES_ID` to `.env.local`
- [ ] Add Script import to `layout.tsx`
- [ ] Add CookieYes script tag
- [ ] Configure cookie categories in CookieYes dashboard
- [ ] Customize banner colors to match Tru8 branding
- [ ] Test banner appears on first visit
- [ ] Test preferences persist across sessions
- [ ] Test PostHog only loads with consent
- [ ] Test "Cookie Preferences" button in footer reopens banner

**Estimated Time:** 1-2 hours

---

## PART 4: AUTH MODAL - TERMS OF SERVICE ACCEPTANCE

### Current State

**File:** `web/components/auth/auth-modal.tsx`

Currently uses Clerk's `<SignUp>` component directly (Lines 160-179) with no ToS acceptance requirement.

### Required Implementation

Add a Terms of Service acceptance checkbox before allowing signup.

### Option A: Clerk Metadata Approach (Recommended)

**Modify:** `web/components/auth/auth-modal.tsx`

**Add State for ToS (After Line 34):**
```tsx
const [tosAccepted, setTosAccepted] = useState(false);
const [showTosError, setShowTosError] = useState(false);
```

**Wrap SignUp Component (Lines 160-179):**
```tsx
<div
  id="signup-panel"
  role="tabpanel"
  aria-labelledby="signup-tab"
  className="clerk-modal-content"
>
  <SignUp
    appearance={{
      elements: {
        formButtonPrimary:
          'bg-[#f57a07] hover:bg-[#e06a00] text-white font-medium',
        card: 'bg-transparent shadow-none',
        headerTitle: 'text-white',
        headerSubtitle: 'text-slate-300',
        socialButtonsBlockButton:
          'border-slate-700 text-white hover:bg-slate-800',
        formFieldInput:
          'bg-[#0f1419] border-slate-700 text-white focus:border-[#f57a07]',
        formFieldLabel: 'text-slate-300',
        footerActionLink: 'text-[#f57a07] hover:text-[#e06a00]',
      },
    }}
    routing="hash"
    afterSignUpUrl="/dashboard"
    unsafeMetadata={{
      tosAccepted: tosAccepted,
      tosAcceptedAt: tosAccepted ? new Date().toISOString() : null
    }}
  />

  {/* ToS Acceptance Checkbox - Below Clerk Form */}
  <div className="mt-4 pt-4 border-t border-slate-700">
    <label className="flex items-start gap-3 cursor-pointer group">
      <input
        type="checkbox"
        checked={tosAccepted}
        onChange={(e) => {
          setTosAccepted(e.target.checked);
          setShowTosError(false);
        }}
        className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800 text-[#f57a07] focus:ring-[#f57a07] focus:ring-offset-0"
      />
      <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
        I agree to the{' '}
        <a
          href="/terms-of-service"
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[#f57a07] hover:text-[#e06a00] underline"
        >
          Terms of Service
        </a>
        {' '}and{' '}
        <a
          href="/privacy-policy"
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[#f57a07] hover:text-[#e06a00] underline"
        >
          Privacy Policy
        </a>
      </span>
    </label>

    {showTosError && (
      <p className="text-red-400 text-xs mt-2">
        You must accept the Terms of Service to create an account
      </p>
    )}
  </div>
</div>
```

**Add Form Submission Intercept:**

Unfortunately, Clerk doesn't provide a direct hook to prevent submission. The metadata approach records acceptance, but to block submission, we need Option B.

### Option B: Custom Signup Flow (More Control)

**Alternative:** Build custom signup form using Clerk's `useSignUp()` hook for full control over validation.

**This is more complex and should only be used if Option A's metadata approach is insufficient for legal requirements.**

### Recommended Approach

**Use Option A** (metadata) with clear UI messaging that signup button won't work until ToS is accepted. Add JavaScript to disable Clerk's submit button until ToS checkbox is checked:

**Add useEffect:**
```tsx
useEffect(() => {
  // Disable Clerk signup button until ToS accepted
  if (activeTab === 'signup') {
    const clerkButton = document.querySelector('[data-clerk-element="formButtonPrimary"]') as HTMLButtonElement;
    if (clerkButton) {
      clerkButton.disabled = !tosAccepted;
      clerkButton.style.opacity = tosAccepted ? '1' : '0.5';
      clerkButton.style.cursor = tosAccepted ? 'pointer' : 'not-allowed';
    }
  }
}, [activeTab, tosAccepted]);
```

### Implementation Checklist

- [ ] Add `tosAccepted` state to auth-modal.tsx
- [ ] Add `showTosError` state
- [ ] Add ToS checkbox below SignUp component
- [ ] Add links to Terms and Privacy Policy (open in new tab)
- [ ] Add useEffect to disable signup button until ToS checked
- [ ] Store ToS acceptance in Clerk unsafeMetadata
- [ ] Test checkbox prevents signup when unchecked
- [ ] Test checkbox allows signup when checked
- [ ] Test links open in new tabs
- [ ] Verify ToS acceptance is recorded in Clerk metadata

**Estimated Time:** 1-2 hours

---

## PART 5: SETTINGS - PRIVACY TAB

### Current State

**File:** `web/app/dashboard/settings/page.tsx`

**Current Tabs (Line 28):**
```tsx
['account', 'subscription', 'notifications']
```

**Files to Modify:**
1. `web/app/dashboard/settings/components/settings-tabs.tsx` - Add Privacy tab
2. `web/app/dashboard/settings/page.tsx` - Handle privacy tab routing
3. Create: `web/app/dashboard/settings/components/privacy-tab.tsx` - New component

### Step 1: Add Privacy Tab to Settings Tabs

**File:** `web/app/dashboard/settings/components/settings-tabs.tsx`

**Update tabs array (Lines 9-13):**
```tsx
const tabs = [
  { id: 'account', label: 'ACCOUNT' },
  { id: 'subscription', label: 'SUBSCRIPTION' },
  { id: 'privacy', label: 'PRIVACY' },          // ← NEW
  { id: 'notifications', label: 'NOTIFICATIONS' },
];
```

### Step 2: Update Settings Page Routing

**File:** `web/app/dashboard/settings/page.tsx`

**Update tab validation (Line 28):**
```tsx
if (tab && ['account', 'subscription', 'privacy', 'notifications'].includes(tab)) {
  setActiveTab(tab);
}
```

**Add Privacy Tab Import (Line 11):**
```tsx
import { PrivacyTab } from './components/privacy-tab';
```

**Add Privacy Tab Render (After Line 134):**
```tsx
{activeTab === 'privacy' && <PrivacyTab />}
```

### Step 3: Create Privacy Tab Component

**Create:** `web/app/dashboard/settings/components/privacy-tab.tsx`

```tsx
'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Download, Cookie, Shield, FileText } from 'lucide-react';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export function PrivacyTab() {
  const { getToken } = useAuth();
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleDataExport = async () => {
    setIsExporting(true);
    setExportError(null);

    try {
      const token = await getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Call data export endpoint
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/export-data`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to export data');
      }

      const data = await response.json();

      // Create downloadable JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `tru8-data-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Data export failed:', error);
      setExportError('Failed to export data. Please try again or contact support.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleCookiePreferences = () => {
    // Open CookieYes banner
    if (typeof window !== 'undefined' && (window as any).cookieyes) {
      (window as any).cookieyes.showBanner();
    }
  };

  return (
    <div className="space-y-8">
      {/* Data Export Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Download size={20} />
          Download Your Data
        </h3>

        <div className="space-y-4">
          <p className="text-slate-300 text-sm">
            Export all your personal data in JSON format. This includes your account
            information, fact-check history, and subscription details.
          </p>

          {exportError && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
              <p className="text-red-400 text-sm">{exportError}</p>
            </div>
          )}

          <button
            onClick={handleDataExport}
            disabled={isExporting}
            className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? 'Exporting...' : 'Download My Data (JSON)'}
          </button>

          <p className="text-xs text-slate-400">
            <strong>GDPR Right to Data Portability:</strong> You can request your data at
            any time. Data is provided in machine-readable JSON format.
          </p>
        </div>
      </section>

      {/* Cookie Preferences Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Cookie size={20} />
          Cookie Preferences
        </h3>

        <div className="space-y-4">
          <p className="text-slate-300 text-sm">
            Manage your cookie consent preferences for analytics and performance tracking.
          </p>

          <button
            onClick={handleCookiePreferences}
            className="w-full px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
          >
            Manage Cookie Preferences
          </button>

          <p className="text-xs text-slate-400">
            Learn more in our <Link href="/cookie-policy" className="text-[#f57a07] hover:text-[#e06a00] underline">Cookie Policy</Link>
          </p>
        </div>
      </section>

      {/* Privacy Policies Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Shield size={20} />
          Privacy & Legal
        </h3>

        <div className="space-y-3">
          <Link
            href="/privacy-policy"
            className="flex items-center justify-between p-4 bg-slate-900/50 hover:bg-slate-900 border border-slate-700 rounded-lg transition-colors group"
          >
            <div className="flex items-center gap-3">
              <FileText size={18} className="text-slate-400 group-hover:text-[#f57a07]" />
              <span className="text-slate-300 group-hover:text-white font-medium">
                Privacy Policy
              </span>
            </div>
            <span className="text-slate-500 group-hover:text-slate-400">→</span>
          </Link>

          <Link
            href="/terms-of-service"
            className="flex items-center justify-between p-4 bg-slate-900/50 hover:bg-slate-900 border border-slate-700 rounded-lg transition-colors group"
          >
            <div className="flex items-center gap-3">
              <FileText size={18} className="text-slate-400 group-hover:text-[#f57a07]" />
              <span className="text-slate-300 group-hover:text-white font-medium">
                Terms of Service
              </span>
            </div>
            <span className="text-slate-500 group-hover:text-slate-400">→</span>
          </Link>

          <Link
            href="/cookie-policy"
            className="flex items-center justify-between p-4 bg-slate-900/50 hover:bg-slate-900 border border-slate-700 rounded-lg transition-colors group"
          >
            <div className="flex items-center gap-3">
              <Cookie size={18} className="text-slate-400 group-hover:text-[#f57a07]" />
              <span className="text-slate-300 group-hover:text-white font-medium">
                Cookie Policy
              </span>
            </div>
            <span className="text-slate-500 group-hover:text-slate-400">→</span>
          </Link>
        </div>
      </section>

      {/* Contact for Privacy Requests */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">Privacy Questions?</h3>
        <p className="text-slate-300 text-sm mb-4">
          For privacy-related inquiries or to exercise your data rights, contact our
          privacy team:
        </p>
        <a
          href="mailto:hello@tru8.com"
          className="inline-flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
        >
          Email: hello@tru8.com
        </a>
        <p className="text-xs text-slate-400 mt-3">
          We respond to all privacy requests within 30 days as required by UK GDPR.
        </p>
      </section>
    </div>
  );
}
```

### Step 4: Create Backend Data Export Endpoint

**Note:** This requires backend implementation (not covered in this UI guide, see legal compliance plan Part 5.1)

**Endpoint:** `GET /api/v1/users/export-data`

**Expected Response:**
```json
{
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2025-01-15T10:30:00Z",
    "credits": 40
  },
  "checks": [
    {
      "id": "check_456",
      "input_text": "Claim text...",
      "verdict": "supported",
      "created_at": "2025-01-20T14:20:00Z"
    }
  ],
  "subscription": {
    "plan": "professional",
    "status": "active",
    "current_period_end": "2025-02-15T00:00:00Z"
  }
}
```

### Implementation Checklist

- [ ] Add Privacy tab to settings-tabs.tsx
- [ ] Update tab validation in settings/page.tsx
- [ ] Create privacy-tab.tsx component
- [ ] Add data export button with download functionality
- [ ] Add cookie preferences button (calls CookieYes API)
- [ ] Add links to legal policies
- [ ] Add privacy contact email
- [ ] Create backend data export endpoint (see legal plan)
- [ ] Test data export downloads JSON file
- [ ] Test cookie preferences button opens banner
- [ ] Test policy links navigate correctly
- [ ] Verify Privacy tab accessible from Settings

**Estimated Time:** 2-3 hours (frontend only, backend endpoint separate)

---

## PART 6: MOBILE APP CONSIDERATIONS (POST-WEB LAUNCH)

**Status:** Not required for initial web launch (planned 3 months after web release)

### Future Requirements

When mobile app is released, the following screens will need to be created in React Native:

1. **Legal Document Screens** (`mobile/app/(legal)/`)
   - `privacy-policy.tsx`
   - `terms-of-service.tsx`
   - `cookie-policy.tsx`
   - `refund-policy.tsx`
   - `contact.tsx`

2. **Settings Privacy Section** (`mobile/app/(tabs)/settings/`)
   - Privacy tab with data export
   - Cookie preferences (mobile-specific implementation)
   - Links to legal documents

3. **Onboarding ToS Acceptance**
   - Terms acceptance before account creation
   - Link to view full terms in WebView or native screen

### Design Considerations

- **React Native Components:** Use React Native's `<ScrollView>`, `<Text>`, `<Pressable>`
- **WebView Option:** Consider rendering legal HTML in WebView for easier updates
- **Native Styling:** Match Tru8 design system (dark theme, orange accents)
- **Deep Links:** Handle `/privacy-policy` deep links from emails

### Implementation Timeline

- **Q2 2025:** Begin mobile legal UI implementation
- **Pre-Release:** Submit app stores with all legal compliance in place

---

## PART 7: IMPLEMENTATION TIMELINE

### Week 1: Foundation (Days 1-3)

**Day 1:** Legal Pages
- [ ] Create `LegalPageLayout` component
- [ ] Add prose styles to globals.css
- [ ] Create Privacy Policy page
- [ ] Create Terms of Service page

**Day 2:** More Legal Pages + Footer
- [ ] Create Cookie Policy page
- [ ] Create Refund Policy page
- [ ] Create Contact page
- [ ] Update footer component with correct routes

**Day 3:** Cookie Consent
- [ ] Set up CookieYes account
- [ ] Configure banner in dashboard
- [ ] Add script to layout.tsx
- [ ] Test banner functionality

### Week 2: Auth & Settings (Days 4-6)

**Day 4:** Auth Modal ToS
- [ ] Add ToS checkbox to auth-modal.tsx
- [ ] Add metadata tracking
- [ ] Add button disable logic
- [ ] Test signup flow

**Day 5:** Settings Privacy Tab
- [ ] Add Privacy tab to settings
- [ ] Create privacy-tab.tsx component
- [ ] Add cookie preferences button
- [ ] Add policy links

**Day 6:** Backend Integration
- [ ] Create data export endpoint (backend)
- [ ] Test data export from frontend
- [ ] Final testing and bug fixes

### Week 3: Polish & Launch (Days 7-8)

**Day 7:** QA & Testing
- [ ] Test all legal pages on desktop/mobile
- [ ] Test footer links work everywhere
- [ ] Test cookie banner preferences persist
- [ ] Test ToS acceptance in signup flow
- [ ] Test data export downloads correctly

**Day 8:** Documentation & Deployment
- [ ] Update README with legal implementation notes
- [ ] Document cookie consent setup
- [ ] Deploy to production
- [ ] Monitor for issues

---

## PART 8: TESTING CHECKLIST

### Legal Pages Testing

- [ ] All 5 legal pages load without errors
- [ ] Navigation back button works
- [ ] Footer "Contact Us" buttons work
- [ ] Responsive layout on mobile (320px, 768px, 1024px)
- [ ] Links open in new tabs where specified
- [ ] Prose styles render correctly
- [ ] Container max-width is 1024px
- [ ] Dark theme colors match design system

### Footer Testing

- [ ] Footer appears on all pages (marketing + dashboard)
- [ ] All legal links navigate to correct pages
- [ ] Cookie Preferences button opens CookieYes banner
- [ ] ICO registration number displays correctly
- [ ] Responsive grid works on mobile

### Cookie Consent Testing

- [ ] Banner appears on first visit
- [ ] Banner doesn't appear on subsequent visits (if choice made)
- [ ] "Accept All" enables all cookies
- [ ] "Reject Non-Essential" only allows essential cookies
- [ ] Preferences persist across browser sessions
- [ ] PostHog doesn't load without consent
- [ ] Sentry doesn't load without consent
- [ ] Cookie Preferences button reopens banner

### Auth Modal Testing

- [ ] ToS checkbox appears on signup tab
- [ ] Signup button disabled when checkbox unchecked
- [ ] Signup button enabled when checkbox checked
- [ ] Terms link opens in new tab
- [ ] Privacy Policy link opens in new tab
- [ ] ToS acceptance stored in Clerk metadata
- [ ] Error shows if user tries to submit without accepting

### Settings Privacy Tab Testing

- [ ] Privacy tab appears in settings
- [ ] Tab routing works (/dashboard/settings?tab=privacy)
- [ ] Data export button downloads JSON file
- [ ] JSON file contains user data, checks, subscription
- [ ] Cookie preferences button opens CookieYes banner
- [ ] Policy links navigate correctly
- [ ] Privacy email link works (mailto:)

### Cross-Browser Testing

Test on:
- [ ] Chrome (Windows/Mac)
- [ ] Firefox (Windows/Mac)
- [ ] Safari (Mac/iOS)
- [ ] Edge (Windows)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

---

## PART 9: FINAL IMPLEMENTATION NOTES

### Environment Variables Required

Add to `web/.env.local`:

```bash
# CookieYes Cookie Consent
NEXT_PUBLIC_COOKIEYES_ID="your-banner-id-here"

# API URL for data export
NEXT_PUBLIC_API_URL="http://localhost:8000"  # Development
# NEXT_PUBLIC_API_URL="https://api.tru8.com"  # Production
```

### Placeholders to Replace

Before going live, replace these placeholders in legal pages:

- `[ZA123456]` → Actual ICO registration number
- `[Business Address]` → Actual business address
- `[VAT Number]` → Actual VAT number (if applicable)
- `hello@tru8.com` → Ensure this email address is created and monitored

### Email Address to Create

Set up this email address before launch:

- `hello@tru8.com` - Single contact email for all inquiries (general support, privacy/GDPR requests, legal inquiries, billing/payment issues, and refund requests)

### Dependencies

No new npm packages required (uses existing):
- `@clerk/nextjs` - Already installed for auth
- `next/script` - Built into Next.js
- `lucide-react` - Already installed for icons

### Backend Requirements

Backend endpoints needed (see legal compliance plan for full specs):

1. `GET /api/v1/users/export-data` - GDPR data export
2. Existing: `DELETE /api/v1/users/{user_id}` - Account deletion

---

## PART 10: SUCCESS CRITERIA

### Launch Readiness Checklist

- [ ] All 5 legal pages live and accessible
- [ ] Footer links updated on all pages
- [ ] Cookie consent banner functional
- [ ] ToS acceptance in signup flow
- [ ] Privacy tab in settings with data export
- [ ] All email addresses created and monitored
- [ ] ICO registration completed and number added
- [ ] CookieYes free tier account active
- [ ] PostHog/Sentry only load with consent
- [ ] Mobile responsive design tested
- [ ] Cross-browser compatibility verified

### Compliance Verification

- [ ] Privacy Policy includes all GDPR disclosures
- [ ] Terms of Service covers all service aspects
- [ ] Cookie Policy lists all cookies accurately
- [ ] Refund Policy matches actual refund process
- [ ] Contact page has all required information
- [ ] ToS acceptance recorded in Clerk metadata
- [ ] Data export works and includes all user data
- [ ] Cookie preferences persist correctly

---

## APPENDIX: Component File Tree

```
web/
├── app/
│   ├── layout.tsx                          # ✏️ MODIFY - Add CookieYes script
│   ├── privacy-policy/
│   │   └── page.tsx                        # ✨ CREATE
│   ├── terms-of-service/
│   │   └── page.tsx                        # ✨ CREATE
│   ├── cookie-policy/
│   │   └── page.tsx                        # ✨ CREATE
│   ├── refund-policy/
│   │   └── page.tsx                        # ✨ CREATE
│   ├── contact/
│   │   └── page.tsx                        # ✨ CREATE
│   ├── dashboard/
│   │   └── settings/
│   │       ├── page.tsx                    # ✏️ MODIFY - Add privacy tab routing
│   │       └── components/
│   │           ├── settings-tabs.tsx       # ✏️ MODIFY - Add privacy tab
│   │           └── privacy-tab.tsx         # ✨ CREATE
│   └── globals.css                         # ✏️ MODIFY - Add prose-legal styles
├── components/
│   ├── auth/
│   │   └── auth-modal.tsx                  # ✏️ MODIFY - Add ToS checkbox
│   ├── layout/
│   │   └── footer.tsx                      # ✏️ MODIFY - Update legal links
│   └── legal/
│       └── legal-page-layout.tsx           # ✨ CREATE
└── .env.local                              # ✏️ MODIFY - Add COOKIEYES_ID

Legend:
✨ CREATE - New file to create
✏️ MODIFY - Existing file to modify
```

---

**Document End** | For questions, contact: hello@tru8.com
