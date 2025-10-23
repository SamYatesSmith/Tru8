'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Search, Shield, Gavel } from 'lucide-react';

interface DecisionStage {
  stage: string;
  description: string;
  result: string;
  details?: any;
}

interface DecisionTrailData {
  stages: DecisionStage[];
  transparency_score: number;
}

interface DecisionTrailProps {
  decisionTrail: DecisionTrailData;
  className?: string;
}

export function DecisionTrail({ decisionTrail, className = '' }: DecisionTrailProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const stageIcons = {
    evidence_retrieval: Search,
    verification: Shield,
    judgment: Gavel,
  };

  return (
    <div className={`bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden ${className}`}>
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-[#f57a07]" />
          <span className="text-sm font-semibold text-white">How was this determined?</span>
        </div>
        {isExpanded ? (
          <ChevronUp size={18} className="text-slate-400" />
        ) : (
          <ChevronDown size={18} className="text-slate-400" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-6 pb-6 space-y-4 border-t border-slate-700">
          {decisionTrail.stages.map((stage, idx) => {
            const Icon = stageIcons[stage.stage as keyof typeof stageIcons] || Shield;
            const isLast = idx === decisionTrail.stages.length - 1;

            return (
              <div key={idx} className="flex gap-4">
                {/* Timeline connector */}
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <Icon size={14} className="text-[#f57a07]" />
                  </div>
                  {!isLast && (
                    <div className="w-0.5 h-full bg-slate-700 mt-2"></div>
                  )}
                </div>

                {/* Stage content */}
                <div className="flex-1 pb-4">
                  <h4 className="text-sm font-semibold text-white capitalize mb-1">
                    {stage.stage.replace(/_/g, ' ')}
                  </h4>
                  <p className="text-xs text-slate-400 mb-2">{stage.description}</p>
                  <p className="text-sm text-slate-300">{stage.result}</p>

                  {/* Details if available */}
                  {stage.details && Object.keys(stage.details).length > 0 && (
                    <div className="mt-2 p-3 bg-slate-900/50 rounded-lg">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {Object.entries(stage.details).map(([key, value]) => (
                          <div key={key}>
                            <span className="text-slate-500 capitalize">
                              {key.replace(/_/g, ' ')}:
                            </span>{' '}
                            <span className="text-slate-300 font-medium">
                              {typeof value === 'number'
                                ? value.toFixed(2)
                                : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
