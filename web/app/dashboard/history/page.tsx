import { auth } from '@clerk/nextjs/server';
import { apiClient } from '@/lib/api';
import { PageHeader } from '../components/page-header';
import { CompassGraphic } from '../components/compass-graphic';
import { HistoryContent } from './components/history-content';

interface ChecksResponse {
  checks: any[];
  total: number;
}

export default async function HistoryPage() {
  const { userId, getToken } = auth();

  // TEMPORARY: Mock data for testing when not authenticated
  let initialChecks: ChecksResponse;

  if (!userId) {
    // Mock data for testing
    initialChecks = {
      checks: [],
      total: 0,
    };
  } else {
    // Fetch first page
    const token = await getToken();
    initialChecks = await apiClient.getChecks(token, 0, 20) as ChecksResponse;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Check History"
        subtitle="View, search, and manage all your fact-checking verifications in one place"
        ctaText="New Check"
        ctaHref="/dashboard/new-check"
        graphic={<CompassGraphic />}
      />

      <HistoryContent initialChecks={initialChecks} />
    </div>
  );
}
