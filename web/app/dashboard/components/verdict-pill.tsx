import { CheckCircle2, XCircle, AlertCircle, HelpCircle, Scale, Clock } from 'lucide-react';
import type { VerdictType } from '@shared/constants';

interface VerdictPillProps {
  verdict: VerdictType;
}

const verdictConfig: Record<VerdictType, {
  icon: any;
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
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
  insufficient_evidence: {
    icon: HelpCircle,
    label: 'INSUFFICIENT EVIDENCE',
    bgColor: 'bg-gray-900/30',
    textColor: 'text-gray-400',
    borderColor: 'border-gray-600',
  },
  conflicting_expert_opinion: {
    icon: Scale,
    label: 'CONFLICTING OPINIONS',
    bgColor: 'bg-purple-900/30',
    textColor: 'text-purple-400',
    borderColor: 'border-purple-600',
  },
  outdated_claim: {
    icon: Clock,
    label: 'OUTDATED',
    bgColor: 'bg-slate-900/30',
    textColor: 'text-slate-400',
    borderColor: 'border-slate-600',
  },
};

export function VerdictPill({ verdict }: VerdictPillProps) {
  const config = verdictConfig[verdict];
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor}`}>
      <Icon size={16} />
      <span className="text-xs font-bold">{config.label}</span>
    </span>
  );
}
