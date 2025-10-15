import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { PageHeader } from '@/app/dashboard/components/page-header';
import { CompassGraphic } from '@/app/dashboard/components/compass-graphic';
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
}

export default async function CheckDetailPage({ params }: CheckDetailPageProps) {
  const { userId, getToken } = auth();

  // TEMPORARY: Mock data for testing when not authenticated
  let checkData: CheckData;

  if (!userId) {
    // Mock check data for testing
    checkData = {
      id: params.id,
      inputType: 'url',
      inputUrl: 'https://example.com/article',
      status: 'completed',
      creditsUsed: 1,
      createdAt: new Date().toISOString(),
      claims: [
        {
          id: 'claim-1',
          text: 'The unemployment rate decreased to 3.7%',
          verdict: 'supported',
          confidence: 87,
          rationale: 'Multiple credible sources confirm this statistic.',
          position: 0,
          evidence: [
            {
              id: 'ev-1',
              source: 'Bureau of Labor Statistics',
              url: 'https://bls.gov/news',
              title: 'Employment Situation Summary',
              snippet: 'The unemployment rate declined to 3.7 percent in October...',
              publishedDate: '2024-01-15T00:00:00Z',
              relevanceScore: 0.92,
              credibilityScore: 1.0,
            },
          ],
        },
      ],
    };
  } else {
    // Fetch real check data
    const token = await getToken();

    try {
      checkData = (await apiClient.getCheckById(params.id, token)) as CheckData;
    } catch (error: any) {
      if (error.message?.includes('404') || error.message?.includes('not found')) {
        redirect('/dashboard/history');
      }
      throw error;
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        title="Check Detail"
        subtitle="View the results of your fact-check"
        graphic={<CompassGraphic />}
      />

      {/* Check Detail Content */}
      <CheckDetailClient initialData={checkData} checkId={params.id} />
    </div>
  );
}
