'use client';

import { SignIn, SignUp } from '@clerk/nextjs';
import { useState } from 'react';
import { X } from 'lucide-react';

/**
 * Tru8-Styled Clerk Authentication Modal
 *
 * Single modal with Sign In / Sign Up tabs.
 *
 * Styling:
 * - Dark background (#1a1f2e)
 * - Orange accents (#f57a07)
 * - Matches Tru8 brand
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
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop - Dark opaque */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative bg-[#1a1f2e] rounded-lg border border-slate-700 p-6 max-w-md w-full mx-4 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('signin')}
            className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
              activeTab === 'signin'
                ? 'text-[#f57a07]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
            {activeTab === 'signin' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('signup')}
            className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
              activeTab === 'signup'
                ? 'text-[#f57a07]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign Up
            {activeTab === 'signup' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
            )}
          </button>
        </div>

        {/* Clerk Components with Custom Styling */}
        <div className="clerk-modal-content">
          {activeTab === 'signin' ? (
            <SignIn
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-[#f57a07] hover:bg-[#e06a00] text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-white',
                  headerSubtitle: 'text-slate-300',
                  socialButtonsBlockButton:
                    'border-slate-700 text-white hover:bg-slate-800',
                  formFieldInput:
                    'bg-[#0f1419] border-slate-700 text-white focus:border-[#f57a07]',
                  formFieldLabel: 'text-slate-300',
                  footerActionLink: 'text-[#f57a07] hover:text-[#e06a00]',
                },
              }}
              redirectUrl="/dashboard"
            />
          ) : (
            <SignUp
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-[#f57a07] hover:bg-[#e06a00] text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-white',
                  headerSubtitle: 'text-slate-300',
                  socialButtonsBlockButton:
                    'border-slate-700 text-white hover:bg-slate-800',
                  formFieldInput:
                    'bg-[#0f1419] border-slate-700 text-white focus:border-[#f57a07]',
                  formFieldLabel: 'text-slate-300',
                  footerActionLink: 'text-[#f57a07] hover:text-[#e06a00]',
                },
              }}
              redirectUrl="/dashboard"
            />
          )}
        </div>
      </div>
    </div>
  );
}
