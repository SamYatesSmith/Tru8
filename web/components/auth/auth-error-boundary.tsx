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
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    // Log error details for debugging
    console.error('Auth Error Boundary caught an error:', error);
    console.error('Error Info:', errorInfo);
    console.error('Component Stack:', errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

          <div className="relative bg-[#1a1f2e] rounded-lg border border-slate-700 p-6 max-w-md w-full mx-4 shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-4">
              Authentication Error
            </h2>

            <p className="text-slate-300 mb-4">
              We encountered an issue loading the sign-in form. Please try again.
            </p>

            <div className="bg-slate-900/50 border border-slate-700 rounded p-3 mb-4">
              <p className="text-xs text-slate-400 font-mono">
                {this.state.error?.message || 'Unknown error'}
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => window.location.reload()}
                className="flex-1 px-4 py-2 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-md transition-colors"
              >
                Reload Page
              </button>

              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-md transition-colors"
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
