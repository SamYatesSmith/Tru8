'use client';

import Link from "next/link";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { useTracking } from "@/hooks/useTracking";

/**
 * Hero Section with Analytics Tracking
 * Phase 04: Marketing Analytics Integration
 *
 * Client component that integrates CTA tracking with MVP analytics system.
 */
export function HeroSection() {
  // PHASE 04: Initialize analytics tracking
  const { trackCTA, trackSignupStart } = useTracking();

  return (
    <section className="hero-section" aria-labelledby="hero-heading">
      <div className="container">
        <h1 id="hero-heading" className="hero-title">
          Instant Fact-Checking with Dated Evidence
        </h1>
        <p className="hero-subtitle">
          Get explainable verdicts on claims from articles, images, videos, and text.
          Professional-grade verification in seconds.
        </p>

        <SignedOut>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4" role="group" aria-label="Get started options">
            <SignInButton mode="modal">
              <Button
                size="lg"
                className="btn-primary px-8 py-4 text-lg"
                aria-describedby="primary-cta-desc"
                onClick={() => {
                  // PHASE 04: Track primary CTA and signup start
                  trackCTA('hero', 'primary');
                  trackSignupStart();
                }}
              >
                Start Fact-Checking Now
              </Button>
            </SignInButton>
            <div id="primary-cta-desc" className="sr-only">
              Create a free account to begin fact-checking
            </div>
            <Button
              variant="outline"
              size="lg"
              className="px-8 py-4 text-lg border-white/30 text-white hover:bg-white/10"
              aria-describedby="demo-cta-desc"
              asChild
            >
              <Link
                href="#features"
                onClick={(e) => {
                  // PHASE 04: Track secondary CTA
                  trackCTA('hero', 'secondary');
                }}
              >
                View Demo
              </Link>
            </Button>
            <div id="demo-cta-desc" className="sr-only">
              See how Tru8 works with feature demonstration
            </div>
          </div>
        </SignedOut>

        <SignedIn>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4" role="group" aria-label="Dashboard options">
            <Button
              size="lg"
              className="btn-primary px-8 py-4 text-lg"
              asChild
            >
              <Link href="/dashboard" aria-label="Go to your dashboard">
                Go to Dashboard
              </Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="px-8 py-4 text-lg border-white/30 text-white hover:bg-white/10"
              asChild
            >
              <Link href="/checks/new" aria-label="Start a new fact-check">
                New Check
              </Link>
            </Button>
          </div>
        </SignedIn>
      </div>
    </section>
  );
}