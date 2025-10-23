import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { CookiePreferencesButton } from '@/components/legal/cookie-preferences-button';

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
            <CookiePreferencesButton>
              "Cookie Preferences"
            </CookiePreferencesButton>
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
