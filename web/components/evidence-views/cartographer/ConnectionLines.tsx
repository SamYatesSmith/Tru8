'use client';

interface ConnectionLinesProps {
  edges: Array<{ fromId: string; toId: string }>;
  nodePositions: Map<string, { x: number; y: number; width: number; height: number }>;
  containerWidth: number;
  containerHeight: number;
}

export function ConnectionLines({ edges, nodePositions, containerWidth, containerHeight }: ConnectionLinesProps) {
  if (edges.length === 0) return null;

  const paths: Array<{ key: string; d: string }> = [];

  for (const edge of edges) {
    const from = nodePositions.get(edge.fromId);
    const to = nodePositions.get(edge.toId);
    if (!from || !to) continue;

    const x1 = from.x + from.width / 2;
    const y1 = from.y + from.height;
    const x2 = to.x + to.width / 2;
    const y2 = to.y;

    // Simple path with slight curve for offset connections
    const midY = (y1 + y2) / 2;
    const d = Math.abs(x1 - x2) < 5
      ? `M${x1},${y1} L${x2},${y2}`
      : `M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`;

    paths.push({ key: `${edge.fromId}-${edge.toId}`, d });
  }

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={containerWidth}
      height={containerHeight}
      style={{ overflow: 'visible' }}
    >
      {paths.map(({ key, d }) => (
        <path
          key={key}
          d={d}
          stroke="#D4D4D8"
          strokeWidth={1}
          fill="none"
        />
      ))}
    </svg>
  );
}
