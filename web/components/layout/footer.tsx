'use client';

import Link from 'next/link';
import Image from 'next/image';

export function Footer() {
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const productLinks = [
    { label: 'Features', sectionId: 'features' },
    { label: 'How It Works', sectionId: 'how-it-works' },
    { label: 'Pricing', sectionId: 'pricing' },
  ];

  const companyLinks = [
    { label: 'About', href: '/about' },
    { label: 'Blog', href: '/blog' },
    { label: 'Contact', href: '/contact' },
  ];

  const legalLinks = [
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Cookie Policy', href: '/cookies' },
  ];

  return (
    <footer className="relative bg-[#0f1419] border-t border-slate-800 mt-20 pb-20 md:pb-0">
      <div className="max-w-7xl mx-auto px-6 py-8 md:py-12">
        {/* Logo & Tagline - Full width on mobile, compact */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Image
              src="/logo.proper.png"
              alt="Tru8 logo"
              width={32}
              height={32}
              className="object-contain"
            />
            <span className="text-2xl font-black text-white">Tru8</span>
          </div>
          <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
            Transparent fact-checking with dated evidence. Verify claims instantly with AI-powered analysis.
          </p>
        </div>

        {/* Links Grid - 2 cols on mobile, 3 cols on desktop */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 mb-8">
          {/* Product Links */}
          <div>
            <h3 className="text-white font-semibold mb-3 text-sm">Product</h3>
            <ul className="space-y-2">
              {productLinks.map((link) => (
                <li key={link.sectionId}>
                  <button
                    onClick={() => scrollToSection(link.sectionId)}
                    className="text-slate-400 hover:text-[#f57a07] transition-colors text-sm"
                  >
                    {link.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h3 className="text-white font-semibold mb-3 text-sm">Company</h3>
            <ul className="space-y-2">
              {companyLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-slate-400 hover:text-[#f57a07] transition-colors text-sm"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h3 className="text-white font-semibold mb-3 text-sm">Legal</h3>
            <ul className="space-y-2">
              {legalLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-slate-400 hover:text-[#f57a07] transition-colors text-sm"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="pt-6 border-t border-slate-800">
          <p className="text-center text-slate-500 text-xs">
            © 2025 Tru8. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
