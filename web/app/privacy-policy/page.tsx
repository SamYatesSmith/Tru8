import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { CookiePreferencesButton } from '@/components/legal/cookie-preferences-button';
import { LEGAL, ICO } from '@/lib/legal';

export const metadata = {
  title: 'Privacy Policy',
  description: 'How Tru8 collects, uses, and protects your data. GDPR-compliant privacy policy.',
  alternates: { canonical: '/privacy-policy' },
};

export default function PrivacyPolicyPage() {
  return (
    <LegalPageLayout
      title="Privacy Policy"
      lastUpdated="27 May 2026"
    >
      <div className="prose-legal">
        <h2>1. Introduction</h2>
        <p>
          {LEGAL.companyName} (company number {LEGAL.companyNumber}), trading as {LEGAL.tradingName} (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) operates the Tru8 evidence research platform.
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
          <li><strong>Research submissions:</strong> Text, URLs, images, or videos you submit</li>
          <li><strong>Check history:</strong> Your past research requests and results</li>
          <li><strong>Credits usage:</strong> Tracking your subscription usage</li>
        </ul>

        <h3>2.3 Payment Information</h3>
        <ul>
          <li><strong>Billing details:</strong> Processed securely by Stripe (we don&apos;t store card numbers)</li>
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
          <li>Provide evidence research services</li>
          <li>Manage your account and subscription</li>
          <li>Process payments</li>
          <li>Send service updates and notifications</li>
          <li>Improve our evidence research service</li>
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

        <h3>5.5 AI Processing</h3>
        <p><strong>Google AI (Gemini):</strong> Processes submitted claims and evidence for classification, mapping, and analysis</p>
        <p>Privacy Policy: <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">policies.google.com/privacy</a></p>
        <p>
          When you submit content for research, it is sent to Google&apos;s Gemini API for
          processing. Google acts as a data processor under our instructions. Submitted
          content is used solely to generate your evidence research results and is not
          used by Google to train their models.
        </p>

        <h2>6. Data Retention</h2>
        <ul>
          <li><strong>Account data:</strong> Retained while account is active + 2 years</li>
          <li><strong>Analysis history:</strong> Retained for 2 years</li>
          <li><strong>Payment records:</strong> Retained for 7 years (UK tax law requirement)</li>
          <li><strong>Error logs:</strong> Retained for 90 days</li>
        </ul>

        <h2>7. Your Rights (UK GDPR)</h2>

        <p>You have the following rights regarding your personal data:</p>

        <h3>7.1 Right to Access</h3>
        <p>Email <a href="mailto:hello@trueight.com">hello@trueight.com</a> to request a data export. We will respond within 30 days.</p>

        <h3>7.2 Right to Rectification</h3>
        <p>Update your name/email in Settings → Account → Update Profile</p>

        <h3>7.3 Right to Erasure (&quot;Right to be Forgotten&quot;)</h3>
        <p>Delete your account in Settings → Account → Delete Account</p>
        <p><em>Note: Payment records retained 7 years for legal compliance</em></p>

        <h3>7.4 Right to Object</h3>
        <p>Opt out of analytics via the Cookie Preferences button in the website footer</p>

        <h3>7.5 Right to Data Portability</h3>
        <p>Email <a href="mailto:hello@trueight.com">hello@trueight.com</a> to request a data export in JSON format</p>

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
          <CookiePreferencesButton />
        </p>

        <h2>11. Children&apos;s Privacy</h2>
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
          <strong>Data Controller:</strong> {LEGAL.companyName} (company number {LEGAL.companyNumber}), trading as {LEGAL.tradingName}<br />
          <strong>Email:</strong> <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a><br />
          <strong>Location:</strong> {LEGAL.location}
        </p>

        <p>
          To exercise your data rights or submit complaints:<br />
          Email: <a href="mailto:hello@trueight.com">hello@trueight.com</a><br />
          Response time: Within 30 days
        </p>

        <p>
          <strong>Complaints to ICO:</strong><br />
          {ICO.name}<br />
          {ICO.addressLines[0]}<br />
          {ICO.addressLines[1]}<br />
          Website: <a href={ICO.websiteUrl} target="_blank" rel="noopener">{ICO.website}</a>
        </p>
        <p>
          <strong>Our ICO registration:</strong> {LEGAL.icoRegistration}
        </p>

        <h2>14. Cross-User Consensus Analysis</h2>
        <p>
          When multiple independent users research the same or similar claims, we may
          aggregate and anonymise evidence data to compute consensus metrics. This
          analysis uses only aggregated counts and classifications — no individual
          user&apos;s evidence set is shared with other users. Consensus data helps
          indicate the stability and convergence of the evidence landscape across
          independent research sessions.
        </p>
      </div>
    </LegalPageLayout>
  );
}
