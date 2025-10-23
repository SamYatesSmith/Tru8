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
