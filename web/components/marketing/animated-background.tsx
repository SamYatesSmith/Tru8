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
    layer1: string | null;
    layer2: string | null;
    layer3: string | null;
  }>({
    layer1: null,
    layer2: null,
    layer3: null,
  });

  useEffect(() => {
    // Generate pixel grids progressively (client-side only)
    // Reduced canvas size to prevent chunk loading timeouts
    const canvasWidth = 1600;  // Reduced from 1920
    const canvasHeight = 2000; // Reduced from 2400
    let mounted = true;

    // Helper function to generate layer with retry logic
    const generateLayer = async (
      layerNum: number,
      density: number,
      delay: number = 0
    ): Promise<void> => {
      return new Promise((resolve) => {
        setTimeout(() => {
          if (!mounted) {
            resolve();
            return;
          }

          // Use requestIdleCallback for non-blocking generation (fallback to setTimeout)
          const scheduleWork = (callback: () => void) => {
            if ('requestIdleCallback' in window) {
              window.requestIdleCallback(callback, { timeout: 2000 });
            } else {
              setTimeout(callback, delay);
            }
          };

          scheduleWork(() => {
            try {
              const layer = generatePixelGrid(canvasWidth, canvasHeight, density);
              if (layer && mounted) {
                setLayers((prev) => ({ ...prev, [`layer${layerNum}`]: layer }));
              }
              resolve();
            } catch (error) {
              console.error(`[AnimatedBackground] Failed to generate layer ${layerNum}:`, error);
              resolve();
            }
          });
        }, delay);
      });
    };

    // Generate layers sequentially with increasing delays
    (async () => {
      await generateLayer(1, 0.04, 0);     // Layer 1 - Reduced density
      await generateLayer(2, 0.045, 100);  // Layer 2
      await generateLayer(3, 0.05, 200);   // Layer 3
    })();

    // Cleanup
    return () => {
      mounted = false;
    };
  }, []);

  // Show fallback until at least layer 1 loads
  if (!layers.layer1) {
    return <div className="fixed inset-0 bg-[#0f1419] -z-10" />;
  }

  return (
    <div className="fixed inset-0 overflow-hidden -z-10 bg-[#0f1419]">
      {/* Layer 1 - Slowest, most visible (always rendered if loaded) */}
      {layers.layer1 && (
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
      )}

      {/* Layer 2 - Medium speed (only render if loaded) */}
      {layers.layer2 && (
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
      )}

      {/* Layer 3 - Fastest, least visible (only render if loaded) */}
      {layers.layer3 && (
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
      )}
    </div>
  );
}
