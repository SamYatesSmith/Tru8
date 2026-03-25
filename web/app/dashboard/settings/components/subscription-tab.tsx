'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Check, AlertTriangle, ArrowRight } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { TIERS, getTierPriceId, type TierConfig } from '@/lib/tiers';

interface SubscriptionTabProps {
  userData: any;
  subscriptionData: any;
  onUpdate: () => void;
}

const TIER_ORDER = ['free', 'starter', 'professional', 'enterprise'];

export function SubscriptionTab({
  userData,
  subscriptionData,
  onUpdate,
}: SubscriptionTabProps) {
  const { getToken } = useAuth();
  const [periodUsage, setPeriodUsage] = useState(0);
  const [creditsPerPeriod, setCreditsPerPeriod] = useState(3);
  const [isTrial, setIsTrial] = useState(true);
  const [loading, setLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [reactivateLoading, setReactivateLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const currentPlan = subscriptionData?.hasSubscription
    ? subscriptionData.plan
    : 'free';
  const subscriptionsEnabled = subscriptionData?.subscriptionsEnabled ?? false;
  const cancelAtPeriodEnd = subscriptionData?.cancelAtPeriodEnd ?? false;
  const currentTierIndex = TIER_ORDER.indexOf(currentPlan);
  const currentTierConfig = TIERS.find((t) => t.id === currentPlan) || TIERS[0];
  const isPaid = currentPlan !== 'free';
  const creditsPerMonth = subscriptionData?.hasSubscription
    ? subscriptionData.creditsPerMonth
    : 3;

  const periodEndFormatted = subscriptionData?.currentPeriodEnd
    ? new Date(subscriptionData.currentPeriodEnd).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    : null;

  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const token = await getToken();
        const usageData = (await apiClient.getUsage(token)) as any;
        setPeriodUsage(usageData.periodCreditsUsed || 0);
        setCreditsPerPeriod(usageData.creditsPerPeriod || 3);
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
      const session = (await apiClient.createCheckoutSession(
        { price_id: priceId, plan: tier.id },
        token
      )) as any;
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
      const portal = (await apiClient.createBillingPortalSession(token)) as any;
      window.location.href = portal.url;
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      alert('Failed to open billing portal. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    const periodEnd =
      periodEndFormatted || 'the end of the current period';
    const confirmed = confirm(
      `Are you sure? Your subscription will remain active until ${periodEnd}, then revert to the free plan.`
    );
    if (!confirmed) return;

    setCancelLoading(true);
    setActionMessage(null);
    try {
      const token = await getToken();
      await apiClient.cancelSubscription(token);
      setActionMessage({
        type: 'success',
        text: `Your subscription will cancel on ${periodEnd}.`,
      });
      onUpdate();
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      setActionMessage({
        type: 'error',
        text: 'Failed to cancel subscription. Please try again.',
      });
    } finally {
      setCancelLoading(false);
    }
  };

  const handleReactivateSubscription = async () => {
    setReactivateLoading(true);
    setActionMessage(null);
    try {
      const token = await getToken();
      await apiClient.reactivateSubscription(token);
      setActionMessage({
        type: 'success',
        text: 'Subscription reactivated successfully.',
      });
      onUpdate();
    } catch (error) {
      console.error('Failed to reactivate subscription:', error);
      setActionMessage({
        type: 'error',
        text: 'Failed to reactivate subscription. Please try again.',
      });
    } finally {
      setReactivateLoading(false);
    }
  };

  // Max feature count for equal-height cards
  const maxFeatures = Math.max(...TIERS.map((t) => t.features.length));

  return (
    <div className="space-y-10">
      {/* ── Current Plan ── */}
      <section className="bg-white border border-zinc-200">
        <div className="p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
            {/* Left: Plan info */}
            <div className="flex-1 min-w-0">
              <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-3">
                Your Current Plan
              </h3>
              <h4 className="text-2xl md:text-3xl font-black text-zinc-900">
                {currentTierConfig.name}
              </h4>
              <p className="text-zinc-500 mt-1 font-mono text-sm">
                {isPaid
                  ? `£${currentTierConfig.price}/month · ${creditsPerMonth} checks`
                  : '3 free checks to try Tru8'}
              </p>
            </div>

            {/* Right: Usage + actions */}
            <div className="md:text-right md:min-w-[240px]">
              {!isPaid ? (
                <>
                  <p className="text-sm text-zinc-600 mb-2">
                    {periodUsage} of 3 checks used
                  </p>
                  <div className="w-full h-1.5 bg-zinc-100 overflow-hidden">
                    <div
                      className="h-full bg-zinc-900 transition-all duration-500"
                      style={{
                        width: `${Math.min((periodUsage / 3) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </>
              ) : (
                <>
                  <p className="text-sm text-zinc-600">
                    {periodUsage} of {creditsPerMonth} checks used this month
                  </p>
                  {!cancelAtPeriodEnd && periodEndFormatted && (
                    <p className="text-xs text-zinc-400 mt-1">
                      Renews {periodEndFormatted}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Cancellation Warning */}
          {isPaid && cancelAtPeriodEnd && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 mt-6">
              <AlertTriangle
                size={18}
                className="text-amber-600 flex-shrink-0 mt-0.5"
              />
              <div>
                <p className="text-sm font-medium text-amber-800">
                  Your subscription cancels on {periodEndFormatted}
                </p>
                <p className="text-xs text-amber-600 mt-1">
                  You&apos;ll keep access until then, after which your account
                  reverts to the free plan.
                </p>
              </div>
            </div>
          )}

          {/* Action Message */}
          {actionMessage && (
            <div
              className={`p-3 text-sm mt-4 ${
                actionMessage.type === 'success'
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}
            >
              {actionMessage.text}
            </div>
          )}
        </div>

        {/* Footer actions for paid users */}
        {isPaid && (
          <div className="border-t border-zinc-200 px-6 md:px-8 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-6">
              <button
                onClick={handleManageSubscription}
                disabled={loading}
                className="text-xs font-medium text-zinc-900 hover:text-accent transition-colors disabled:opacity-50"
              >
                Manage subscription &rarr;
              </button>
              <button
                onClick={handleManageSubscription}
                className="text-xs text-zinc-400 hover:text-zinc-900 transition-colors"
              >
                Billing history
              </button>
            </div>
            <div>
              {cancelAtPeriodEnd ? (
                <button
                  onClick={handleReactivateSubscription}
                  disabled={reactivateLoading}
                  className="text-xs text-accent hover:underline transition-colors disabled:opacity-50"
                >
                  {reactivateLoading
                    ? 'Reactivating...'
                    : 'Reactivate subscription'}
                </button>
              ) : (
                <button
                  onClick={handleCancelSubscription}
                  disabled={cancelLoading}
                  className="text-xs text-zinc-400 hover:text-red-500 transition-colors disabled:opacity-50"
                >
                  {cancelLoading ? 'Cancelling...' : 'Cancel subscription'}
                </button>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Available Plans ── */}
      <section>
        <h3 className="font-mono text-[10px] font-bold tracking-[0.3em] uppercase text-zinc-400 mb-6">
          Compare Plans
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TIERS.map((tier) => {
            const tierIndex = TIER_ORDER.indexOf(tier.id);
            const isCurrent = tier.id === currentPlan;
            const isUpgrade = tierIndex > currentTierIndex;
            const isEnterprise = tier.id === 'enterprise';
            const canUpgrade = isUpgrade && subscriptionsEnabled;
            const isHighlighted = tier.highlighted;

            return (
              <div
                key={tier.id}
                className={`relative flex flex-col bg-white border p-5 ${
                  isHighlighted
                    ? 'border-zinc-900 ring-1 ring-zinc-900'
                    : isCurrent
                    ? 'border-accent'
                    : 'border-zinc-200'
                }`}
              >

                {/* Current plan indicator */}
                {isCurrent && (
                  <div className="absolute -top-3 left-5 bg-accent text-white text-[9px] font-bold uppercase tracking-[0.2em] px-3 py-1">
                    Current
                  </div>
                )}

                {/* Price */}
                <div className="mb-5 pt-2">
                  <h4 className="text-sm font-bold uppercase tracking-wide text-zinc-900 mb-2">
                    {tier.name}
                  </h4>
                  {tier.price !== null ? (
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-black text-zinc-900">
                        £{tier.price}
                      </span>
                      <span className="text-xs text-zinc-400 font-mono">
                        {tier.period === 'lifetime' ? '' : '/mo'}
                      </span>
                    </div>
                  ) : (
                    <div>
                      <span className="text-3xl font-black text-zinc-900">
                        Custom
                      </span>
                    </div>
                  )}
                </div>

                {/* Features — equal height via min-height */}
                <ul className="space-y-2.5 mb-6 flex-1">
                  {tier.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm text-zinc-600"
                    >
                      <Check
                        size={16}
                        className="text-emerald-500 flex-shrink-0 mt-0.5"
                      />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA — pinned to bottom */}
                <div className="mt-auto">
                  {isCurrent ? (
                    <div className="w-full py-2.5 text-center text-xs font-medium text-zinc-400 border border-zinc-200">
                      Current Plan
                    </div>
                  ) : isEnterprise ? (
                    <a
                      href={tier.contactUrl}
                      className="flex items-center justify-center gap-2 w-full py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
                    >
                      Contact Us
                      <ArrowRight size={14} />
                    </a>
                  ) : isUpgrade ? (
                    <button
                      onClick={() => handleUpgrade(tier)}
                      disabled={loading}
                      className="flex items-center justify-center gap-2 w-full py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50"
                    >
                      {loading ? 'Loading...' : 'Upgrade'}
                      {!loading && <ArrowRight size={14} />}
                    </button>
                  ) : (
                    <div className="w-full py-2.5 text-center text-xs font-medium text-zinc-300 border border-zinc-100">
                      &mdash;
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
