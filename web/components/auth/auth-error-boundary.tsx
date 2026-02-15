'use client';

import { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary for Auth Components
 *
 * Catches React errors in Clerk authentication components
 * and provides a fallback UI instead of crashing the app.
 *
 * Usage:
 *   <AuthErrorBoundary>
 *     <AuthModal />
 *   </AuthErrorBoundary>
 */
export class AuthErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Auth Error Boundary caught an error:', error);
    console.error('Error Info:', errorInfo);
    console.error('Component Stack:', errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          <div className="relative bg-white border border-zinc-200 p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold text-zinc-900 mb-4">
              Authentication Error
            </h2>

            <p className="text-zinc-500 mb-4">
              We encountered an issue loading the sign-in form. Please try again.
            </p>

            <div className="bg-zinc-50 border border-zinc-200 p-3 mb-4">
              <p className="text-xs text-zinc-400 font-mono">
                {this.state.error?.message || 'Unknown error'}
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => window.location.reload()}
                className="flex-1 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
              >
                Reload Page
              </button>

              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="flex-1 px-4 py-2 border border-zinc-200 hover:bg-zinc-50 text-zinc-500 text-xs font-bold uppercase tracking-[0.2em] transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
