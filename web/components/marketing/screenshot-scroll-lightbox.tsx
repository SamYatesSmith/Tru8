'use client';

import { useEffect, useRef } from 'react';
import { X, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';

export interface ScreenshotSlide {
  src: string;
  alt: string;
  title: string;
  route: string;
}

interface ScreenshotScrollLightboxProps {
  slides: ScreenshotSlide[];
  open: boolean;
  index: number;
  onClose: () => void;
  onIndexChange?: (index: number) => void;
}

export function ScreenshotScrollLightbox({
  slides,
  open,
  index,
  onClose,
  onIndexChange,
}: ScreenshotScrollLightboxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft' && index > 0) onIndexChange?.(index - 1);
      else if (e.key === 'ArrowRight' && index < slides.length - 1) onIndexChange?.(index + 1);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, index, slides.length, onClose, onIndexChange]);

  useEffect(() => {
    if (!open) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = originalOverflow; };
  }, [open]);

  // Reset scroll position when slide changes
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [index]);

  if (!open) return null;
  const slide = slides[index];
  if (!slide) return null;

  const canPrev = index > 0;
  const canNext = index < slides.length - 1;

  return (
    <div className="fixed inset-0 z-50 bg-zinc-950/96 flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 md:px-10 py-5 border-b border-zinc-800">
        <div className="flex items-baseline gap-4 md:gap-6 min-w-0">
          <span className="font-mono text-[10px] md:text-[11px] tracking-[0.3em] uppercase text-zinc-50 font-medium truncate">
            {slide.title}
          </span>
          <span className="font-mono text-[10px] tracking-[0.3em] text-zinc-400 tabular-nums shrink-0">
            {String(index + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}
          </span>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <a
            href={slide.src}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[0.2em] uppercase text-zinc-400 hover:text-white transition-colors"
            aria-label="Open full image in new tab"
          >
            Open full size
            <ExternalLink size={12} />
          </a>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-zinc-300 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Scrollable body — image renders at natural width within container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden"
        onClick={(e) => {
          // Click on the surrounding padding (not the image itself) closes
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div className="max-w-5xl mx-auto py-8 px-6 md:px-10">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={slide.src}
            alt={slide.alt}
            className="w-full h-auto border border-zinc-800 bg-zinc-900 block"
          />
          <p className="font-mono text-[10px] tracking-[0.15em] text-zinc-400 mt-4 text-center lowercase">
            {slide.route}
          </p>
        </div>
      </div>

      {/* Prev / Next arrows — only render when navigation is possible */}
      {canPrev && (
        <button
          onClick={() => onIndexChange?.(index - 1)}
          aria-label="Previous"
          className="fixed left-2 md:left-6 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors p-2"
        >
          <ChevronLeft size={32} />
        </button>
      )}
      {canNext && (
        <button
          onClick={() => onIndexChange?.(index + 1)}
          aria-label="Next"
          className="fixed right-2 md:right-6 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors p-2"
        >
          <ChevronRight size={32} />
        </button>
      )}
    </div>
  );
}
