'use client';

import { useState, type ReactNode } from 'react';
import Image from 'next/image';
import { ArrowUpRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { ScreenshotScrollLightbox, type ScreenshotSlide } from './screenshot-scroll-lightbox';

interface Panel {
  number: string;
  label: string;
  route: string;
  headline: ReactNode;
  description: string;
  src: string;
  /** Optional separate higher-resolution / longer image shown in the lightbox.
   *  When omitted, lightbox uses `src`. Use this for tall full-page captures
   *  whose 4:3 thumbnail crop hides most of the content. */
  lightboxSrc?: string;
  alt: string;
  lightboxTitle: string;
}

const PANELS: Panel[] = [
  {
    number: '01',
    label: 'Librarian',
    route: '/dashboard/check/[id]?view=librarian',
    headline: (
      <>
        Every source <span className="font-bold">classified.</span>
      </>
    ),
    description:
      'Tier × type heatmap and ledger. Filter, sort, browse. Receipts for everything excluded — no hidden curation.',
    src: '/imagery/screenshots/librarian-landscape.png',
    lightboxSrc: '/imagery/screenshots/librarian-landscape-full.png',
    alt: 'The Librarian view — evidence classified by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic). Heatmap grid with a ledger of source rows underneath.',
    lightboxTitle: 'Librarian — evidence landscape',
  },
  {
    number: '02',
    label: 'Cartographer',
    route: '/dashboard/check/[id]?view=cartographer',
    headline: (
      <>
        The shape of the <span className="font-bold">conversation.</span>
      </>
    ),
    description:
      'A citation cascade. See where sources agree, where they diverge, and which are just echoing the same original.',
    src: '/imagery/screenshots/cartographer-network.png',
    lightboxSrc: '/imagery/screenshots/cartographer-network-full.png',
    alt: 'The Cartographer view — a Dagre layout of evidence nodes clustered by source and connected by citation relationships. Tier-coloured nodes; one claim node selected with its evidence panel populated.',
    lightboxTitle: 'Cartographer — citation cascade',
  },
  {
    number: '03',
    label: 'Seeker',
    route: '/dashboard/check/[id]?view=seeker',
    headline: (
      <>
        What we <span className="font-bold">don&rsquo;t know yet.</span>
      </>
    ),
    description:
      'Every evidence gap, surfaced clearly. Specify what data would fill each one, then trigger a targeted re-search.',
    src: '/imagery/screenshots/seeker-unknowns.png',
    lightboxSrc: '/imagery/screenshots/seeker-unknowns-full.png',
    alt: 'The Seeker view — a ledger of unresolved elements with their uncertainty notes, bounty text, and a "Re-search" action button per gap.',
    lightboxTitle: 'Seeker — known unknowns',
  },
  {
    number: '04',
    label: 'Chronologist',
    route: '/dashboard/check/[id]?view=chronologist',
    headline: (
      <>
        When did each piece of evidence <span className="font-bold">appear?</span>
      </>
    ),
    description:
      'A timeline of every source, ordered by publication date. See how the conversation developed and where the reporting clusters.',
    src: '/imagery/screenshots/chronologist-timeline.png',
    lightboxSrc: '/imagery/screenshots/chronologist-timeline-full.png',
    alt: 'The Chronologist view — a horizontal SVG timeline with evidence markers plotted by publication date, grouped into temporal clusters with tier indicators.',
    lightboxTitle: 'Chronologist — evidence timeline',
  },
];

const SLIDES: ScreenshotSlide[] = PANELS.map((p) => ({
  src: p.lightboxSrc ?? p.src,
  alt: p.alt,
  title: p.lightboxTitle,
  route: p.route,
}));

export function StitchProductPreview() {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const openAt = (index: number) => {
    setLightboxIndex(index);
    setLightboxOpen(true);
  };

  return (
    <section id="preview" className="py-24 md:py-32 bg-white border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        <ScrollReveal>
          <div className="mb-20 md:mb-28 max-w-3xl">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
              Module — See It Work
            </span>
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-extralight tracking-[-0.02em] text-zinc-900 leading-[0.95]">
              Six views.<br />
              One <span className="font-bold">landscape.</span>
            </h2>
            <p className="text-sm md:text-base text-zinc-500 leading-relaxed mt-6 max-w-xl">
              The same evidence research, surfaced six ways. Four are shown here — click any panel to open it full-size with zoom.
            </p>
          </div>
        </ScrollReveal>

        <div className="space-y-24 md:space-y-32">
          {PANELS.map((panel, index) => (
            <PanelRow
              key={panel.number}
              panel={panel}
              index={index}
              total={PANELS.length}
              flipped={index % 2 === 1}
              onOpen={() => openAt(index)}
            />
          ))}
        </div>
      </div>

      <ScreenshotScrollLightbox
        slides={SLIDES}
        open={lightboxOpen}
        index={lightboxIndex}
        onClose={() => setLightboxOpen(false)}
        onIndexChange={setLightboxIndex}
      />
    </section>
  );
}

interface PanelRowProps {
  panel: Panel;
  index: number;
  total: number;
  flipped: boolean;
  onOpen: () => void;
}

function PanelRow({ panel, index, total, flipped, onOpen }: PanelRowProps) {
  const pagination = `${panel.number} / ${String(total).padStart(2, '0')}`;

  return (
    <ScrollReveal>
      <div
        className={`grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-center ${
          flipped ? 'lg:[&>*:first-child]:order-2' : ''
        }`}
      >
        {/* Caption rail */}
        <div className="lg:col-span-4 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent">
              {pagination}
            </span>
            <div className="h-px flex-grow bg-zinc-200" />
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
              {panel.label}
            </span>
          </div>
          <h3 className="text-3xl md:text-4xl lg:text-5xl font-extralight tracking-[-0.02em] text-zinc-900 leading-[1.05] mb-5">
            {panel.headline}
          </h3>
          <p className="text-sm md:text-base text-zinc-500 leading-relaxed mb-8">
            {panel.description}
          </p>
          <button
            type="button"
            onClick={onOpen}
            className="group inline-flex items-center gap-2 self-start font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-900 hover:text-accent transition-colors"
            aria-label={`Open ${panel.label} screenshot full-size`}
          >
            <span>Click to zoom</span>
            <ArrowUpRight
              size={14}
              className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            />
          </button>
        </div>

        {/* Screenshot frame */}
        <div className="lg:col-span-8">
          <button
            type="button"
            onClick={onOpen}
            className="group block w-full text-left border border-zinc-200 bg-white overflow-hidden transition-colors hover:border-zinc-900 focus-visible:border-zinc-900"
            aria-label={`Open ${panel.label} screenshot full-size`}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-100">
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
                {panel.label} view — Dashboard
              </span>
              <span className="font-mono text-[10px] text-zinc-300 hidden sm:inline">
                {panel.route}
              </span>
            </div>
            <div className="relative aspect-[4/3] bg-zinc-50 flex items-center justify-center">
              {/* object-contain so the entire screenshot is visible inline; lightbox handles zoom */}
              <Image
                src={panel.src}
                alt={panel.alt}
                fill
                sizes="(min-width: 1024px) 66vw, 100vw"
                className="object-contain transition-transform duration-500 group-hover:scale-[1.01]"
                priority={index === 0}
              />
              <span
                className="absolute bottom-3 right-3 font-mono text-[10px] tracking-[0.3em] uppercase bg-white/95 text-zinc-900 px-3 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-hidden="true"
              >
                Open ↗
              </span>
            </div>
          </button>
        </div>
      </div>
    </ScrollReveal>
  );
}
