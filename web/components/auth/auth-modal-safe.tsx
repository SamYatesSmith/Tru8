'use client';

import { SignIn, SignUp } from '@clerk/nextjs';
import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { AuthErrorBoundary } from './auth-error-boundary';

/**
 * Tru8-Styled Clerk Authentication Modal (Safe Version)
 *
 * IMPROVEMENTS OVER ORIGINAL:
 * - Wrapped in AuthErrorBoundary to catch Clerk errors
 * - Simplified appearance config to reduce serialization issues
 * - Uses path routing instead of hash routing (more stable)
 * - Added error recovery mechanisms
 *
 * This is a SAFER version that handles the event handler error gracefully.
 *
 * TO USE THIS VERSION:
 * 1. Rename current auth-modal.tsx → auth-modal-old.tsx
 * 2. Rename this file → auth-modal.tsx
 * 3. Test thoroughly
 */
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModalSafe({ isOpen, onClose }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const [mounted, setMounted] = useState(false);

  // Ensure client-side only rendering
  useEffect(() => {
    setMounted(true);
  }, []);

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen && mounted) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose, mounted]);

  if (!isOpen || !mounted) return null;

  return (
    <AuthErrorBoundary>
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Modal Content */}
        <div className="relative bg-[#1a1f2e] rounded-lg border border-slate-700 p-6 max-w-md w-full mx-4 shadow-2xl">
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors z-10"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Hidden title for screen readers */}
          <h2 id="auth-modal-title" className="sr-only">
            Authentication
          </h2>

          {/* Tabs */}
          <div
            className="flex gap-4 mb-6 border-b border-slate-700"
            role="tablist"
            aria-label="Authentication options"
          >
            <button
              onClick={() => setActiveTab('signin')}
              className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
                activeTab === 'signin'
                  ? 'text-[#f57a07]'
                  : 'text-slate-400 hover:text-white'
              }`}
              role="tab"
              aria-selected={activeTab === 'signin'}
              aria-controls="signin-panel"
            >
              Sign In
              {activeTab === 'signin' && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]"
                  aria-hidden="true"
                />
              )}
            </button>

            <button
              onClick={() => setActiveTab('signup')}
              className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
                activeTab === 'signup'
                  ? 'text-[#f57a07]'
                  : 'text-slate-400 hover:text-white'
              }`}
              role="tab"
              aria-selected={activeTab === 'signup'}
              aria-controls="signup-panel"
            >
              Sign Up
              {activeTab === 'signup' && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]"
                  aria-hidden="true"
                />
              )}
            </button>
          </div>

          {/* Clerk Components - Simplified Appearance */}
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
                    // SIMPLIFIED: Only essential styling to reduce risk
                    formButtonPrimary: 'bg-[#f57a07] hover:bg-[#e06a00]',
                    card: 'bg-transparent shadow-none',
                    rootBox: 'w-full',
                  },
                }}
                afterSignInUrl="/dashboard"
                // Removed hash routing - using default path routing
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
                    // SIMPLIFIED: Only essential styling to reduce risk
                    formButtonPrimary: 'bg-[#f57a07] hover:bg-[#e06a00]',
                    card: 'bg-transparent shadow-none',
                    rootBox: 'w-full',
                  },
                }}
                afterSignUpUrl="/dashboard"
                // Removed hash routing - using default path routing
              />
            </div>
          )}
        </div>
      </div>
    </AuthErrorBoundary>
  );
}
