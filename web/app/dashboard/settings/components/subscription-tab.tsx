'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Check } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SubscriptionsComingSoon } from '@/components/subscriptions/coming-soon';

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
  const [periodUsage, setPeriodUsage] = useState(0);
  const [isTrial, setIsTrial] = useState(true);
  const [loading, setLoading] = useState(false);

  const isFree = !subscriptionData?.hasSubscription;
  const isPro = subscriptionData?.plan === 'pro';
  const subscriptionsEnabled = subscriptionData?.subscriptionsEnabled ?? false;

  // Fetch usage from backend
  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const token = await getToken();
        const usageData = await apiClient.getUsage(token) as any;
        setPeriodUsage(usageData.periodCreditsUsed || 0);
        setIsTrial(usageData.isTrial ?? true);
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

  // Show Coming Soon for free users when subscriptions are disabled
  if (isFree && !subscriptionsEnabled) {
    return (
      <div className="space-y-8">
        {/* Current Plan Card - Still show their free tier status */}
        <section className="bg-white border border-zinc-200 p-6">
          <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-6">Your Current Plan</h3>
          <div className="space-y-4">
            <div>
              <h4 className="text-2xl font-black text-zinc-900">Free Trial</h4>
              <p className="text-zinc-500 mt-1">3 free checks to try Tru8</p>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-zinc-600">
                  Trial usage: {periodUsage} / 3 checks
                </p>
                <p className="text-sm font-bold text-zinc-900 font-mono">
                  {Math.round((periodUsage / 3) * 100)}%
                </p>
              </div>
              <div className="w-full h-2 bg-zinc-100 overflow-hidden">
                <div
                  className="h-full bg-zinc-900 transition-all duration-500"
                  style={{ width: `${Math.min((periodUsage / 3) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Coming Soon Section */}
        <SubscriptionsComingSoon source="settings" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Current Plan Card */}
      <section className="bg-white border border-zinc-200 p-6">
        <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-6">Your Current Plan</h3>

        <div className="space-y-4">
          {/* Plan Name */}
          <div>
            <h4 className="text-2xl font-black text-zinc-900">
              {isFree ? 'Free Trial' : 'Professional'}
            </h4>
            <p className="text-zinc-500 mt-1 font-mono text-sm">
              {isFree ? '3 free checks to try Tru8' : '£7 per month · 40 checks'}
            </p>
          </div>

          {/* Usage */}
          {isFree ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-zinc-600">
                  Trial usage: {periodUsage} / 3 checks
                </p>
                <p className="text-sm font-bold text-zinc-900 font-mono">
                  {Math.round((periodUsage / 3) * 100)}%
                </p>
              </div>
              <div className="w-full h-2 bg-zinc-100 overflow-hidden">
                <div
                  className="h-full bg-zinc-900 transition-all duration-500"
                  style={{ width: `${Math.min((periodUsage / 3) * 100, 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm text-zinc-600 mb-1">
                Next billing date:{' '}
                {subscriptionData?.currentPeriodEnd
                  ? new Date(subscriptionData.currentPeriodEnd).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })
                  : 'N/A'}
              </p>
              <p className="text-sm text-zinc-600">
                Usage this month: {periodUsage} checks
              </p>
            </div>
          )}

          {/* Action Button */}
          {isFree ? (
            <button
              onClick={handleUpgrade}
              disabled={loading}
              className="w-full px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Upgrade to Professional'}
            </button>
          ) : (
            <button
              onClick={handleManageSubscription}
              disabled={loading}
              className="w-full px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </section>

      {/* Available Plans */}
      <section>
        <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-6">Available Plans</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Plan Card */}
          <div className="bg-white border border-zinc-200 p-6">
            <h4 className="text-2xl font-black text-zinc-900 mb-2">Free</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-zinc-900">£0</p>
              <p className="text-zinc-500 font-mono text-sm">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>3 free checks</span>
              </li>
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>Evidence research</span>
              </li>
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>Community support</span>
              </li>
            </ul>

            <button
              disabled={isFree}
              className="w-full px-6 py-3 border border-zinc-200 text-zinc-400 cursor-not-allowed"
            >
              {isFree ? 'Current Plan' : 'Downgrade'}
            </button>
          </div>

          {/* Professional Plan Card */}
          <div className="bg-white border border-zinc-200 p-6">
            <h4 className="text-2xl font-black text-zinc-900 mb-2">Professional</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-zinc-900">£7</p>
              <p className="text-zinc-500 font-mono text-sm">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>40 checks per month</span>
              </li>
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>Priority processing</span>
              </li>
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>Priority support</span>
              </li>
              <li className="flex items-start gap-2 text-zinc-600">
                <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>Export reports</span>
              </li>
            </ul>

            {isPro ? (
              <button
                disabled
                className="w-full px-6 py-3 border border-zinc-200 text-zinc-400 cursor-not-allowed"
              >
                Current Plan
              </button>
            ) : (
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50"
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
