import Link from "next/link";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { MainLayout } from "@/components/layout/main-layout";
import { CheckCircle, Clock, Search, Shield, Zap, Globe } from "lucide-react";
// Phase 01: Performance & SEO Foundation - Enhanced metadata for homepage
import { homeMetadata } from "./metadata";
import { MarketingStructuredData, OrganizationStructuredData, FAQStructuredData } from "@/components/seo/structured-data";

// PHASE 01: Enhanced SEO metadata with Open Graph, Twitter Cards, and robots
export const metadata = homeMetadata;

export default function HomePage() {
  return (
    <>
      {/* PHASE 01: Schema.org structured data for enhanced search visibility */}
      <MarketingStructuredData />
      <OrganizationStructuredData />
      <FAQStructuredData />
      <MainLayout>
      {/* PHASE 03: Semantic main content wrapper */}
      <main id="main-content" role="main">
        {/* Hero Section */}
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
                  <Link href="#features">View Demo</Link>
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

        {/* Features Section */}
        <section
          className="py-24 bg-white"
          aria-labelledby="features-heading"
          id="features"
        >
          <div className="container">
            <div className="text-center mb-16">
              <h2 id="features-heading" className="text-4xl font-bold text-gray-900 mb-4">
                Professional Fact-Checking, Simplified
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                Built for journalists, researchers, and truth-seekers who need fast,
                accurate verification with transparent sourcing.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8" role="list">
              {/* Feature 1 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <Zap className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Lightning Fast
                </h3>
                <p className="text-gray-600">
                  Get comprehensive fact-check results in under 10 seconds with our
                  optimized AI pipeline.
                </p>
              </article>

              {/* Feature 2 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <Shield className="h-6 w-6 text-green-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Transparent Sources
                </h3>
                <p className="text-gray-600">
                  Every verdict includes credible sources with publication dates and
                  relevance scores for full transparency.
                </p>
              </article>

              {/* Feature 3 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <Search className="h-6 w-6 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Multi-Format Support
                </h3>
                <p className="text-gray-600">
                  Process URLs, images, videos, and text content. Extract claims
                  from any format seamlessly.
                </p>
              </article>

              {/* Feature 4 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <Clock className="h-6 w-6 text-amber-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Real-Time Updates
                </h3>
                <p className="text-gray-600">
                  Watch your fact-check progress in real-time with live pipeline
                  status updates.
                </p>
              </article>

              {/* Feature 5 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <CheckCircle className="h-6 w-6 text-red-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  AI-Powered Verdicts
                </h3>
                <p className="text-gray-600">
                  Advanced NLI models and LLM judges provide nuanced, explainable
                  claim assessments.
                </p>
              </article>

              {/* Feature 6 */}
              <article className="card text-center" role="listitem">
                <div
                  className="w-12 h-12 bg-cyan-100 rounded-lg flex items-center justify-center mx-auto mb-4"
                  aria-hidden="true"
                >
                  <Globe className="h-6 w-6 text-cyan-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Global Coverage
                </h3>
                <p className="text-gray-600">
                  Search across international news sources and databases for
                  comprehensive fact-checking coverage.
                </p>
              </article>
          </div>
        </div>
      </section>

        {/* CTA Section */}
        <SignedOut>
          <section
            className="py-16 bg-gray-100"
            aria-labelledby="cta-heading"
            id="get-started"
          >
            <div className="container text-center">
              <h2 id="cta-heading" className="text-3xl font-bold text-gray-900 mb-4">
                Ready to Start Fact-Checking?
              </h2>
              <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                Join professionals worldwide who trust Tru8 for accurate,
                fast fact-checking with transparent evidence.
              </p>
              <div
                className="flex flex-col sm:flex-row items-center justify-center gap-4"
                role="group"
                aria-label="Account signup options"
              >
                <SignInButton mode="modal">
                  <Button
                    size="lg"
                    className="btn-primary px-8 py-3"
                    aria-label="Get started with free account"
                  >
                    Get Started Free
                  </Button>
                </SignInButton>
                <Button
                  variant="outline"
                  size="lg"
                  className="px-8 py-3"
                  asChild
                >
                  <Link href="/pricing" aria-label="View pricing plans">
                    View Pricing
                  </Link>
                </Button>
              </div>
            </div>
          </section>
        </SignedOut>
      </main>
      </MainLayout>
    </>
  );
}