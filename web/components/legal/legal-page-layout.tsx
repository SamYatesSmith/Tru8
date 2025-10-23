'use client';

import { Navigation } from '@/components/layout/navigation';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  return (
    <>
      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="min-h-screen bg-[#0f1419] pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* Page Header */}
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-black text-white mb-4">
              {title}
            </h1>
            <p className="text-slate-400 text-sm">
              Last Updated: <span className="text-slate-300">{lastUpdated}</span>
            </p>
          </div>

          {/* Content Container */}
          <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-8 md:p-12">
            <div className="prose prose-invert prose-slate max-w-none">
              {children}
            </div>
          </div>

          {/* Contact Footer */}
          <div className="mt-12 text-center">
            <p className="text-slate-400 text-sm mb-4">
              Have questions about this policy?
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg font-medium transition-colors"
            >
              Contact Us
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
