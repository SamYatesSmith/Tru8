import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'About | Tru8',
  description: 'Learn about Tru8 - Making truth accessible, calm, and clear in a world that often feels anything but.',
};

export default function AboutPage() {
  return (
    <>
      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="min-h-screen bg-[#0f1419] pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          {/* Back Button */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>

          {/* About Tru8 Section */}
          <section className="mb-16 md:mb-20">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-black text-white mb-6 md:mb-8">
              About Tru8
            </h1>

            <div className="space-y-6 text-base md:text-lg text-slate-300 leading-relaxed">
              <p>
                Tru8 was created with a simple idea in mind: <span className="text-white font-medium">finding the truth online shouldn&apos;t feel overwhelming.</span>
              </p>

              <p>
                The internet moves fast. Headlines compete for attention, opinions spread instantly, and it&apos;s not always clear what&apos;s factual and what isn&apos;t. Most people don&apos;t have the time — or the desire — to dig through multiple articles just to understand whether a claim holds up.
              </p>

              <p>
                Tru8 takes all of that complexity and makes it easier. You paste a claim, and Tru8 checks the sources, compares the evidence, and gives you a clear, structured summary you can trust.
              </p>

              {/* Emphasis Block */}
              <div className="bg-slate-800/50 border-l-4 border-[#f57a07] rounded-r-lg px-6 py-5 my-8">
                <p className="text-white font-medium text-lg md:text-xl leading-relaxed">
                  No noise.<br />
                  No pressure.<br />
                  No agenda.<br />
                  <span className="text-[#f57a07]">Just clarity you can use.</span>
                </p>
              </div>

              <p>
                Tru8 is built for everyday people — not researchers, not experts, just anyone who wants a simpler way to understand the information in front of them. And as the platform grows to support images, videos, and audio, the mission stays the same:
              </p>

              <p className="text-white text-lg md:text-xl font-medium">
                Make truth accessible, calm, and clear — in a world that often feels anything but.
              </p>
            </div>
          </section>

          {/* Divider */}
          <div className="border-t border-slate-700 my-12 md:my-16" />

          {/* About the Founder Section */}
          <section>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-6 md:mb-8">
              About the Founder
            </h2>

            <div className="space-y-6 text-base md:text-lg text-slate-300 leading-relaxed">
              <p className="text-xl md:text-2xl text-white font-medium">
                Hi — I&apos;m Sam, the founder of Tru8.
              </p>

              <p>
                I&apos;ve never followed a straight line. Before building software, I spent years learning and working across a wide mix of fields — from film, video, and radio, to psychology, marketing, business, law, sales, and construction. Some of that education was formal, some of it was hands-on, and a lot of it came from simply being curious and wanting to understand how things work.
              </p>

              <p>
                For the longest part of my working life, I ran a construction business. It was practical, demanding, and very real — the kind of work where problems need solving quickly and clearly, and where there&apos;s no room for unnecessary complexity. That experience shaped how I think more than anything else: <span className="text-white font-medium">build things that work, explain things plainly, and don&apos;t overcomplicate what should be simple.</span>
              </p>

              <p>
                Over time, I became increasingly interested in technology — not as a buzzword, but as a tool. I retrained, learned to code, and started building systems that could take complex problems and make them easier for people to deal with.
              </p>

              <p>
                Tru8 grew out of that mindset. I kept noticing how difficult it had become to trust what we read online, and how exhausting it can be to try and work out what&apos;s actually true. Most people don&apos;t want to argue online or dig through endless sources — they just want clarity.
              </p>

              <p>
                So I built Tru8 myself, step by step. Not to prove a point, and not to chase trends — but to create something calm, useful, and grounded. A tool that helps people feel a little more confident in the information they&apos;re faced with.
              </p>

              <p>
                If Tru8 helps someone pause, understand, and make a better-informed decision — even just once — then it&apos;s doing what I hoped it would.
              </p>

              <p className="text-slate-400 mt-8">
                Thanks for taking the time to read this, and for being here.
              </p>

              {/* Signature */}
              <div className="mt-8 pt-6 border-t border-slate-800">
                <p className="text-white font-medium">— Sam Yates-Smith</p>
                <p className="text-slate-400 text-sm">Founder, Tru8</p>
              </div>
            </div>
          </section>

          {/* CTA Section */}
          <div className="mt-16 md:mt-20 text-center bg-slate-800/30 border border-slate-700 rounded-xl p-8 md:p-12">
            <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Ready to try Tru8?
            </h3>
            <p className="text-slate-400 mb-6 max-w-lg mx-auto">
              Start verifying claims with confidence. Your first 3 checks are free.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-xl font-bold transition-colors"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
