'use client';

import { SignIn, SignUp } from '@clerk/nextjs';
import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * Tru8-Styled Clerk Authentication Modal
 *
 * Single modal with Sign In / Sign Up tabs.
 *
 * Styling:
 * - Light background (white surfaces, zinc borders)
 * - Accent color via CSS var (--accent)
 * - Matches Stitch design system
 *
 * Behavior:
 * - Opens when Sign In or Get Started clicked
 * - Tabs allow switching between Sign In ↔ Sign Up
 * - After auth: Redirects to /dashboard (configured in .env)
 * - Backend: User auto-created via GET /api/v1/users/me on first login
 *
 * Backend Integration:
 * - Clerk provides JWT token
 * - Frontend uses token to call /api/v1/users/me
 * - Backend auto-creates user with 3 credits (backend/app/api/v1/users.py:22-31)
 */
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  redirectUrl?: string;
}

export function AuthModal({ isOpen, onClose, redirectUrl }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const afterAuthUrl = redirectUrl || '/dashboard';

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Content */}
      <div className="relative bg-white border border-zinc-200 p-6 max-w-md w-full mx-4">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Hidden title for screen readers */}
        <h2 id="auth-modal-title" className="sr-only">
          Authentication
        </h2>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-zinc-200" role="tablist" aria-label="Authentication options">
          <button
            onClick={() => setActiveTab('signin')}
            className={`pb-2 px-1 font-mono text-[10px] font-bold uppercase tracking-[0.2em] transition-colors relative ${
              activeTab === 'signin'
                ? 'text-zinc-900'
                : 'text-zinc-400 hover:text-zinc-900'
            }`}
            role="tab"
            aria-selected={activeTab === 'signin'}
            aria-controls="signin-panel"
          >
            Sign In
            {activeTab === 'signin' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900" aria-hidden="true" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('signup')}
            className={`pb-2 px-1 font-mono text-[10px] font-bold uppercase tracking-[0.2em] transition-colors relative ${
              activeTab === 'signup'
                ? 'text-zinc-900'
                : 'text-zinc-400 hover:text-zinc-900'
            }`}
            role="tab"
            aria-selected={activeTab === 'signup'}
            aria-controls="signup-panel"
          >
            Sign Up
            {activeTab === 'signup' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900" aria-hidden="true" />
            )}
          </button>
        </div>

        {/* Clerk Components with Custom Styling */}
        {activeTab === 'signin' ? (
          <div
            id="signin-panel"
            role="tabpanel"
            aria-labelledby="signin-tab"
            className="clerk-modal-content"
          >
            <SignIn
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-zinc-900 hover:bg-zinc-800 text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-zinc-900',
                  headerSubtitle: 'text-zinc-500',
                  socialButtonsBlockButton:
                    'border-zinc-200 text-zinc-900 hover:bg-zinc-50',
                  formFieldInput:
                    'bg-white border-zinc-200 text-zinc-900 focus:border-black',
                  formFieldLabel: 'text-zinc-500',
                  footerActionLink: 'text-accent hover:text-accent/80',
                },
              }}
              routing="hash"
              forceRedirectUrl={afterAuthUrl}
            />
          </div>
        ) : (
          <div
            id="signup-panel"
            role="tabpanel"
            aria-labelledby="signup-tab"
            className="clerk-modal-content"
          >
            <SignUp
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-zinc-900 hover:bg-zinc-800 text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-zinc-900',
                  headerSubtitle: 'text-zinc-500',
                  socialButtonsBlockButton:
                    'border-zinc-200 text-zinc-900 hover:bg-zinc-50',
                  formFieldInput:
                    'bg-white border-zinc-200 text-zinc-900 focus:border-black',
                  formFieldLabel: 'text-zinc-500',
                  footerActionLink: 'text-accent hover:text-accent/80',
                },
              }}
              routing="hash"
              forceRedirectUrl={afterAuthUrl}
            />
          </div>
        )}
      </div>
    </div>
  );
}
