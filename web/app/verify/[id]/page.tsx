/**
 * Record verification page — /verify/[id]
 *
 * Calls the public backend verify endpoint (GET /verify/{id}, no auth) and
 * renders the result as a document-grammar datasheet. Honest framing only:
 * the manifest is a server-attested HMAC over the record's signed fields
 * (identifiers, states, tier, landscape) — NOT an independent third-party
 * timestamp, and it does not re-fetch the original sources. So we say
 * "signed record / the signed fields have not changed since signing",
 * never "tamper-evident" or "independently verifiable".
 */

import { Metadata } from 'next';
import Link from 'next/link';
import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';

interface PageProps {
  params: { id: string };
}

interface VerifyResult {
  valid: boolean;
  checkId?: string;
  signedAt?: string;
  kid?: string;
  executedTier?: string;
  pipelineFingerprint?: string;
  reason?: string;
}

async function getVerification(id: string): Promise<VerifyResult | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  try {
    const res = await fetch(`${apiUrl}/verify/${id}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    console.error('Failed to fetch verification:', error);
    return null;
  }
}

export const metadata: Metadata = {
  title: 'Verify record | Tru8',
  description:
    'Confirm a Tru8 evidence record has not changed since it was signed — its signed fields re-checked against the signature.',
  robots: { index: false, follow: false },
};

const REASON_COPY: Record<string, { head: string; body: string }> = {
  not_found: {
    head: 'No record found',
    body: 'No record matches this reference. Check the link, or open the report it came from.',
  },
  signing_disabled: {
    head: 'Record not signed',
    body: 'This record predates signing, so there is no signature to check. Newer records carry a signed manifest.',
  },
  invalid_signature: {
    head: 'Signature did not validate',
    body: 'The signature on this record could not be validated. Treat the record with caution and re-run the check.',
  },
  data_modified: {
    head: 'Signed fields have changed',
    body: 'The signed fields no longer match the signature taken at signing time. The record may have been altered since.',
  },
};

function Row({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-12 gap-1 sm:gap-4 px-6 py-4 border-t border-zinc-100">
      <span className="sm:col-span-4 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
        {label}
      </span>
      <span className="sm:col-span-8 font-mono text-sm text-zinc-900 break-all">{value}</span>
    </div>
  );
}

export default async function VerifyPage({ params }: PageProps) {
  const result = await getVerification(params.id);
  const valid = result?.valid === true;
  const reasonCopy = result?.reason ? REASON_COPY[result.reason] : undefined;

  return (
    <>
      <Navigation />
      <MobileBottomNav />

      <main className="min-h-screen bg-white pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-3xl">
          <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-4">
            Verification
          </div>

          <div className="border border-zinc-200 border-t-2 border-t-accent bg-white">
            <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-zinc-200">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900">
                Tru8 record
              </span>
              <span
                className={`font-mono text-[10px] tracking-[0.2em] uppercase ${
                  valid ? 'text-zinc-900' : 'text-zinc-500'
                }`}
              >
                {valid ? 'Valid' : 'Unverified'}
              </span>
            </div>

            {valid ? (
              <>
                <div className="px-6 py-8">
                  <h1 className="text-2xl md:text-3xl font-normal text-zinc-900 leading-snug">
                    The signed fields have not changed since signing.
                  </h1>
                  <p className="text-sm text-zinc-600 mt-3 leading-relaxed">
                    Tru8 re-checked this record against the signature created when it was produced. The
                    identifiers, states, tier and landscape summary below match what was signed. This is
                    server-attested using a key held by Tru8 — not an independent third-party timestamp,
                    and it does not re-fetch the original sources.
                  </p>
                </div>
                <div>
                  <Row label="Check ID" value={result?.checkId} />
                  <Row label="Signed at" value={result?.signedAt} />
                  <Row label="Key ID" value={result?.kid} />
                  <Row label="Executed tier" value={result?.executedTier} />
                  <Row label="Pipeline fingerprint" value={result?.pipelineFingerprint} />
                </div>
              </>
            ) : (
              <div className="px-6 py-8">
                <h1 className="text-2xl md:text-3xl font-normal text-zinc-900 leading-snug">
                  {reasonCopy?.head || 'Could not verify this record'}
                </h1>
                <p className="text-sm text-zinc-600 mt-3 leading-relaxed">
                  {reasonCopy?.body ||
                    'We could not reach the verification service for this record just now. Please try again shortly.'}
                </p>
              </div>
            )}

            <div className="border-t border-zinc-200 px-6 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-500">
                <span aria-hidden="true" className="w-2 h-2 bg-accent rotate-45 shrink-0" />
                {valid ? 'signed record' : 'verification'}
              </span>
              <Link
                href={`/r/${params.id}`}
                className="font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-900 hover:text-accent transition-colors"
              >
                View the report →
              </Link>
            </div>
          </div>

          <p className="text-[13px] text-zinc-500 mt-6 leading-relaxed">
            Verification confirms the record&rsquo;s signed fields — claim and element identifiers, states,
            tier and the landscape summary — are unchanged since signing. It is server-attested using a key
            held by Tru8; it is not an independent third-party timestamp, and it does not re-fetch or
            re-check the original sources.
          </p>
        </div>
      </main>

      <Footer />
    </>
  );
}
