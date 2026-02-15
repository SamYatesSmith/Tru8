'use client';

import { useState } from 'react';
import { Sparkles, Bell, Check, ArrowRight, X } from 'lucide-react';
import Link from 'next/link';

interface SubscriptionsComingSoonProps {
  /** Where the user came from, for context in the waitlist signup */
  source?: 'settings' | 'pricing' | 'upgrade-banner' | 'upgrade-modal' | 'beta-access';
  /** Optional callback when user dismisses or navigates away */
  onDismiss?: () => void;
  /** Show as modal overlay vs inline */
  variant?: 'inline' | 'modal';
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function SubscriptionsComingSoon({
  source = 'settings',
  onDismiss,
  variant = 'inline',
}: SubscriptionsComingSoonProps) {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleWaitlistSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setIsSubmitting(true);
    setError('');

    try {
      // Use public waitlist endpoint (no auth required)
      const response = await fetch(`${API_BASE_URL}/api/v1/waitlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to join waitlist');
      }

      setIsSubmitted(true);
    } catch (err: any) {
      console.error('Waitlist signup failed:', err);
      setError(err.message || 'Failed to join waitlist. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const content = (
    <div className="text-center">
      {/* Icon */}
      <div className="flex justify-center mb-6">
        <div className="w-20 h-20 bg-zinc-100 flex items-center justify-center">
          <Sparkles className="w-10 h-10 text-accent" />
        </div>
      </div>

      {/* Heading */}
      <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 mb-3">
        {source === 'upgrade-modal' ? 'Closed Beta' : 'Pro Subscriptions Coming Soon'}
      </h2>

      <p className="text-zinc-500 mb-8 max-w-md mx-auto">
        {source === 'upgrade-modal'
          ? "Tru8 is currently in closed beta with limited access. Join our waitlist to be notified when we open to the public!"
          : "We're currently in beta testing. Pro subscriptions with 40 monthly checks, priority processing, and advanced features will be available soon."
        }
      </p>

      {/* Waitlist Form */}
      {!isSubmitted ? (
        <form onSubmit={handleWaitlistSignup} className="max-w-sm mx-auto mb-8">
          <label className="block font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-2 text-left">
            <Bell className="w-3 h-3 inline mr-2" />
            Get notified when Pro launches
          </label>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 px-4 py-3 bg-white border border-zinc-200 text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-black transition-colors"
              required
            />
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? '...' : 'Notify Me'}
            </button>
          </div>
          {error && (
            <p className="text-red-600 text-sm mt-2">{error}</p>
          )}
        </form>
      ) : (
        <div className="max-w-sm mx-auto mb-8 p-4 bg-emerald-50 border border-emerald-200">
          <div className="flex items-center justify-center gap-2 text-emerald-700">
            <Check className="w-5 h-5" />
            <span className="font-medium">You&apos;re on the list!</span>
          </div>
          <p className="text-zinc-500 text-sm mt-1">
            We&apos;ll email you when Pro subscriptions are available.
          </p>
        </div>
      )}

      {/* What's included preview */}
      <div className="bg-zinc-50 border border-zinc-200 p-6 mb-8 text-left max-w-md mx-auto">
        <h3 className="font-mono text-[10px] font-bold tracking-widest uppercase text-zinc-400 mb-4">
          What&apos;s coming with Pro
        </h3>
        <ul className="space-y-3">
          {[
            '40 analyses per month',
            'View all sources analysed per check',
            'Priority processing',
            'Advanced source analysis',
            'Export reports (PDF, CSV, JSON)',
            'Priority support',
          ].map((feature, i) => (
            <li key={i} className="flex items-center gap-3 text-zinc-600">
              <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              {feature}
            </li>
          ))}
        </ul>
      </div>

      {/* Navigation links */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Link
          href="/dashboard"
          onClick={() => {
            // Blur focus to prevent skip-link from appearing
            if (document.activeElement instanceof HTMLElement) {
              document.activeElement.blur();
            }
            onDismiss?.();
          }}
          className="px-6 py-3 border border-zinc-200 hover:bg-zinc-50 text-zinc-900 transition-colors flex items-center justify-center gap-2"
        >
          Back to Dashboard
          <ArrowRight className="w-4 h-4" />
        </Link>
        <Link
          href="/dashboard/new-check"
          onClick={() => {
            if (document.activeElement instanceof HTMLElement) {
              document.activeElement.blur();
            }
            onDismiss?.();
          }}
          className="px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors flex items-center justify-center gap-2"
        >
          Start a Free Check
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );

  // Modal variant
  if (variant === 'modal') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onDismiss}
        />

        {/* Modal */}
        <div className="relative z-10 bg-white border border-zinc-200 p-8 max-w-lg w-full max-h-[90vh] overflow-y-auto">
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
          {content}
        </div>
      </div>
    );
  }

  // Inline variant
  return (
    <div className="bg-white border border-zinc-200 p-8">
      {content}
    </div>
  );
}
