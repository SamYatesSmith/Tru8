import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface VerdictPillProps {
  verdict: 'supported' | 'contradicted' | 'uncertain';
}

const verdictConfig = {
  supported: {
    icon: CheckCircle2,
    label: 'SUPPORTED',
    bgColor: 'bg-emerald-900/30',
    textColor: 'text-emerald-400',
    borderColor: 'border-emerald-600',
  },
  contradicted: {
    icon: XCircle,
    label: 'CONTRADICTED',
    bgColor: 'bg-red-900/30',
    textColor: 'text-red-400',
    borderColor: 'border-red-600',
  },
  uncertain: {
    icon: AlertCircle,
    label: 'UNCERTAIN',
    bgColor: 'bg-amber-900/30',
    textColor: 'text-amber-400',
    borderColor: 'border-amber-600',
  },
};

export function VerdictPill({ verdict }: VerdictPillProps) {
  const config = verdictConfig[verdict];
  const Icon = config.icon;

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor}`}>
      <Icon size={16} />
      <span className="text-xs font-bold">{config.label}</span>
    </div>
  );
}
