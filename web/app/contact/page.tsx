import { LegalPageLayout } from '@/components/legal/legal-page-layout';
import { LEGAL, ICO } from '@/lib/legal';
import { Mail, MapPin } from 'lucide-react';

export const metadata = {
  title: 'Contact',
  description: 'Get in touch with Tru8 for support, billing enquiries, privacy requests, or general questions. Trueight Ltd, registered in England and Wales.',
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
          <p className="text-zinc-600 mb-2">
            <strong className="text-zinc-900">Company:</strong> {LEGAL.companyName} (company number {LEGAL.companyNumber}), registered in {LEGAL.placeOfRegistration}, trading as {LEGAL.tradingName}
          </p>
          <p className="text-zinc-600 flex items-start gap-2">
            <MapPin className="text-zinc-500 flex-shrink-0 mt-1" size={18} />
            <span><strong className="text-zinc-900">Registered office:</strong> {LEGAL.registeredOffice}</span>
          </p>
        </div>

        <h2>Who you are actually emailing</h2>
        <p>
          Tru8 is built and run by one person. There is no support desk and no
          call queue — your email comes to me directly, and I answer it myself.
        </p>
        <p>
          In practice that means most messages get a reply the same working day,
          and complicated ones get a considered answer rather than a template. It
          also means I am occasionally asleep. If something is urgent, say so in
          the subject line.
        </p>

        <h2>If you are not happy with my answer</h2>
        <p>
          Reply and say so plainly. I would rather hear it than not. If we still
          cannot resolve it, you can escalate a data-protection complaint to the{' '}
          <a href={ICO.websiteUrl} target="_blank" rel="noopener noreferrer">
            {ICO.name}
          </a>{' '}
          ({ICO.website}), the UK&apos;s supervisory authority.
        </p>
      </div>
    </LegalPageLayout>
  );
}
