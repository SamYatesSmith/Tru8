import { auth } from '@clerk/nextjs/server';
import { apiClient, UserStats } from '@/lib/api';
import { PageHeader } from './components/page-header';
import { JusticeScalesGraphic } from './components/justice-scales-graphic';
import { UpgradeBanner } from './components/upgrade-banner';
import { UsageCard } from './components/usage-card';
import { QuickActionCard } from './components/quick-action-card';
import { RecentChecksList } from './components/recent-checks-list';
import { UserInsightsCard } from './components/user-insights-card';

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
  monthlyCreditsUsed: number;
  creditsPerMonth: number;
  creditsRemaining: number;
  totalCreditsUsed: number;
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
  // Middleware guarantees authentication - just get token and fetch data
  const { getToken } = auth();
  const token = await getToken();
  const [user, subscription, usage, checksResponse, stats] = await Promise.all([
    apiClient.getCurrentUser(token) as Promise<User>,
    apiClient.getSubscriptionStatus(token) as Promise<Subscription>,
    apiClient.getUsage(token) as Promise<UsageData>,
    apiClient.getChecks(token, 0, 5) as Promise<ChecksResponse>,
    apiClient.getUserStats(token) as Promise<UserStats>,
  ]);

  // Use server-calculated monthly usage
  const monthlyUsage = usage.monthlyCreditsUsed;
  const creditsPerMonth = usage.creditsPerMonth;

  // Show upgrade banner only for free users
  const showUpgradeBanner = !subscription.hasSubscription || subscription.plan === 'free';

  // Check for upgrade/cancellation status from URL params
  const isUpgraded = searchParams.upgraded === 'true';
  const isCancelled = searchParams.cancelled === 'true';

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <PageHeader
        title="Tru8: Your truth companion"
        subtitle="Instantly verify claims, URLs, and articles."
        ctaText="Start Verifying"
        ctaHref="/dashboard/new-check"
        graphic={<JusticeScalesGraphic />}
      />

      {/* Success/Cancellation Messages */}
      {isUpgraded && (
        <div className="bg-emerald-900/20 border border-emerald-700 rounded-lg p-4 flex items-start gap-3">
          <svg className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="text-emerald-400 font-bold mb-1">Upgrade Successful!</h3>
            <p className="text-emerald-200 text-sm">
              Welcome to Tru8 Professional! Your account has been upgraded and you now have access to 40 checks per month.
            </p>
          </div>
        </div>
      )}

      {isCancelled && (
        <div className="bg-amber-900/20 border border-amber-700 rounded-lg p-4 flex items-start gap-3">
          <svg className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="text-amber-400 font-bold mb-1">Upgrade Cancelled</h3>
            <p className="text-amber-200 text-sm">
              Your upgrade was cancelled. You can try again anytime.
            </p>
          </div>
        </div>
      )}

      {/* Welcome Message */}
      <h2 className="text-3xl font-bold text-white mt-12 mb-8">
        Welcome back, {user.name || 'User'}
      </h2>

      {/* Upgrade Banner (conditional) */}
      {showUpgradeBanner && (
        <UpgradeBanner currentPlan="Free" />
      )}

      {/* Two-Column Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <UsageCard
          used={monthlyUsage}
          total={creditsPerMonth}
          label="Checks used this month"
        />
        <QuickActionCard />
      </div>

      {/* Recent Checks */}
      <RecentChecksList checks={checksResponse.checks} />

      {/* User Insights (only show if user has completed checks) */}
      {stats.totalChecks > 0 && (
        <UserInsightsCard stats={stats} />
      )}
    </div>
  );
}
