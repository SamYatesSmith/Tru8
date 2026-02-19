'use client';

interface ClarityResponseProps {
  userQuery: string;
  queryResponse?: string;
  querySources?: Array<{
    id: string;
    source: string;
    url: string;
    title: string;
    snippet: string;
    publishedDate?: string;
  }>;
  relatedClaims?: number[];
  claims?: any[];
}

export function ClarityResponseCard({
  userQuery,
  queryResponse,
  querySources,
  relatedClaims,
  claims
}: ClarityResponseProps) {
  const hasDirectAnswer = !!queryResponse;

  return (
    <div className="bg-white border-l-4 border-accent p-6 space-y-4 border border-zinc-200">
      {/* Header */}
      <div>
        <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">Clarity Response</span>
        <h3 className="text-lg font-bold text-zinc-900 mt-1">Your Question</h3>
      </div>

      {/* User's Question */}
      <p className="text-base text-zinc-700">&ldquo;{userQuery}&rdquo;</p>

      <hr className="border-zinc-100" />

      {/* Direct Answer */}
      {hasDirectAnswer && queryResponse && (
        <>
          <div>
            <p className="text-base text-zinc-900 leading-relaxed">
              {queryResponse}
            </p>
          </div>

          {/* Sources */}
          {querySources && querySources.length > 0 && (
            <div>
              <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-2">Sources</p>
              <div className="space-y-2">
                {querySources.map((source, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-50 p-3 border border-zinc-200"
                  >
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:text-accent/80 font-semibold transition-colors"
                    >
                      {source.source}
                    </a>
                    {source.publishedDate && (
                      <>
                        <span className="text-zinc-400 mx-2">&middot;</span>
                        <span className="text-sm text-zinc-500">{source.publishedDate}</span>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* No Direct Answer - Show Related Claims */}
      {!hasDirectAnswer && relatedClaims && relatedClaims.length > 0 && (
        <>
          <div className="bg-amber-50 border border-amber-200 p-4">
            <p className="text-amber-800 text-sm">
              We couldn&apos;t find a direct answer to your question in the available sources.
            </p>
          </div>

          <div>
            <p className="text-sm font-semibold text-zinc-700 mb-3">
              However, these related claims may help:
            </p>
            <div className="space-y-3">
              {relatedClaims.map((position) => {
                const claim = claims?.find(c => c.position === position);
                if (!claim) return null;

                return (
                  <div
                    key={position}
                    className="bg-zinc-50 p-4 border border-zinc-200 cursor-pointer hover:border-black transition-colors group"
                    onClick={() => {
                      const element = document.getElementById(`claim-${position}`);
                      element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <p className="text-zinc-900 flex-1">
                        Claim {position + 1}: {claim.text}
                      </p>
                      <span className="ml-4 text-xs font-mono text-zinc-400">
                        {claim.claimMap?.orientation || 'Analysis pending'}
                      </span>
                    </div>
                    <p className="text-sm text-accent mt-2 hover:underline">
                      Jump to details
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
        <div className="bg-red-50 border border-red-200 p-4">
          <p className="text-red-800 text-sm">
            We couldn&apos;t find information addressing your question in the analyzed content or evidence sources.
            The standard analysis below may still contain relevant information.
          </p>
        </div>
      )}
    </div>
  );
}
