"use client";

import { 
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
  SheetClose
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ExternalLink, Calendar, BarChart, FileText } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { ConfidenceBar } from "./confidence-bar";
import type { Evidence } from "@shared/types";

interface EvidenceDrawerProps {
  evidence: Evidence[];
  claimText: string;
  verdict: 'supported' | 'contradicted' | 'uncertain';
  children: React.ReactNode;
}

export function EvidenceDrawer({ 
  evidence, 
  claimText,
  verdict,
  children 
}: EvidenceDrawerProps) {
  const getRelevanceLabel = (score: number) => {
    if (score >= 0.8) return { label: "High", color: "bg-green-100 text-green-800" };
    if (score >= 0.5) return { label: "Medium", color: "bg-yellow-100 text-yellow-800" };
    return { label: "Low", color: "bg-gray-100 text-gray-800" };
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Evidence Details</SheetTitle>
          <SheetDescription className="text-left">
            <div className="space-y-3 mt-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-1">Claim:</h4>
                <p className="text-sm text-gray-700">{claimText}</p>
              </div>
            </div>
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-200px)] mt-6">
          <div className="space-y-4 pr-4">
            {evidence.map((item, index) => {
              const relevance = getRelevanceLabel(item.relevanceScore);
              
              return (
                <div 
                  key={item.id} 
                  className="card border-l-4 hover:shadow-md transition-shadow"
                  style={{
                    borderLeftColor: verdict === 'supported' 
                      ? 'var(--verdict-supported)' 
                      : verdict === 'contradicted' 
                      ? 'var(--verdict-contradicted)'
                      : 'var(--verdict-uncertain)'
                  }}
                >
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 space-y-1">
                        <h4 className="font-semibold text-gray-900 line-clamp-2">
                          {item.title}
                        </h4>
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <span className="font-medium">{item.source}</span>
                          {item.publishedDate && (
                            <>
                              <span>·</span>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                <span>{formatDate(item.publishedDate)}</span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                      <Badge className={relevance.color}>
                        {relevance.label} Relevance
                      </Badge>
                    </div>

                    {/* Snippet */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <FileText className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-gray-700 leading-relaxed">
                          {item.snippet}
                        </p>
                      </div>
                    </div>

                    {/* Relevance Score */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <BarChart className="h-4 w-4 text-gray-400" />
                        <span className="text-gray-600">Relevance Score</span>
                      </div>
                      <ConfidenceBar 
                        confidence={item.relevanceScore * 100}
                        size="sm"
                        showLabel={false}
                        animated={true}
                      />
                    </div>

                    {/* Actions */}
                    <div className="pt-2 border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View Original Source
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>

        <SheetFooter className="mt-6">
          <SheetClose asChild>
            <Button variant="outline">Close</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}