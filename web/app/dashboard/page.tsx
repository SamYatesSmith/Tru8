import { auth } from '@clerk/nextjs/server';
import { apiClient } from '@/lib/api';
import { calculateMonthlyUsage } from '@/lib/usage-utils';
import { PageHeader } from './components/page-header';
import { JusticeScalesGraphic } from './components/justice-scales-graphic';
import { UpgradeBanner } from './components/upgrade-banner';
import { UsageCard } from './components/usage-card';
import { QuickActionCard } from './components/quick-action-card';
import { RecentChecksList } from './components/recent-checks-list';

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
}

interface ChecksResponse {
  checks: any[];
  total: number;
}

export default async function DashboardPage() {
  const { userId, getToken } = auth();

  // TEMPORARY: Mock data for testing when not authenticated
  let user: User;
  let subscription: Subscription;
  let checksResponse: ChecksResponse;

  if (!userId) {
    // Mock data for testing
    user = {
      id: 'test-user-123',
      name: 'Test User',
      email: 'test@example.com',
      credits: 3,
    };

    subscription = {
      hasSubscription: false,
      plan: 'free',
      creditsPerMonth: 3,
    };

    checksResponse = {
      checks: [],
      total: 0,
    };
  } else {
    // Real data fetch
    const token = await getToken();
    [user, subscription, checksResponse] = await Promise.all([
      apiClient.getCurrentUser(token) as Promise<User>,
      apiClient.getSubscriptionStatus(token) as Promise<Subscription>,
      apiClient.getChecks(token, 0, 5) as Promise<ChecksResponse>,
    ]);
  }

  // Calculate monthly usage
  const monthlyUsage = calculateMonthlyUsage(checksResponse.checks);

  // Determine credits per month (3 for free, or subscription amount)
  const creditsPerMonth = subscription.hasSubscription
    ? subscription.creditsPerMonth
    : 3;

  // Show upgrade banner only for free users
  const showUpgradeBanner = !subscription.hasSubscription || subscription.plan === 'free';

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
    </div>
  );
}
