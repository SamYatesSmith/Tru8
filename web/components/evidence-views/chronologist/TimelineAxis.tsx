import type { TickMark } from './ChronologistView';

interface TimelineAxisProps {
  ticks: TickMark[];
}

export function TimelineAxis({ ticks }: TimelineAxisProps) {
  return (
    <div className="relative h-8 border-t border-zinc-200">
      {ticks.map((tick, i) => (
        <div
          key={i}
          className="absolute top-0"
          style={{ left: `${tick.position}%`, transform: 'translateX(-50%)' }}
        >
          <div className="w-[1px] h-2 bg-zinc-300 mx-auto" />
          <span className="block font-mono text-[9px] text-zinc-400 whitespace-nowrap mt-1">
            {tick.label}
          </span>
        </div>
      ))}
    </div>
  );
}
