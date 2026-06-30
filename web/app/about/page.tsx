import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { SheetHeader } from '@/components/marketing/sheet-header';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'About',
  description: 'Tru8 lays out the evidence for and against a claim \u2014 every source classified by tier and type, every exclusion receipted, no verdict. For researchers, journalists and analysts who need to show their working. We organise; you decide.',
  alternates: { canonical: '/about' },
};

export default function AboutPage() {
  return (
    <>
      <Navigation />
      <MobileBottomNav />

      <main className="min-h-screen pt-24 md:pt-32 pb-24 md:pb-20">
        {/* Document-grammar spine (xl+) */}
        <div
          aria-hidden="true"
          className="pointer-events-none fixed left-1.5 top-1/2 z-40 hidden -translate-y-1/2 rotate-180 select-none font-mono text-[9px] tracking-[0.3em] text-zinc-300 [writing-mode:vertical-rl] xl:block"
        >
          TRU8 · ABOUT · REV 2026.06
        </div>
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-900 transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* About Tru8 Section */}
          <section className="mb-16 md:mb-20">
            <SheetHeader number="01" label="Company Overview" />
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-normal text-zinc-900 mb-6 md:mb-8">
              About Tru8
            </h1>

            <div className="space-y-6 text-base md:text-lg text-zinc-600 leading-relaxed">
              <p>
                Tru8 was created with a simple idea in mind: <span className="text-zinc-900 font-medium">understanding the evidence behind a news story shouldn&apos;t feel overwhelming.</span>
              </p>

              <p>
                News moves fast. Headlines compete for attention, reporting gets recycled, and it&apos;s not always clear what&apos;s well-supported and what isn&apos;t. Most people don&apos;t have the time — or the tools — to dig through dozens of sources just to understand whether what they&apos;re reading holds up.
              </p>

              <p>
                Tru8 takes that complexity and makes it manageable. You paste a news article, headline, or claim, and Tru8 searches across 30+ public sources, classifies each by tier and type, maps what supports and challenges each claim, names what is missing, and gives you a structured evidence record you can explore — and defend.
              </p>

              {/* Emphasis Block */}
              <div className="bg-zinc-50 border-l-2 border-accent px-6 py-5 my-8">
                <p className="text-zinc-900 font-medium text-lg md:text-xl leading-relaxed">
                  Every source shown.<br />
                  Every exclusion receipted.<br />
                  No verdict.<br />
                  <span className="font-semibold text-zinc-900">You decide.</span>
                </p>
              </div>

              <p>
                Tru8 is built for people who have to show their working — journalists, analysts, policy researchers and independent writers who need to see the evidence for and against a claim, and stand behind their sources. (And anyone who simply wants to understand what&apos;s behind the news.) The mission stays the same:
              </p>

              <p className="text-zinc-900 text-lg md:text-xl font-medium">
                Make the evidence accessible and defensible. We organise; you decide.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-zinc-200 my-12 md:my-16" />

          {/* About the Founder Section */}
          <section>
            <SheetHeader number="02" label="Founder" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal text-zinc-900 mb-6 md:mb-8">
              About the Founder
            </h2>

            <div className="space-y-6 text-base md:text-lg text-zinc-600 leading-relaxed">
              <p className="text-xl md:text-2xl text-zinc-900 font-medium">
                Hi — I&apos;m Sam, the founder of Tru8.
              </p>

              <p>
                I&apos;ve never followed a straight line. Before building software, I spent years learning and working across a wide mix of fields — from film, video, and radio, to psychology, marketing, business, law, sales, and construction. Some of that education was formal, some of it was hands-on, and a lot of it came from simply being curious and wanting to understand how things work.
              </p>

              <p>
                For the longest part of my working life, I ran a construction business. It was practical, demanding, and very real — the kind of work where problems need solving quickly and clearly, and where there&apos;s no room for unnecessary complexity. That experience shaped how I think more than anything else: <span className="text-zinc-900 font-medium">build things that work, explain things plainly, and don&apos;t overcomplicate what should be simple.</span>
              </p>

              <p>
                Over time, I became increasingly interested in technology — not as a buzzword, but as a tool. I retrained, learned to code, and started building systems that could take complex problems and make them easier for people to deal with.
              </p>

              <p>
                Tru8 grew out of that mindset. I kept noticing how difficult it had become to navigate conflicting news coverage, and how exhausting it can be to try and work out what&apos;s actually well-supported. Most people don&apos;t want to argue online or dig through endless sources — they just want clarity.
              </p>

              <p>
                So I built Tru8 myself, step by step. Not to prove a point, and not to chase trends — but to create something calm, useful, and grounded. A tool that helps people feel a little more confident in the information they&apos;re faced with.
              </p>

              <p>
                If Tru8 helps someone pause, understand, and make a better-informed decision — even just once — then it&apos;s doing what I hoped it would.
              </p>

              <p className="text-zinc-500 mt-8">
                Thanks for taking the time to read this, and for being here.
              </p>

              {/* Signature */}
              <div className="mt-8 pt-6 border-t border-zinc-200">
                <p className="text-zinc-900 font-medium">— Sam Yates-Smith</p>
                <p className="text-zinc-500 text-sm">Founder, Tru8</p>
              </div>
            </div>
          </section>

          {/* CTA Section */}
          <div className="mt-16 md:mt-20 text-center border border-zinc-200 p-8 md:p-12">
            <h3 className="text-2xl md:text-3xl font-normal text-zinc-900 mb-4">
              See the evidence for yourself
            </h3>
            <p className="text-zinc-500 mb-6 max-w-lg mx-auto">
              Your first checks are free — no card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] transition-colors"
              >
                Start in the browser
              </Link>
              <Link
                href="/research"
                className="inline-flex items-center gap-2 px-8 py-4 border border-zinc-300 text-zinc-900 hover:border-zinc-900 text-xs font-bold uppercase tracking-[0.2em] transition-colors"
              >
                How it works
              </Link>
            </div>
          </div>

          {/* Mono metadata footer */}
          <div className="mt-12 pt-6 border-t border-zinc-100">
            <span className="font-mono text-[10px] tracking-widest uppercase text-zinc-500">
              TRU8 · ABOUT · REV 2026.06
            </span>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
