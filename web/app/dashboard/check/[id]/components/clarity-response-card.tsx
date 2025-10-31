'use client';

interface ClarityResponseProps {
  userQuery: string;
  queryResponse?: string;
  queryConfidence?: number;
  querySources?: Array<{
    id: string;
    source: string;
    url: string;
    title: string;
    snippet: string;
    publishedDate?: string;
    credibilityScore: number;
  }>;
  relatedClaims?: number[];
  claims?: any[];
}

export function ClarityResponseCard({
  userQuery,
  queryResponse,
  queryConfidence,
  querySources,
  relatedClaims,
  claims
}: ClarityResponseProps) {
  const hasDirectAnswer = queryConfidence !== undefined && queryConfidence >= 40;

  return (
    <div className="bg-gradient-to-r from-[#1E40AF05] to-[#7C3AED05] border-l-4 border-[#1E40AF] rounded-xl p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">💡</span>
        <h3 className="text-xl font-bold text-white">CLARITY RESPONSE</h3>
      </div>

      {/* User's Question */}
      <div>
        <p className="text-sm text-slate-400 italic mb-1">Your question:</p>
        <p className="text-lg text-slate-200">&ldquo;{userQuery}&rdquo;</p>
      </div>

      <hr className="border-slate-700" />

      {/* Direct Answer (if confidence >= 40%) */}
      {hasDirectAnswer && queryResponse && (
        <>
          <div>
            <p className="text-base text-white leading-relaxed">
              {queryResponse}
            </p>
          </div>

          {/* Confidence Bar */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-semibold text-slate-300">Confidence</span>
              <span className="text-sm font-bold text-white">{Math.round(queryConfidence!)}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3">
              <div
                className="bg-gradient-to-r from-[#1E40AF] to-[#7C3AED] h-3 rounded-full transition-all duration-1000"
                style={{ width: `${queryConfidence}%` }}
              />
            </div>
            {queryConfidence! < 70 && (
              <p className="text-xs text-slate-400 mt-1">
                ℹ️ Moderate confidence - limited sources available
              </p>
            )}
          </div>

          {/* Sources */}
          {querySources && querySources.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-300 mb-2">📚 Sources:</p>
              <div className="space-y-2">
                {querySources.map((source, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-800/50 rounded-lg p-3 border border-slate-700"
                  >
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#f57a07] hover:text-[#e06a00] font-semibold transition-colors"
                    >
                      {source.source}
                    </a>
                    {source.publishedDate && (
                      <>
                        <span className="text-slate-500 mx-2">·</span>
                        <span className="text-sm text-slate-400">{source.publishedDate}</span>
                      </>
                    )}
                    <span className="text-slate-500 mx-2">·</span>
                    <span className="text-sm text-slate-400">
                      Credibility: {Math.round(source.credibilityScore * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* No Direct Answer - Show Related Claims (if confidence < 40%) */}
      {!hasDirectAnswer && relatedClaims && relatedClaims.length > 0 && (
        <>
          <div className="bg-amber-900/20 border border-amber-600/30 rounded-lg p-4">
            <p className="text-amber-200 text-sm">
              ⚠️ We couldn&apos;t find a direct answer to your question in the available sources.
            </p>
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-300 mb-3">
              However, these related claims may help:
            </p>
            <div className="space-y-3">
              {relatedClaims.map((position) => {
                const claim = claims?.find(c => c.position === position);
                if (!claim) return null;

                return (
                  <div
                    key={position}
                    className="bg-slate-800/50 rounded-lg p-4 border border-slate-700 cursor-pointer hover:border-slate-600 transition-colors group"
                    onClick={() => {
                      // Scroll to claim
                      const element = document.getElementById(`claim-${position}`);
                      element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <p className="text-white flex-1">
                        → Claim {position + 1}: {claim.text}
                      </p>
                      <span className="ml-4 text-xs font-semibold text-slate-400">
                        {claim.verdict.toUpperCase()} ({claim.confidence}%)
                      </span>
                    </div>
                    <p className="text-sm text-[#f57a07] mt-2 hover:underline">
                      Jump to details ↓
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* No Related Claims Either */}
      {!hasDirectAnswer && (!relatedClaims || relatedClaims.length === 0) && (
        <div className="bg-red-900/20 border border-red-600/30 rounded-lg p-4">
          <p className="text-red-200 text-sm">
            We couldn&apos;t find information addressing your question in the analyzed content or evidence sources.
            The standard fact-check below may still contain relevant information.
          </p>
        </div>
      )}
    </div>
  );
}
