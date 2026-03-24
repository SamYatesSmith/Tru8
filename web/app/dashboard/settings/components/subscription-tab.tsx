'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Check } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SubscriptionsComingSoon } from '@/components/subscriptions/coming-soon';
import { TIERS, getTierPriceId, type TierConfig } from '@/lib/tiers';

interface SubscriptionTabProps {
  userData: any;
  subscriptionData: any;
  onUpdate: () => void;
}

/** Tier ordering for upgrade/downgrade logic */
const TIER_ORDER = ['free', 'starter', 'professional', 'enterprise'];

export function SubscriptionTab({
  userData,
  subscriptionData,
  onUpdate,
}: SubscriptionTabProps) {
  const { getToken } = useAuth();
  const [periodUsage, setPeriodUsage] = useState(0);
  const [isTrial, setIsTrial] = useState(true);
  const [loading, setLoading] = useState(false);

  const currentPlan = subscriptionData?.hasSubscription
    ? subscriptionData.plan
    : 'free';
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

  const handleUpgrade = async (tier: TierConfig) => {
    const priceId = getTierPriceId(tier);
    if (!priceId) {
      alert('This plan is not yet available. Please try again later.');
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      const session = await apiClient.createCheckoutSession({
        price_id: priceId,
        plan: tier.id,
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

  const currentTierIndex = TIER_ORDER.indexOf(currentPlan);

  // Find current tier config for display
  const currentTierConfig = TIERS.find((t) => t.id === currentPlan) || TIERS[0];

  // Show Coming Soon for free users when subscriptions are disabled
  if (currentPlan === 'free' && !subscriptionsEnabled) {
    return (
      <div className="space-y-8">
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
          <div>
            <h4 className="text-2xl font-black text-zinc-900">
              {currentTierConfig.name}
            </h4>
            <p className="text-zinc-500 mt-1 font-mono text-sm">
              {currentPlan === 'free'
                ? '3 free checks to try Tru8'
                : `£${currentTierConfig.price} per month · ${creditsPerMonth} checks`}
            </p>
          </div>

          {/* Usage */}
          {currentPlan === 'free' ? (
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
          {currentPlan !== 'free' && (
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
          {TIERS.map((tier) => {
            const tierIndex = TIER_ORDER.indexOf(tier.id);
            const isCurrent = tier.id === currentPlan;
            const isUpgrade = tierIndex > currentTierIndex;
            const isEnterprise = tier.id === 'enterprise';

            return (
              <div key={tier.id} className="bg-white border border-zinc-200 p-6 relative">
                {tier.highlighted && (
                  <div className="absolute top-3 right-3 bg-accent w-2 h-2" />
                )}

                <h4 className="text-2xl font-black text-zinc-900 mb-2">{tier.name}</h4>
                <div className="mb-6">
                  {tier.price !== null ? (
                    <>
                      <p className="text-4xl font-black text-zinc-900">£{tier.price}</p>
                      <p className="text-zinc-500 font-mono text-sm">
                        {tier.period === 'lifetime' ? 'one-time' : 'per month'}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-4xl font-black text-zinc-900">Custom</p>
                      <p className="text-zinc-500 font-mono text-sm">contact us</p>
                    </>
                  )}
                </div>

                <ul className="space-y-3 mb-6">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-zinc-600">
                      <Check size={20} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <button
                    disabled
                    className="w-full px-6 py-3 border border-zinc-200 text-zinc-400 cursor-not-allowed"
                  >
                    Current Plan
                  </button>
                ) : isEnterprise ? (
                  <a
                    href={tier.contactUrl}
                    className="block w-full px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors text-center"
                  >
                    Contact Us
                  </a>
                ) : isUpgrade ? (
                  <button
                    onClick={() => handleUpgrade(tier)}
                    disabled={loading}
                    className="w-full px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50"
                  >
                    {loading ? 'Loading...' : 'Upgrade Now'}
                  </button>
                ) : (
                  <button
                    disabled
                    className="w-full px-6 py-3 border border-zinc-200 text-zinc-400 cursor-not-allowed"
                  >
                    Downgrade
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
