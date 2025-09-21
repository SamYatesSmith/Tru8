'use client';

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/main-layout";
import { ClaimCard } from "@/components/check/claim-card";
import { VerdictPill } from "@/components/check/verdict-pill";
import { ConfidenceBar } from "@/components/check/confidence-bar";
import { ShareModal } from "@/components/check/share-modal";
import { ExportModal } from "@/components/check/export-modal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Clock, Calendar, Link as LinkIcon, FileText, Image, Video } from "lucide-react";
import Link from "next/link";
import { getCheck } from "@/lib/api";
import { useCheckProgress } from "@/hooks/use-check-progress";
import type { Check } from "@shared/types";

export default function CheckResultsPage() {
  const params = useParams();
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const checkId = params.id as string;

  const { data: check, isLoading, error, refetch } = useQuery({
    queryKey: ["check", checkId],
    queryFn: async () => {
      const token = await getToken();
      return getCheck(checkId, token!);
    },
    enabled: !!checkId,
  });

  // Track progress and refetch when completed
  const progress = useCheckProgress(checkId);

  // Refetch check data when SSE indicates completion
  useEffect(() => {
    if (progress.isComplete && !progress.error) {
      // Invalidate and refetch the check query to get updated data
      queryClient.invalidateQueries({ queryKey: ["check", checkId] });
      refetch();
    }
  }, [progress.isComplete, progress.error, queryClient, checkId, refetch]);

  const getInputTypeIcon = (inputType: string) => {
    switch (inputType) {
      case 'url':
        return <LinkIcon className="h-4 w-4" />;
      case 'text':
        return <FileText className="h-4 w-4" />;
      case 'image':
        return <Image className="h-4 w-4" />;
      case 'video':
        return <Video className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getInputTypeLabel = (inputType: string) => {
    return inputType.charAt(0).toUpperCase() + inputType.slice(1);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getOverallVerdict = (claims: any[]) => {
    if (!claims || claims.length === 0) return { verdict: 'uncertain', confidence: 0 };
    
    const supportedCount = claims.filter(c => c.verdict === 'supported').length;
    const contradictedCount = claims.filter(c => c.verdict === 'contradicted').length;
    const uncertainCount = claims.filter(c => c.verdict === 'uncertain').length;
    const total = claims.length;

    if (supportedCount / total >= 0.6) {
      return { verdict: 'supported', confidence: (supportedCount / total) * 100 };
    } else if (contradictedCount / total >= 0.4) {
      return { verdict: 'contradicted', confidence: (contradictedCount / total) * 100 };
    } else {
      return { verdict: 'uncertain', confidence: 50 };
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-48 bg-gray-200 rounded"></div>
          </div>
        </div>
      </MainLayout>
    );
  }

  // Show progress if check is still processing
  if (check && check.status === 'pending' && !progress.isComplete) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle>Processing Fact-Check</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <ConfidenceBar
                    confidence={progress.progress}
                    verdict="uncertain"
                    size="lg"
                    className="mb-4"
                  />
                  <div className="text-center">
                    <p className="text-gray-600 mb-2">{progress.message || 'Processing...'}</p>
                    <p className="text-sm text-gray-500">
                      Stage: {progress.stage} ({progress.progress}%)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error || !check) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Check Not Found</h1>
            <p className="text-gray-600 mb-6">The requested fact-check could not be found.</p>
            <Link href="/dashboard">
              <Button>Return to Dashboard</Button>
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }

  const overallVerdict = getOverallVerdict(check.claims || []);

  return (
    <MainLayout>
      {/* Hero Section with Gradient Background */}
      <div className="relative bg-gradient-to-br from-tru8-primary via-purple-600 to-pink-500 text-white">
        <div className="container py-12">
          <Link href="/dashboard">
            <Button variant="ghost" className="mb-4 text-white hover:bg-white/10">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
          
          <div className="space-y-4">
            <h1 className="text-5xl font-black">
              Fact-Check Results
            </h1>
            
            <div className="flex items-center gap-4 flex-wrap">
              <VerdictPill 
                verdict={overallVerdict.verdict as any}
                confidence={overallVerdict.confidence}
                size="lg"
              />
              <div className="text-lg opacity-90">
                {check.claims?.length || 0} claims analyzed
              </div>
            </div>
            
            <div className="max-w-2xl">
              <ConfidenceBar
                confidence={overallVerdict.confidence}
                verdict={overallVerdict.verdict as any}
                size="lg"
                className="mt-4"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="container py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overall Results Card */}
            <Card className="card-featured">
              <CardHeader>
                <CardTitle className="text-2xl">Assessment Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <p className="text-gray-600 mb-4">
                      Based on analysis of {check.claims?.length || 0} claims found in the content.
                    </p>
                    
                    {check.inputUrl && (
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <h4 className="font-semibold text-gray-900 mb-2">Source</h4>
                        <a 
                          href={check.inputUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-tru8-primary hover:underline break-all"
                        >
                          {check.inputUrl}
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Claims */}
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900">
                Claims Analysis ({check.claims?.length || 0})
              </h2>
              
              {check.claims && check.claims.length > 0 ? (
                <div className="space-y-4">
                  {check.claims.map((claim: any, index: number) => (
                    <ClaimCard 
                      key={claim.id} 
                      claim={claim}
                      index={index + 1}
                    />
                  ))}
                </div>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-gray-500">No claims were extracted from this content.</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Check Details */}
            <Card>
              <CardHeader>
                <CardTitle>Check Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-2">
                  {getInputTypeIcon(check.inputType)}
                  <Badge variant="outline">{getInputTypeLabel(check.inputType)}</Badge>
                </div>
                
                <div className="text-sm text-gray-600 space-y-2">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <span>Created: {formatDate(check.createdAt)}</span>
                  </div>
                  
                  {check.completedAt && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      <span>Completed: {formatDate(check.completedAt)}</span>
                    </div>
                  )}
                  
                  {check.processingTimeMs && (
                    <div className="text-sm">
                      <strong>Processing time:</strong> {(check.processingTimeMs / 1000).toFixed(1)}s
                    </div>
                  )}
                </div>
                
                <div className="pt-2 border-t">
                  <div className="text-sm">
                    <strong>Credits used:</strong> {check.creditsUsed}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <ShareModal 
                  checkId={check.id}
                  verdict={overallVerdict.verdict}
                >
                  <Button variant="outline" className="w-full">
                    Share Results
                  </Button>
                </ShareModal>
                
                <ExportModal check={check}>
                  <Button variant="outline" className="w-full">
                    Export Report
                  </Button>
                </ExportModal>
                <Link href="/checks/new">
                  <Button className="btn-primary w-full">
                    New Fact-Check
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}