/**
 * Calculate monthly usage from checks
 * Filters checks by current month and sums creditsUsed
 */
export function calculateMonthlyUsage(checks: any[]): number {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  const monthlyChecks = checks.filter(check => {
    const checkDate = new Date(check.createdAt);
    return checkDate >= startOfMonth;
  });

  return monthlyChecks.reduce((sum, check) => {
    return sum + (check.creditsUsed || 1);
  }, 0);
}
