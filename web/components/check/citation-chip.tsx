"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Shield, AlertCircle, Info } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

interface CitationChipProps {
  source: string;
  date?: string;
  url: string;
  relevanceScore?: number;
  showCredibility?: boolean;
  className?: string;
}

export function CitationChip({ 
  source, 
  date, 
  url, 
  relevanceScore,
  showCredibility = false,
  className 
}: CitationChipProps) {
  const handleClick = () => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Determine credibility based on source reputation (simplified for MVP)
  const getCredibilityIndicator = () => {
    const trustedSources = ['bbc', 'reuters', 'ap', 'guardian', 'nytimes', 'washingtonpost', 'nature', 'science'];
    const sourceLower = source.toLowerCase();
    
    if (trustedSources.some(trusted => sourceLower.includes(trusted))) {
      return { icon: Shield, color: 'text-green-600', label: 'Trusted' };
    }
    
    if (relevanceScore && relevanceScore > 0.7) {
      return { icon: Info, color: 'text-blue-600', label: 'Relevant' };
    }
    
    return { icon: AlertCircle, color: 'text-gray-400', label: 'Unverified' };
  };

  const credibility = showCredibility ? getCredibilityIndicator() : null;
  const CredIcon = credibility?.icon;

  return (
    <div className={cn("inline-flex items-center gap-1", className)}>
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        className={cn(
          "h-7 px-2 text-xs gap-1",
          showCredibility ? "max-w-64" : "max-w-48"
        )}
      >
        {showCredibility && CredIcon && (
          <CredIcon className={cn("h-3 w-3 flex-shrink-0", credibility.color)} />
        )}
        <span className="truncate font-medium">{source}</span>
        {date && (
          <>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">
              {formatDate(date)}
            </span>
          </>
        )}
        {relevanceScore !== undefined && (
          <>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">
              {Math.round(relevanceScore * 100)}%
            </span>
          </>
        )}
        <ExternalLink className="h-3 w-3 flex-shrink-0 ml-1" />
      </Button>
      
      {showCredibility && credibility && (
        <Badge 
          variant="outline" 
          className={cn("h-5 text-xs px-1", credibility.color)}
        >
          {credibility.label}
        </Badge>
      )}
    </div>
  );
}