"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { VerdictPill } from "./verdict-pill";
import { CitationChip } from "./citation-chip";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface Evidence {
  id: string;
  source: string;
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string;
  relevanceScore: number;
}

interface Claim {
  id: string;
  text: string;
  verdict: 'supported' | 'contradicted' | 'uncertain';
  confidence: number;
  rationale: string;
  evidence: Evidence[];
  position: number;
}

interface ClaimCardProps {
  claim: Claim;
  className?: string;
}

export function ClaimCard({ claim, className }: ClaimCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className={cn("relative", className)}>
      <CardHeader className="pb-4">
        {/* Claim Text */}
        <div className="space-y-3">
          <p className="text-base leading-relaxed">{claim.text}</p>
          
          {/* Verdict and Confidence */}
          <div className="flex items-center justify-between">
            <VerdictPill 
              verdict={claim.verdict} 
              confidence={claim.confidence}
            />
            <span className="text-sm text-muted-foreground">
              Claim {claim.position + 1}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Rationale */}
        <div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {claim.rationale}
          </p>
        </div>

        {/* Top Citations (always visible) */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Sources:</h4>
          <div className="flex flex-wrap gap-2">
            {claim.evidence.slice(0, 2).map((evidence) => (
              <CitationChip 
                key={evidence.id}
                source={evidence.source}
                date={evidence.publishedDate}
                url={evidence.url}
              />
            ))}
            {claim.evidence.length > 2 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-6 px-2 text-xs"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    +{claim.evidence.length - 2} more
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Expanded Evidence Details */}
        {isExpanded && claim.evidence.length > 2 && (
          <div className="space-y-3 pt-2 border-t">
            <h4 className="text-sm font-medium">Additional Sources:</h4>
            {claim.evidence.slice(2).map((evidence) => (
              <div key={evidence.id} className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <CitationChip 
                    source={evidence.source}
                    date={evidence.publishedDate}
                    url={evidence.url}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => window.open(evidence.url, '_blank')}
                  >
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                </div>
                <blockquote className="text-xs text-muted-foreground border-l-2 border-border pl-3">
                  "{evidence.snippet}"
                </blockquote>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}