"use client";

import { Progress } from "@/components/ui/progress";
import { CheckCircle, Circle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

type PipelineStage = 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'complete';

interface ProgressStepperProps {
  currentStage: PipelineStage;
  progress: number; // 0-100
  message?: string;
  error?: string;
}

const stages = [
  { 
    key: 'ingest' as const, 
    label: 'Ingesting', 
    description: 'Processing your content...' 
  },
  { 
    key: 'extract' as const, 
    label: 'Extracting', 
    description: 'Finding claims to fact-check...' 
  },
  { 
    key: 'retrieve' as const, 
    label: 'Researching', 
    description: 'Gathering evidence from sources...' 
  },
  { 
    key: 'verify' as const, 
    label: 'Verifying', 
    description: 'Checking claims against evidence...' 
  },
  { 
    key: 'judge' as const, 
    label: 'Analyzing', 
    description: 'Generating verdict and rationale...' 
  },
];

function getStageIndex(stage: PipelineStage): number {
  if (stage === 'complete') return stages.length;
  return stages.findIndex(s => s.key === stage);
}

export function ProgressStepper({ 
  currentStage, 
  progress, 
  message, 
  error 
}: ProgressStepperProps) {
  const currentIndex = getStageIndex(currentStage);
  const isComplete = currentStage === 'complete';

  return (
    <div className="space-y-6">
      {/* Overall Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="font-medium">
            {error ? 'Processing failed' : isComplete ? 'Complete!' : 'Processing...'}
          </span>
          <span className="text-muted-foreground">{progress}%</span>
        </div>
        <Progress value={progress} className="h-3" />
        {message && (
          <p className="text-sm text-muted-foreground">{message}</p>
        )}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </div>

      {/* Stage Steps */}
      <div className="space-y-4">
        {stages.map((stage, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex && !isComplete;
          const isPending = index > currentIndex;

          return (
            <div
              key={stage.key}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg border transition-all",
                {
                  "bg-primary/10 border-primary": isCurrent,
                  "bg-muted/50 border-muted": isCompleted,
                  "border-border": isPending,
                }
              )}
            >
              <div className="flex-shrink-0 mt-0.5">
                {isCompleted ? (
                  <CheckCircle className="h-5 w-5 text-primary" />
                ) : isCurrent ? (
                  <Clock className="h-5 w-5 text-primary animate-pulse" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <h4 className={cn(
                  "font-medium",
                  {
                    "text-primary": isCurrent,
                    "text-foreground": isCompleted,
                    "text-muted-foreground": isPending,
                  }
                )}>
                  {stage.label}
                </h4>
                <p className="text-sm text-muted-foreground mt-1">
                  {stage.description}
                </p>
              </div>
              
              {isCurrent && (
                <div className="flex-shrink-0">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
                </div>
              )}
            </div>
          );
        })}

        {/* Completion Step */}
        {isComplete && (
          <div className="flex items-start gap-3 p-3 rounded-lg border bg-primary/10 border-primary">
            <CheckCircle className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-primary">Complete!</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Your fact-check results are ready.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}