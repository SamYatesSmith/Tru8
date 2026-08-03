import { LegalPageLayout } from '@/components/legal/legal-page-layout';

export const metadata = {
  title: 'Refund Policy | Tru8',
  description: 'Tru8 refund policy and cancellation terms',
  alternates: { canonical: '/refund-policy' },
};

export default function RefundPolicyPage() {
  return (
    <LegalPageLayout
      title="Refund Policy"
      lastUpdated="13 July 2026"
    >
      <div className="prose-legal">
        <h2>1. Subscription Cancellation</h2>
        <p>
          You may cancel your Tru8 subscription at any time:
        </p>
        <ul>
          <li>Go to Settings → Subscription</li>
          <li>Click &quot;Cancel Subscription&quot;</li>
          <li>Access continues until the end of your current billing period</li>
          <li>No charges after cancellation</li>
        </ul>

        <h2>2. Refund Eligibility</h2>

        <h3>2.1 14-Day Money-Back Guarantee</h3>
        <p>
          <strong>NEW CUSTOMERS:</strong> If you&apos;re not satisfied within 14 days of your
          first subscription payment, we&apos;ll provide a full refund.
        </p>

        <h3>2.2 How to Request</h3>
        <ol>
          <li>Email <a href="mailto:hello@trueight.com">hello@trueight.com</a> within 14 days of payment</li>
          <li>Include your account email and reason for refund</li>
          <li>We&apos;ll process your request within 5 business days</li>
          <li>Refunds issued to original payment method within 7-10 business days</li>
        </ol>

        <h2>3. Non-Refundable Situations</h2>
        <p>
          Refunds are <strong>NOT</strong> available for:
        </p>
        <ul>
          <li>Partial months (prorated refunds not offered)</li>
          <li>Renewal payments beyond 14 days</li>
          <li>Unused monthly checks (checks don&apos;t roll over)</li>
          <li>Prepaid API credit already spent on calls (unspent prepaid credit does not expire and remains available on your account)</li>
          <li>Service dissatisfaction after 14-day period</li>
          <li>Account termination due to Terms of Service violations</li>
        </ul>

        <h2>4. Billing Errors</h2>
        <p>
          If you believe you were charged in error:
        </p>
        <ul>
          <li>Contact <a href="mailto:hello@trueight.com">hello@trueight.com</a> immediately</li>
          <li>Provide transaction details (date, amount, payment method)</li>
          <li>We&apos;ll investigate and resolve within 7 business days</li>
        </ul>

        <h2>5. Statutory Cancellation Rights</h2>
        <p>
          <strong>UK consumers:</strong> you have the right to cancel within 14 days
          of entering the contract, for any reason, under the Consumer Contracts
          (Information, Cancellation and Additional Charges) Regulations 2013.
        </p>
        <p>
          <strong>EU consumers:</strong> the equivalent 14-day right of withdrawal
          applies under the EU Consumer Rights Directive.
        </p>
        <p>
          Where you ask us to begin the service within the cancellation period, we
          may normally charge for what you have used. <strong>We do not.</strong>{' '}
          Our 14-day guarantee above is a full refund, which is more generous than
          the statutory minimum in both cases.
        </p>

        <h2>6. Free Trial</h2>
        <p>
          The free trial has no charges and therefore no refunds apply. Free trial
          checks are provided as-is with no cash value.
        </p>

        <h2>7. Contact</h2>
        <p>
          <strong>For refund requests and billing questions:</strong> <a href="mailto:hello@trueight.com">hello@trueight.com</a><br />
          <strong>Response Time:</strong> Within 5 business days
        </p>
      </div>
    </LegalPageLayout>
  );
}
