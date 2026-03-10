import { auth } from '@clerk/nextjs/server';
import { apiClient, UserStats } from '@/lib/api';
import { PageHeader } from './components/page-header';
import { UpgradeBanner } from './components/upgrade-banner';
import { UsageCard } from './components/usage-card';
import { QuickActionCard } from './components/quick-action-card';
import { RecentChecksList } from './components/recent-checks-list';
import { UserInsightsCard } from './components/user-insights-card';

// Force dynamic rendering - prevents Next.js from caching this page
export const dynamic = 'force-dynamic';

interface User {
  id: string;
  name: string | null;
  email: string;
  credits: number;
}

interface Subscription {
  hasSubscription: boolean;
  plan: string;
  creditsPerMonth: number;
  currentPeriodStart?: string;
}

interface UsageData {
  periodCreditsUsed: number;
  creditsPerPeriod: number;
  creditsRemaining: number;
  totalCreditsUsed: number;
  isTrial: boolean;
}

interface ChecksResponse {
  checks: any[];
  total: number;
}

/**
 * Dashboard Page
 *
 * UNIFIED AUTH FLOW:
 * - Middleware guarantees authentication
 * - Just fetch data and render
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: { upgraded?: string; cancelled?: string };
}) {
  const { getToken } = auth();
  const token = await getToken();
  const [user, subscription, usage, checksResponse, stats] = await Promise.all([
    apiClient.getCurrentUser(token) as Promise<User>,
    apiClient.getSubscriptionStatus(token) as Promise<Subscription>,
    apiClient.getUsage(token) as Promise<UsageData>,
    apiClient.getChecks(token, 0, 5) as Promise<ChecksResponse>,
    apiClient.getUserStats(token) as Promise<UserStats>,
  ]);

  const periodUsage = usage.periodCreditsUsed;
  const creditsLimit = usage.creditsPerPeriod;
  const isTrial = usage.isTrial;

  const showUpgradeBanner = isTrial || !subscription.hasSubscription || subscription.plan === 'free' || subscription.plan === 'free_trial';

  const isUpgraded = searchParams.upgraded === 'true';
  const isCancelled = searchParams.cancelled === 'true';

  return (
    <div className="space-y-4 md:space-y-8">
      {/* Hero Section */}
      <PageHeader
        title="Evidence Research Dashboard"
        subtitle="Submit claims, URLs, and articles for multi-source analysis."
        ctaText="New Check"
        ctaHref="/dashboard/new-check"
      />

      {/* Success/Cancellation Messages */}
      {isUpgraded && (
        <div className="bg-emerald-50 border border-emerald-200 p-3 md:p-4 flex items-start gap-3">
          <svg className="w-5 h-5 md:w-6 md:h-6 text-emerald-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="text-emerald-800 font-bold mb-1 text-sm md:text-base">Upgrade Successful!</h3>
            <p className="text-emerald-600 text-xs md:text-sm">
              Your account has been upgraded! Check your new monthly allowance below.
            </p>
          </div>
        </div>
      )}

      {isCancelled && (
        <div className="bg-amber-50 border border-amber-200 p-3 md:p-4 flex items-start gap-3">
          <svg className="w-5 h-5 md:w-6 md:h-6 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="text-amber-800 font-bold mb-1 text-sm md:text-base">Upgrade Cancelled</h3>
            <p className="text-amber-600 text-xs md:text-sm">
              Your upgrade was cancelled. You can try again anytime.
            </p>
          </div>
        </div>
      )}

      {/* Welcome Message */}
      <h2 className="hidden md:block text-xl font-bold text-zinc-900 mt-8 mb-6">
        Welcome back, {user.name || 'User'}
      </h2>

      {/* Upgrade Banner (conditional) */}
      {showUpgradeBanner && (
        <UpgradeBanner currentPlan="Free" />
      )}

      {/* Two-Column Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-4 md:mb-8">
        <UsageCard
          used={periodUsage}
          total={creditsLimit}
          label={isTrial ? "Trial checks used" : "Checks used this month"}
        />
        <QuickActionCard used={periodUsage} limit={creditsLimit} />
      </div>

      {/* Recent Checks */}
      <RecentChecksList checks={checksResponse.checks} />

      {/* User Insights */}
      {stats.totalChecks > 0 && (
        <UserInsightsCard stats={stats} />
      )}
    </div>
  );
}
