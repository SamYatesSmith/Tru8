'use client';

import { useEffect, useId, useState, type CSSProperties } from 'react';

interface Tru8MarkProps {
  size?: number;
  animated?: boolean;
  className?: string;
  style?: CSSProperties;
}

// Split the figure-8 into TWO strands that meet at the X (50, 65).
// UNDER strand traces the SW-going diagonal (drawn first → underneath).
// OVER strand traces the NW-going diagonal (drawn last → on top).
// Each is half of the figure-8, opened at the crossover.
const UNDER_STRAND = 'M 50,8 C 90,8 90,55 50,65 C 10,75 10,122 50,122';
const OVER_STRAND = 'M 50,122 C 90,122 90,75 50,65 C 10,55 10,8 50,8';

// Dot's Möbius-edge route — continuous 2-lap figure-8 traversal.
// The Möbius strip's single edge has length 2L (twice the strip length), so in 2D
// projection it winds around the figure-8 TWICE before returning home.
//
// Path = figure-8 bezier traversed TWICE end-to-end (no M-jumps, fully continuous).
// Each lap: 4 cubic beziers, ~95 units each, totalling ~380 units per lap.
// 2 laps = ~760 units. Each crossover encounter at 12.5% of cycle (95/760).
//
// Crossover encounters within the 2-lap cycle:
//   12.5% — Lap 1, first crossover (going SW) — THE TWIST: front face → back face
//   37.5% — Lap 1, second crossover (going NW) — no twist
//   62.5% — Lap 2, first crossover (going SW) — THE TWIST: back face → front face (HOME)
//   87.5% — Lap 2, second crossover (going NW) — no twist
//
// The dot is on FRONT FACE (visible) from 0%→12.5% and from 62.5%→100%.
// The dot is on BACK FACE (invisible) from 12.5%→62.5%.
// Viewer infers the unseen Möbius traversal from the absence + the asymmetric reappearance.
const FULL_PATH = [
  'M 50,8',
  // Lap 1
  'C 90,8 90,55 50,65',
  'C 10,75 10,122 50,122',
  'C 90,122 90,75 50,65',
  'C 10,55 10,8 50,8',
  // Lap 2
  'C 90,8 90,55 50,65',
  'C 10,75 10,122 50,122',
  'C 90,122 90,75 50,65',
  'C 10,55 10,8 50,8',
].join(' ');

// Opacity timeline: visible 0→11%, fade out 11→13%, invisible 13→62%,
// fade in 62→64%, visible 64→100%.
const OPACITY_KEYTIMES = '0;0.11;0.13;0.62;0.64;1';
const OPACITY_KEYSPLINES = '0 0 1 1;0.4 0 0.6 1;0 0 1 1;0.4 0 0.6 1;0 0 1 1';

// Ghost path — figure-8 offset OUTWARD from the visible ribbon by ~6 units, so the glow
// sits on the far side of the outer dark stroke. Same 2-lap structure as FULL_PATH.
const GHOST_PATH = [
  'M 50,-1',
  // Lap 1 (outer offset)
  'C 96,-1 96,53 50,65',
  'C 4,77 4,131 50,131',
  'C 96,131 96,77 50,65',
  'C 4,53 4,-1 50,-1',
  // Lap 2
  'C 96,-1 96,53 50,65',
  'C 4,77 4,131 50,131',
  'C 96,131 96,77 50,65',
  'C 4,53 4,-1 50,-1',
].join(' ');

// Ghost trail — same shape as DOT_LAYERS but on the outer offset path, inverted timing.
const GHOST_LAYERS = [
  { r: 2.5, opacity: 0.18, begin: '0.45s' },
  { r: 3.5, opacity: 0.32, begin: '0.3s' },
  { r: 4.5, opacity: 0.46, begin: '0.15s' },
  { r: 5, opacity: 0.55, begin: '0s' },
];

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

const DOT_LAYERS = [
  { r: 2.5, opacity: 0.25, begin: '0.45s' },
  { r: 3.5, opacity: 0.5, begin: '0.3s' },
  { r: 4, opacity: 0.8, begin: '0.15s' },
  { r: 4.5, opacity: 1, begin: '0s' },
];

const STROKE_OUTER = 10;
const STROKE_INNER = 6;

export function Tru8Mark({
  size = 40,
  animated = true,
  className,
  style,
}: Tru8MarkProps) {
  const reactId = useId().replace(/:/g, '');
  const glowId = `tru8-glow-${reactId}`;
  const ghostGlowId = `tru8-ghost-${reactId}`;
  const shadowId = `tru8-shadow-${reactId}`;

  const reducedMotion = useReducedMotion();
  const showAnimation = animated && !reducedMotion;

  const height = Math.round(size * 1.39);

  return (
    <svg
      width={size}
      height={height}
      viewBox="-6 -12 112 150"
      fill="none"
      className={className}
      style={style}
      aria-hidden="true"
    >
      <defs>
        <filter id={glowId} x="-200%" y="-200%" width="500%" height="500%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Diffuse glow for the GHOST trail — sits outside the ribbon, suggesting the unseen back-face traversal */}
        <filter id={ghostGlowId} x="-200%" y="-200%" width="500%" height="500%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Drop shadow for the OVER strand — gives it visible depth above the under strand */}
        <filter id={shadowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="1.5" />
          <feOffset dx="0" dy="1.5" result="offsetblur" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.5" />
          </feComponentTransfer>
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* GHOST trail — rendered UNDER the visible ribbon, so the ribbon's strokes naturally cover
          any glow that bleeds into the parallel tracks. Ghost only shows outside the ribbon footprint. */}
      {showAnimation && GHOST_LAYERS.map((layer, i) => (
        <circle
          key={`ghost-${i}`}
          r={layer.r}
          fill="#EA580C"
          opacity="0"
          filter={`url(#${ghostGlowId})`}
        >
          <animateMotion
            dur="12s"
            begin={layer.begin}
            repeatCount="indefinite"
            path={GHOST_PATH}
          />
          <animate
            attributeName="opacity"
            dur="12s"
            begin={layer.begin}
            repeatCount="indefinite"
            calcMode="spline"
            values={`0;0;${layer.opacity};${layer.opacity};0;0`}
            keyTimes={OPACITY_KEYTIMES}
            keySplines={OPACITY_KEYSPLINES}
          />
        </circle>
      ))}

      {/* UNDER STRAND — drawn first, gets covered at the X */}
      <path d={UNDER_STRAND} stroke="#18181b" strokeWidth={STROKE_OUTER} strokeLinecap="butt" fill="none" />
      <path d={UNDER_STRAND} stroke="white" strokeWidth={STROKE_INNER} strokeLinecap="butt" fill="none" />

      {/* WHITE PATCH at the X — cuts a clean break in the under strand so the over strand reads as "passing over" */}
      <ellipse cx="50" cy="65" rx="14" ry="8" fill="white" />

      {/* OVER STRAND — drawn last with a drop shadow, visibly bridges over the under strand */}
      <g filter={`url(#${shadowId})`}>
        <path d={OVER_STRAND} stroke="#18181b" strokeWidth={STROKE_OUTER} strokeLinecap="butt" fill="none" />
        <path d={OVER_STRAND} stroke="white" strokeWidth={STROKE_INNER} strokeLinecap="butt" fill="none" />
      </g>

      {/* Main dot + trail — rendered ON TOP, visible above the ribbon */}
      {showAnimation ? (
        <>
          {DOT_LAYERS.map((layer, i) => (
          <circle
            key={i}
            r={layer.r}
            fill="#EA580C"
            opacity={layer.opacity}
            filter={`url(#${glowId})`}
          >
            <animateMotion
              dur="12s"
              begin={layer.begin}
              repeatCount="indefinite"
              path={FULL_PATH}
            />
            <animate
              attributeName="opacity"
              dur="12s"
              begin={layer.begin}
              repeatCount="indefinite"
              calcMode="spline"
              values={`${layer.opacity};${layer.opacity};0;0;${layer.opacity};${layer.opacity}`}
              keyTimes={OPACITY_KEYTIMES}
              keySplines={OPACITY_KEYSPLINES}
            />
          </circle>
        ))}
        </>
      ) : (
        <circle
          cx="50"
          cy="8"
          r="4.5"
          fill="#EA580C"
          filter={`url(#${glowId})`}
        />
      )}
    </svg>
  );
}
