import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { CookiePreferencesButton } from '@/components/legal/cookie-preferences-button';

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
          Tru8 Ltd (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) operates the Tru8 fact-checking platform.
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

        <h3>7.3 Right to Erasure (&quot;Right to be Forgotten&quot;)</h3>
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
          Information Commissioner&apos;s Office<br />
          Wycliffe House, Water Lane<br />
          Wilmslow, Cheshire SK9 5AF<br />
          Website: <a href="https://ico.org.uk" target="_blank" rel="noopener">ico.org.uk</a>
        </p>
      </div>
    </LegalPageLayout>
  );
}
