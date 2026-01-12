'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Globe, Search, Calendar, Shield, BarChart3, CheckCircle2 } from 'lucide-react';

/**
 * Feature Carousel Component
 *
 * Rollerdeck-style carousel with 6 feature cards - tightly overlapping.
 *
 * Features:
 * 1. Multi-Source Verification
 * 2. Article Analysis
 * 3. Dated Evidence
 * 4. Source Credibility
 * 5. Confidence Scoring
 * 6. Global Coverage
 *
 * Rollerdeck Specifications:
 * - All cards: Fixed dimensions (480x320px desktop, 320x280px mobile) for uniform sizing
 * - Content: Line-clamped text (2 lines title, 4 lines description) with flexbox layout
 * - Center card: Scale 1.0 (full size), opacity 100%, z-index 30
 * - Adjacent cards: Scale 0.85, opacity 100%, z-index 25
 * - Far cards: Scale 0.7, opacity 100%, z-index 20
 * - Very far cards: Scale 0.5, opacity 100%, z-index 15
 * - Positioning: Tight spacing (220px desktop, 150px mobile)
 * - Auto-play: 5-second interval
 * - Manual: Left/Right arrow buttons
 * - Animation: 300ms ease-in-out
 */
export function FeatureCarousel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const features = [
    {
      icon: CheckCircle2,
      title: 'Multi-Source Verification',
      description: 'Cross-reference claims against multiple authoritative sources for comprehensive validation',
    },
    {
      icon: Search,
      title: 'Article Analysis',
      description: 'Deep content analysis with context understanding and claim extraction',
    },
    {
      icon: Calendar,
      title: 'Dated Evidence',
      description: 'Every source includes publication dates for temporal accuracy verification',
    },
    {
      icon: Shield,
      title: 'Source Listings',
      description: 'Full transparency with complete source listings—see every article, publication, and reference reviewed during verification',
    },
    {
      icon: BarChart3,
      title: 'Confidence Scoring',
      description: 'Transparent confidence metrics showing verification strength for each claim',
    },
    {
      icon: Globe,
      title: 'Global Coverage',
      description: 'Access to international sources across languages and regions',
    },
  ];

  const totalCards = features.length;

  // Auto-play functionality
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % totalCards);
    }, 5000); // 5 seconds

    return () => clearInterval(interval);
  }, [isPaused, totalCards]);

  const goToPrevious = () => {
    setIsPaused(true);
    setActiveIndex((prev) => (prev - 1 + totalCards) % totalCards);
    setTimeout(() => setIsPaused(false), 3000); // Resume after 3s
  };

  const goToNext = () => {
    setIsPaused(true);
    setActiveIndex((prev) => (prev + 1) % totalCards);
    setTimeout(() => setIsPaused(false), 3000); // Resume after 3s
  };

  // Calculate circular position - wraps smoothly in both directions
  const getCircularOffset = (index: number) => {
    let diff = (index - activeIndex + totalCards) % totalCards;

    // Normalize to -3 to +3 range for circular effect (shows 3 cards on each side)
    if (diff > totalCards / 2) {
      diff = diff - totalCards;
    }

    return diff;
  };

  const getCardStyle = (offset: number) => {
    const absDiff = Math.abs(offset);
    let scale = 1;
    let blur = 0;

    if (absDiff === 0) {
      scale = 1.0;
      blur = 0;
    } else if (absDiff === 1) {
      scale = 0.8;
      blur = 2;
    } else if (absDiff === 2) {
      scale = 0.6;
      blur = 4;
    } else {
      scale = 0.4;
      blur = 6;
    }

    const zIndex = 30 - absDiff * 5;
    return { scale, zIndex, offset, blur };
  };

  return (
    <section id="features" className="py-20 px-4 overflow-hidden">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-[#f57a07] mb-4">
            Professional Fact-Checking Tools
          </h2>
          <p className="text-xl text-slate-400">
            Enterprise-grade verification powered by AI
          </p>
        </div>

        {/* Carousel Container */}
        <div className="relative px-8 md:px-0">
          {/* 3D Perspective Container - Circular Rollerdeck */}
          <div className="carousel-perspective relative h-[230px] md:h-[380px] flex items-center justify-center">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const offset = getCircularOffset(index);
              const { scale, zIndex, blur } = getCardStyle(offset);

              return (
                <div
                  key={index}
                  className="carousel-card absolute transition-all duration-300 ease-in-out w-[270px] h-[205px] md:w-[480px] md:h-[320px] -ml-[135px] md:-ml-[240px] left-1/2"
                  style={{
                    '--offset': offset,
                    '--scale': scale,
                    zIndex,
                    filter: blur > 0 ? `blur(${blur}px)` : 'none',
                  } as React.CSSProperties}
                >
                  <div className="bg-[#1a1f2e] rounded-lg p-4 md:p-8 border border-slate-700 shadow-xl h-full flex flex-col">
                    {/* Icon */}
                    <div className="mb-2 md:mb-4 flex-shrink-0">
                      <Icon className="w-8 h-8 md:w-12 md:h-12 text-[#22d3ee]" />
                    </div>

                    {/* Content */}
                    <h3 className="text-lg md:text-xl font-semibold text-white mb-2 md:mb-3 flex-shrink-0">
                      {feature.title}
                    </h3>
                    <p className="text-slate-400 leading-snug md:leading-relaxed text-sm md:text-sm flex-grow">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Navigation Arrows - positioned outside cards on mobile */}
          <button
            onClick={goToPrevious}
            className="absolute -left-2 md:left-0 top-1/2 -translate-y-1/2 z-40 p-2 md:p-3 bg-[#1a1f2e] hover:bg-[#1a1f2e] border border-slate-700 hover:border-[#f57a07] rounded-full transition-colors"
            aria-label="Previous feature"
          >
            <ChevronLeft className="w-5 h-5 md:w-6 md:h-6 text-white" />
          </button>

          <button
            onClick={goToNext}
            className="absolute -right-2 md:right-0 top-1/2 -translate-y-1/2 z-40 p-2 md:p-3 bg-[#1a1f2e] hover:bg-[#1a1f2e] border border-slate-700 hover:border-[#f57a07] rounded-full transition-colors"
            aria-label="Next feature"
          >
            <ChevronRight className="w-5 h-5 md:w-6 md:h-6 text-white" />
          </button>

          {/* Indicator Dots */}
          <div className="flex justify-center gap-2 mt-8">
            {features.map((_, index) => (
              <button
                key={index}
                onClick={() => {
                  setActiveIndex(index);
                  setIsPaused(true);
                  setTimeout(() => setIsPaused(false), 3000);
                }}
                className={`w-2 h-2 rounded-full transition-all ${
                  index === activeIndex
                    ? 'bg-[#f57a07] w-8'
                    : 'bg-slate-600 hover:bg-slate-500'
                }`}
                aria-label={`Go to feature ${index + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Carousel styles - global needed for class selectors to work */}
      <style jsx global>{`
        .carousel-perspective {
          perspective: 1200px;
          perspective-origin: center;
        }

        .carousel-card {
          transform-style: preserve-3d;
          transition: all 300ms ease-in-out;
          transform: translateX(calc(var(--offset) * 100px)) scale(var(--scale, 1));
        }

        /* Desktop spacing */
        @media (min-width: 768px) {
          .carousel-card {
            transform: translateX(calc(var(--offset) * 220px)) scale(var(--scale, 1));
          }
        }

        /* Respect reduced motion preference */
        @media (prefers-reduced-motion: reduce) {
          .carousel-card {
            transition: none;
          }
        }
      `}</style>
    </section>
  );
}
