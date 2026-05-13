'use client';

import Lightbox from 'yet-another-react-lightbox';
import Captions from 'yet-another-react-lightbox/plugins/captions';
import Counter from 'yet-another-react-lightbox/plugins/counter';
import Zoom from 'yet-another-react-lightbox/plugins/zoom';

import 'yet-another-react-lightbox/styles.css';
import 'yet-another-react-lightbox/plugins/captions.css';
import 'yet-another-react-lightbox/plugins/counter.css';

import './screenshot-lightbox.css';

export interface ScreenshotSlide {
  src: string;
  alt: string;
  title: string;
  route: string;
}

interface ScreenshotLightboxProps {
  slides: ScreenshotSlide[];
  open: boolean;
  index: number;
  onClose: () => void;
  onIndexChange?: (index: number) => void;
}

export function ScreenshotLightbox({
  slides,
  open,
  index,
  onClose,
  onIndexChange,
}: ScreenshotLightboxProps) {
  const lightboxSlides = slides.map((slide) => ({
    src: slide.src,
    alt: slide.alt,
    title: slide.title,
    description: slide.route,
  }));

  return (
    <Lightbox
      open={open}
      close={onClose}
      index={index}
      slides={lightboxSlides}
      plugins={[Captions, Counter, Zoom]}
      className="stitch-lightbox"
      controller={{ closeOnBackdropClick: true }}
      carousel={{ finite: true, padding: 0 }}
      animation={{ fade: 300, swipe: 400 }}
      zoom={{ maxZoomPixelRatio: 3, scrollToZoom: true, doubleTapDelay: 200 }}
      counter={{ container: { style: { top: 24, left: 32, bottom: 'unset', right: 'unset' } } }}
      captions={{ showToggle: false, descriptionTextAlign: 'start' }}
      on={{
        view: ({ index: nextIndex }) => onIndexChange?.(nextIndex),
      }}
    />
  );
}
