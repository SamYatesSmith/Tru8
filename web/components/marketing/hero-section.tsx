'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { CheckCircle, Clock, Users } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';
import { scrollToSection } from '@/lib/scroll-utils';

// Card colors: Orange (inner) → Yellow (outer)
const CARD_COLORS = [
  '#F57A07', // Card 1 - Brand orange (innermost/front)
  '#FA9406', // Card 2
  '#F9A305', // Card 3
  '#FAB306', // Card 4
  '#FAC50B', // Card 5
  '#FAD60E', // Card 6
  '#F0DE14', // Card 7 - Yellow (outermost/back)
];

// SVG dimensions (viewBox)
const SVG_WIDTH = 610;
const SVG_HEIGHT = 366;
const CARD_RADIUS = 24;

// Calculate card dimensions
// Card 7 = 100%, Card 6 = 95%, ..., Card 1 = 70%, Foreground = 65%
function getCardDimensions(cardNumber: number) {
  // cardNumber: 0=foreground (65%), 1-7 where 7 is largest (100%) and 1 is smallest (70%)
  const percent = cardNumber === 0 ? 65 : 70 + ((cardNumber - 1) * 5);
  const width = SVG_WIDTH * (percent / 100);
  const height = SVG_HEIGHT * (percent / 100);
  const x = (SVG_WIDTH - width) / 2;
  const y = (SVG_HEIGHT - height) / 2;
  return { width, height, x, y };
}

/**
 * Card stack with Tru8 stencil mask and JS-powered animation
 */
function HeroVisual() {
  const fgDims = getCardDimensions(0);

  // Track opacity for each card (1-7)
  const [cardOpacity, setCardOpacity] = useState<Record<number, number>>({
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1
  });

  // Track current text color (matches the innermost visible card)
  const [textColor, setTextColor] = useState(CARD_COLORS[0]);

  useEffect(() => {
    // Animation cycle: 14 steps
    // Steps 0-6: fade out cards 7→1 (back to front)
    // Steps 7-13: fade in cards 1→7 (front to back)
    const STEP_DURATION = 900; // 0.9 seconds per step
    let step = 0;

    const animate = () => {
      setCardOpacity(() => {
        const newOpacity: Record<number, number> = { 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1 };

        if (step < 7) {
          // Fade out phase: cards 7→1 disappear one by one
          for (let i = 7; i > 7 - step - 1; i--) {
            if (i >= 1) newOpacity[i] = 0;
          }
          // Text color matches the innermost visible card (the one about to fade)
          const innermostVisible = 7 - step;
          if (innermostVisible >= 1) {
            setTextColor(CARD_COLORS[innermostVisible - 1]);
          }
        } else {
          // Fade in phase: all cards start hidden, then 1→7 reappear
          const fadeInStep = step - 7;
          for (let i = 1; i <= 7; i++) {
            newOpacity[i] = i <= fadeInStep + 1 ? 1 : 0;
          }
          // Text color matches the newest card being added
          const newestCard = fadeInStep + 1;
          if (newestCard <= 7) {
            setTextColor(CARD_COLORS[newestCard - 1]);
          }
        }

        return newOpacity;
      });

      step = (step + 1) % 14; // 14 steps total
    };

    const interval = setInterval(animate, STEP_DURATION);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative flex items-center justify-center pt-12 pb-8 md:pt-52 md:pb-12 px-4">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="w-full max-w-md sm:max-w-xl md:max-w-3xl lg:max-w-4xl"
        aria-hidden="true"
      >
        <defs>
          <mask id="tru8-stencil">
            <rect
              fill="white"
              width={fgDims.width}
              height={fgDims.height}
              x={fgDims.x}
              y={fgDims.y}
              rx={CARD_RADIUS}
            />
            <text
              fill="black"
              x={SVG_WIDTH / 2}
              y={SVG_HEIGHT / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="114"
              fontWeight="900"
              fontFamily="Quantify, system-ui, sans-serif"
              letterSpacing="12"
            >
              Tru8
            </text>
          </mask>
          {/* Mask for shadow - shows on grey card but NOT on letter areas */}
          <mask id="outer-shadow-mask">
            <rect
              fill="white"
              width={fgDims.width}
              height={fgDims.height}
              x={fgDims.x}
              y={fgDims.y}
              rx={CARD_RADIUS}
            />
            {/* Black text cuts out the letter areas from the mask */}
            <text
              fill="black"
              x={SVG_WIDTH / 2}
              y={SVG_HEIGHT / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="114"
              fontWeight="900"
              fontFamily="Quantify, system-ui, sans-serif"
              letterSpacing="12"
            >
              Tru8
            </text>
          </mask>
          {/* Blur filter for outer glow - intensified */}
          <filter id="letter-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="12" />
          </filter>
          {/* Inner shadow for grey card perimeter - intensified */}
          <filter id="card-inner-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feComponentTransfer in="SourceAlpha">
              <feFuncA type="table" tableValues="1 0" />
            </feComponentTransfer>
            <feGaussianBlur stdDeviation="10" />
            <feOffset dx="0" dy="0" result="offsetblur" />
            <feFlood floodColor="#000000" floodOpacity="0.55" />
            <feComposite in2="offsetblur" operator="in" />
            <feComposite in2="SourceAlpha" operator="in" />
            <feMerge>
              <feMergeNode in="SourceGraphic" />
              <feMergeNode />
            </feMerge>
          </filter>
        </defs>

        {/* Render cards 7 to 1 (back to front) */}
        {[7, 6, 5, 4, 3, 2, 1].map((cardNum) => {
          const dims = getCardDimensions(cardNum);
          const color = CARD_COLORS[cardNum - 1];
          return (
            <rect
              key={cardNum}
              fill={color}
              width={dims.width}
              height={dims.height}
              x={dims.x}
              y={dims.y}
              rx={CARD_RADIUS}
              style={{
                opacity: cardOpacity[cardNum],
                transition: 'opacity 0.5s ease-in-out'
              }}
            />
          );
        })}

        {/* Dynamic colored text that shows through the stencil cutout */}
        <text
          fill={textColor}
          x={SVG_WIDTH / 2}
          y={SVG_HEIGHT / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="114"
          fontWeight="900"
          fontFamily="Quantify, system-ui, sans-serif"
          letterSpacing="12"
          style={{
            transition: 'fill 0.5s ease-in-out'
          }}
        >
          Tru8
        </text>

        {/* Foreground slate card with Tru8 cutout and inner perimeter shadow */}
        <rect
          fill="#1e293b"
          width={fgDims.width}
          height={fgDims.height}
          x={fgDims.x}
          y={fgDims.y}
          rx={CARD_RADIUS}
          mask="url(#tru8-stencil)"
          filter="url(#card-inner-shadow)"
        />

        {/* Shadow glow around letters - only on grey surface, not on letters */}
        <text
          fill="rgba(0,0,0,0.75)"
          x={SVG_WIDTH / 2}
          y={SVG_HEIGHT / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="114"
          fontWeight="900"
          fontFamily="Quantify, system-ui, sans-serif"
          letterSpacing="12"
          filter="url(#letter-glow)"
          mask="url(#outer-shadow-mask)"
        >
          Tru8
        </text>
      </svg>
    </section>
  );
}

function HeroContent({ onOpenAuth }: { onOpenAuth: () => void }) {
  return (
    <section className="py-12 md:py-16 px-4">
      <div className="container mx-auto max-w-4xl text-center">
        <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 md:mb-6">
          Stop Guessing. Start Knowing.
        </h1>
        <p className="text-sm sm:text-base md:text-lg lg:text-xl text-slate-300 mb-8 md:mb-12 max-w-3xl mx-auto leading-relaxed">
          In a world of misinformation, see what the sources say.
          Professional claim verification backed by credible sources you can cite.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-8 md:mb-12">
          <button
            onClick={onOpenAuth}
            className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg text-base sm:text-lg font-semibold transition-all hover:shadow-lg hover:shadow-[rgba(245,122,7,0.3)] cta-pulse btn-scale-hover"
          >
            Start Verifying Free
          </button>
          <button
            onClick={() => scrollToSection('how-it-works')}
            className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 bg-transparent border-2 border-slate-600 hover:border-[#f57a07] text-white rounded-lg text-base sm:text-lg font-semibold transition-all btn-scale-hover"
          >
            See How It Works
          </button>
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 text-xs sm:text-sm">
          <div className="flex items-center gap-2 trust-badge-1">
            <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-[#22d3ee]" />
            <span className="text-slate-400">Verified Sources</span>
          </div>
          <div className="flex items-center gap-2 trust-badge-2">
            <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-[#22d3ee]" />
            <span className="text-slate-400">Real-time Results</span>
          </div>
          <div className="flex items-center gap-2 trust-badge-3">
            <Users className="w-4 h-4 sm:w-5 sm:h-5 text-[#22d3ee]" />
            <span className="text-slate-400">Professional Grade</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HeroSection() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <>
      {/* Mobile Logo - only visible on mobile */}
      <div className="flex justify-center pt-6 md:hidden">
        <Image
          src="/logo.proper.png"
          alt="Tru8 Logo"
          width={102}
          height={34}
          priority
        />
      </div>
      <HeroVisual />
      <HeroContent onOpenAuth={() => setIsAuthModalOpen(true)} />
      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </>
  );
}
