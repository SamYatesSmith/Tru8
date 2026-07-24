import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { LEGAL } from '@/lib/legal';

export const metadata = {
  title: 'Terms of Service',
  description: 'Tru8 terms of service — user agreements, acceptable use, and conditions for using the evidence research platform.',
  alternates: { canonical: '/terms-of-service' },
};

export default function TermsOfServicePage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      lastUpdated="13 July 2026"
    >
      <div className="prose-legal">
        <h2>1. Agreement to Terms</h2>
        <p>
          By accessing Tru8, you agree to these Terms of Service. If you disagree,
          do not use our services.
        </p>

        <h2>2. Service Description</h2>
        <p>
          <strong>BETA STATUS:</strong> Tru8 is currently in public beta. Features,
          pricing, and availability may change as we continue development. By using
          our service during beta, you acknowledge that results may vary and help
          us improve the platform.
        </p>
        <p>
          Tru8 provides AI-powered evidence research services that cross-reference
          claims against publicly available sources. Our service:
        </p>
        <ul>
          <li>Extracts claims from text, URLs, images, and videos</li>
          <li>Searches publicly available sources for relevant evidence</li>
          <li>Provides dated citations and evidence references</li>
          <li>Organises evidence into a classified landscape — we organise; you decide</li>
          <li>Provides a developer API and MCP server for programmatic and AI agent access</li>
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

        <h2>4. Plans and Pricing</h2>

        <h3>4.1 Free Trial</h3>
        <ul>
          <li>3 free checks on signup</li>
          <li>Full analysis features and all six views</li>
          <li>Standard support</li>
        </ul>

        <h3>4.2 Tru8 Console (£20/month or £200/year)</h3>
        <ul>
          <li>200 checks per month</li>
          <li>All source types and all six views</li>
          <li>Signed evidence records with a receipt for every exclusion; export to PDF, CSV and JSON</li>
          <li>Targeted re-search and a personal API allowance</li>
          <li>The annual option (£200/year) is billed once a year</li>
        </ul>

        <h3>4.3 Teams (from £75/month)</h3>
        <ul>
          <li>For newsrooms and research teams: shared access and volume pricing, arranged with us</li>
          <li>Direct support</li>
          <li>Contact us for a quote</li>
        </ul>

        <h3>4.4 API and Agent Access (metered, pay-as-you-go)</h3>
        <ul>
          <li>Available on any account using an API key, independent of any subscription</li>
          <li>Billed per call from a prepaid balance in GBP, from £0.02 per call up to £0.15 for a full record</li>
          <li>Includes the MCP server and the Agent Commerce Gateway tiers (lookup, consensus, quick, full)</li>
          <li>Prepaid credit is bought in packs and drawn down as you make calls</li>
        </ul>

        <h3>4.5 Legacy Plans</h3>
        <ul>
          <li>Our Starter and Professional plans are closed to new subscriptions</li>
          <li>Existing subscribers remain on their current plan and price until they change plan or cancel</li>
        </ul>

        <h3>4.6 Billing</h3>
        <ul>
          <li>Subscriptions auto-renew (monthly or annually) until cancelled</li>
          <li>Payment is processed via Stripe</li>
          <li>Prices are in GBP. Tru8 is not currently VAT-registered, so no VAT is added; if we become VAT-registered, we will give notice before applying VAT</li>
          <li>Prepaid API credit does not expire, is usable only for Tru8 services, and is not exchangeable for cash. It is charged per call as it is used, and is non-refundable except where required by law</li>
          <li>Unused monthly checks do not roll over</li>
        </ul>

        <h2>5. Acceptable Use Policy</h2>

        <h3>5.1 Permitted Use</h3>
        <ul>
          <li>Research claims for personal or professional use</li>
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

        <h2>6. API & Developer Usage</h2>

        <h3>6.1 API Access</h3>
        <ul>
          <li>API access is a separate metered product, available on any account using an API key — a Console subscription is not required</li>
          <li>Each API key is tied to a single account and carries your identity and usage quota</li>
          <li>You are responsible for all activity performed using your API key</li>
          <li>API keys must be stored securely — never in client-side code, version control, or logs</li>
          <li>Compromised keys must be revoked immediately via dashboard settings</li>
        </ul>

        <h3>6.2 Rate Limits & Fair Use</h3>
        <ul>
          <li>API requests are subject to rate limits applied per API key</li>
          <li>Concurrent request limits apply per API key (currently 3 simultaneous requests)</li>
          <li>Requests exceeding rate limits will receive HTTP 429 responses</li>
          <li>Sustained high-volume usage may be better served by a Teams agreement</li>
        </ul>

        <h3>6.3 Agent & Automated Usage</h3>
        <ul>
          <li>AI agents and automated systems may use the API under the same terms as human users</li>
          <li>Agent usage via MCP (Model Context Protocol) or direct API calls is permitted within plan limits</li>
          <li>The Agent Commerce Gateway provides pay-per-use access for agents via prepaid credit, without a subscription</li>
          <li>Agent operators are responsible for their agents&apos; compliance with these terms</li>
        </ul>

        <h3>6.4 Data Retention & Privacy</h3>
        <ul>
          <li>Analysis results are retained for the duration of your subscription</li>
          <li>API responses may be cached server-side to improve performance and reduce costs</li>
          <li>Cached results may be served to subsequent requests for the same claim (lookup tier)</li>
          <li>You may request deletion of your data in accordance with our Privacy Policy</li>
          <li>Evidence snippets displayed are extracted from publicly available sources and attributed with URLs</li>
        </ul>

        <h3>6.5 Redistribution</h3>
        <ul>
          <li>You may incorporate Tru8 results into your own applications and services</li>
          <li>Attribution to Tru8 is required when displaying results to end users</li>
          <li>You may not resell raw API access or create a competing evidence research service using Tru8 data</li>
          <li>Signed manifests and verification URLs may be shared publicly to demonstrate evidence provenance</li>
        </ul>

        <h2>7. Service Limitations & Disclaimers</h2>

        <h3>7.1 AI Limitations</h3>
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

        <h3>7.2 No Warranty</h3>
        <p>
          Services provided &quot;AS IS&quot; without warranties of:
        </p>
        <ul>
          <li>Accuracy or completeness</li>
          <li>Fitness for particular purpose</li>
          <li>Uninterrupted availability</li>
        </ul>

        <h3>7.3 Source Classification</h3>
        <p>
          Tru8 classifies sources by tier (primary, reporting, commentary) and
          type (data, official statement, news reporting, analysis, opinion, academic)
          to help you understand the evidence landscape. These classifications:
        </p>
        <ul>
          <li>Are descriptive labels, not quality judgments</li>
          <li>Help organise evidence by origin and function</li>
          <li>Do not constitute Tru8&apos;s endorsement or criticism of any publication</li>
          <li>Are subject to periodic review and update</li>
        </ul>
        <p>
          Every source excluded from the evidence display includes a receipt
          explaining the reason for exclusion (e.g. duplicate content, insufficient
          text, or irrelevance to the claim under analysis).
        </p>

        <h2>8. Intellectual Property</h2>

        <h3>8.1 Our IP</h3>
        <ul>
          <li>Tru8 platform, code, design, and branding remain our property</li>
          <li>AI models and algorithms are proprietary</li>
        </ul>

        <h3>8.2 Your Content</h3>
        <ul>
          <li>You retain ownership of content you submit</li>
          <li>You grant us a licence to process content for analysis</li>
          <li>We may use anonymized data to improve our services</li>
        </ul>

        <h3>8.3 Analysis Results</h3>
        <ul>
          <li>You may use results for personal/professional purposes</li>
          <li>Attribute Tru8 when sharing results publicly</li>
        </ul>

        <h2>9. Liability Limitations</h2>

        <p>
          To the maximum extent permitted by law:
        </p>
        <ul>
          <li>We are not liable for decisions made based on our results</li>
          <li>Total liability limited to fees paid in past 12 months</li>
          <li>No liability for indirect, consequential, or punitive damages</li>
        </ul>

        <h2>10. Indemnification</h2>
        <p>
          You agree to indemnify Tru8 from claims arising from:
        </p>
        <ul>
          <li>Your use of the service</li>
          <li>Violation of these terms</li>
          <li>Content you submit</li>
        </ul>

        <h2>11. Termination</h2>

        <h3>11.1 By You</h3>
        <ul>
          <li>Cancel subscription anytime in Settings</li>
          <li>Delete account in Settings → Account</li>
          <li>No refunds for partial months (see Refund Policy)</li>
        </ul>

        <h3>11.2 By Us</h3>
        <p>We may suspend or terminate accounts for:</p>
        <ul>
          <li>Violation of these terms</li>
          <li>Fraudulent payment activity</li>
          <li>Abuse of service</li>
        </ul>

        <h2>12. Dispute Resolution</h2>

        <h3>12.1 Governing Law</h3>
        <p>These terms are governed by the laws of England and Wales</p>

        <h3>12.2 Jurisdiction</h3>
        <p>Disputes will be resolved in the courts of England and Wales</p>

        <h3>12.3 EU Consumer Rights</h3>
        <p>EU users retain statutory consumer protection rights</p>

        <h2>13. Changes to Terms</h2>
        <p>
          We may update these terms with 30 days notice via email.
          Continued use constitutes acceptance.
        </p>

        <h2>14. Contact</h2>
        <p>
          <strong>Company:</strong> {LEGAL.companyName} (company number {LEGAL.companyNumber}), trading as {LEGAL.tradingName}<br />
          <strong>Email:</strong> <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a><br />
          <strong>ICO registration:</strong> {LEGAL.icoRegistration}
        </p>
      </div>
    </LegalPageLayout>
  );
}
