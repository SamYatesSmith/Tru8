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
      bg: 'bg-emerald-900/30',
      text: 'text-emerald-400',
      border: 'border-emerald-700',
    },
    processing: {
      bg: 'bg-blue-900/30',
      text: 'text-blue-400',
      border: 'border-blue-700',
    },
    pending: {
      bg: 'bg-amber-900/30',
      text: 'text-amber-400',
      border: 'border-amber-700',
    },
    failed: {
      bg: 'bg-red-900/30',
      text: 'text-red-400',
      border: 'border-red-700',
    },
  };

  const config = statusConfig[check.status as keyof typeof statusConfig] || statusConfig.pending;

  // Get content to display
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
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Input Type */}
        <div>
          <p className="text-slate-400 text-sm mb-1">Input Type</p>
          <p className="text-white font-medium uppercase">{check.inputType}</p>
        </div>

        {/* Status */}
        <div>
          <p className="text-slate-400 text-sm mb-1">Status</p>
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${config.bg} ${config.text} ${config.border}`}
          >
            {check.status.toUpperCase()}
          </span>
        </div>

        {/* Content */}
        <div className="md:col-span-2">
          <p className="text-slate-400 text-sm mb-1">Content</p>
          <p className="text-white font-medium break-all">{getContentDisplay()}</p>
        </div>

        {/* Submitted */}
        <div>
          <p className="text-slate-400 text-sm mb-1">Submitted</p>
          <p className="text-white font-medium">{formatRelativeTime(check.createdAt)}</p>
        </div>

        {/* Credits Used */}
        <div>
          <p className="text-slate-400 text-sm mb-1">Credits Used</p>
          <p className="text-white font-medium">{check.creditsUsed}</p>
        </div>
      </div>
    </div>
  );
}
