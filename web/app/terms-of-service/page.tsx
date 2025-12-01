import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Terms of Service | Tru8',
  description: 'Tru8 terms of service - User agreements and conditions',
};

export default function TermsOfServicePage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      lastUpdated="21 November 2025"
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
          <li>Violating others&apos; intellectual property rights</li>
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
          Services provided &quot;AS IS&quot; without warranties of:
        </p>
        <ul>
          <li>Accuracy or completeness</li>
          <li>Fitness for particular purpose</li>
          <li>Uninterrupted availability</li>
        </ul>

        <h3>6.3 Source Credibility Scoring</h3>
        <p>
          Tru8 assigns credibility scores to sources based on:
        </p>
        <ul>
          <li>Independent media research and academic studies</li>
          <li>Fact-checking track records (IFCN signatory assessments)</li>
          <li>Journalistic standards and editorial processes</li>
        </ul>
        <p>
          These scores:
        </p>
        <ul>
          <li>Reflect general reliability patterns, not quality of individual articles</li>
          <li>Are used to weight evidence, not to exclude sources entirely</li>
          <li>Do not constitute Tru8&apos;s endorsement or criticism of any publication</li>
          <li>May differ from other rating systems or personal assessments</li>
        </ul>
        <p>
          Source ratings are editorial judgments informed by third-party research
          and are subject to periodic review and update.
        </p>

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
