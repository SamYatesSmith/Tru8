interface UsageCardProps {
  used: number;
  total: number;
  label: string;
}

export function UsageCard({ used, total, label }: UsageCardProps) {
  const percentage = (used / total) * 100;

  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-2">Usage Summary</h3>
      <p className="text-slate-400 mb-6">{label}: {used} / {total}</p>

      <div className="flex items-end justify-between mb-4">
        <div className="text-6xl font-black text-white">{used}</div>
        <div className="text-2xl text-slate-400">/ {total}</div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
