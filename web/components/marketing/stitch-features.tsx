'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Map, BookOpen, Users, Video, Clock, Compass } from 'lucide-react';

/**
 * Stitch W-01 Features Section (Six Professions)
 *
 * Horizontal rollerdeck carousel with prominent center card
 * and fading adjacent cards. Auto-advances every 6 seconds.
 */

const professions = [
  {
    icon: Map,
    action: 'Map',
    name: 'The Cartographer',
    question: 'What\u2019s the shape of the conversation?',
    description:
      'See where sources agree, where they diverge, and which are just echoing the same original.',
  },
  {
    icon: BookOpen,
    action: 'Evidence',
    name: 'The Librarian',
    question: 'Show me the full set, clearly labelled.',
    description:
      'Every source classified by tier and type. Filter, sort, browse. Nothing hidden.',
  },
  {
    icon: Users,
    action: 'Sources',
    name: 'The Correspondent',
    question: 'Who\u2019s in the room?',
    description:
      'See which domains contributed evidence, how concentrated or diverse they are, and where single-source coverage may need attention.',
  },
  {
    icon: Video,
    action: 'Video',
    name: 'The Projectionist',
    question: 'What\u2019s being said about this on camera?',
    description:
      'Relevant video context from YouTube, classified the same way as text sources.',
  },
  {
    icon: Clock,
    action: 'Timeline',
    name: 'The Chronologist',
    question: 'When did each piece of evidence appear?',
    description:
      'A timeline of every source, ordered by publication date. See how the conversation developed and where the reporting clusters.',
  },
  {
    icon: Compass,
    action: 'Gaps',
    name: 'The Seeker',
    question: 'What don\u2019t we know yet?',
    description:
      'Every evidence gap, surfaced clearly. Specify what data would fill each one, then trigger a targeted re-search.',
  },
];

const TOTAL = professions.length;
const AUTO_ADVANCE_MS = 6000;

/** Compute shortest circular distance between two indices. */
function getCircularDiff(index: number, active: number): number {
  let diff = index - active;
  if (diff > TOTAL / 2) diff -= TOTAL;
  if (diff < -TOTAL / 2) diff += TOTAL;
  return diff;
}

export function StitchFeatures() {
  const [activeIndex, setActiveIndex] = useState(0);
  const pauseRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // Auto-advance
  useEffect(() => {
    const timer = setInterval(() => {
      if (!pauseRef.current) {
        setActiveIndex((prev) => (prev + 1) % TOTAL);
      }
    }, AUTO_ADVANCE_MS);
    return () => clearInterval(timer);
  }, []);

  const goTo = useCallback((index: number) => {
    setActiveIndex(index);
    pauseRef.current = true;
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    resumeTimerRef.current = setTimeout(() => {
      pauseRef.current = false;
    }, 12000);
  }, []);

  return (
    <section id="features" className="py-24 bg-zinc-50 border-y border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="mb-16">
          <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
            Six Evidence Views
          </span>
          <h2 className="text-3xl md:text-4xl font-light tracking-tight">
            Six ways to <span className="font-bold">explore</span>
          </h2>
        </div>

        {/* Carousel */}
        <div
          className="relative overflow-hidden h-[300px] md:h-[280px]"
          onMouseEnter={() => {
            pauseRef.current = true;
          }}
          onMouseLeave={() => {
            pauseRef.current = false;
          }}
        >
          {professions.map((profession, index) => {
            const Icon = profession.icon;
            const diff = getCircularDiff(index, activeIndex);
            const absDiff = Math.abs(diff);
            const isActive = diff === 0;

            let opacity: number;
            let scale: number;
            if (absDiff === 0) {
              opacity = 1;
              scale = 1;
            } else if (absDiff === 1) {
              opacity = 0.45;
              scale = 0.97;
            } else if (absDiff === 2) {
              opacity = 0.12;
              scale = 0.95;
            } else {
              opacity = 0;
              scale = 0.93;
            }

            return (
              <div
                key={profession.name}
                className="absolute top-0 w-[85%] md:w-[33.333%] px-2"
                style={{
                  left: '50%',
                  transform: `translateX(calc(-50% + ${diff * 103}%)) scale(${scale})`,
                  opacity,
                  transition:
                    'transform 700ms cubic-bezier(0.4, 0, 0.2, 1), opacity 700ms ease',
                  zIndex: 10 - absDiff,
                  pointerEvents: absDiff > 1 ? 'none' : 'auto',
                }}
                onClick={() => !isActive && goTo(index)}
              >
                <div
                  className={`bg-white p-8 border h-full transition-colors duration-500 ${
                    isActive
                      ? 'border-black'
                      : 'border-zinc-200 cursor-pointer hover:border-zinc-300'
                  }`}
                >
                  <Icon
                    className={`mb-6 transition-colors duration-500 ${
                      isActive ? 'text-zinc-900' : 'text-zinc-400'
                    }`}
                    size={24}
                  />
                  <h4 className="font-bold uppercase tracking-wider text-sm mb-1">
                    {profession.action}
                  </h4>
                  <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-3">
                    {profession.name}
                  </p>
                  <p className="text-sm text-zinc-500 italic mb-4">
                    &ldquo;{profession.question}&rdquo;
                  </p>
                  <p className="text-sm text-zinc-500 leading-relaxed">
                    {profession.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Navigation dots */}
        <div className="flex justify-center gap-2 mt-8">
          {professions.map((_, index) => (
            <button
              key={index}
              onClick={() => goTo(index)}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                index === activeIndex
                  ? 'bg-zinc-900 w-4'
                  : 'bg-zinc-300 w-1.5 hover:bg-zinc-400'
              }`}
              aria-label={`View ${professions[index].action}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
