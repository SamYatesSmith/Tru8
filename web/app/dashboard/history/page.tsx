import { auth } from '@clerk/nextjs/server';
import { apiClient } from '@/lib/api';
import { PageHeader } from '../components/page-header';
import { HistoryContent } from './components/history-content';

interface ChecksResponse {
  checks: any[];
  total: number;
}

export default async function HistoryPage() {
  const { getToken } = auth();

  // Fetch first page of checks
  const token = await getToken();
  const initialChecks = await apiClient.getChecks(token, 0, 20) as ChecksResponse;

  return (
    <div className="space-y-8">
      {/* Custom wrapper for History page with extra vertical space */}
      <div className="py-8">
        <PageHeader
          title="Check History"
          subtitle="View, search, and manage all your analyses in one place"
          ctaText="New Check"
          ctaHref="/dashboard/new-check"
        />
      </div>

      <HistoryContent initialChecks={initialChecks} />
    </div>
  );
}
