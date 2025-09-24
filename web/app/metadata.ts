import type { Metadata } from "next";

/**
 * Enhanced SEO metadata for Tru8 homepage
 * Phase 01: Performance & SEO Foundation
 */
export const homeMetadata: Metadata = {
  title: "Tru8 - Instant Fact-Checking with Dated Evidence | Professional Verification",
  description: "Get explainable fact-check verdicts in under 10 seconds. Process URLs, images, videos, and text with transparent sourcing. Professional-grade verification for journalists and researchers.",
  keywords: [
    "fact checking",
    "fact checker",
    "verification",
    "misinformation",
    "disinformation",
    "truth",
    "evidence",
    "sources",
    "journalism tools",
    "research verification",
    "claim verification",
    "AI fact checking",
    "news verification",
    "media fact check",
    "content verification"
  ].join(", "),

  authors: [{ name: "Tru8" }],
  creator: "Tru8",
  publisher: "Tru8",

  // Open Graph
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://tru8.ai",
    siteName: "Tru8",
    title: "Tru8 - Professional Fact-Checking Platform",
    description: "Instant fact-checking with transparent sources and dated evidence. Built for journalists, researchers, and truth-seekers.",
    images: [
      {
        url: "/og-marketing-hero.jpg",
        width: 1200,
        height: 630,
        alt: "Tru8 Fact-Checking Platform - Instant Verification with Transparent Sources",
      }
    ],
  },

  // Twitter
  twitter: {
    card: "summary_large_image",
    site: "@tru8platform",
    creator: "@tru8platform",
    title: "Tru8 - Instant Fact-Checking with Dated Evidence",
    description: "Professional-grade verification in seconds with transparent sourcing. Process URLs, images, videos, and text.",
    images: ["/og-marketing-hero.jpg"],
  },

  // Additional SEO
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },

  alternates: {
    canonical: "https://tru8.ai",
  },

  category: 'technology',

  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
};