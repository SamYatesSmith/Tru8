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
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-zinc-900 mb-2">
          Clerk Auth Diagnostic Page
        </h1>
        <p className="text-zinc-500 mb-4">
          Test different Clerk configurations to isolate the error
        </p>

        {/* Variant Switcher */}
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => setVariant('default')}
            className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] transition-colors ${
              variant === 'default'
                ? 'bg-zinc-900 text-white'
                : 'border border-zinc-200 text-zinc-500 hover:bg-zinc-50'
            }`}
          >
            Default
          </button>

          <button
            onClick={() => setVariant('styled')}
            className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] transition-colors ${
              variant === 'styled'
                ? 'bg-zinc-900 text-white'
                : 'border border-zinc-200 text-zinc-500 hover:bg-zinc-50'
            }`}
          >
            Styled
          </button>

          <button
            onClick={() => setVariant('hash')}
            className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] transition-colors ${
              variant === 'hash'
                ? 'bg-zinc-900 text-white'
                : 'border border-zinc-200 text-zinc-500 hover:bg-zinc-50'
            }`}
          >
            Hash Routing
          </button>
        </div>
      </div>

      {/* Test Variants */}
      <div className="bg-white border border-zinc-200 p-6">
        {variant === 'default' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-zinc-500">
                Test 1: Default Clerk component (no customization)
              </p>
            </div>
            <SignIn fallbackRedirectUrl="/dashboard" />
          </>
        )}

        {variant === 'styled' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-zinc-500">
                Test 2: Clerk component with custom appearance
              </p>
            </div>
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
              fallbackRedirectUrl="/dashboard"
            />
          </>
        )}

        {variant === 'hash' && (
          <>
            <div className="mb-4 text-center">
              <p className="text-sm text-zinc-500">
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
        <p className="text-xs text-zinc-400">
          Monitor browser console for errors. If error occurs, note which variant causes it.
        </p>
      </div>
    </div>
  );
}
