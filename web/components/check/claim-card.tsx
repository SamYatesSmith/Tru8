"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { VerdictPill } from "./verdict-pill";
import { CitationChip } from "./citation-chip";
import { ConfidenceBar } from "./confidence-bar";
import { EvidenceDrawer } from "./evidence-drawer";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, ExternalLink, FileSearch } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Claim, Evidence } from "@shared/types";

interface ClaimCardProps {
  claim: Claim;
  index?: number;
  className?: string;
}

export function ClaimCard({ claim, index, className }: ClaimCardProps) {
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
              Claim {index || claim.position + 1}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Confidence Bar */}
        <ConfidenceBar 
          confidence={claim.confidence}
          verdict={claim.verdict}
          size="md"
          animated={true}
        />
        
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
                relevanceScore={evidence.relevanceScore}
                showCredibility={true}
              />
            ))}
            {claim.evidence.length > 2 && (
              <EvidenceDrawer 
                evidence={claim.evidence}
                claimText={claim.text}
                verdict={claim.verdict}
              >
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                >
                  <FileSearch className="h-3 w-3 mr-1" />
                  View all {claim.evidence.length} sources
                </Button>
              </EvidenceDrawer>
            )}
          </div>
        </div>

      </CardContent>
    </Card>
  );
}