'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { MainLayout } from "@/components/layout/main-layout";
import { CreateCheckForm } from "@/components/check/create-check-form";
import { ProgressStepper } from "@/components/check/progress-stepper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCheckProgress } from "@/hooks/use-check-progress";

export default function NewCheckPage() {
  const router = useRouter();
  const [checkId, setCheckId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const progressState = useCheckProgress(checkId);

  const handleCheckCreated = (newCheckId: string) => {
    setCheckId(newCheckId);
    setIsProcessing(true);
  };

  // Navigate to results when complete
  useEffect(() => {
    if (progressState.isComplete && !progressState.error && checkId) {
      const timer = setTimeout(() => {
        router.push(`/checks/${checkId}`);
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [progressState.isComplete, progressState.error, checkId, router]);

  const handleViewResults = () => {
    if (checkId) {
      router.push(`/checks/${checkId}`);
    }
  };

  return (
    <MainLayout>
      <div className="container py-8">
        {/* Header */}
        <div className="mb-8">
          <Link href="/dashboard">
            <Button variant="ghost" className="mb-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Create New Fact-Check
          </h1>
          <p className="text-xl text-gray-600">
            Submit content to verify claims with evidence-based analysis
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Form */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Input Content</CardTitle>
              </CardHeader>
              <CardContent>
                <CreateCheckForm 
                  onSuccess={handleCheckCreated}
                />
              </CardContent>
            </Card>

            {/* Instructions */}
            <Card>
              <CardHeader>
                <CardTitle>How it works</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-tru8-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Process Content</h4>
                    <p className="text-gray-600 text-sm">We extract and analyze your content for factual claims</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-tru8-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Gather Evidence</h4>
                    <p className="text-gray-600 text-sm">Search credible sources for supporting or contradicting evidence</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-tru8-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">Generate Verdict</h4>
                    <p className="text-gray-600 text-sm">AI analysis provides verdict with confidence and reasoning</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Progress Monitor */}
          <div className="space-y-6">
            {isProcessing && checkId && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Processing Progress</CardTitle>
                    {!progressState.isConnected && progressState.error && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={progressState.reconnect}
                        className="h-8"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Reconnect
                      </Button>
                    )}
                  </div>
                  {!progressState.isConnected && !progressState.error && (
                    <p className="text-sm text-amber-600">Connecting to progress updates...</p>
                  )}
                </CardHeader>
                <CardContent>
                  <ProgressStepper
                    currentStage={progressState.stage}
                    progress={progressState.progress}
                    message={progressState.message}
                    error={progressState.error}
                  />
                  
                  {progressState.isComplete && (
                    <div className="mt-6">
                      <Button 
                        onClick={handleViewResults}
                        className="btn-primary w-full"
                        size="lg"
                      >
                        View Results
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Tips */}
            <Card>
              <CardHeader>
                <CardTitle>Tips for better results</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-gray-600">
                  <strong>URLs:</strong> Articles, news posts, and blog entries work best
                </div>
                <div className="text-sm text-gray-600">
                  <strong>Text:</strong> Paste factual claims or statements to verify
                </div>
                <div className="text-sm text-gray-600">
                  <strong>Images:</strong> Screenshots with readable text (max 6MB)
                </div>
                <div className="text-sm text-gray-600">
                  <strong>Videos:</strong> YouTube links under 8 minutes work best
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}