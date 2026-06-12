'use client';

import Link from 'next/link';
import { Tru8Mark } from '@/components/brand/tru8-mark';
import { openConsentBanner } from '@/lib/consent';

export function Footer() {
  const platformLinks = [
    { label: 'Features', href: '/#features' },
    { label: 'Pricing', href: '/#pricing' },
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Developers', href: '/developers' },
    { label: 'Compare', href: '/compare' },
  ];

  const companyLinks = [
    { label: 'About', href: '/about' },
    { label: 'Blog', href: '/blog' },
    { label: 'Contact', href: '/contact' },
  ];

  const legalLinks = [
    { label: 'Privacy Policy', href: '/privacy-policy' },
    { label: 'Terms of Service', href: '/terms-of-service' },
    { label: 'Cookie Policy', href: '/cookie-policy' },
    { label: 'Refund Policy', href: '/refund-policy' },
  ];

  return (
    <footer className="bg-zinc-50 pt-20 pb-12 border-t border-zinc-100">
      <div className="max-w-7xl mx-auto px-6">
        {/* Grid: Logo + 3 columns */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-20">
          {/* Logo + Tagline */}
          <div>
            <div className="flex items-center gap-3 mb-6">
              <Tru8Mark size={24} animated={false} className="opacity-80" />
              <span className="font-bold tracking-tighter uppercase">
                TRU<span className="text-zinc-400 font-normal">8</span>
              </span>
            </div>
            <p className="text-sm text-zinc-400 leading-relaxed max-w-xs">
              Research the evidence behind the news. We organise; you decide.
            </p>
          </div>

          {/* Platform */}
          <div>
            <h5 className="font-mono text-[10px] font-bold tracking-widest uppercase mb-6">Platform</h5>
            <ul className="space-y-3 text-sm text-zinc-500">
              {platformLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="hover:text-black transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h5 className="font-mono text-[10px] font-bold tracking-widest uppercase mb-6">Company</h5>
            <ul className="space-y-3 text-sm text-zinc-500">
              {companyLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="hover:text-black transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal + Connect */}
          <div>
            <h5 className="font-mono text-[10px] font-bold tracking-widest uppercase mb-6">Legal</h5>
            <ul className="space-y-3 text-sm text-zinc-500">
              {legalLinks.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="hover:text-black transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
              <li>
                <button
                  onClick={() => openConsentBanner()}
                  className="text-zinc-500 hover:text-black transition-colors"
                >
                  Cookie Preferences
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-zinc-200/50">
          <div className="font-mono text-[10px] text-zinc-400 tracking-widest uppercase mb-4 md:mb-0">
            &copy; 2026 TRU8 LTD. ALL RIGHTS RESERVED.
          </div>
          <div className="flex gap-8 font-mono text-[10px] text-zinc-400 tracking-widest uppercase">
            <Link href="/privacy-policy" className="hover:text-black transition-colors">Privacy Policy</Link>
            <Link href="/terms-of-service" className="hover:text-black transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
