import { Play } from 'lucide-react';

/**
 * Stitch W-01 Video Section
 *
 * Dark rounded container with centered play button,
 * mono walkthrough label at bottom-left.
 */
export function StitchVideo() {
  return (
    <section className="py-24 md:py-32">
      <div className="max-w-5xl mx-auto px-6">
        <div className="aspect-video bg-zinc-900 rounded-3xl overflow-hidden relative group cursor-pointer shadow-2xl">
          {/* Play button */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 md:w-20 md:h-20 bg-white rounded-full flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
              <Play className="text-black ml-1" size={28} />
            </div>
          </div>

          {/* Mono label */}
          <div className="absolute bottom-6 left-6 md:bottom-8 md:left-8">
            <span className="font-mono text-[10px] tracking-widest text-white/60 uppercase">
              Platform Walkthrough
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
