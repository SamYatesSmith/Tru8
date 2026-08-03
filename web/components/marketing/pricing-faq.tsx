/**
 * PricingFaq — buyer Q&A block + FAQPage JSON-LD for /pricing.
 *
 * Server component: ships as clean server HTML so AI answer engines and
 * structured-data crawlers can read it without executing JS. Follows the
 * stitch-faq.tsx pattern. Questions cover product behaviour only — what a
 * check is, what it returns, no-verdict position, timing, export, API.
 * Positioning locks: no verdict language; "We organise; you decide";
 * "evidence research" / "analysis", never "fact-checking" or "verdict".
 */

interface QA {
  q: string;
  a: string;
}

const PRICING_FAQS: ReadonlyArray<QA> = [
  {
    q: 'What is a check?',
    a: 'A check is a single evidence research run. You submit a URL, an article or a claim; Tru8 breaks it into its constituent elements, retrieves relevant evidence from published sources, and returns an organised evidence record — with a receipt for every source included and every source excluded.',
  },
  {
    q: 'What does a check return?',
    a: 'Six structured views of the same evidence set: a Map of element relationships, a Librarian ledger of every source by tier and type, a Correspondent view for element-by-element analysis, a Timeline of when evidence appeared, a Projectionist view of video evidence, and a Seeker report of what could not be found. Every record is signed and exportable as PDF, CSV or JSON.',
  },
  {
    q: 'Does Tru8 issue a verdict?',
    a: 'No. Tru8 organises evidence; it never scores credibility or labels a claim true or false. You see the full retrieval — what supports each element, what challenges it, and what is missing — and reach your own judgement. We organise; you decide.',
  },
  {
    q: 'How long does a check take?',
    a: 'Most checks complete in under two minutes. Tru8 pauses briefly after extracting the checkable elements so you can confirm which ones to research; the evidence retrieval and organisation then runs in the background.',
  },
  {
    q: 'Can I export the evidence record?',
    a: 'Yes. Every check includes a full export in PDF, CSV and JSON. The JSON export carries the complete evidence record, including provenance metadata and the signed manifest, so the record can be independently confirmed.',
  },
  {
    q: 'Is there an API?',
    a: 'Yes. Tru8 has a metered API for integration into automated workflows and agent systems. Each API call runs the same pipeline as a Console check — the same sources, the same evidence views, the same signed record — and is billed per call from a prepaid balance. See the developers portal for endpoints and rates.',
  },
];

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: PRICING_FAQS.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: {
      '@type': 'Answer',
      text: item.a,
    },
  })),
};

export function PricingFaq() {
  return (
    <section className="relative py-20 md:py-28 border-t border-zinc-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, '\\u003c') }}
      />
      <div className="max-w-6xl mx-auto px-6">
        <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-5 md:mb-6">
          Common Questions
        </div>
        <h2 className="max-w-3xl text-2xl sm:text-3xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 leading-tight mb-12 md:mb-16">
          How Tru8 works &mdash; and what a check contains.
        </h2>

        <dl className="max-w-3xl divide-y divide-zinc-100 border-t border-zinc-100">
          {PRICING_FAQS.map((item) => (
            <div key={item.q} className="py-7 md:py-8">
              <dt className="text-base md:text-lg font-medium text-zinc-900 mb-3 flex gap-3">
                <span aria-hidden="true" className="mt-2 w-1.5 h-1.5 bg-accent rotate-45 shrink-0" />
                <span>{item.q}</span>
              </dt>
              <dd className="text-sm md:text-base text-zinc-500 leading-relaxed pl-[18px]">
                {item.a}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
