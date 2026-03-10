'use client';

import { useState } from 'react';
import { Sparkles, CreditCard, Code, User, LayoutDashboard } from 'lucide-react';
import { useAuth } from '@clerk/nextjs';
import { AuthModal } from '@/components/auth/auth-modal';
import Link from 'next/link';

/**
 * Mobile Bottom Navigation Component (Stitch light theme)
 *
 * Fixed at bottom of screen on mobile only (< 768px).
 * Page navigation links (not scroll-to-section).
 */
export function MobileBottomNav() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const { isSignedIn } = useAuth();

  const navItems = [
    { id: 'features', label: 'Features', icon: Sparkles, href: '/#features' },
    { id: 'pricing', label: 'Pricing', icon: CreditCard, href: '/#pricing' },
    { id: 'developers', label: 'Developers', icon: Code, href: '/developers' },
    isSignedIn
      ? { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' }
      : { id: 'sign-in', label: 'Sign In', icon: User, href: undefined },
  ];

  return (
    <>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-zinc-100" aria-label="Mobile navigation">
        <div className="grid grid-cols-4 h-16">
          {navItems.map((item) => {
            const Icon = item.icon;

            if (item.href) {
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className="flex flex-col items-center justify-center gap-1"
                  aria-label={item.label}
                >
                  <Icon className="w-5 h-5 text-zinc-400" aria-hidden="true" />
                  <span className="text-xs text-zinc-400">{item.label}</span>
                </Link>
              );
            }

            return (
              <button
                key={item.id}
                onClick={() => setIsAuthModalOpen(true)}
                className="flex flex-col items-center justify-center gap-1"
                aria-label={item.label}
              >
                <Icon className="w-5 h-5 text-zinc-400" aria-hidden="true" />
                <span className="text-xs text-zinc-400">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
