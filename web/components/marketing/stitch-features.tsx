import { Map, Database, BarChart3, GitPullRequest, ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * Stitch W-01 Features Section (Core Capabilities)
 *
 * Zinc-50 background, mono "Core Capabilities" label,
 * 4-column grid of feature cards with hover:border-black.
 */

const features = [
  {
    icon: Map,
    title: 'Evidence Mapping',
    description: 'Visual relationships between clinical data and technical requirements.',
  },
  {
    icon: Database,
    title: 'Multi-Source Research',
    description: 'Cross-reference across 14+ technical source types in real-time.',
  },
  {
    icon: BarChart3,
    title: 'Source Analysis',
    description: 'Comprehensive evidence landscape across primary, reporting, and commentary sources.',
  },
  {
    icon: GitPullRequest,
    title: 'Claim Decomposition',
    description: 'Atomic breakdown of complex claims into analysable technical components.',
  },
];

export function StitchFeatures() {
  return (
    <section id="features" className="py-24 bg-zinc-50 border-y border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header row */}
        <div className="flex justify-between items-end mb-16">
          <div>
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
              Core Capabilities
            </span>
            <h2 className="text-3xl md:text-4xl font-light tracking-tight">
              Technical <span className="font-bold">Precision</span>
            </h2>
          </div>
          <div className="hidden sm:flex gap-2">
            <button
              className="w-10 h-10 border border-zinc-200 flex items-center justify-center hover:bg-white transition-colors"
              aria-label="Previous"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              className="w-10 h-10 border border-zinc-200 flex items-center justify-center hover:bg-white transition-colors"
              aria-label="Next"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="bg-white p-8 border border-zinc-200 group hover:border-black transition-colors"
              >
                <Icon className="text-zinc-900 mb-6 group-hover:text-accent transition-colors" size={24} />
                <h4 className="font-bold uppercase tracking-wider text-sm mb-4">{feature.title}</h4>
                <p className="text-sm text-zinc-500 leading-relaxed">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
