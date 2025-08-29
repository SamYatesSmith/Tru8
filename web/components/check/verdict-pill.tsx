import { Badge } from "@/components/ui/badge";
import { getVerdictBadgeClass } from "@/lib/utils";
import { VERDICT_LABELS, VERDICT_ICONS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface VerdictPillProps {
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function VerdictPill({ verdict, confidence, size = 'md', className }: VerdictPillProps) {
  const sizeClasses = {
    sm: "text-xs px-2 py-1",
    md: "text-sm px-3 py-1.5", 
    lg: "text-base px-4 py-2",
  };

  const confidenceClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div className={cn(
        "inline-flex items-center gap-1 rounded-full font-semibold",
        sizeClasses[size],
        getVerdictBadgeClass(verdict)
      )}>
        <span>
          {VERDICT_ICONS[verdict]}
        </span>
        {VERDICT_LABELS[verdict]}
      </div>
      {confidence !== undefined && (
        <span className={cn("font-medium text-muted-foreground", confidenceClasses[size])}>
          {Math.round(confidence)}%
        </span>
      )}
    </div>
  );
}