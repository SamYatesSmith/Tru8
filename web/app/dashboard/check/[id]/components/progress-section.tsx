'use client';

import { CheckCircle2, Loader2, Circle } from 'lucide-react';

interface ProgressSectionProps {
  progress: number;
  currentStage: string;
  isConnected: boolean;
  message?: string | null;
}

export function ProgressSection({ progress, currentStage, isConnected, message }: ProgressSectionProps) {
  const stages = [
    { key: 'ingest', label: 'Reading Content', description: 'Analyzing your submission' },
    { key: 'extract', label: 'Finding Claims', description: 'Identifying statements to verify' },
    { key: 'retrieve', label: 'Gathering Evidence', description: 'Searching trusted sources' },
    { key: 'verify', label: 'Cross-Checking Facts', description: 'Comparing claims against evidence' },
    { key: 'judge', label: 'Generating Verdict', description: 'Creating final assessment' },
  ];

  const getStageStatus = (stageKey: string) => {
    const stageIndex = stages.findIndex((s) => s.key === stageKey);
    const currentIndex = stages.findIndex((s) => s.key === currentStage);

    if (currentIndex === -1) return 'pending';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'processing';
    return 'pending';
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-6">Verification Progress</h3>

      {/* Stage List */}
      <div className="space-y-4 mb-6">
        {stages.map((stage) => {
          const status = getStageStatus(stage.key);

          return (
            <div key={stage.key} className="flex items-start gap-3">
              <div className="mt-0.5">
                {status === 'completed' && (
                  <CheckCircle2 size={20} className="text-emerald-400 flex-shrink-0" />
                )}
                {status === 'processing' && (
                  <Loader2 size={20} className="text-blue-400 animate-spin flex-shrink-0" />
                )}
                {status === 'pending' && (
                  <Circle size={20} className="text-slate-600 flex-shrink-0" />
                )}
              </div>

              <div className="flex-1">
                <div
                  className={`text-sm font-semibold ${
                    status === 'completed'
                      ? 'text-emerald-400'
                      : status === 'processing'
                      ? 'text-blue-400'
                      : 'text-slate-500'
                  }`}
                >
                  {stage.label}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {stage.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current Stage Message */}
      {message && (
        <div className="mb-6 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
          <p className="text-sm text-blue-300 font-medium">{message}</p>
        </div>
      )}

      {/* Progress Bar */}
      <div className="relative">
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-right text-sm text-slate-400 mt-2">{progress}%</p>
      </div>

      {/* Connection Status */}
      {!isConnected && (
        <p className="text-amber-400 text-sm mt-4">⚠ Connection lost. Reconnecting...</p>
      )}
    </div>
  );
}
