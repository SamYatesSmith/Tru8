'use client';

import { SignIn } from '@clerk/nextjs';
import { useState } from 'react';

/**
 * Minimal Authentication Test Page
 *
 * Purpose: Isolate Clerk sign-in component to diagnose errors
 *
 * Tests:
 * 1. Clerk component renders without custom styling
 * 2. No wrapper modals or complex state management
 * 3. Default Clerk appearance
 *
 * Access: http://localhost:3000/test-auth
 *
 * If this works → Issue is in AuthModal wrapper or styling
 * If this fails → Issue is in Clerk itself (version/config)
 */
export default function TestAuthPage() {
  const [variant, setVariant] = useState<'default' | 'styled' | 'hash'>('default');

  return (
    <div className="min-h-screen bg-[#0f1419] flex flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-white mb-2">
          Clerk Auth Diagnostic Page
        </h1>
        <p className="text-slate-400 mb-4">
          Test different Clerk configurations to isolate the error
        </p>

        {/* Variant Switcher */}
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => setVariant('default')}
            className={`px-4 py-2 rounded-md transition-colors ${
              variant === 'default'
                ? 'bg-[#f57a07] text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Default
          </button>

          <button
            onClick={() => setVariant('styled')}
            className={`px-4 py-2 rounded-md transition-colors ${
              variant === 'styled'
                ? 'bg-[#f57a07] text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Styled
          </button>

          <button
            onClick={() => setVariant('hash')}
            className={`px-4 py-2 rounded-md transition-colors ${
              variant === 'hash'
                ? 'bg-[#f57a07] text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Hash Routing
          </button>
        </div>
      </div>

      {/* Test Variants */}
      <div className="bg-[#1a1f2e] rounded-lg border border-slate-700 p-6">
        {variant === 'default' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-slate-400">
                Test 1: Default Clerk component (no customization)
              </p>
            </div>
            <SignIn fallbackRedirectUrl="/dashboard" />
          </>
        )}

        {variant === 'styled' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-slate-400">
                Test 2: Clerk component with custom appearance
              </p>
            </div>
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
              fallbackRedirectUrl="/dashboard"
            />
          </>
        )}

        {variant === 'hash' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-slate-400">
                Test 3: Clerk component with hash routing
              </p>
            </div>
            <SignIn
              routing="hash"
              fallbackRedirectUrl="/dashboard"
            />
          </>
        )}
      </div>

      <div className="mt-6 text-center max-w-lg">
        <p className="text-xs text-slate-500">
          Monitor browser console for errors. If error occurs, note which variant causes it.
        </p>
      </div>
    </div>
  );
}
