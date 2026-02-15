'use client';

import { useState } from 'react';
import { CheckCircle } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { SubscriptionsComingSoon } from '@/components/subscriptions/coming-soon';

const SUBSCRIPTIONS_ENABLED = process.env.NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED === 'true';

/**
 * Stitch W-01 Pricing Section
 *
 * Two cards: Free Trial ($0) + Professional (GBP 7/month).
 * Black CTAs, orange check icons on pro card, tiny orange square indicator.
 * Retains Stripe checkout + auth modal logic from original PricingCards.
 */
export function StitchPricing() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showComingSoon, setShowComingSoon] = useState(false);
  const { isSignedIn, getToken } = useAuth();

  const handleFreePlan = () => {
    setIsAuthModalOpen(true);
  };

  const handleProfessionalPlan = async () => {
    if (!SUBSCRIPTIONS_ENABLED) {
      setShowComingSoon(true);
      return;
    }

    if (!isSignedIn) {
      setIsAuthModalOpen(true);
      return;
    }

    setIsProcessing(true);
    try {
      const token = await getToken();
      const session = await apiClient.createCheckoutSession({
        price_id: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO || 'price_placeholder',
        plan: 'professional',
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
      setIsProcessing(false);
    }
  };

  return (
    <>
      <section id="pricing" className="py-24 md:py-32 border-t border-zinc-100">
        <div className="max-w-5xl mx-auto px-6">
          {/* Header */}
          <div className="text-center mb-20">
            <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
              Deployment Models
            </span>
            <h2 className="text-3xl md:text-4xl font-light tracking-tight">
              Choose your <span className="font-bold">Scale</span>
            </h2>
          </div>

          {/* Pricing cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* Free Trial */}
            <div className="border border-zinc-200 p-8 md:p-12 flex flex-col bg-white">
              <div className="mb-10">
                <h3 className="text-2xl font-bold uppercase tracking-tight mb-2">Free Trial</h3>
                <p className="text-zinc-500 text-sm">Perfect for individual researchers</p>
              </div>
              <div className="text-5xl font-light mb-10">
                $0<span className="text-lg text-zinc-400">/mo</span>
              </div>
              <ul className="space-y-4 mb-12 flex-grow">
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-zinc-300 flex-shrink-0 mt-0.5" size={18} />
                  5 Research Checks / Month
                </li>
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-zinc-300 flex-shrink-0 mt-0.5" size={18} />
                  Standard Source Access
                </li>
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-zinc-300 flex-shrink-0 mt-0.5" size={18} />
                  Community Support
                </li>
              </ul>
              <button
                onClick={handleFreePlan}
                className="w-full bg-black text-white py-4 text-[11px] font-bold tracking-[0.2em] uppercase hover:bg-zinc-800 transition-colors"
              >
                Start Trial
              </button>
            </div>

            {/* Professional */}
            <div className="border border-zinc-200 p-8 md:p-12 flex flex-col bg-white relative">
              <div className="absolute top-4 right-4 bg-accent w-2 h-2" />
              <div className="mb-10">
                <h3 className="text-2xl font-bold uppercase tracking-tight mb-2">Professional</h3>
                <p className="text-zinc-500 text-sm">For clinical teams &amp; labs</p>
              </div>
              <div className="text-5xl font-light mb-10">
                GBP 7<span className="text-lg text-zinc-400">/month</span>
              </div>
              <ul className="space-y-4 mb-12 flex-grow">
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-accent flex-shrink-0 mt-0.5" size={18} />
                  40 credits / Month
                </li>
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-accent flex-shrink-0 mt-0.5" size={18} />
                  All 14+ Advanced Sources
                </li>
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-accent flex-shrink-0 mt-0.5" size={18} />
                  Priority Support + Export Tools
                </li>
                <li className="flex items-start gap-3 text-sm text-zinc-600">
                  <CheckCircle className="text-accent flex-shrink-0 mt-0.5" size={18} />
                  Team Collaboration Suite
                </li>
              </ul>
              <button
                onClick={handleProfessionalPlan}
                disabled={isProcessing}
                className="w-full bg-black text-white py-4 text-[11px] font-bold tracking-[0.2em] uppercase hover:bg-zinc-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Processing...' : 'Get Started'}
              </button>
            </div>
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
