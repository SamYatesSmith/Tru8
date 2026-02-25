'use client';

import { useState } from 'react';
import { CheckCircle } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { SubscriptionsComingSoon } from '@/components/subscriptions/coming-soon';
import { TIERS, getTierPriceId, type TierConfig } from '@/lib/tiers';

const SUBSCRIPTIONS_ENABLED = process.env.NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED === 'true';

/**
 * Stitch W-01 Pricing Section
 *
 * Four cards: Free Trial, Professional, Developer (highlighted), Enterprise.
 * Black CTAs, orange accent on highlighted card. Stripe checkout for paid tiers.
 */
export function StitchPricing() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [processingTier, setProcessingTier] = useState<string | null>(null);
  const [showComingSoon, setShowComingSoon] = useState(false);
  const { isSignedIn, getToken } = useAuth();

  const handleTierClick = async (tier: TierConfig) => {
    // Free tier — just open auth modal
    if (tier.id === 'free') {
      setIsAuthModalOpen(true);
      return;
    }

    // Enterprise — open contact link
    if (tier.contactUrl) {
      window.location.href = tier.contactUrl;
      return;
    }

    // Paid tiers — Stripe checkout
    if (!SUBSCRIPTIONS_ENABLED) {
      setShowComingSoon(true);
      return;
    }

    if (!isSignedIn) {
      setIsAuthModalOpen(true);
      return;
    }

    const priceId = getTierPriceId(tier);
    if (!priceId) {
      alert('This plan is not yet available. Please try again later.');
      return;
    }

    setProcessingTier(tier.id);
    try {
      const token = await getToken();
      const session = await apiClient.createCheckoutSession({
        price_id: priceId,
        plan: tier.id,
      }, token) as { session_id: string; url: string };

      if (session.url) {
        window.location.href = session.url;
      }
    } catch (error: any) {
      console.error('Failed to create checkout session:', error);
      if (error.message?.includes('coming soon') || error.message?.includes('beta')) {
        setShowComingSoon(true);
      } else {
        alert('Failed to start checkout. Please try again.');
      }
      setProcessingTier(null);
    }
  };

  return (
    <>
      <section id="pricing" className="py-24 md:py-32 border-t border-zinc-100">
        <div className="max-w-6xl mx-auto px-6">
          {/* Header */}
          <div className="text-center mb-20">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
              Plans
            </span>
            <h2 className="text-3xl md:text-4xl font-light tracking-tight">
              Choose your <span className="font-bold">plan</span>
            </h2>
          </div>

          {/* Pricing cards — 2x2 grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {TIERS.map((tier) => (
              <div
                key={tier.id}
                className="border border-zinc-200 p-8 md:p-12 flex flex-col bg-white relative"
              >
                {tier.highlighted && (
                  <div className="absolute top-4 right-4 bg-accent w-2 h-2" />
                )}

                <div className="mb-10">
                  <h3 className="text-2xl font-bold uppercase tracking-tight mb-2">
                    {tier.name}
                  </h3>
                  <p className="text-zinc-500 text-sm">{tier.description}</p>
                </div>

                <div className="text-5xl font-light mb-10">
                  {tier.price !== null ? (
                    <>
                      £{tier.price}
                      <span className="text-lg text-zinc-400">
                        /{tier.period === 'lifetime' ? 'mo' : 'mo'}
                      </span>
                    </>
                  ) : (
                    <span className="text-3xl">Custom</span>
                  )}
                </div>

                <ul className="space-y-4 mb-12 flex-grow">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm text-zinc-600">
                      <CheckCircle
                        className={`flex-shrink-0 mt-0.5 ${
                          tier.highlighted ? 'text-accent' : 'text-zinc-300'
                        }`}
                        size={18}
                      />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleTierClick(tier)}
                  disabled={processingTier === tier.id}
                  className="w-full bg-black text-white py-4 text-[11px] font-bold tracking-[0.2em] uppercase hover:bg-zinc-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {processingTier === tier.id ? 'Processing...' : tier.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      {showComingSoon && (
        <SubscriptionsComingSoon
          variant="modal"
          source="pricing"
          onDismiss={() => setShowComingSoon(false)}
        />
      )}
    </>
  );
}
