'use client';

import { useState, type ReactNode } from 'react';
import Image from 'next/image';
import { ArrowUpRight } from 'lucide-react';

import { ScrollReveal } from './scroll-reveal';
import { SheetHeader } from './sheet-header';
import { ScreenshotScrollLightbox, type ScreenshotSlide } from './screenshot-scroll-lightbox';

/**
 * Homepage — Sheet 02, Inside a check (C1 entry-point clarity, 2026-07-09).
 *
 * "The summary, then the lenses." — the results summary LEADS (labelled THE
 * SUMMARY, deliberately unnumbered so it never reads as a seventh view), then
 * the four strongest lenses as LENS 01–04. Large alternating clickable panels
 * with the existing lightbox — the layout the founder kept. Sources + Video
 * are named in the quiet strip below, so "six" stays honest without six heavy
 * panels. Screenshots refreshed in C4 (post-C2 summary redesign).
 */

interface Panel {
  /** 'summary' renders the unnumbered THE SUMMARY chip; lenses get LENS NN / NN. */
  kind: 'summary' | 'lens';
  number?: string;
  label: string;
  subtitle: string;
  route: string;
  headline: ReactNode;
  description: string;
  src: string;
  /** Optional separate higher-resolution / longer image shown in the lightbox. */
  lightboxSrc?: string;
  alt: string;
  lightboxTitle: string;
}

/** AWAKE (C4, 2026-07-09): C2 shipped the redesigned summary card and the
 *  founder captured fresh screenshots (summary-digest{,-full}.png plus
 *  re-shot Evidence/Map/Timeline). Gaps is NOT panelled (founder decision:
 *  the capture check had no gaps to show) — it is named in the
 *  "Also inside the console" strip alongside Sources and Video. */
const SHOW_SUMMARY_PANEL = true;

const SUMMARY_PANEL: Panel = {
  kind: 'summary',
  label: 'Summary',
  subtitle: 'Digest',
  route: '/dashboard/check/[id]',
  headline: (
    <>
      The whole record, <span className="font-bold">at a glance.</span>
    </>
  ),
  description:
    "What was examined, how the evidence stacks up on each side, where the sourcing runs thin, and what's missing — before you open a single source.",
  src: '/imagery/screenshots/summary-digest.png',
  lightboxSrc: '/imagery/screenshots/summary-digest-full.png',
  alt: 'The check summary — the claim, the elements examined, how many sources support and challenge each, sourcing-quality notes, and named gaps, in one card.',
  lightboxTitle: 'Summary — the whole record at a glance',
};

const LENS_PANELS: Panel[] = [
  {
    kind: 'lens',
    number: '01',
    label: 'Evidence',
    subtitle: 'Librarian',
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
    alt: 'The Evidence view — evidence classified by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic). Heatmap grid with a ledger of source rows underneath.',
    lightboxTitle: 'Evidence — classified landscape',
  },
  {
    kind: 'lens',
    number: '02',
    label: 'Map',
    subtitle: 'Cartographer',
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
    alt: 'The Map view — a Dagre layout of evidence nodes clustered by source and connected by citation relationships. Tier-coloured nodes; one claim node selected with its evidence panel populated.',
    lightboxTitle: 'Map — citation cascade',
  },
  {
    kind: 'lens',
    number: '03',
    label: 'Timeline',
    subtitle: 'Chronologist',
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
    alt: 'The Timeline view — a horizontal SVG timeline with evidence markers plotted by publication date, grouped into temporal clusters with tier indicators.',
    lightboxTitle: 'Timeline — evidence timeline',
  },
];

const PANELS: Panel[] = SHOW_SUMMARY_PANEL ? [SUMMARY_PANEL, ...LENS_PANELS] : LENS_PANELS;

const LENS_TOTAL = String(PANELS.filter((p) => p.kind === 'lens').length).padStart(2, '0');

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
    <section id="preview" className="py-24 md:py-32 bg-white border-t border-zinc-100 scroll-mt-24">
      <div className="max-w-7xl mx-auto px-6">
        <SheetHeader number="02" label="Inside a check" refText="ONE SUMMARY · SIX LENSES" />
        <ScrollReveal>
          <div className="mb-16 md:mb-20 max-w-3xl">
            <h2 className="text-3xl md:text-5xl font-normal tracking-[-0.02em] text-zinc-900 leading-[1.0]">
              The summary, <span className="font-bold">then the lenses.</span>
            </h2>
            <p className="text-sm md:text-base text-zinc-500 leading-relaxed mt-6 max-w-xl">
              Every check opens on a plain-English summary of what was found. Behind
              it, the same evidence arranged six ways. Click any screen to look closer.
            </p>
          </div>
        </ScrollReveal>

        <div className="space-y-20 md:space-y-28">
          {PANELS.map((panel, index) => (
            <PanelRow
              key={panel.label}
              panel={panel}
              index={index}
              flipped={index % 2 === 1}
              onOpen={() => openAt(index)}
            />
          ))}
        </div>

        {/* The remaining lenses — named, not panelled */}
        <div className="mt-16 md:mt-20 pt-8 border-t border-zinc-100 flex flex-wrap items-baseline gap-x-3 gap-y-2 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400">
          <span aria-hidden="true" className="w-1.5 h-1.5 bg-accent rotate-45 self-center shrink-0" />
          <span>Also inside the console:</span>
          <span className="text-zinc-600">Gaps</span>
          <span>— what&rsquo;s missing, with targeted re-search</span>
          <span aria-hidden="true">·</span>
          <span className="text-zinc-600">Sources</span>
          <span>— outlet by outlet</span>
          <span aria-hidden="true">·</span>
          <span className="text-zinc-600">Video</span>
          <span>— what&rsquo;s said on camera</span>
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
  flipped: boolean;
  onOpen: () => void;
}

function PanelRow({ panel, index, flipped, onOpen }: PanelRowProps) {
  const pagination =
    panel.kind === 'summary' ? 'The Summary' : `Lens ${panel.number} / ${LENS_TOTAL}`;

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
            <span
              className={`font-mono text-[10px] tracking-[0.3em] uppercase ${
                panel.kind === 'summary' ? 'text-accent' : 'text-zinc-500'
              }`}
            >
              {pagination}
            </span>
            <div className="h-px flex-grow bg-zinc-200" />
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
              {panel.label}
            </span>
          </div>
          <h3 className="text-3xl md:text-4xl lg:text-5xl font-normal tracking-[-0.02em] text-zinc-900 leading-[1.05] mb-5">
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
            <span>View full size</span>
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
            className="group block w-full text-left border border-zinc-200 bg-white overflow-hidden transition-colors hover:border-accent focus-visible:border-accent"
            aria-label={`Open ${panel.label} screenshot full-size`}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-100">
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
                {panel.label} — Console
              </span>
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 hidden sm:inline">
                {panel.subtitle}
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
                View full size ↗
              </span>
            </div>
          </button>
        </div>
      </div>
    </ScrollReveal>
  );
}
