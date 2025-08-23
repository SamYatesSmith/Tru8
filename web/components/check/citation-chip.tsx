"use client";

import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";
import { formatDate } from "@/lib/utils";

interface CitationChipProps {
  source: string;
  date?: string;
  url: string;
  className?: string;
}

export function CitationChip({ source, date, url, className }: CitationChipProps) {
  const handleClick = () => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleClick}
      className="h-7 px-2 text-xs gap-1 max-w-48"
    >
      <span className="truncate">{source}</span>
      {date && (
        <>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">
            {formatDate(date)}
          </span>
        </>
      )}
      <ExternalLink className="h-3 w-3 flex-shrink-0" />
    </Button>
  );
}