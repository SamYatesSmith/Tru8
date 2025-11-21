'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Check } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface SubscriptionTabProps {
  userData: any;
  subscriptionData: any;
  onUpdate: () => void;
}

export function SubscriptionTab({
  userData,
  subscriptionData,
  onUpdate,
}: SubscriptionTabProps) {
  const { getToken } = useAuth();
  const [monthlyUsage, setMonthlyUsage] = useState(0);
  const [loading, setLoading] = useState(false);

  const isFree = !subscriptionData?.hasSubscription;
  const isPro = subscriptionData?.plan === 'pro';

  // Fetch monthly usage from backend
  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const token = await getToken();
        const usageData = await apiClient.getUsage(token) as any;
        setMonthlyUsage(usageData.monthlyCreditsUsed || 0);
      } catch (error) {
        console.error('Failed to fetch usage:', error);
      }
    };

    fetchUsage();
  }, [getToken]);

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const priceId = process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO || 'price_placeholder';

      const session = await apiClient.createCheckoutSession({
        price_id: priceId,
        plan: 'pro',
      }, token) as any;

      window.location.href = session.url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start upgrade process. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const portal = await apiClient.createBillingPortalSession(token) as any;
      window.location.href = portal.url;
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      alert('Failed to open billing portal. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const creditsPerMonth = subscriptionData?.hasSubscription
    ? subscriptionData.creditsPerMonth
    : 3;

  return (
    <div className="space-y-8">
      {/* Current Plan Card */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6">Your Current Plan</h3>

        <div className="space-y-4">
          {/* Plan Name */}
          <div>
            <h4 className="text-2xl font-black text-white">
              {isFree ? 'Free' : 'Professional'}
            </h4>
            <p className="text-slate-400 mt-1">
              {isFree ? '3 free checks' : '£7 per month · 40 checks'}
            </p>
          </div>

          {/* Usage */}
          {isFree ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-300">
                  Usage this month: {monthlyUsage} / 3 checks
                </p>
                <p className="text-sm font-bold text-slate-300">
                  {Math.round((monthlyUsage / 3) * 100)}%
                </p>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] transition-all duration-500"
                  style={{ width: `${Math.min((monthlyUsage / 3) * 100, 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-300 mb-1">
                Next billing date:{' '}
                {subscriptionData?.currentPeriodEnd
                  ? new Date(subscriptionData.currentPeriodEnd).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })
                  : 'N/A'}
              </p>
              <p className="text-sm text-slate-300">
                Usage this month: {monthlyUsage} checks
              </p>
            </div>
          )}

          {/* Action Button */}
          {isFree ? (
            <button
              onClick={handleUpgrade}
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Upgrade to Professional'}
            </button>
          ) : (
            <button
              onClick={handleManageSubscription}
              disabled={loading}
              className="w-full px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </section>

      {/* Available Plans */}
      <section>
        <h3 className="text-xl font-bold text-white mb-6">Available Plans</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Plan Card */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h4 className="text-2xl font-black text-white mb-2">Free</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-white">£0</p>
              <p className="text-slate-400">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>3 free checks</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Basic verification</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Standard support</span>
              </li>
            </ul>

            <button
              disabled={isFree}
              className="w-full px-6 py-3 bg-slate-700 text-slate-400 font-medium rounded-lg cursor-not-allowed"
            >
              {isFree ? 'Current Plan' : 'Downgrade'}
            </button>
          </div>

          {/* Professional Plan Card */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h4 className="text-2xl font-black text-white mb-2">Professional</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-white">£7</p>
              <p className="text-slate-400">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>40 checks per month</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Priority processing</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Priority support</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Advanced features</span>
              </li>
            </ul>

            {isPro ? (
              <button
                disabled
                className="w-full px-6 py-3 bg-slate-700 text-slate-400 font-medium rounded-lg cursor-not-allowed"
              >
                Current Plan
              </button>
            ) : (
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Upgrade Now'}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
