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
 * - Center card: Scale 1.0, opacity 100%, z-index highest
 * - Adjacent cards: Scale 0.9, opacity 80%, tightly overlapping
 * - Far cards: Scale 0.8, opacity 50%, behind adjacent
 * - Cards positioned with minimal spacing for tight overlap
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
      title: 'Source Credibility',
      description: 'Automatic credibility scoring based on publisher reputation and track record',
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

  const getCardPosition = (offset: number) => {
    const absDiff = Math.abs(offset);

    if (absDiff === 0) return 'center';
    if (absDiff === 1) return 'adjacent';
    return 'far';
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
        <div className="relative">
          {/* 3D Perspective Container - Circular Rollerdeck */}
          <div className="carousel-perspective relative h-[400px] md:h-[450px] flex items-center justify-center">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const offset = getCircularOffset(index);
              const position = getCardPosition(offset);

              return (
                <div
                  key={index}
                  className="carousel-card absolute w-full max-w-md transition-all duration-300 ease-in-out"
                  style={{
                    transform: `translateX(${offset * 35}%) scale(${
                      position === 'center' ? 1 : position === 'adjacent' ? 0.9 : 0.8
                    })`,
                    opacity: position === 'center' ? 1 : position === 'adjacent' ? 0.8 : 0.5,
                    zIndex: position === 'center' ? 30 : position === 'adjacent' ? 20 : 10,
                  }}
                >
                  <div className="bg-[#1a1f2e]/90 backdrop-blur-sm rounded-lg p-8 border border-slate-700 h-full shadow-xl">
                    {/* Icon */}
                    <div className="mb-6">
                      <Icon className="w-16 h-16 text-[#22d3ee]" />
                    </div>

                    {/* Content */}
                    <h3 className="text-2xl font-semibold text-white mb-4">
                      {feature.title}
                    </h3>
                    <p className="text-slate-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Navigation Arrows */}
          <button
            onClick={goToPrevious}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-40 p-3 bg-[#1a1f2e]/80 hover:bg-[#1a1f2e] border border-slate-700 hover:border-[#f57a07] rounded-full transition-colors"
            aria-label="Previous feature"
          >
            <ChevronLeft className="w-6 h-6 text-white" />
          </button>

          <button
            onClick={goToNext}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-40 p-3 bg-[#1a1f2e]/80 hover:bg-[#1a1f2e] border border-slate-700 hover:border-[#f57a07] rounded-full transition-colors"
            aria-label="Next feature"
          >
            <ChevronRight className="w-6 h-6 text-white" />
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
    </section>
  );
}
