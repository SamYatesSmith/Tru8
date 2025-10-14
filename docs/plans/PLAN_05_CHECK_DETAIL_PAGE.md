# 📄 PLAN #5: CHECK DETAIL PAGE

**File:** `web/app/dashboard/check/[id]/page.tsx`
**Type:** Server Component (initial fetch) + Client Component (real-time updates)
**Status:** NOT STARTED

---

## **PURPOSE**

Individual check detail page displaying:
- Real-time verification progress (SSE)
- Check metadata (input, timestamp, credits used)
- Claims with verdict pills and confidence bars
- Evidence citations with publisher/date/credibility
- Status-based rendering (pending/processing/completed/failed)
- Social sharing functionality

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Page Header** (visible in check detail screenshot)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Compass Graphic]                                          │
│  Check Detail                                               │
│  View the results of your fact-check                        │
└─────────────────────────────────────────────────────────────┘
```

**Elements:**
- Background graphic: Compass icon (`/imagery/compass.png`)
- Headline: "Check Detail" (text-4xl, font-black)
- Subheading: "View the results of your fact-check" (text-slate-400)
- Reuse: `<PageHeader />` component from PLAN_02

### **Check Metadata Card**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Input Type: URL                                            │
│  Content: https://example.com/article                       │
│  Submitted: 2024-01-15 14:32                               │
│  Credits Used: 1                                            │
│  Status: [COMPLETED] (green pill)                          │
└─────────────────────────────────────────────────────────────┘
```

**Styling:**
- Background: `bg-slate-800/50`
- Border: `border border-slate-700`
- Padding: `p-6`
- Border radius: `rounded-xl`
- Grid layout: 2 columns on desktop, 1 on mobile

**Status Pills:**
- Completed: Green background (`bg-emerald-900/30`, `text-emerald-400`, `border-emerald-700`)
- Processing: Blue background (`bg-blue-900/30`, `text-blue-400`, `border-blue-700`)
- Pending: Amber background (`bg-amber-900/30`, `text-amber-400`, `border-amber-700`)
- Failed: Red background (`bg-red-900/30`, `text-red-400`, `border-red-700`)

### **Progress Section** (only visible when status = 'processing')

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Verification Progress                                      │
│                                                             │
│  [✓] Ingesting content...                                  │
│  [⟳] Extracting claims...                                  │
│  [ ] Retrieving evidence...                                │
│  [ ] Verifying claims...                                   │
│  [ ] Generating final verdict...                           │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 40%        │
└─────────────────────────────────────────────────────────────┘
```

**Progress Steps:**
- Icons: CheckCircle2 (completed), Loader2 (processing), Circle (pending)
- Colors: Green (completed), Blue (processing), Slate (pending)
- Animated progress bar with percentage
- Auto-updates via SSE

### **Claims Section** (visible when status = 'completed')

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Claims Analyzed (3)                                        │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  [SUPPORTED] 87%                                      │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │
│  │                                                       │ │
│  │  "The unemployment rate decreased to 3.7%"           │ │
│  │                                                       │ │
│  │  Evidence Sources (4)                                │ │
│  │  • Bureau of Labor Statistics · Jan 2024 · 9.2/10   │ │
│  │  • Reuters · Jan 2024 · 8.8/10                      │ │
│  │  • AP News · Jan 2024 · 8.5/10                      │ │
│  │  • Bloomberg · Jan 2024 · 8.3/10                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  [Similar cards for other claims...]                       │
└─────────────────────────────────────────────────────────────┘
```

**Claim Card Structure:**
- Verdict pill (top left): Reuse `<VerdictPill />` from PLAN_02
- Confidence percentage (top right): Bold text
- Confidence bar: Animated gradient bar matching verdict color
- Claim text: White text, font-medium, text-lg
- Evidence list: Collapsible accordion (collapsed by default)
- Evidence chips: `Publisher · Date · Score/10` format

### **Social Share Section**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Share This Check                                           │
│                                                             │
│  [Facebook] [Twitter] [LinkedIn] [Copy Link]               │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Web Share API (primary)
- Platform-specific fallback URLs (as approved in GAP #6)
- Copy link functionality with toast notification

### **Error State** (when status = 'failed')

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [X Circle Icon]                                            │
│  Check Failed                                               │
│  We encountered an error processing this check.             │
│                                                             │
│  Error: [error_message from backend]                       │
│                                                             │
│  [Try Again] [Contact Support]                             │
└─────────────────────────────────────────────────────────────┘
```

---

## **BACKEND INTEGRATION**

### **Check Data Fetch (Initial Load)**

```typescript
const token = await getToken();
const checkData = await apiClient.getCheckById(checkId, token);
```

**API Endpoint:** `GET /api/v1/checks/{check_id}`

**Response Schema:**
```typescript
{
  check: {
    id: string,
    user_id: string,
    input_type: 'url' | 'text' | 'image' | 'video',
    url: string | null,
    content: string | null,
    status: 'pending' | 'processing' | 'completed' | 'failed',
    error_message: string | null,
    credits_used: number,
    created_at: string,      // ISO date
    updated_at: string,      // ISO date
    completed_at: string | null
  },
  claims: [
    {
      id: string,
      check_id: string,
      text: string,
      verdict: 'supported' | 'contradicted' | 'uncertain',
      confidence: number,      // 0-100
      reasoning: string,
      order_index: number
    }
  ],
  evidence: [
    {
      id: string,
      claim_id: string,
      source: string,          // Publisher name
      url: string,
      title: string,
      snippet: string,
      published_date: string,  // ISO date
      credibility_score: number, // 0-10
      relevance_score: number    // 0-10
    }
  ]
}
```

**Backend File Reference:** `backend/app/api/v1/checks.py:74-112`

### **Real-Time Progress (SSE)**

**API Endpoint:** `GET /api/v1/checks/{check_id}/progress`

**SSE Event Stream:**
```typescript
// Event format
data: {"stage": "ingest", "status": "completed", "message": "Content ingested successfully"}
data: {"stage": "extract", "status": "processing", "message": "Extracting claims..."}
data: {"stage": "retrieve", "status": "pending", "message": "Waiting to retrieve evidence"}
data: {"progress": 40}
```

**Stage Mapping:**
```typescript
const stages = [
  { key: 'ingest', label: 'Ingesting content...' },
  { key: 'extract', label: 'Extracting claims...' },
  { key: 'retrieve', label: 'Retrieving evidence...' },
  { key: 'verify', label: 'Verifying claims...' },
  { key: 'judge', label: 'Generating final verdict...' }
];
```

**Backend File Reference:** `backend/app/api/v1/checks.py:129-161`

---

## **COMPONENT STRUCTURE**

### **File: `web/app/dashboard/check/[id]/page.tsx`**

```typescript
import { auth } from '@clerk/nextjs';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { CheckDetailClient } from './check-detail-client';
import { PageHeader } from '@/app/dashboard/components/page-header';

interface CheckDetailPageProps {
  params: { id: string };
}

export default async function CheckDetailPage({ params }: CheckDetailPageProps) {
  // 1. Check authentication
  const { userId, getToken } = auth();

  if (!userId) {
    redirect('/?signin=true');
  }

  // 2. Fetch check data
  const token = await getToken();

  let checkData;
  try {
    checkData = await apiClient.getCheckById(params.id, token);
  } catch (error: any) {
    if (error.response?.status === 404) {
      redirect('/dashboard/history');
    }
    throw error;
  }

  // 3. Render page
  return (
    <div className="space-y-8">
      <PageHeader
        title="Check Detail"
        description="View the results of your fact-check"
        imagePath="/imagery/compass.png"
      />

      <CheckDetailClient
        initialData={checkData}
        checkId={params.id}
        token={token}
      />
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/check-detail-client.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { CheckMetadataCard } from './components/check-metadata-card';
import { ProgressSection } from './components/progress-section';
import { ClaimsSection } from './components/claims-section';
import { ShareSection } from './components/share-section';
import { ErrorState } from './components/error-state';
import { useCheckProgress } from '@/hooks/use-check-progress';

interface CheckDetailClientProps {
  initialData: any;
  checkId: string;
  token: string;
}

export function CheckDetailClient({ initialData, checkId, token }: CheckDetailClientProps) {
  const [checkData, setCheckData] = useState(initialData);

  // Real-time progress updates via SSE
  const { progress, currentStage, isConnected } = useCheckProgress(
    checkId,
    token,
    checkData.check.status === 'processing'
  );

  // Poll for updates if processing
  useEffect(() => {
    if (checkData.check.status === 'processing') {
      const interval = setInterval(async () => {
        const updated = await apiClient.getCheckById(checkId, token);
        setCheckData(updated);

        // Stop polling if completed or failed
        if (updated.check.status !== 'processing') {
          clearInterval(interval);
        }
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [checkData.check.status, checkId, token]);

  return (
    <div className="space-y-6">
      {/* Metadata Card */}
      <CheckMetadataCard check={checkData.check} />

      {/* Status-based Rendering */}
      {checkData.check.status === 'processing' && (
        <ProgressSection
          progress={progress}
          currentStage={currentStage}
          isConnected={isConnected}
        />
      )}

      {checkData.check.status === 'completed' && (
        <>
          <ClaimsSection
            claims={checkData.claims}
            evidence={checkData.evidence}
          />
          <ShareSection checkId={checkId} />
        </>
      )}

      {checkData.check.status === 'failed' && (
        <ErrorState
          errorMessage={checkData.check.error_message}
          checkId={checkId}
        />
      )}

      {checkData.check.status === 'pending' && (
        <div className="text-center py-12">
          <p className="text-slate-400">Your check is queued and will begin processing soon...</p>
        </div>
      )}
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/components/check-metadata-card.tsx`**

```typescript
'use client';

import { formatDistanceToNow } from 'date-fns';

interface CheckMetadataCardProps {
  check: {
    input_type: string;
    url: string | null;
    content: string | null;
    status: string;
    credits_used: number;
    created_at: string;
  };
}

export function CheckMetadataCard({ check }: CheckMetadataCardProps) {
  const statusConfig = {
    completed: { bg: 'bg-emerald-900/30', text: 'text-emerald-400', border: 'border-emerald-700' },
    processing: { bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-700' },
    pending: { bg: 'bg-amber-900/30', text: 'text-amber-400', border: 'border-amber-700' },
    failed: { bg: 'bg-red-900/30', text: 'text-red-400', border: 'border-red-700' },
  };

  const config = statusConfig[check.status] || statusConfig.pending;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-slate-400 text-sm mb-1">Input Type</p>
          <p className="text-white font-medium uppercase">{check.input_type}</p>
        </div>

        <div>
          <p className="text-slate-400 text-sm mb-1">Status</p>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${config.bg} ${config.text} ${config.border}`}>
            {check.status.toUpperCase()}
          </span>
        </div>

        <div className="md:col-span-2">
          <p className="text-slate-400 text-sm mb-1">Content</p>
          <p className="text-white font-medium break-all">
            {check.url || check.content}
          </p>
        </div>

        <div>
          <p className="text-slate-400 text-sm mb-1">Submitted</p>
          <p className="text-white font-medium">
            {formatDistanceToNow(new Date(check.created_at), { addSuffix: true })}
          </p>
        </div>

        <div>
          <p className="text-slate-400 text-sm mb-1">Credits Used</p>
          <p className="text-white font-medium">{check.credits_used}</p>
        </div>
      </div>
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/components/progress-section.tsx`**

```typescript
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
    { key: 'judge', label: 'Generating final verdict...' }
  ];

  const getStageStatus = (stageKey: string) => {
    const stageIndex = stages.findIndex(s => s.key === stageKey);
    const currentIndex = stages.findIndex(s => s.key === currentStage);

    if (currentIndex === -1) return 'pending';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'processing';
    return 'pending';
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-6">Verification Progress</h3>

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

              <span className={`text-sm font-medium ${
                status === 'completed' ? 'text-emerald-400' :
                status === 'processing' ? 'text-blue-400' :
                'text-slate-500'
              }`}>
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

      {!isConnected && (
        <p className="text-amber-400 text-sm mt-4">
          ⚠ Connection lost. Reconnecting...
        </p>
      )}
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/components/claims-section.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { VerdictPill } from '@/app/dashboard/components/verdict-pill';
import { ConfidenceBar } from '@/app/dashboard/components/confidence-bar';
import { format } from 'date-fns';

interface ClaimsSectionProps {
  claims: any[];
  evidence: any[];
}

export function ClaimsSection({ claims, evidence }: ClaimsSectionProps) {
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null);

  const getClaimEvidence = (claimId: string) => {
    return evidence
      .filter(e => e.claim_id === claimId)
      .sort((a, b) => b.relevance_score - a.relevance_score);
  };

  return (
    <div className="space-y-6">
      <h3 className="text-2xl font-bold text-white">
        Claims Analyzed ({claims.length})
      </h3>

      {claims.map((claim) => {
        const claimEvidence = getClaimEvidence(claim.id);
        const isExpanded = expandedClaim === claim.id;

        return (
          <div
            key={claim.id}
            className="bg-slate-800/50 border border-slate-700 rounded-xl p-6"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <VerdictPill verdict={claim.verdict} />
              <span className="text-2xl font-bold text-white">
                {Math.round(claim.confidence)}%
              </span>
            </div>

            {/* Confidence Bar */}
            <ConfidenceBar
              confidence={claim.confidence}
              verdict={claim.verdict}
              className="mb-4"
            />

            {/* Claim Text */}
            <p className="text-lg font-medium text-white mb-4">
              "{claim.text}"
            </p>

            {/* Reasoning */}
            {claim.reasoning && (
              <p className="text-sm text-slate-400 mb-4">
                {claim.reasoning}
              </p>
            )}

            {/* Evidence Toggle */}
            <button
              onClick={() => setExpandedClaim(isExpanded ? null : claim.id)}
              className="flex items-center gap-2 text-sm text-[#f57a07] hover:text-[#ff8c1a] transition-colors"
            >
              <span className="font-medium">
                Evidence Sources ({claimEvidence.length})
              </span>
              {isExpanded ? (
                <ChevronUp size={16} />
              ) : (
                <ChevronDown size={16} />
              )}
            </button>

            {/* Evidence List */}
            {isExpanded && (
              <div className="mt-4 space-y-3">
                {claimEvidence.map((item) => (
                  <a
                    key={item.id}
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-3 p-4 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white truncate">
                          {item.title}
                        </span>
                        <ExternalLink
                          size={14}
                          className="text-slate-400 group-hover:text-white transition-colors flex-shrink-0"
                        />
                      </div>

                      <p className="text-xs text-slate-400 mb-2 line-clamp-2">
                        {item.snippet}
                      </p>

                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="font-medium">{item.source}</span>
                        <span>·</span>
                        <span>
                          {item.published_date
                            ? format(new Date(item.published_date), 'MMM yyyy')
                            : 'Date unknown'}
                        </span>
                        <span>·</span>
                        <span className="font-medium">
                          {item.credibility_score.toFixed(1)}/10
                        </span>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/components/share-section.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { Facebook, Twitter, Linkedin, Link as LinkIcon, Check } from 'lucide-react';

interface ShareSectionProps {
  checkId: string;
}

export function ShareSection({ checkId }: ShareSectionProps) {
  const [copied, setCopied] = useState(false);

  const shareUrl = `${window.location.origin}/check/${checkId}`;
  const shareText = 'Check out this fact-check on Tru8';

  const handleShare = async (platform: string) => {
    if (platform === 'native' && navigator.share) {
      try {
        await navigator.share({
          title: 'Tru8 Fact-Check',
          text: shareText,
          url: shareUrl,
        });
      } catch (error) {
        console.error('Share failed:', error);
      }
      return;
    }

    const shareUrls = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
    };

    if (platform in shareUrls) {
      window.open(shareUrls[platform], '_blank', 'width=600,height=400');
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h3 className="text-xl font-bold text-white mb-4">Share This Check</h3>

      <div className="flex items-center gap-3">
        <button
          onClick={() => handleShare('facebook')}
          className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          aria-label="Share on Facebook"
        >
          <Facebook size={20} />
        </button>

        <button
          onClick={() => handleShare('twitter')}
          className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          aria-label="Share on Twitter"
        >
          <Twitter size={20} />
        </button>

        <button
          onClick={() => handleShare('linkedin')}
          className="flex items-center justify-center w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          aria-label="Share on LinkedIn"
        >
          <Linkedin size={20} />
        </button>

        <button
          onClick={handleCopyLink}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
        >
          {copied ? (
            <>
              <Check size={18} />
              <span className="text-sm font-medium">Copied!</span>
            </>
          ) : (
            <>
              <LinkIcon size={18} />
              <span className="text-sm font-medium">Copy Link</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
```

### **File: `web/app/dashboard/check/[id]/components/error-state.tsx`**

```typescript
'use client';

import { XCircle } from 'lucide-react';
import Link from 'next/link';

interface ErrorStateProps {
  errorMessage: string | null;
  checkId: string;
}

export function ErrorState({ errorMessage, checkId }: ErrorStateProps) {
  return (
    <div className="bg-red-900/20 border border-red-700 rounded-xl p-12 text-center">
      <XCircle size={64} className="text-red-400 mx-auto mb-4" />

      <h3 className="text-2xl font-bold text-white mb-2">Check Failed</h3>

      <p className="text-slate-300 mb-6">
        We encountered an error processing this check.
      </p>

      {errorMessage && (
        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
          <p className="text-sm text-slate-400 text-left">
            <span className="font-medium text-red-400">Error:</span> {errorMessage}
          </p>
        </div>
      )}

      <div className="flex items-center justify-center gap-4">
        <Link
          href="/dashboard/new-check"
          className="px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all"
        >
          Try Again
        </Link>

        <a
          href="mailto:support@tru8.com"
          className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
        >
          Contact Support
        </a>
      </div>
    </div>
  );
}
```

### **File: `web/hooks/use-check-progress.ts`**

```typescript
'use client';

import { useState, useEffect, useRef } from 'react';

interface ProgressData {
  stage?: string;
  status?: string;
  message?: string;
  progress?: number;
}

export function useCheckProgress(checkId: string, token: string, enabled: boolean) {
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const url = `${process.env.NEXT_PUBLIC_API_URL}/checks/${checkId}/progress?token=${token}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data: ProgressData = JSON.parse(event.data);

        if (data.stage) {
          setCurrentStage(data.stage);
        }

        if (data.progress !== undefined) {
          setProgress(data.progress);
        }
      } catch (error) {
        console.error('Failed to parse SSE data:', error);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
    };

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
    };
  }, [checkId, token, enabled]);

  return { progress, currentStage, isConnected };
}
```

---

## **STYLING REQUIREMENTS**

### **Colors**
- Card background: `bg-slate-800/50`
- Border: `border-slate-700`
- Progress bar: `bg-gradient-to-r from-blue-500 to-blue-400`
- Error state: `bg-red-900/20 border-red-700`

### **Verdict Colors** (from DESIGN_SYSTEM.md)
- Supported: Emerald (`#059669`)
- Contradicted: Red (`#DC2626`)
- Uncertain: Amber (`#D97706`)

### **Status Pills**
- Completed: Green tones
- Processing: Blue tones with animation
- Pending: Amber tones
- Failed: Red tones

### **Typography**
- Page title: `text-4xl font-black`
- Section headings: `text-2xl font-bold`
- Claim text: `text-lg font-medium`
- Evidence text: `text-sm`

### **Spacing** (4pt Grid)
- Card padding: `p-6`
- Section gaps: `space-y-6`
- Element gaps: `gap-3`, `gap-4`

---

## **REUSABLE COMPONENTS**

### **From Existing Plans**
✅ **`<PageHeader />`** - PLAN_02
- Reuse for "Check Detail" header with compass graphic

✅ **`<VerdictPill />`** - PLAN_02
- Reuse for claim verdict display

✅ **`<ConfidenceBar />`** - PLAN_02
- Reuse for claim confidence visualization

### **New Components (No Overlap)**
- `CheckMetadataCard` - Check metadata display
- `ProgressSection` - Real-time progress tracker
- `ClaimsSection` - Claims with evidence accordion
- `ShareSection` - Social sharing buttons
- `ErrorState` - Error display component

---

## **GAP RESOLUTIONS**

### **SSE Connection Handling**

**Challenge:** EventSource doesn't support custom headers (can't send Bearer token)

**Solution:** Pass token as query parameter (secure over HTTPS)

```typescript
const url = `${API_URL}/checks/${checkId}/progress?token=${token}`;
const eventSource = new EventSource(url);
```

**Backend Validation:**
```python
@router.get("/checks/{check_id}/progress")
async def check_progress(
    check_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Validate token
    user = verify_token(token)
    # Stream progress...
```

### **Evidence Date Formatting**

**Challenge:** Backend may not always provide `published_date`

**Solution:** Handle null dates gracefully

```typescript
{item.published_date
  ? format(new Date(item.published_date), 'MMM yyyy')
  : 'Date unknown'}
```

### **Polling Fallback**

**Challenge:** SSE may not work in all browsers/networks

**Solution:** Implement polling fallback (every 3s)

```typescript
useEffect(() => {
  if (checkData.check.status === 'processing') {
    const interval = setInterval(async () => {
      const updated = await apiClient.getCheckById(checkId, token);
      setCheckData(updated);

      if (updated.check.status !== 'processing') {
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }
}, [checkData.check.status]);
```

---

## **GAPS RESOLVED**

### **✅ GAP #14 RESOLVED: Public Check Sharing**

**Issue:**
- Current route: `/dashboard/check/[id]` (requires authentication)
- Share URLs would fail for non-authenticated users
- Screenshot shows social sharing, implying public access

**DECISION APPROVED:** ✅ Option C: Authenticated-only check sharing for MVP

**Implementation:**
- All check detail pages require authentication
- Share URLs redirect to signin if user not authenticated
- Social share buttons still functional (share URL, but requires signin to view)
- Route: `/dashboard/check/[id]` (protected route)

**Rationale:**
- Faster MVP launch with simpler privacy model
- No need for public/private toggle complexity
- Reduces abuse potential (spam, misuse)
- Can add public sharing in Phase 2 after user validation

**Phase 2 Enhancement:**
- Add public/private toggle to check settings
- Create public route `/check/[id]` for public checks
- Default to private, user opts in to public sharing
- Public checks shown in search/discovery feed

---

### **✅ GAP #15 RESOLVED: Evidence Snippet Length**

**Issue:**
- Screenshot doesn't show evidence snippet length limits
- Backend provides `snippet` field (variable length)
- Need flexible display that handles variety of lengths from AI

**DECISION APPROVED:** ✅ Flexible text field with generous allocation - NO hard truncation

**Implementation:**
```typescript
// Use line-clamp-4 (4 lines) instead of 2 for more generous display
// Remove character limits - let AI return full snippets
<p className="text-xs text-slate-400 mb-2 line-clamp-4">
  {item.snippet}
</p>
```

**Rationale:**
- Evidence snippets need to be wordy to provide proper context
- AI-generated snippets vary significantly in length
- Must be flexible and versatile to handle variety
- Better UX to show more context than truncate too early

**Alternative Enhancement:**
- Use expandable "Read more" link if snippet exceeds 4 lines
- Accordion pattern: collapsed by default, expand on click
- Preserves layout while allowing full snippet access

---

### **✅ GAP #16 RESOLVED: SSE Token Security**

**Issue:**
- SSE doesn't support custom headers
- Passing token as query parameter exposes it in URL
- Query params are logged by servers/proxies

**DECISION APPROVED:** ✅ Option A: Short-lived SSE tokens (5 min expiry)

**Implementation:**

**Frontend:**
```typescript
// Step 1: Request short-lived SSE token
const sseToken = await apiClient.createSSEToken(checkId, token);

// Step 2: Connect with short-lived token
const url = `${API_URL}/checks/${checkId}/progress?token=${sseToken.token}`;
const eventSource = new EventSource(url);
```

**Backend (New Endpoint Required):**
```python
@router.post("/checks/{check_id}/sse-token")
async def create_sse_token(
    check_id: str,
    current_user: User = Depends(get_current_user)
):
    # Verify user owns the check
    check = db.query(Check).filter(
        Check.id == check_id,
        Check.user_id == current_user.id
    ).first()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Create short-lived token (5 min expiry)
    token = create_jwt_token(
        user_id=current_user.id,
        check_id=check_id,
        exp=300,  # 5 minutes
        scope="sse_only"
    )

    return {"token": token, "expires_in": 300}
```

**Rationale:**
- Mitigates security risk of full JWT in query params
- Tokens expire after 5 minutes (short window for exposure)
- Tokens scoped to single check and SSE endpoint only
- Minimal additional complexity vs WebSocket

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Server Component Setup**
- [ ] Create `web/app/dashboard/check/[id]/page.tsx`
- [ ] Add authentication check
- [ ] Fetch check data with error handling
- [ ] Handle 404 redirect

### **Phase 2: Client Component**
- [ ] Create `CheckDetailClient` component
- [ ] Implement status-based rendering logic
- [ ] Add polling fallback for processing checks
- [ ] Connect SSE hook

### **Phase 3: Metadata & Progress**
- [ ] Create `CheckMetadataCard` component
- [ ] Create `ProgressSection` component
- [ ] Implement `useCheckProgress` hook
- [ ] Add SSE connection status indicator

### **Phase 4: Claims & Evidence**
- [ ] Create `ClaimsSection` component
- [ ] Implement evidence accordion (expand/collapse)
- [ ] Add external link icons
- [ ] Format evidence dates and scores

### **Phase 5: Sharing & Error States**
- [ ] Create `ShareSection` component
- [ ] Implement Web Share API with fallbacks
- [ ] Add copy link functionality
- [ ] Create `ErrorState` component

### **Phase 6: Styling & Polish**
- [ ] Apply 4pt grid spacing
- [ ] Add verdict color system
- [ ] Implement animated progress bar
- [ ] Add hover states and transitions
- [ ] Test responsive behavior

### **Phase 7: Testing**
- [ ] Test all status states (pending/processing/completed/failed)
- [ ] Test SSE connection and reconnection
- [ ] Test evidence accordion expand/collapse
- [ ] Test share functionality (all platforms)
- [ ] Test copy link functionality
- [ ] Test error state rendering
- [ ] Test 404 redirect for invalid check IDs

---

## **DEPENDENCIES**

### **Required Before Starting**
- ✅ Backend `/checks/{id}` endpoint functional
- ✅ Backend `/checks/{id}/progress` SSE endpoint functional
- ✅ VerdictPill component available (from PLAN_02)
- ✅ ConfidenceBar component available (from PLAN_02)
- ✅ PageHeader component available (from PLAN_02)

### **External Dependencies**
- `date-fns` - Date formatting
- `lucide-react` - Icons
- EventSource API - SSE connection

---

## **TESTING SCENARIOS**

### **Status Transitions**
1. **Pending → Processing:** Should show progress section
2. **Processing → Completed:** Should hide progress, show claims
3. **Processing → Failed:** Should show error state
4. **Immediate Completed:** Should render claims directly (no progress)

### **Real-Time Updates**
1. **SSE connection:** Progress bar should update in real-time
2. **SSE disconnect:** Should show reconnection warning
3. **Polling fallback:** Should update every 3s if SSE unavailable

### **Evidence Display**
1. **No evidence:** Should hide evidence section
2. **Multiple evidence:** Should show all with relevance sorting
3. **Long snippets:** Should truncate with line-clamp-2
4. **Missing dates:** Should show "Date unknown"

### **Sharing**
1. **Web Share API:** Should trigger native share on mobile
2. **Fallback URLs:** Should open social media windows on desktop
3. **Copy link:** Should copy URL and show "Copied!" confirmation

### **Error Handling**
1. **404 check ID:** Should redirect to history page
2. **Failed check:** Should show error message and actions
3. **Network error:** Should show error boundary

---

## **NOTES**

- This page handles all check statuses with status-based rendering
- SSE provides real-time progress updates during processing
- Polling fallback ensures updates even if SSE fails
- Evidence is collapsed by default to reduce visual clutter
- Social sharing uses Web Share API with platform-specific fallbacks
- All verdict colors and confidence bars reuse existing components
- Page is fully responsive with mobile-first design

---

## **PERFORMANCE CONSIDERATIONS**

### **SSE Connection Management**
- Only connect when status = 'processing'
- Close connection on unmount
- Implement exponential backoff for reconnection

### **Polling Strategy**
- 3-second interval (balance between UX and server load)
- Stop polling when status changes to completed/failed
- Clear interval on unmount

### **Evidence Rendering**
- Use accordion to hide evidence by default (reduce initial render cost)
- Lazy render evidence content when expanded
- Limit evidence to top 10 per claim (sorted by relevance)

### **Image Optimization**
- Use Next.js Image component for graphics
- Lazy load evidence thumbnails (if added in future)
