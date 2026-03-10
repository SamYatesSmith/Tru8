interface UsageCardProps {
  used: number;
  total: number;
  label: string;
}

export function UsageCard({ used, total, label }: UsageCardProps) {
  const percentage = total > 0 ? (used / total) * 100 : 0;

  return (
    <div className="bg-white border border-zinc-200 p-8">
      <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-900 mb-2">Usage Summary</h3>
      <p className="text-zinc-500 text-sm mb-6">{label}: {used} / {total}</p>

      <div className="flex items-end justify-between mb-4">
        <div className="text-5xl font-mono font-light text-[var(--accent)]">{used}</div>
        <div className="text-xl text-zinc-400 font-mono">/ {total}</div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-1.5 bg-zinc-100 overflow-hidden">
        <div
          className="h-full bg-[var(--accent)] transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
