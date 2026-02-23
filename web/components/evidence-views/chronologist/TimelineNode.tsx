interface TimelineNodeProps {
  color: string;
  title: string;
  domain: string;
  date: string;
  tier?: string;
  url?: string;
  label?: string;
}

export function TimelineNode({ color, title, domain, date, tier, url, label }: TimelineNodeProps) {
  const handleClick = () => {
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <button onClick={handleClick} className="group relative cursor-pointer">
      <div
        className="w-3 h-3 rounded-full border-2 border-white shadow-sm transition-transform group-hover:scale-150"
        style={{ backgroundColor: color }}
      />
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20 pointer-events-none">
        <div className="bg-zinc-900 text-white px-3 py-2 max-w-[200px]">
          <p className="font-mono text-[10px] font-medium truncate">{title}</p>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="font-mono text-[9px] text-zinc-400">{domain}</span>
            <span className="font-mono text-[9px] text-zinc-600">&middot;</span>
            <span className="font-mono text-[9px] text-zinc-400">{date}</span>
          </div>
          {tier && (
            <span className="font-mono text-[8px] uppercase tracking-wider text-zinc-500 mt-1 block">{tier}</span>
          )}
          {label && (
            <span className="font-mono text-[8px] text-zinc-500 mt-0.5 block">{label}</span>
          )}
        </div>
      </div>
    </button>
  );
}
