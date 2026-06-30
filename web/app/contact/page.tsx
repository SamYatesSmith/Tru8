import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { Mail, MapPin } from 'lucide-react';

export const metadata = {
  title: 'Contact',
  description: 'Get in touch with Tru8 for support, billing enquiries, privacy requests, or general questions. Based in London, UK.',
  alternates: { canonical: '/contact' },
};

export default function ContactPage() {
  return (
    <LegalPageLayout
      title="Contact Us"
      sheetLabel="Support"
    >
      <div className="prose-legal">
        <p className="text-lg text-zinc-600 mb-12">
          We&apos;re here to help. Contact us for any enquiry related to your account, privacy, billing, or general questions.
        </p>

        {/* Single Contact Email */}
        <div className="bg-zinc-50 border border-zinc-200 p-8 not-prose mb-12">
          <div className="flex items-start gap-6">
            <div className="bg-zinc-900 p-4 flex-shrink-0">
              <Mail className="text-white" size={32} />
            </div>
            <div className="flex-1">
              <h3 className="text-2xl font-normal text-zinc-900 mb-3">Get in Touch</h3>
              <p className="text-zinc-600 mb-4">
                For all enquiries including general support, privacy/GDPR requests, billing issues, refunds, and feedback:
              </p>
              <a
                href="mailto:hello@trueight.com"
                className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors no-underline"
              >
                <Mail size={16} />
                hello@trueight.com
              </a>
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-zinc-500 text-sm">
                    <strong className="text-zinc-900">General Enquiries:</strong> 24-48 hours
                  </p>
                </div>
                <div>
                  <p className="text-zinc-500 text-sm">
                    <strong className="text-zinc-900">GDPR Requests:</strong> Within 30 days
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <h2>Business Information</h2>
        <div className="bg-zinc-50 border border-zinc-200 p-6 not-prose">
          <p className="text-zinc-600 mb-2 flex items-center gap-2">
            <MapPin className="text-zinc-500 flex-shrink-0" size={18} />
            <span><strong className="text-zinc-900">Location:</strong> London, UK</span>
          </p>
          <p className="text-zinc-600 ml-[26px]">
            <strong className="text-zinc-900">Company:</strong> Tru8 Ltd
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
