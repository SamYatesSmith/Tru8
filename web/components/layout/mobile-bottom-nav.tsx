'use client';

import { useState, useEffect } from 'react';
import { Sparkles, Info, CreditCard, User } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Mobile Bottom Navigation Component
 *
 * Fixed at bottom of screen on mobile only (< 768px).
 *
 * Navigation Items:
 * - Features (Sparkles icon) → Scrolls to #features
 * - How It Works (Info icon) → Scrolls to #how-it-works
 * - Pricing (CreditCard icon) → Scrolls to #pricing
 * - Sign In (User icon) → Opens Clerk auth modal
 *
 * Active State:
 * - Orange icon color (#f57a07)
 * - Orange top border
 * - Updates via Intersection Observer on scroll
 *
 * Design:
 * - Background: #1a1f2e
 * - Border top: slate-700
 * - Icon size: 20px
 * - Text size: 12px
 * - Evenly distributed spacing
 */
export function MobileBottomNav() {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Intersection Observer to detect active section
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.5 } // Section is active when 50% visible
    );

    const sections = ['features', 'how-it-works', 'pricing'];
    sections.forEach((id) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, []);

  const navItems = [
    {
      id: 'features',
      label: 'Features',
      icon: Sparkles,
      onClick: () => scrollToSection('features'),
    },
    {
      id: 'how-it-works',
      label: 'How It Works',
      icon: Info,
      onClick: () => scrollToSection('how-it-works'),
    },
    {
      id: 'pricing',
      label: 'Pricing',
      icon: CreditCard,
      onClick: () => scrollToSection('pricing'),
    },
    {
      id: 'sign-in',
      label: 'Sign In',
      icon: User,
      onClick: () => setIsAuthModalOpen(true),
    },
  ];

  return (
    <>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#1a1f2e] border-t border-slate-700">
        <div className="grid grid-cols-4 h-16">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                onClick={item.onClick}
                className="flex flex-col items-center justify-center gap-1 relative"
                aria-label={item.label}
              >
                {/* Active indicator (orange top border) */}
                {isActive && (
                  <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
                )}

                {/* Icon */}
                <Icon
                  className={`w-5 h-5 ${
                    isActive ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                />

                {/* Label */}
                <span
                  className={`text-xs ${
                    isActive ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                >
                  {item.label}
                </span>
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
