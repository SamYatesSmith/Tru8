import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { Footer } from '@/components/layout/footer';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Tru8 — A First Public Release | Blog | Tru8',
  description: 'This is the first public release of Tru8. A tool that\'s ready to be used and tested outside of development.',
};

export default function FirstPublicReleasePage() {
  return (
    <>
      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main className="min-h-screen bg-[#0f1419] pt-24 md:pt-32 pb-24 md:pb-20">
        <div className="container mx-auto px-4 md:px-6 max-w-3xl">
          {/* Back Button */}
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors mb-6 md:mb-8"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Back to Blog</span>
          </Link>

          {/* Article Header */}
          <header className="mb-10 md:mb-12">
            <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
              <span className="flex items-center gap-1.5">
                <Calendar size={14} />
                6 January 2026
              </span>
              <span>·</span>
              <span className="flex items-center gap-1.5">
                <Clock size={14} />
                4 min read
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white leading-tight">
              Tru8 — A First Public Release
            </h1>
          </header>

          {/* Article Content */}
          <article className="space-y-6 text-slate-300 text-base md:text-lg leading-relaxed">
            <p className="text-xl md:text-2xl text-white font-medium">
              This is the first public release of Tru8.
            </p>

            <p>
              There&apos;s no big announcement behind it — just a tool that&apos;s ready to be used and tested outside of development. This post is here to explain what Tru8 is, why it exists, and what to expect from it at this stage.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">Why Tru8 Exists</h2>

            <p>
              The internet has never had more information, yet it often feels harder than ever to understand what&apos;s actually true.
            </p>

            <p>
              Headlines are written to grab attention. Claims spread quickly. Different sources say different things about the same topic, and working out what&apos;s well-supported can take more time than most people realistically have.
            </p>

            <p className="text-white font-medium">
              Tru8 exists to make that process simpler.
            </p>

            <p>
              It doesn&apos;t aim to replace research or tell people what to think. The goal is to take a claim and present the available evidence clearly, so people can understand what it&apos;s based on and decide for themselves.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">What Tru8 Does</h2>

            <p>
              Tru8 helps you check written claims.
            </p>

            <p>
              You paste in a statement, and Tru8 searches for relevant sources, compares what they say, and presents the findings in a clear, structured way. All sources used are shown, so you can explore them further if you want to.
            </p>

            <p>
              The focus is on clarity rather than commentary — showing what credible sources say, where they agree, and where they don&apos;t.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">What This First Release Is (and Isn&apos;t)</h2>

            <p>
              This is an early version of Tru8.
            </p>

            <p>
              It currently focuses on written content only. It won&apos;t always find a clear answer, and it won&apos;t be useful for every claim. That&apos;s expected at this stage.
            </p>

            <p>
              This release is about usefulness, not completeness. The aim is to learn how Tru8 performs in real-world use and where it needs to improve.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">How Tru8 Might Be Useful Right Now</h2>

            <p>
              Some common ways Tru8 can be useful include:
            </p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-slate-300">
              <li>Checking headlines that feel exaggerated</li>
              <li>Comparing conflicting news articles</li>
              <li>Verifying claims shared on social media</li>
              <li>Sense-checking statements that sound unusually certain</li>
              <li>Reviewing multiple sources around a single topic in one place</li>
            </ul>

            <p>
              If you&apos;re unsure about a claim, that&apos;s usually a good moment to try Tru8.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">Feedback That Helps Most</h2>

            <p>
              If you do use Tru8, honest feedback is genuinely helpful.
            </p>

            <p>In particular:</p>

            <ul className="list-disc list-outside ml-6 space-y-2 text-slate-300">
              <li>Are the results easy to understand?</li>
              <li>Do the sources feel relevant and trustworthy?</li>
              <li>Does the summary help clarify the claim?</li>
              <li>Where does Tru8 fall short or feel unclear?</li>
            </ul>

            <p>
              Knowing where Tru8 doesn&apos;t help is just as important as knowing where it does.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">What Comes Next</h2>

            <p>
              This release is a starting point.
            </p>

            <p>
              Tru8 will improve over time through clearer explanations, better sourcing, and support for more types of content. The direction it takes will be shaped by real usage and feedback.
            </p>

            <p>
              The aim is to keep Tru8 grounded, transparent, and genuinely useful.
            </p>

            <h2 className="text-2xl md:text-3xl font-bold text-white pt-6">A Final Note</h2>

            <p>
              Thanks for taking the time to try Tru8 or read about its first release.
            </p>

            <p>
              If it brings a little clarity to something you&apos;ve read online, then it&apos;s already moving in the right direction.
            </p>
          </article>

          {/* CTA Section */}
          <div className="mt-12 md:mt-16 text-center bg-slate-800/30 border border-slate-700 rounded-xl p-8 md:p-10">
            <h3 className="text-xl md:text-2xl font-bold text-white mb-3">
              Ready to try Tru8?
            </h3>
            <p className="text-slate-400 mb-6">
              Start verifying claims with your first 3 checks free.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-xl font-bold transition-colors"
            >
              Get Started Free
            </Link>
          </div>

          {/* Back to Blog */}
          <div className="mt-10 pt-8 border-t border-slate-800">
            <Link
              href="/blog"
              className="inline-flex items-center gap-2 text-slate-400 hover:text-[#f57a07] transition-colors"
            >
              <ArrowLeft size={18} />
              <span className="font-medium">Back to all posts</span>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}
