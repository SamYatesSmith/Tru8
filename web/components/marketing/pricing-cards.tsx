'use client';

import { useState } from 'react';
import { Check } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

/**
 * Pricing Cards Component
 *
 * Two pricing tiers: Free and Professional
 *
 * Free Plan (£0):
 * - 7 day trial / 5 free checks (Note: Backend gives 3 credits)
 * - Basic source checking
 * - Standard support
 * - Web interface access
 * - CTA: "START FREE TRIAL" → Opens Clerk auth modal
 * - Border: slate-700
 *
 * Professional Plan (£7/month):
 * - Badge: "Most Popular" (cyan)
 * - X40 verifications p/m
 * - Ability to verify URL's
 * - Quick & Deep modes
 * - Export to PDF/JSON/CSV
 * - Comprehensive sources (10+ citations)
 * - Priority support
 * - CTA: "GET STARTED" → Stripe checkout
 * - Border: cyan-400 (highlighted)
 *
 * Backend Integration:
 * - Free plan: Opens auth modal → User auto-created with 3 credits
 * - Professional plan: POST /api/v1/payments/create-checkout-session
 * - If not authenticated: Opens auth first, then triggers checkout
 */
export function PricingCards() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { isSignedIn, getToken } = useAuth();

  const handleFreePlan = () => {
    // Open auth modal for free trial
    setIsAuthModalOpen(true);
  };

  const handleProfessionalPlan = async () => {
    // Check if user is authenticated
    if (!isSignedIn) {
      // Open auth modal first
      setIsAuthModalOpen(true);
      return;
    }

    // Create Stripe checkout session
    setIsProcessing(true);
    try {
      // Get auth token from Clerk
      const token = await getToken();

      const session = await apiClient.createCheckoutSession({
        price_id: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO || 'price_placeholder',
        plan: 'professional',
      }, token) as { session_id: string; url: string };

      // Redirect to Stripe checkout
      if (session.url) {
        window.location.href = session.url;
      }
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start checkout. Please try again.');
      setIsProcessing(false);
    }
  };

  const plans = [
    {
      name: 'Free',
      price: '£0',
      period: '',
      badge: null,
      features: [
        '7 day trial / 5 free checks',
        'Basic source checking',
        'Standard support',
        'Web interface access',
      ],
      cta: 'START FREE TRIAL',
      highlighted: false,
      onCTA: handleFreePlan,
    },
    {
      name: 'Professional',
      price: '£7',
      period: '/month',
      badge: 'Most Popular',
      features: [
        'X40 verifications p/m',
        'Ability to verify URL\'s',
        'Quick & Deep modes',
        'Export to PDF/JSON/CSV',
        'Comprehensive sources (10+ citations)',
        'Priority support',
      ],
      cta: 'GET STARTED',
      highlighted: true,
      onCTA: handleProfessionalPlan,
    },
  ];

  return (
    <>
      <section id="pricing" className="py-20 px-4">
        <div className="container mx-auto max-w-7xl">
          {/* Header */}
          <div className="text-center mb-20">
            <h2 className="text-5xl md:text-6xl font-bold text-[#f57a07] mb-6">
              Choose Your Plan
            </h2>
            <p className="text-2xl text-slate-400">
              Professional fact-checking for every need
            </p>
          </div>

          {/* Pricing Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative bg-[#1a1f2e]/90 backdrop-blur-sm rounded-2xl p-12 border-2 ${
                  plan.highlighted
                    ? 'border-[#22d3ee] shadow-2xl shadow-[#22d3ee]/30'
                    : 'border-slate-700'
                } transition-all hover:border-opacity-80 hover:shadow-xl`}
              >
                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-5 left-1/2 -translate-x-1/2">
                    <div className="bg-[#22d3ee] text-slate-900 px-6 py-2 rounded-full text-base font-bold">
                      {plan.badge}
                    </div>
                  </div>
                )}

                {/* Plan Name */}
                <h3 className="text-3xl font-bold text-white mb-4">{plan.name}</h3>

                {/* Price */}
                <div className="mb-8">
                  <span className="text-7xl font-black text-white">{plan.price}</span>
                  {plan.period && (
                    <span className="text-slate-400 text-2xl ml-2">{plan.period}</span>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-4 mb-10">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-4">
                      <Check className="w-6 h-6 text-[#22d3ee] flex-shrink-0 mt-1" />
                      <span className="text-slate-300 text-lg">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <button
                  onClick={plan.onCTA}
                  disabled={isProcessing && plan.highlighted}
                  className={`w-full py-5 rounded-xl text-xl font-bold transition-all ${
                    plan.highlighted
                      ? 'bg-[#f57a07] hover:bg-[#e06a00] text-white shadow-xl hover:shadow-2xl'
                      : 'bg-transparent border-2 border-slate-700 hover:border-[#f57a07] hover:bg-slate-800/50 text-white'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isProcessing && plan.highlighted ? 'Processing...' : plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
