/**
 * Pixel Grid Generator
 *
 * Generates seamless tiling pixel grid patterns for animated background.
 *
 * Specifications:
 * - 3 layers (back, middle, front)
 * - Shapes: Circles or rounded squares (configurable per layer)
 * - Pixel sizes: 8px, 12px, 16px (mixed)
 * - Colors: slate-300, slate-400, slate-500, stone-300, orange (#f57a07)
 *   - Circles: 15% orange, 85% slate/stone mix
 *   - Squares: 5% orange, 95% slate/stone mix
 * - Borders: 15% of shapes have 1px contrasting borders
 * - Pop effect: 15% of orange circles can be marked for pop animation (optional)
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
const CORNER_RADIUS = 2; // Softened corners for pixels
const BORDER_WIDTH = 1; // Narrow border width for accented shapes

// Contrasting border colors for each main color
const BORDER_COLORS: Record<string, string> = {
  '#cbd5e1': '#334155', // slate-300 → slate-700 (light to dark)
  '#94a3b8': '#334155', // slate-400 → slate-700 (medium to dark)
  '#64748b': '#cbd5e1', // slate-500 → slate-300 (dark to light)
  '#d6d3d1': '#334155', // stone-300 → slate-700 (light to dark)
  '#f57a07': '#d97706', // orange → darker amber
};

/**
 * Draw a rounded rectangle on canvas
 */
function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
  borderColor?: string
): void {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();

  // Draw border if specified
  if (borderColor) {
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = BORDER_WIDTH;
    ctx.stroke();
  }

  ctx.fill();
}

/**
 * Draw a circle on canvas
 */
function drawCircle(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  borderColor?: string
): void {
  ctx.beginPath();
  ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);

  // Draw border if specified
  if (borderColor) {
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = BORDER_WIDTH;
    ctx.stroke();
  }

  ctx.fill();
}

export interface PopShape {
  x: number;
  y: number;
  size: number;
  delay: number; // Animation delay in seconds
  color: string;
}

export interface PixelGridResult {
  dataUrl: string;
  popShapes?: PopShape[]; // Only for circles with pop effects
}

/**
 * Generate a pixel grid pattern as a data URL
 *
 * @param width - Canvas width (default: 1920px)
 * @param height - Canvas height (default: 2160px, 2x viewport for seamless loop)
 * @param density - Percentage of pixels filled (0.03 = 3%)
 * @param shape - Shape type: 'square' (default) or 'circle'
 * @param enablePop - If true, 15% of orange circles will pop (only for circles)
 * @returns Object with dataUrl and optional popShapes array
 */
export function generatePixelGrid(
  width: number = 1920,
  height: number = 2160,
  density: number = 0.03, // 3% of pixels filled
  shape: 'square' | 'circle' = 'square',
  enablePop: boolean = false
): PixelGridResult {
  if (typeof window === 'undefined') {
    // Server-side rendering - return empty result
    return { dataUrl: '', popShapes: [] };
  }

  // Reduced canvas size limits to prevent memory issues and chunk loading timeouts
  const MAX_CANVAS_DIMENSION = 2048; // Reduced from 4096 for better performance
  const MAX_CANVAS_AREA = 4194304;  // 2048 * 2048 (reduced from 16MB)

  // Check dimensions and scale down aggressively
  if (width > MAX_CANVAS_DIMENSION || height > MAX_CANVAS_DIMENSION) {
    console.warn(`Canvas size ${width}x${height} exceeds safe limits, scaling down`);
    const scale = Math.min(MAX_CANVAS_DIMENSION / width, MAX_CANVAS_DIMENSION / height);
    width = Math.floor(width * scale);
    height = Math.floor(height * scale);
  }

  // Check total area
  const requestedArea = width * height;
  if (requestedArea > MAX_CANVAS_AREA) {
    throw new Error(`Canvas area ${requestedArea} exceeds maximum ${MAX_CANVAS_AREA}`);
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

  // Track orange circles for pop effect
  const popShapes: PopShape[] = [];
  const orangeCircles: { x: number; y: number; size: number }[] = [];

  for (let i = 0; i < totalPixels; i++) {
    // Random position
    const x = Math.floor(Math.random() * width);
    const y = Math.floor(Math.random() * height);

    // Random pixel size
    const size = PIXEL_SIZES[Math.floor(Math.random() * PIXEL_SIZES.length)];

    // Random color (weighted distribution)
    // For circles: 15% orange, for squares: 5% orange
    let color: string;
    const rand = Math.random();

    if (shape === 'circle') {
      // Circle color distribution: 15% orange
      if (rand < 0.28) color = COLORS[0]; // slate-300 (28%)
      else if (rand < 0.53) color = COLORS[1]; // slate-400 (25%)
      else if (rand < 0.73) color = COLORS[2]; // slate-500 (20%)
      else if (rand < 0.85) color = COLORS[3]; // stone-300 (12%)
      else color = COLORS[4]; // orange (15% - higher for circles)
    } else {
      // Square color distribution: 5% orange
      if (rand < 0.30) color = COLORS[0]; // slate-300 (30%)
      else if (rand < 0.55) color = COLORS[1]; // slate-400 (25%)
      else if (rand < 0.75) color = COLORS[2]; // slate-500 (20%)
      else if (rand < 0.95) color = COLORS[3]; // stone-300 (20%)
      else color = COLORS[4]; // orange (5% - rare accent)
    }

    // Track orange circles for potential pop effect
    const isOrangeCircle = shape === 'circle' && color === COLORS[4];
    if (isOrangeCircle && enablePop) {
      orangeCircles.push({ x, y, size });
    }

    // 15% chance of having a contrasting border
    const hasBorder = Math.random() < 0.15;
    const borderColor = hasBorder ? BORDER_COLORS[color] : undefined;

    // Draw shape based on type
    ctx.fillStyle = color;
    if (shape === 'circle') {
      drawCircle(ctx, x, y, size, borderColor);
    } else {
      drawRoundedRect(ctx, x, y, size, size, CORNER_RADIUS, borderColor);
    }
  }

  // Select 15% of orange circles to pop (if pop is enabled)
  if (enablePop && shape === 'circle' && orangeCircles.length > 0) {
    const numPopShapes = Math.max(1, Math.floor(orangeCircles.length * 0.15));

    // Randomly select shapes to pop
    const shuffled = [...orangeCircles].sort(() => Math.random() - 0.5);
    const selectedForPop = shuffled.slice(0, numPopShapes);

    // Create pop shapes with random delays (0-8 seconds)
    selectedForPop.forEach(({ x, y, size }) => {
      popShapes.push({
        x,
        y,
        size,
        delay: Math.random() * 8,
        color: COLORS[4], // orange
      });
    });
  }

  // Convert to data URL with error handling
  try {
    const dataUrl = canvas.toDataURL('image/png');

    // Validate output
    if (!dataUrl || dataUrl.length < 100) {
      throw new Error('Generated invalid or empty data URL');
    }

    // Log memory usage for debugging (only on first call)
    if (typeof window !== 'undefined' && !(window as any).__pixelGridMemoryLogged) {
      const sizeInMB = (dataUrl.length / (1024 * 1024)).toFixed(2);
      console.log(`[PixelGrid] Generated ${width}x${height} canvas: ${sizeInMB}MB`);
      if (popShapes.length > 0) {
        console.log(`[PixelGrid] Generated ${popShapes.length} pop shapes`);
      }
      (window as any).__pixelGridMemoryLogged = true;
    }

    return {
      dataUrl,
      popShapes: popShapes.length > 0 ? popShapes : undefined,
    };
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Unknown error';
    console.error(`[PixelGrid] Failed to convert canvas to data URL: ${errorMsg}`);
    throw new Error(`Canvas encoding failed: ${errorMsg}`);
  }
}
