'use client';

import { CheckCircle2, Loader2, Circle } from 'lucide-react';

interface ProgressSectionProps {
  progress: number;
  currentStage: string;
  isConnected: boolean;
}

export function ProgressSection({ progress, currentStage, isConnected }: ProgressSectionProps) {
  const stages = [
    { key: 'ingest', label: 'Ingesting content...' },
    { key: 'extract', label: 'Extracting claims...' },
    { key: 'retrieve', label: 'Retrieving evidence...' },
    { key: 'verify', label: 'Verifying claims...' },
    { key: 'judge', label: 'Generating final verdict...' },
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
            <div key={stage.key} className="flex items-center gap-3">
              {status === 'completed' && (
                <CheckCircle2 size={20} className="text-emerald-400 flex-shrink-0" />
              )}
              {status === 'processing' && (
                <Loader2 size={20} className="text-blue-400 animate-spin flex-shrink-0" />
              )}
              {status === 'pending' && (
                <Circle size={20} className="text-slate-600 flex-shrink-0" />
              )}

              <span
                className={`text-sm font-medium ${
                  status === 'completed'
                    ? 'text-emerald-400'
                    : status === 'processing'
                    ? 'text-blue-400'
                    : 'text-slate-500'
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

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
