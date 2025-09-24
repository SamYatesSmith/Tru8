/**
 * Accessible loading and error states
 * Phase 03: Accessibility Compliance
 *
 * FOUNDATION: Ready for use in app components requiring accessible loading/error states
 * Usage: Import and use for loading screens, error boundaries, dynamic content
 */

import { Button } from "@/components/ui/button";

export function AccessibleLoadingState() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading page content"
      className="loading-container flex items-center justify-center p-8"
    >
      <div className="loading-skeleton animate-pulse bg-gray-200 h-4 w-32 rounded" aria-hidden="true" />
      <span className="sr-only">Loading Tru8 homepage content...</span>
    </div>
  );
}

export function AccessibleErrorState({ error }: { error: string }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="error-container p-8 text-center bg-red-50 border border-red-200 rounded-lg"
    >
      <h2 className="error-title text-xl font-semibold text-red-800 mb-4">
        Page Loading Error
      </h2>
      <p className="error-message text-red-700 mb-6">{error}</p>
      <Button
        onClick={() => window.location.reload()}
        aria-label="Reload the page to try again"
        className="btn-primary"
      >
        Try Again
      </Button>
    </div>
  );
}