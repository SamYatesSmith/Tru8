import { ClerkProvider } from '@clerk/nextjs'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import type { Metadata, Viewport } from 'next'
import { ServiceWorkerTombstone } from '@/components/layout/service-worker-tombstone'
import { AnalyticsProvider } from '@/components/analytics/posthog-provider'
import { AnalyticsIdentify } from '@/components/analytics/analytics-identify'
import { CookieConsent } from '@/components/legal/cookie-consent'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const viewport: Viewport = {
  themeColor: '#f27907',
}

export const metadata: Metadata = {
  title: {
    default: 'Tru8 — Evidence Verification Infrastructure',
    template: '%s | Tru8',
  },
  description: 'Evidence verification infrastructure for factual AI content. Tru8 decomposes content into checkable claims, retrieves external published sources, and returns a structured, tamper-evident evidence record. We organize; you decide.',
  icons: {
    icon: '/favicon.proper.png',
    apple: '/apple-touch-icon.png',
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'),
  openGraph: {
    type: 'website',
    siteName: 'Tru8',
    locale: 'en_US',
    description: 'Verify the evidence behind factual AI output before it ships. We organize; you decide.',
    images: [
      {
        url: '/api/og/default',
        width: 1200,
        height: 630,
        alt: 'Tru8 — Evidence Verification Infrastructure',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@tru8app',
    description: 'Verify the evidence behind factual AI output before it ships. We organize; you decide.',
  },
  robots: {
    index: true,
    follow: true,
  },
  manifest: '/manifest.webmanifest',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
    >
      <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
        <body className="bg-white text-zinc-900 antialiased font-sans" suppressHydrationWarning>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-3 focus:left-3 focus:bg-black focus:text-white focus:px-4 focus:py-2 focus:text-xs focus:font-bold focus:uppercase focus:tracking-widest"
          >
            Skip to content
          </a>
          <ServiceWorkerTombstone />
          <AnalyticsIdentify />
          <AnalyticsProvider>
            {children}
          </AnalyticsProvider>
          {/* First-party consent banner (replaced CookieYes). useEffect-mounted
              → renders null until after hydration, so it can't crash the app. */}
          <CookieConsent />
        </body>
      </html>
    </ClerkProvider>
  )
}
