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
    <section id="how-it-works" className="py-16 md:py-20 px-6 md:px-4">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="text-center mb-10 md:mb-16">
          <h2 className="text-3xl md:text-5xl font-bold text-[#f57a07] mb-3 md:mb-4">
            How Tru8 Works
          </h2>
          <p className="text-base md:text-xl text-slate-400">
            Three simple steps to reliable fact-checking
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.number}
                className="relative bg-[#1a1f2e]/80 backdrop-blur-sm rounded-xl p-5 md:p-8 border border-slate-700 hover:border-slate-600 transition-colors ml-2 md:ml-0"
              >
                {/* Numbered Badge */}
                <div className="absolute -top-3 -left-3 md:-top-4 md:-left-4 w-10 h-10 md:w-12 md:h-12 bg-[#f57a07] rounded-full flex items-center justify-center text-white font-bold text-lg md:text-xl shadow-lg">
                  {step.number}
                </div>

                {/* Icon */}
                <div className="mb-4 md:mb-6 mt-2 md:mt-4">
                  <Icon className="w-10 h-10 md:w-12 md:h-12 text-[#22d3ee]" />
                </div>

                {/* Content */}
                <h3 className="text-xl md:text-2xl font-semibold text-white mb-2 md:mb-3">
                  {step.title}
                </h3>
                <p className="text-sm md:text-base text-slate-400 leading-relaxed">
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
