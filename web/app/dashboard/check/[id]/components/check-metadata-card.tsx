'use client';

import { formatRelativeTime } from '@/lib/utils';

interface CheckMetadataCardProps {
  check: {
    inputType: string;
    inputUrl: string | null;
    inputContent?: any;
    status: string;
    creditsUsed: number;
    createdAt: string;
  };
}

export function CheckMetadataCard({ check }: CheckMetadataCardProps) {
  const statusConfig = {
    completed: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
    },
    processing: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      border: 'border-blue-200',
    },
    pending: {
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      border: 'border-amber-200',
    },
    failed: {
      bg: 'bg-red-50',
      text: 'text-red-700',
      border: 'border-red-200',
    },
  };

  const config = statusConfig[check.status as keyof typeof statusConfig] || statusConfig.pending;

  const getContentDisplay = () => {
    if (check.inputUrl) {
      return check.inputUrl;
    }
    if (check.inputContent?.content) {
      return check.inputContent.content;
    }
    if (check.inputContent?.url) {
      return check.inputContent.url;
    }
    return 'No content available';
  };

  return (
    <div className="space-y-4">
      <div className="bg-white border border-zinc-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Input Type</p>
            <p className="text-zinc-900 font-medium uppercase">{check.inputType}</p>
          </div>

          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Status</p>
            <span
              className={`inline-flex items-center px-3 py-1 text-xs font-bold uppercase tracking-wider border ${config.bg} ${config.text} ${config.border}`}
            >
              {check.status.toUpperCase()}
            </span>
          </div>

          <div className="md:col-span-2">
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Content</p>
            <p className="text-zinc-900 font-medium break-words whitespace-pre-wrap leading-relaxed">{getContentDisplay()}</p>
          </div>

          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Submitted</p>
            <p className="text-zinc-900 font-medium">{formatRelativeTime(check.createdAt)}</p>
          </div>

          <div>
            <p className="font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-1">Credits Used</p>
            <p className="text-zinc-900 font-medium">{check.creditsUsed}</p>
          </div>
        </div>
      </div>

    </div>
  );
}
