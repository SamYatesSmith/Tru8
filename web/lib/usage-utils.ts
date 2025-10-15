/**
 * Calculate monthly usage from checks
 * Filters checks by current month (or subscription start if more recent) and sums creditsUsed
 */
export function calculateMonthlyUsage(checks: any[], subscriptionStartDate?: string | Date): number {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  // If user has a subscription that started this month, only count checks after subscription start
  let cutoffDate = startOfMonth;
  if (subscriptionStartDate) {
    const subStart = new Date(subscriptionStartDate);
    // Use the later of the two dates (start of month or subscription start)
    cutoffDate = subStart > startOfMonth ? subStart : startOfMonth;
  }

  const monthlyChecks = checks.filter(check => {
    const checkDate = new Date(check.createdAt);
    return checkDate >= cutoffDate;
  });

  return monthlyChecks.reduce((sum, check) => {
    return sum + (check.creditsUsed || 1);
  }, 0);
}
