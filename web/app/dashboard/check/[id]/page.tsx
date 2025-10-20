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
  const { getToken } = auth();

  // Fetch check data
  const token = await getToken();
  let checkData: CheckData;

  try {
    checkData = (await apiClient.getCheckById(params.id, token)) as CheckData;
  } catch (error: any) {
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      redirect('/dashboard/history');
    }
    throw error;
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
