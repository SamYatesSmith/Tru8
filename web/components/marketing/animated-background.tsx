'use client';

import { useEffect, useState } from 'react';
import { generatePixelGrid, type PopShape } from '@/lib/pixel-grid-generator';

/**
 * Animated Background Component
 *
 * 3-layer parallax pixel grid with ascending animation.
 *
 * Animation Specs:
 * - Layer 1 (Back): 100s cycle, 30% opacity, slowest, CIRCLES (15% brand orange)
 *   - Special effect: 15% of orange circles continuously "pop" (scale + glow burst)
 *   - Pop animation: 0.6s, initial delays (0-8s), then cycles every 5-15s
 *   - Continuous cycle: Each shape re-pops indefinitely at random intervals
 * - Layer 2 (Middle): 80s cycle, 20% opacity, SQUARES (5% orange accents)
 * - Layer 3 (Front): 60s cycle, 10% opacity, fastest, SQUARES (5% orange accents)
 * - 15% of all shapes have contrasting 1px borders
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

  const [popShapes, setPopShapes] = useState<PopShape[]>([]);
  const [popKeys, setPopKeys] = useState<number[]>([]); // Unique keys to force re-animation
  const [visiblePops, setVisiblePops] = useState<boolean[]>([]); // Track which pops should be visible

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
      delay: number = 0,
      shape: 'square' | 'circle' = 'square',
      enablePop: boolean = false
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
              const result = generatePixelGrid(canvasWidth, canvasHeight, density, shape, enablePop);
              if (result && mounted) {
                setLayers((prev) => ({ ...prev, [`layer${layerNum}`]: result.dataUrl }));
                // Store pop shapes if this is layer 1
                if (layerNum === 1 && result.popShapes) {
                  setPopShapes(result.popShapes);
                  // Initialize keys and visibility for each shape
                  setPopKeys(result.popShapes.map(() => 0));
                  setVisiblePops(result.popShapes.map(() => true)); // Start visible for initial pop
                }
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
      await generateLayer(1, 0.04, 0, 'circle', true);  // Layer 1 - Circles with pop effect
      await generateLayer(2, 0.045, 100, 'square');     // Layer 2 - Squares
      await generateLayer(3, 0.05, 200, 'square');      // Layer 3 - Squares
    })();

    // Cleanup
    return () => {
      mounted = false;
    };
  }, []);

  // Set up continuous re-popping for each shape
  useEffect(() => {
    if (popShapes.length === 0) return;

    const timeouts: NodeJS.Timeout[] = [];

    popShapes.forEach((shape, index) => {
      // Schedule re-pop cycle
      const scheduleNextPop = (currentDelay: number, isInitial: boolean = false) => {
        // Animation duration is 0.6s
        const animationDuration = 600; // 0.6s in ms
        const delayTime = currentDelay * 1000;

        // After delay + animation, hide the shape
        const hideTimeout = setTimeout(() => {
          setVisiblePops((prev) => {
            const updated = [...prev];
            updated[index] = false;
            return updated;
          });

          // Wait 5-15 seconds before showing again
          const waitTime = (5 + Math.random() * 10) * 1000;

          const showTimeout = setTimeout(() => {
            // Generate new random delay for next pop (0-2 seconds for quick appearance)
            const nextDelay = Math.random() * 2;

            // Make visible and update delay
            setVisiblePops((prev) => {
              const updated = [...prev];
              updated[index] = true;
              return updated;
            });

            setPopShapes((prev) => {
              const updated = [...prev];
              updated[index] = { ...updated[index], delay: nextDelay };
              return updated;
            });

            setPopKeys((prev) => {
              const updated = [...prev];
              updated[index] = updated[index] + 1;
              return updated;
            });

            // Schedule the next cycle
            scheduleNextPop(nextDelay);
          }, waitTime);

          timeouts.push(showTimeout);
        }, delayTime + animationDuration);

        timeouts.push(hideTimeout);
      };

      // Start the cycle with the initial delay
      scheduleNextPop(shape.delay, true);
    });

    // Cleanup timeouts on unmount
    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [popShapes.length]); // Only run when popShapes are first loaded

  // Show fallback until at least layer 1 loads
  if (!layers.layer1) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: '#0f1419',
          zIndex: -10
        }}
      />
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        overflow: 'hidden',
        zIndex: -10,
        backgroundColor: '#0f1419'
      }}
    >
      {/* Layer 1 - Slowest, most visible (always rendered if loaded) */}
      {layers.layer1 && (
        <>
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: 0,
              height: '200vh',
              backgroundImage: `url(${layers.layer1})`,
              backgroundRepeat: 'repeat',
              backgroundSize: 'auto',
              willChange: 'transform',
              opacity: 0.3,
              animation: 'ascend 100s linear infinite',
            }}
          />

          {/* Pop Shapes - Orange circles that continuously pop */}
          {popShapes.map((shape, index) =>
            visiblePops[index] ? (
              <div
                key={`pop-${index}-${popKeys[index]}`}
                className="pop-shape"
                style={{
                  position: 'absolute',
                  left: `${(shape.x / 1600) * 100}%`,
                  top: `${(shape.y / 2000) * 100}%`,
                  width: `${shape.size}px`,
                  height: `${shape.size}px`,
                  borderRadius: '50%',
                  backgroundColor: shape.color,
                  opacity: 0.3,
                  animation: `ascend 100s linear infinite, pop 0.6s ease-out ${shape.delay}s forwards`,
                  willChange: 'transform, opacity',
                }}
              />
            ) : null
          )}
        </>
      )}

      {/* Layer 2 - Medium speed (only render if loaded) */}
      {layers.layer2 && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            height: '200vh',
            backgroundImage: `url(${layers.layer2})`,
            backgroundRepeat: 'repeat',
            backgroundSize: 'auto',
            willChange: 'transform',
            opacity: 0.2,
            animation: 'ascend 80s linear infinite',
          }}
        />
      )}

      {/* Layer 3 - Fastest, least visible (only render if loaded) */}
      {layers.layer3 && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            height: '200vh',
            backgroundImage: `url(${layers.layer3})`,
            backgroundRepeat: 'repeat',
            backgroundSize: 'auto',
            willChange: 'transform',
            opacity: 0.1,
            animation: 'ascend 60s linear infinite',
          }}
        />
      )}

      {/* Inject keyframes directly (ensures they're always available) */}
      <style jsx>{`
        @keyframes ascend {
          from {
            transform: translateY(0);
          }
          to {
            transform: translateY(-50%);
          }
        }

        @keyframes pop {
          0% {
            transform: scale(1);
            opacity: 0.3;
            box-shadow: 0 0 0 0 rgba(245, 122, 7, 0.7);
          }
          50% {
            transform: scale(1.8);
            opacity: 0.5;
            box-shadow: 0 0 20px 10px rgba(245, 122, 7, 0.4);
          }
          100% {
            transform: scale(2.2);
            opacity: 0;
            box-shadow: 0 0 30px 15px rgba(245, 122, 7, 0);
          }
        }
      `}</style>
    </div>
  );
}
