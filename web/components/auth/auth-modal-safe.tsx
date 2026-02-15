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

  useEffect(() => {
    setMounted(true);
  }, []);

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
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Modal Content */}
        <div className="relative bg-white border border-zinc-200 p-6 max-w-md w-full mx-4">
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-900 transition-colors z-10"
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
            className="flex gap-4 mb-6 border-b border-zinc-200"
            role="tablist"
            aria-label="Authentication options"
          >
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
                <div
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900"
                  aria-hidden="true"
                />
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
                <div
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-900"
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
                    formButtonPrimary: 'bg-zinc-900 hover:bg-zinc-800',
                    card: 'bg-transparent shadow-none',
                    rootBox: 'w-full',
                  },
                }}
                fallbackRedirectUrl="/dashboard"
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
                    formButtonPrimary: 'bg-zinc-900 hover:bg-zinc-800',
                    card: 'bg-transparent shadow-none',
                    rootBox: 'w-full',
                  },
                }}
                fallbackRedirectUrl="/dashboard"
              />
            </div>
          )}
        </div>
      </div>
    </AuthErrorBoundary>
  );
}
