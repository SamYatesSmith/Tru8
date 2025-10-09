'use client';

import { useEffect, useState } from 'react';
import { generatePixelGrid } from '@/lib/pixel-grid-generator';

/**
 * Animated Background Component
 *
 * 3-layer parallax pixel grid with ascending animation.
 *
 * Animation Specs:
 * - Layer 1 (Back): 100s cycle, 30% opacity, slowest
 * - Layer 2 (Middle): 80s cycle, 20% opacity
 * - Layer 3 (Front): 60s cycle, 10% opacity, fastest
 * - Each layer is 200vh tall to prevent blank space during animation
 * - Animation translateY(-50%) moves up by 100vh, always keeping viewport covered
 *
 * Accessibility:
 * - Respects prefers-reduced-motion (disables animation)
 *
 * Performance:
 * - GPU-accelerated (will-change: transform)
 * - Pure CSS animation (no JavaScript RAF)
 * - Dynamic canvas height (2x viewport) for seamless tiling
 */
export function AnimatedBackground() {
  const [layers, setLayers] = useState<{
    layer1: string;
    layer2: string;
    layer3: string;
  } | null>(null);

  useEffect(() => {
    // Generate pixel grids on mount (client-side only)
    try {
      // Fixed canvas size - large enough to tile seamlessly but not memory-intensive
      // 1920x2400 is sufficient for smooth tiling on all screen sizes
      const canvasWidth = 1920;
      const canvasHeight = 2400;

      const layer1 = generatePixelGrid(canvasWidth, canvasHeight, 0.05);
      const layer2 = generatePixelGrid(canvasWidth, canvasHeight, 0.06);
      const layer3 = generatePixelGrid(canvasWidth, canvasHeight, 0.07);

      // Only set layers if they were generated successfully
      if (layer1 && layer2 && layer3) {
        setLayers({ layer1, layer2, layer3 });
      }
    } catch (error) {
      console.error('Failed to generate pixel grids:', error);
    }
  }, []);

  if (!layers) {
    // Loading state - show solid dark background
    return <div className="fixed inset-0 bg-[#0f1419] -z-10" />;
  }

  return (
    <div className="fixed inset-0 overflow-hidden -z-10 bg-[#0f1419]">
      {/* Layer 1 - Slowest, most visible */}
      <div
        className="absolute left-0 right-0 top-0 animate-ascend-slow opacity-30"
        style={{
          height: '200vh',
          backgroundImage: `url(${layers.layer1})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />

      {/* Layer 2 - Medium speed */}
      <div
        className="absolute left-0 right-0 top-0 animate-ascend-medium opacity-20"
        style={{
          height: '200vh',
          backgroundImage: `url(${layers.layer2})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />

      {/* Layer 3 - Fastest, least visible */}
      <div
        className="absolute left-0 right-0 top-0 animate-ascend-fast opacity-10"
        style={{
          height: '200vh',
          backgroundImage: `url(${layers.layer3})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />
    </div>
  );
}
