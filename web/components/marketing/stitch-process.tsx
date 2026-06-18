import { SheetHeader } from './sheet-header';

/**
 * Stitch — How It Works (integration-first, verification/dev-led).
 * Four steps; mono micro-labels; raw zinc + accent tokens.
 */
const steps = [
  {
    number: '01',
    label: 'Submit',
    title: 'Submit content or a claim',
    description:
      'Send AI-generated text, a URL, or a single claim — via the API or the Research Console.',
  },
  {
    number: '02',
    label: 'Decompose',
    title: 'Decompose into elements',
    description:
      'Each claim is broken into 1–5 checkable factual elements, so evidence maps to specifics, not vibes.',
  },
  {
    number: '03',
    label: 'Retrieve',
    title: 'Retrieve external sources at depth',
    description:
      'Tru8 searches official data, research, legislation, and reporting — each source classified by tier and type.',
  },
  {
    number: '04',
    label: 'Return',
    title: 'Return a structured record',
    description:
      'Supports, challenges, context, gaps, receipts, and a signed manifest. You decide what ships.',
  },
];

export function StitchProcess() {
  return (
    <section className="py-20 md:py-24 bg-white border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="02" label="Process" refText="~60–90s · IDEMPOTENT" />
        <div className="max-w-3xl mb-12 md:mb-14">
          <h2 className="text-2xl md:text-3xl font-normal tracking-[-0.01em] text-zinc-900 leading-[1.1]">
            One submission, a retainable record.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 lg:gap-10">
          {steps.map((step) => {
            return (
              <div key={step.number} className="flex flex-col">
                <div className="flex items-center gap-3 mb-6">
                  <span className="font-mono text-[10px] text-zinc-400">{step.number}</span>
                  <div className="h-px flex-grow bg-zinc-100" />
                </div>
                <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-500 mb-2">
                  {step.label}
                </span>
                <h3 className="text-base font-normal mb-3 text-zinc-900">
                  {step.title}
                </h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{step.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
