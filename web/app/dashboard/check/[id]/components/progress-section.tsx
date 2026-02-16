'use client';

import { CheckCircle2, Loader2, Circle } from 'lucide-react';

interface ProgressSectionProps {
  progress: number;
  currentStage: string;
  isConnected: boolean;
  message?: string | null;
  timeEstimate?: string | null;
}

export function ProgressSection({ progress, currentStage, isConnected, message, timeEstimate }: ProgressSectionProps) {
  const stages = [
    { key: 'ingest', label: 'Reading Content', description: 'Analyzing your submission' },
    { key: 'extract', label: 'Finding Claims', description: 'Identifying claims to analyze' },
    { key: 'select', label: 'Selecting Claims', description: 'Ranking claims for analysis' },
    { key: 'decompose', label: 'Decomposing Claims', description: 'Breaking claims into elements' },
    { key: 'retrieve', label: 'Gathering Evidence', description: 'Searching trusted sources' },
    { key: 'analyze', label: 'Mapping Evidence', description: 'Connecting evidence to elements' },
  ];

  const getStageStatus = (stageKey: string) => {
    const stageIndex = stages.findIndex((s) => s.key === stageKey);
    const currentIndex = stages.findIndex((s) => s.key === currentStage);

    if (progress >= 100) return 'completed';
    if (currentIndex === -1) return progress > 0 ? 'completed' : 'pending';

    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'processing';
    return 'pending';
  };

  return (
    <div className="bg-white border border-zinc-200 p-6">
      <h3 className="text-lg font-bold text-zinc-900 mb-6">Analysis Progress</h3>

      {/* Stage List */}
      <div className="space-y-4 mb-6">
        {stages.map((stage) => {
          const status = getStageStatus(stage.key);

          return (
            <div key={stage.key} className="flex items-start gap-3">
              <div className="mt-0.5">
                {status === 'completed' && (
                  <CheckCircle2 size={20} className="text-emerald-500 flex-shrink-0" />
                )}
                {status === 'processing' && (
                  <Loader2 size={20} className="text-accent animate-spin flex-shrink-0" />
                )}
                {status === 'pending' && (
                  <Circle size={20} className="text-zinc-300 flex-shrink-0" />
                )}
              </div>

              <div className="flex-1">
                <div
                  className={`text-sm font-semibold ${
                    status === 'completed'
                      ? 'text-emerald-600'
                      : status === 'processing'
                      ? 'text-zinc-900'
                      : 'text-zinc-400'
                  }`}
                >
                  {stage.label}
                </div>
                <div className="text-xs text-zinc-400 mt-0.5">
                  {stage.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current Stage Message */}
      {message && (
        <div className={`mb-6 p-3 ${
          progress >= 100
            ? 'bg-emerald-50 border border-emerald-200'
            : 'bg-zinc-50 border border-zinc-200'
        }`}>
          <p className={`text-sm font-medium ${
            progress >= 100 ? 'text-emerald-700' : 'text-zinc-700'
          }`}>{message}</p>
        </div>
      )}

      {/* Progress Bar */}
      <div className="relative">
        <div className="w-full h-2 bg-zinc-100 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              progress >= 100
                ? 'bg-emerald-500'
                : 'bg-zinc-900'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          {timeEstimate && progress < 100 ? (
            <p className="text-sm text-zinc-500">Usually completes {timeEstimate}</p>
          ) : (
            <span />
          )}
          <p className="text-sm font-mono text-zinc-400">{progress}%</p>
        </div>
      </div>

      {/* Connection Status */}
      {!isConnected && progress === 0 && !currentStage && (
        <p className="text-amber-600 text-sm mt-4">Connecting...</p>
      )}
    </div>
  );
}
