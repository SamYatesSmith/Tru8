import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { PageHeader } from '@/app/dashboard/components/page-header';
import { CompassGraphic } from '@/app/dashboard/components/compass-graphic';
import { SourcesClient } from './sources-client';

interface SourcesPageProps {
  params: { id: string };
}

export default async function SourcesPage({ params }: SourcesPageProps) {
  const { getToken } = auth();
  const token = await getToken();

  // Fetch sources data
  let sourcesData: any;

  try {
    sourcesData = await apiClient.getCheckSources(params.id, { includeFiltered: true }, token);

    // If user needs to upgrade, redirect to check page with upgrade param
    if (sourcesData.requiresUpgrade) {
      redirect(`/dashboard/check/${params.id}?upgrade=sources`);
    }

    // If legacy check with no data, redirect back
    if (sourcesData.legacyCheck) {
      redirect(`/dashboard/check/${params.id}`);
    }
  } catch (error: any) {
    if (error.message?.includes('404') || error.message?.includes('not found')) {
      redirect('/dashboard/history');
    }
    if (error.message?.includes('403')) {
      redirect(`/dashboard/check/${params.id}?upgrade=sources`);
    }
    throw error;
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        title="Sources Reviewed"
        subtitle={`${sourcesData.totalSources} sources analyzed during fact-checking`}
        graphic={<CompassGraphic />}
      />

      {/* Sources Content */}
      <SourcesClient
        checkId={params.id}
        initialData={sourcesData}
      />
    </div>
  );
}
