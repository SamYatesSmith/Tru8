import { Play } from 'lucide-react';

/**
 * Video Demo Placeholder Component
 *
 * Placeholder for demo video section.
 *
 * Content:
 * - Orange heading: "See Tru8 in Action"
 * - Gray subheading: "Watch how Tru8 verifies content in real-time"
 * - Large placeholder box with play button icon (cyan)
 * - Text: "Demo video coming soon"
 * - Ready for video embed (YouTube/Vimeo iframe)
 *
 * Design:
 * - Dark card background (#1a1f2e)
 * - Play button: Cyan circle with play icon
 * - Ready for video URL to be added later
 */
export function VideoDemo() {
  return (
    <section id="video-demo" className="py-20 px-4">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-[#f57a07] mb-4">
            See Tru8 in Action
          </h2>
          <p className="text-xl text-slate-400">
            Watch how Tru8 verifies content in real-time
          </p>
        </div>

        {/* Video Placeholder */}
        <div className="relative bg-[#1a1f2e]/80 backdrop-blur-sm rounded-lg border border-slate-700 aspect-video flex flex-col items-center justify-center overflow-hidden group hover:border-slate-600 transition-colors">
          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#f57a07]/10 via-transparent to-[#22d3ee]/10" />

          {/* Play Button */}
          <div className="relative z-10 mb-6">
            <div className="w-24 h-24 bg-[#22d3ee]/20 rounded-full flex items-center justify-center group-hover:bg-[#22d3ee]/30 transition-colors">
              <div className="w-20 h-20 bg-[#22d3ee] rounded-full flex items-center justify-center">
                <Play className="w-10 h-10 text-white ml-1" fill="currentColor" />
              </div>
            </div>
          </div>

          {/* Text */}
          <div className="relative z-10 text-center">
            <p className="text-2xl font-semibold text-white mb-2">
              Demo video coming soon
            </p>
            <p className="text-slate-400">
              This section is ready for your demo video
            </p>
          </div>

          {/* Decorative Elements */}
          <div className="absolute top-4 right-4 text-xs text-slate-500 font-mono">
            16:9 Aspect Ratio
          </div>
        </div>

        {/* Future Implementation Note (hidden in production) */}
        <div className="mt-4 text-center text-sm text-slate-500 hidden">
          {/* To add video: Replace placeholder with <iframe> or <video> element */}
        </div>
      </div>
    </section>
  );
}
