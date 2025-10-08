/**
 * Pixel Grid Generator
 *
 * Generates seamless tiling pixel grid patterns for animated background.
 *
 * Specifications:
 * - 3 layers (back, middle, front)
 * - Pixel sizes: 8px, 12px, 16px (mixed)
 * - Colors: slate-300, slate-400, slate-500, stone-300, orange (#f57a07) sparse
 * - Pattern: 2x viewport height for seamless looping
 * - Seamless horizontal + vertical tiling
 */

const COLORS = [
  '#cbd5e1', // slate-300 (30% frequency)
  '#94a3b8', // slate-400 (25% frequency)
  '#64748b', // slate-500 (20% frequency)
  '#d6d3d1', // stone-300 (20% frequency)
  '#f57a07', // orange (5% frequency - accent)
];

const PIXEL_SIZES = [8, 12, 16];

/**
 * Generate a pixel grid pattern as a data URL
 *
 * @param width - Canvas width (default: 1920px)
 * @param height - Canvas height (default: 2160px, 2x viewport for seamless loop)
 * @param density - Percentage of pixels filled (0.03 = 3%)
 * @returns Data URL for use in CSS background-image
 */
export function generatePixelGrid(
  width: number = 1920,
  height: number = 2160,
  density: number = 0.03 // 3% of pixels filled
): string {
  if (typeof window === 'undefined') {
    // Server-side rendering - return empty string
    return '';
  }

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  if (!ctx) throw new Error('Canvas context not available');

  // Fill with transparent background
  ctx.clearRect(0, 0, width, height);

  // Calculate number of pixels based on density
  const totalPixels = Math.floor((width * height) / 256) * density;

  for (let i = 0; i < totalPixels; i++) {
    // Random position
    const x = Math.floor(Math.random() * width);
    const y = Math.floor(Math.random() * height);

    // Random pixel size
    const size = PIXEL_SIZES[Math.floor(Math.random() * PIXEL_SIZES.length)];

    // Random color (weighted distribution)
    let color: string;
    const rand = Math.random();
    if (rand < 0.30) color = COLORS[0]; // slate-300 (30%)
    else if (rand < 0.55) color = COLORS[1]; // slate-400 (25%)
    else if (rand < 0.75) color = COLORS[2]; // slate-500 (20%)
    else if (rand < 0.95) color = COLORS[3]; // stone-300 (20%)
    else color = COLORS[4]; // orange (5% - rare accent)

    // Draw pixel
    ctx.fillStyle = color;
    ctx.fillRect(x, y, size, size);
  }

  // Return as data URL
  return canvas.toDataURL('image/png');
}
