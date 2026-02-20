import { Map, BookOpen, Focus, Video } from 'lucide-react';

/**
 * Stitch W-01 Features Section (Four Professions)
 *
 * Zinc-50 background, mono "Your Research Team" label,
 * 4-column grid of profession cards with hover:border-black.
 * Each card: icon, profession name, question hook, plain-English explanation.
 */

const professions = [
  {
    icon: Map,
    name: 'The Cartographer',
    question: 'What\u2019s the shape of the conversation?',
    description: 'See where sources agree, where they diverge, and which are just echoing the same original.',
  },
  {
    icon: BookOpen,
    name: 'The Librarian',
    question: 'Show me the full set, clearly labelled.',
    description: 'Every source classified by proximity and type. Filter, sort, browse. Nothing hidden.',
  },
  {
    icon: Focus,
    name: 'The Interpreter',
    question: 'Answer this specific sub-question.',
    description: 'Pick one element of a claim. See what supports it, what challenges it, and what adds context.',
  },
  {
    icon: Video,
    name: 'The Projectionist',
    question: 'What\u2019s being said about this on camera?',
    description: 'Relevant video context from YouTube, classified the same way as text sources.',
  },
];

export function StitchFeatures() {
  return (
    <section id="features" className="py-24 bg-zinc-50 border-y border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header row */}
        <div className="mb-16">
          <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
            Your Research Team
          </span>
          <h2 className="text-3xl md:text-4xl font-light tracking-tight">
            Four ways to <span className="font-bold">explore</span>
          </h2>
        </div>

        {/* Profession cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
          {professions.map((profession) => {
            const Icon = profession.icon;
            return (
              <div
                key={profession.name}
                className="bg-white p-8 border border-zinc-200 group hover:border-black transition-colors"
              >
                <Icon className="text-zinc-900 mb-6 group-hover:text-accent transition-colors" size={24} />
                <h4 className="font-bold uppercase tracking-wider text-sm mb-2">{profession.name}</h4>
                <p className="text-sm text-zinc-500 italic mb-4">&ldquo;{profession.question}&rdquo;</p>
                <p className="text-sm text-zinc-500 leading-relaxed">{profession.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
