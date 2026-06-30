'use client';

import { Navigation } from '@/components/layout/navigation';
import { Footer } from '@/components/layout/footer';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { SheetHeader } from '@/components/marketing/sheet-header';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface LegalPageLayoutProps {
  title: string;
  lastUpdated?: string;
  /** Document-grammar masthead category (mono, uppercased). Defaults to "Legal". */
  sheetLabel?: string;
  children: React.ReactNode;
}

export function LegalPageLayout({ title, lastUpdated, sheetLabel = 'Legal', children }: LegalPageLayoutProps) {
  const pathname = usePathname();
  return (
    <>
      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="min-h-screen bg-white pt-32 pb-20">
        {/* Document-grammar spine (xl+) */}
        <div
          aria-hidden="true"
          className="pointer-events-none fixed left-1.5 top-1/2 z-40 hidden -translate-y-1/2 rotate-180 select-none font-mono text-[9px] tracking-[0.3em] text-zinc-300 [writing-mode:vertical-rl] xl:block"
        >
          {`TRU8 · ${sheetLabel.toUpperCase()} · REV 2026.06`}
        </div>
        <div className="container mx-auto px-6 max-w-3xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-900 transition-colors mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Page Header */}
          <div className="mb-12">
            <SheetHeader number="01" label={sheetLabel} />
            <h1 className="text-3xl md:text-4xl font-normal text-zinc-900 mb-4">
              {title}
            </h1>
            {lastUpdated && (
              <p className="text-zinc-500 text-sm">
                Last Updated: <span className="text-zinc-600">{lastUpdated}</span>
              </p>
            )}
          </div>

          {/* Content Container */}
          <div className="prose-legal max-w-none">
            {children}
          </div>

          {/* Contact Footer — hidden on /contact itself to avoid a self-link */}
          {pathname !== '/contact' && (
            <div className="mt-12 text-center">
              <p className="text-zinc-500 text-sm mb-4">
                Have a question, or need something clarified?
              </p>
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
              >
                Contact Us
              </Link>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <Footer />
      <MobileBottomNav />
    </>
  );
}
