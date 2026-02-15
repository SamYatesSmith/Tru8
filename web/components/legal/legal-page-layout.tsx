'use client';

import { Navigation } from '@/components/layout/navigation';
import { Footer } from '@/components/layout/footer';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface LegalPageLayoutProps {
  title: string;
  lastUpdated?: string;
  children: React.ReactNode;
}

export function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  return (
    <>
      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="min-h-screen bg-white pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-3xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-zinc-900 transition-colors mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Page Header */}
          <div className="mb-12">
            <h1 className="text-3xl md:text-4xl font-bold text-zinc-900 mb-4">
              {title}
            </h1>
            {lastUpdated && (
              <p className="text-zinc-500 text-sm">
                Last Updated: <span className="text-zinc-600">{lastUpdated}</span>
              </p>
            )}
          </div>

          {/* Content Container */}
          <div className="bg-white border border-zinc-200 rounded-lg p-8 md:p-12">
            <div className="prose-legal max-w-none">
              {children}
            </div>
          </div>

          {/* Contact Footer */}
          <div className="mt-12 text-center">
            <p className="text-zinc-500 text-sm mb-4">
              Have questions about this policy?
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
            >
              Contact Us
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
      <MobileBottomNav />
    </>
  );
}
