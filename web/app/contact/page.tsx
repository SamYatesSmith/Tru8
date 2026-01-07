import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { Mail, MapPin } from 'lucide-react';

export const metadata = {
  title: 'Contact Us | Tru8',
  description: 'Get in touch with Tru8 for all support and inquiries',
};

export default function ContactPage() {
  return (
    <LegalPageLayout
      title="Contact Us"
    >
      <div className="prose-legal">
        <p className="text-lg text-slate-200 mb-12">
          We&apos;re here to help. Contact us for any inquiry related to your account, privacy, billing, or general questions.
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
                For all inquiries including general support, privacy/GDPR requests, billing issues, refunds, and feedback:
              </p>
              <a
                href="mailto:hello@trueight.com"
                className="inline-flex items-center gap-2 px-6 py-3 bg-[#f57a07] hover:bg-[#e06a00] rounded-lg font-semibold transition-colors text-lg no-underline"
                style={{ color: 'white' }}
              >
                <Mail size={20} className="text-white" />
                <span className="text-white">hello@trueight.com</span>
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
          <p className="text-slate-300 mb-2 flex items-center gap-2">
            <MapPin className="text-[#f57a07] flex-shrink-0" size={18} />
            <span><strong className="text-white">Location:</strong> London, UK</span>
          </p>
          <p className="text-slate-300 ml-[26px]">
            <strong className="text-white">Company:</strong> Tru8 Ltd
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
      </div>
    </LegalPageLayout>
  );
}
