import { Badge } from "@/components/ui/badge";
import { getVerdictBadgeClass } from "@/lib/utils";
import { VERDICT_LABELS, VERDICT_ICONS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface VerdictPillProps {
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence?: number;
  className?: string;
}

export function VerdictPill({ verdict, confidence, className }: VerdictPillProps) {
  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div className={cn(
        "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium",
        getVerdictBadgeClass(verdict)
      )}>
        <span className="text-sm">
          {VERDICT_ICONS[verdict]}
        </span>
        {VERDICT_LABELS[verdict]}
      </div>
      {confidence !== undefined && (
        <span className="text-sm font-medium text-muted-foreground">
          {Math.round(confidence)}%
        </span>
      )}
    </div>
  );
}