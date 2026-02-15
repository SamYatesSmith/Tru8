import { Upload, GitBranch, ClipboardCheck } from 'lucide-react';

/**
 * Stitch W-01 Process Section (How It Works)
 *
 * 3-column grid: icon + line + step number, orange micro-label,
 * bold uppercase title, zinc description.
 */

const steps = [
  {
    icon: Upload,
    number: '01',
    label: 'Initialize',
    title: 'Submit Claim',
    description: 'Input any technical specification or clinical hypothesis for decomposition.',
  },
  {
    icon: GitBranch,
    number: '02',
    label: 'Process',
    title: 'AI Research',
    description: 'Platform scans 14+ database types including clinical trials and patent filings.',
  },
  {
    icon: ClipboardCheck,
    number: '03',
    label: 'Analyze',
    title: 'Review Map',
    description: 'Analyze the evidence mapping and form a technical orientation based on data.',
  },
];

export function StitchProcess() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div key={step.number} className="flex flex-col">
                <div className="flex items-center gap-3 mb-6">
                  <Icon className="text-zinc-300 flex-shrink-0" size={30} />
                  <div className="h-[1px] flex-grow bg-zinc-100" />
                  <span className="font-mono text-[10px] text-zinc-400">{step.number}</span>
                </div>
                <span className="font-mono text-[10px] tracking-widest uppercase text-accent mb-2">
                  {step.label}
                </span>
                <h3 className="text-lg font-bold mb-4 uppercase tracking-wide">{step.title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{step.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
