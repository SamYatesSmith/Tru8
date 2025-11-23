import { Upload, Zap, FileText } from 'lucide-react';

/**
 * How Tru8 Works Component
 *
 * 3-step process section explaining the verification flow.
 *
 * Steps:
 * 1. Submit Content (Upload icon)
 *    - "Upload articles, images, videos, or paste text directly into our platform"
 * 2. AI Verification (Zap icon)
 *    - "Our AI analyzes content against thousands of verified sources in real-time"
 * 3. Get Results (FileText icon)
 *    - "Receive detailed reports with evidence, sources, and confidence scores"
 *
 * Design:
 * - Orange heading
 * - Gray subheading
 * - 3 cards in grid (stacks on mobile)
 * - Dark background with cyan icons
 * - Numbered badges (1, 2, 3)
 */
export function HowItWorks() {
  const steps = [
    {
      number: 1,
      title: 'Submit Content',
      description: 'Upload articles, URLs, record voice messages, or paste text directly into our platform',
      icon: Upload,
    },
    {
      number: 2,
      title: 'AI Verification',
      description: 'Our AI analyzes content against thousands of verified sources in real-time',
      icon: Zap,
    },
    {
      number: 3,
      title: 'Get Results',
      description: 'Receive detailed reports with evidence, sources, and confidence scores',
      icon: FileText,
    },
  ];

  return (
    <section id="how-it-works" className="py-20 px-4">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-[#f57a07] mb-4">
            How Tru8 Works
          </h2>
          <p className="text-xl text-slate-400">
            Three simple steps to reliable fact-checking
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.number}
                className="relative bg-[#1a1f2e]/80 backdrop-blur-sm rounded-lg p-8 border border-slate-700 hover:border-slate-600 transition-colors"
              >
                {/* Numbered Badge */}
                <div className="absolute -top-4 -left-4 w-12 h-12 bg-[#f57a07] rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg">
                  {step.number}
                </div>

                {/* Icon */}
                <div className="mb-6 mt-4">
                  <Icon className="w-12 h-12 text-[#22d3ee]" />
                </div>

                {/* Content */}
                <h3 className="text-2xl font-semibold text-white mb-3">
                  {step.title}
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  {step.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
