/**
 * Stitch FAQ — answer-first Q&A block + FAQPage JSON-LD.
 *
 * Server component (no 'use client') so the questions and answers ship as clean
 * server HTML, high in the DOM and free of JS dependency — the structure that
 * AI answer engines (ChatGPT/Claude/Perplexity/AI Overviews) parse and quote,
 * and that earns FAQ rich results. Copy obeys the positioning locks: no verdict
 * language, "We organise; you decide", UK spelling (D13, updated 2026-06-29). Functional manifest
 * "confirm/checked" wording is used instead of "verify a claim".
 */

interface QA {
  q: string;
  a: string;
}

const FAQS: ReadonlyArray<QA> = [
  {
    q: 'What is Tru8?',
    a: 'Tru8 is evidence research infrastructure. You submit a claim or a question, and Tru8 decomposes it into checkable elements, retrieves evidence from published sources, and organises the results into a structured evidence landscape — what supports each element, what challenges it, and what is missing. Submit an article and Tru8 extracts its claims for you to choose from. Tru8 does not issue a verdict. We organise; you decide.',
  },
  {
    q: 'How is Tru8 different from a fact-checker?',
    a: 'A fact-checker hands you a rating — true, false, misleading. Tru8 hands you the organised evidence and its provenance, and leaves the judgement to you. You see every source, how it relates to the claim, and what could not be found, so you can show your working.',
  },
  {
    q: 'Who is Tru8 for?',
    a: 'Researchers, journalists, analysts and developers who need to show their working — people who would rather present an organised evidence trail than ask others to trust a single score.',
  },
  {
    q: 'What sources does Tru8 search?',
    a: 'The open web, plus specialist APIs across government, legislation, academic literature, economic data, news and archives — for example GOV.UK, Hansard, FRED, Semantic Scholar, PubMed, the World Bank and the Internet Archive. Every source that is included, and every one that is excluded, carries a receipt.',
  },
  {
    q: 'Does Tru8 use AI to decide what is true?',
    a: 'No. AI is used to decompose claims, retrieve evidence and classify it by source type and tier. It never scores credibility and never issues a verdict. The judgement stays with you.',
  },
];
// C1 (2026-07-09): "Is there an API?" + "Can a report be checked independently?"
// moved to the /developers FAQ — this page keeps the five human-buyer questions.

const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: {
      '@type': 'Answer',
      text: item.a,
    },
  })),
};

export function StitchFaq() {
  return (
    <section className="relative py-20 md:py-28 border-t border-zinc-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, '\\u003c') }}
      />
      <div className="max-w-7xl mx-auto px-5 md:px-6">
        <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-500 mb-5 md:mb-6">
          Common Questions
        </div>
        <h2 className="max-w-3xl text-2xl sm:text-3xl md:text-4xl font-normal tracking-[-0.02em] text-zinc-900 leading-tight mb-12 md:mb-16">
          What Tru8 does &mdash; and what it deliberately does not.
        </h2>

        <dl className="max-w-3xl divide-y divide-zinc-100 border-t border-zinc-100">
          {FAQS.map((item) => (
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
