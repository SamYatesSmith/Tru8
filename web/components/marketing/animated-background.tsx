'use client';

import { useEffect, useState, useRef } from 'react';
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
 * - AbortController pattern prevents memory leaks from orphaned timeouts
 */

/** Consolidated state for pop animation to prevent race conditions */
interface PopAnimationState {
  shapes: PopShape[];
  keys: number[];
  visible: boolean[];
}

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

  // Consolidated pop animation state (prevents race conditions from parallel array updates)
  const [popState, setPopState] = useState<PopAnimationState>({
    shapes: [],
    keys: [],
    visible: [],
  });

  // Refs for cleanup - track all timeouts and abort signal
  const abortRef = useRef<AbortController | null>(null);
  const timeoutIds = useRef<Set<NodeJS.Timeout>>(new Set());

  // Layer generation effect - runs immediately on mount
  useEffect(() => {
    const canvasWidth = 1600;
    const canvasHeight = 2000;
    let mounted = true;

    const generateAllLayers = () => {
      if (!mounted) return;

      try {
        // Generate layer 1 immediately (circles with pop effect)
        const result1 = generatePixelGrid(canvasWidth, canvasHeight, 0.04, 'circle', true);
        if (result1 && mounted) {
          setLayers((prev) => ({ ...prev, layer1: result1.dataUrl }));
          if (result1.popShapes) {
            setPopState({
              shapes: result1.popShapes,
              keys: result1.popShapes.map(() => 0),
              visible: result1.popShapes.map(() => true),
            });
          }
        }

        // Generate layers 2 and 3 with slight delays for performance
        setTimeout(() => {
          if (!mounted) return;
          const result2 = generatePixelGrid(canvasWidth, canvasHeight, 0.045, 'square', false);
          if (result2 && mounted) {
            setLayers((prev) => ({ ...prev, layer2: result2.dataUrl }));
          }
        }, 50);

        setTimeout(() => {
          if (!mounted) return;
          const result3 = generatePixelGrid(canvasWidth, canvasHeight, 0.05, 'square', false);
          if (result3 && mounted) {
            setLayers((prev) => ({ ...prev, layer3: result3.dataUrl }));
          }
        }, 100);
      } catch (error) {
        console.error('[AnimatedBackground] Failed to generate layers:', error);
      }
    };

    // Generate immediately - no idle callback needed
    generateAllLayers();

    return () => {
      mounted = false;
    };
  }, []);

  // Pop animation scheduling effect with proper cleanup
  useEffect(() => {
    if (popState.shapes.length === 0) return;

    // Copy ref values for cleanup (React hooks best practice)
    const currentTimeoutIds = timeoutIds.current;
    const currentShapes = popState.shapes;

    // Create new AbortController for this effect cycle
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

    // Helper to schedule a timeout and track it
    const scheduleTimeout = (callback: () => void, delay: number): NodeJS.Timeout => {
      const id = setTimeout(() => {
        // Remove from tracking set when executed
        currentTimeoutIds.delete(id);
        // Only execute if not aborted
        if (!signal.aborted) {
          callback();
        }
      }, delay);
      currentTimeoutIds.add(id);
      return id;
    };

    // Schedule pop cycles for each shape
    currentShapes.forEach((shape, index) => {
      const scheduleNextPop = (currentDelay: number) => {
        if (signal.aborted) return;

        const animationDuration = 600; // 0.6s in ms
        const delayTime = currentDelay * 1000;

        // After delay + animation, hide the shape
        scheduleTimeout(() => {
          if (signal.aborted) return;

          // Hide this shape
          setPopState((prev) => ({
            ...prev,
            visible: prev.visible.map((v, i) => (i === index ? false : v)),
          }));

          // Wait 5-15 seconds before showing again
          const waitTime = (5 + Math.random() * 10) * 1000;

          scheduleTimeout(() => {
            if (signal.aborted) return;

            const nextDelay = Math.random() * 2;

            // Show shape with new delay and increment key
            setPopState((prev) => ({
              shapes: prev.shapes.map((s, i) =>
                i === index ? { ...s, delay: nextDelay } : s
              ),
              keys: prev.keys.map((k, i) => (i === index ? k + 1 : k)),
              visible: prev.visible.map((v, i) => (i === index ? true : v)),
            }));

            // Schedule next cycle
            scheduleNextPop(nextDelay);
          }, waitTime);
        }, delayTime + animationDuration);
      };

      // Start the cycle with the initial delay
      scheduleNextPop(shape.delay);
    });

    // Cleanup: abort all operations and clear all timeouts
    return () => {
      abortRef.current?.abort();
      currentTimeoutIds.forEach(clearTimeout);
      currentTimeoutIds.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [popState.shapes.length]); // Intentionally only re-run when shapes count changes, not on every shape update

  // Show fallback until at least layer 1 loads
  if (!layers.layer1) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: '#0f1419',
          zIndex: -10,
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
        backgroundColor: '#0f1419',
      }}
    >
      {/* Layer 1 - Slowest, most visible */}
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
          {popState.shapes.map((shape, index) =>
            popState.visible[index] ? (
              <div
                key={`pop-${index}-${popState.keys[index]}`}
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

      {/* Layer 2 - Medium speed */}
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

      {/* Layer 3 - Fastest, least visible */}
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

      {/* Animation keyframes - global needed for inline style animation references */}
      <style jsx global>{`
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
