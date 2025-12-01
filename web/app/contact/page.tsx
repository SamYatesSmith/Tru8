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
          We&apos;re here to help. Contact us for any inquiry related to your account, privacy, billing, or legal matters.
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
          If you&apos;re not satisfied with our response:
        </p>
        <ol>
          <li>Reply to the original support email requesting escalation</li>
          <li>Your case will be reviewed by a senior team member</li>
          <li>You&apos;ll receive a response within 7 business days</li>
        </ol>

        <h2>Regulatory Authority</h2>
        <p>
          For data protection complaints, you may contact the UK Information Commissioner&apos;s Office:
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
