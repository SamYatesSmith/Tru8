import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { PageHeader } from '@/app/dashboard/components/page-header';
import { CheckDetailClient } from './check-detail-client';

interface CheckDetailPageProps {
  params: { id: string };
}

interface CheckData {
  id: string;
  inputType: string;
  inputContent?: any;
  inputUrl?: string;
  status: string;
  creditsUsed: number;
  processingTimeMs?: number;
  errorMessage?: string;
  claims?: any[];
  createdAt: string;
  completedAt?: string;
  rawSourcesCount?: number;  // Full Sources List feature
  // Article classification
  articleDomain?: string;
  articleSecondaryDomains?: string[];
  articleJurisdiction?: string;
  articleClassificationSource?: string;
}

export default async function CheckDetailPage({ params }: CheckDetailPageProps) {
  const { getToken } = auth();

  // Fetch check data and subscription status in parallel
  const token = await getToken();
  let checkData: CheckData;
  let isPro = false;
  let rawSourcesCount = 0;

  try {
    // Fetch check data and subscription status in parallel
    const [checkResult, sourcesResult] = await Promise.all([
      apiClient.getCheckById(params.id, token) as Promise<CheckData>,
      apiClient.getCheckSources(params.id, { includeFiltered: true }, token).catch(() => null),
    ]);

    checkData = checkResult;

    // Get sources count from the sources endpoint (works for both Pro and non-Pro)
    if (sourcesResult) {
      rawSourcesCount = sourcesResult.totalSources || 0;
      isPro = !sourcesResult.requiresUpgrade;
    }
  } catch (error: any) {
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      redirect('/dashboard/history');
    }
    throw error;
  }

  // Single-claim skip: go directly to Detail page (V-04: "Never show an Overview page with a single card")
  if (checkData.status === 'completed' && checkData.claims?.length === 1) {
    redirect(`/dashboard/check/${params.id}/claim/0`);
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        title="Check Detail"
        subtitle="View the results of your analysis"
      />

      {/* Check Detail Content */}
      <CheckDetailClient
        initialData={checkData}
        checkId={params.id}
        isPro={isPro}
        rawSourcesCount={rawSourcesCount}
      />
    </div>
  );
}
