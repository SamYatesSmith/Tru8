'use client';

import { useEffect, useState, type CSSProperties } from 'react';

/**
 * Tru8 mark — the Möbius band, drawn as a luminous lattice.
 *
 * The artwork is GENERATED, not hand-authored: `design/mobius-mark/` holds the
 * geometry and lighting model, and `python design/mobius-mark/build_assets.py`
 * emits the files in `public/brand/`. Never edit those SVGs by hand — rerun the
 * builder and commit its output.
 *
 * Why files rather than inline JSX: the mark is static art, so it belongs in
 * `public/` where the browser caches it once, not in the JS bundle where it is
 * re-parsed on every page. SMIL keeps running inside an `<img>` (browsers use
 * "secure animated mode" there — declarative animation allowed, script not),
 * verified by pixel-diffing the rendered frames. 5.2KB gzipped animated.
 *
 * THERE IS ONE LOGO. This is the hero mark rendered small — same band, same
 * lattice, same proportions, fewer sample points. It is not a nav-specific
 * variant, and reintroducing one is a regression: the builder asserts every
 * emitted asset shares an aspect ratio precisely so they cannot drift apart.
 *
 * Sized by HEIGHT, because the mark is tall and narrow (1 wide : 2.15 high) and
 * every place it appears is height-constrained — an 80px navbar, a 64px mobile
 * bar, a line of footer text. Width follows from the ratio.
 *
 * Motion is refusable two ways — `prefers-reduced-motion` and the `animated`
 * prop — and both resolve to a genuinely frozen file, not a paused one.
 */

interface Tru8MarkProps {
  /** Rendered height in px. Width is derived — never set it independently. */
  height?: number;
  animated?: boolean;
  className?: string;
  style?: CSSProperties;
}

/** Height per unit width, mirrored from `build_assets.py`, which prints it and
 *  asserts all four assets agree. Rerun the builder and update this together. */
const ASPECT = 2.1488;

const SRC_ANIMATED = '/brand/tru8-mark.svg';
const SRC_STATIC = '/brand/tru8-mark-static.svg';

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const handler = (event: MediaQueryListEvent) => setReduced(event.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return reduced;
}

export function Tru8Mark({
  height = 44,
  animated = true,
  className,
  style,
}: Tru8MarkProps) {
  const reducedMotion = useReducedMotion();
  const showAnimation = animated && !reducedMotion;
  const size = Math.round(height / ASPECT);

  return (
    // eslint-disable-next-line @next/next/no-img-element -- generated SVG art;
    // next/image would neither optimise nor resize it, and would defer paint.
    <img
      src={showAnimation ? SRC_ANIMATED : SRC_STATIC}
      width={size}
      height={height}
      alt=""
      aria-hidden="true"
      draggable={false}
      className={className}
      style={style}
    />
  );
}
