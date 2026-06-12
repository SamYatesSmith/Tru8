import { ClerkProvider } from '@clerk/nextjs'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import type { Metadata, Viewport } from 'next'
import { ServiceWorkerTombstone } from '@/components/layout/service-worker-tombstone'
import { AnalyticsProvider } from '@/components/analytics/posthog-provider'

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
    default: 'Tru8 — AI-Powered News Evidence Research',
    template: '%s | Tru8',
  },
  description: 'AI-powered news evidence research. Paste a news article or claim, and Tru8 searches multiple source types to organise the evidence landscape. No verdicts — just clarity.',
  icons: {
    icon: '/favicon.proper.png',
    apple: '/apple-touch-icon.png',
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'https://www.trueight.com'),
  openGraph: {
    type: 'website',
    siteName: 'Tru8',
    locale: 'en_GB',
    images: [{ url: '/api/og/default', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@tru8app',
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
        {/* CookieYes consent banner — TEMPORARILY DISABLED 2026-06-12.
            The cdn-cookieyes.com script crashes hydration site-wide (React
            #418/#423/#425): its auto-blocking rewrites/disables scripts —
            including Next.js's own hydration chunks — once it loads, which
            breaks React under both beforeInteractive and afterInteractive.
            Re-enable only after configuring CookieYes auto-blocking to skip
            first-party scripts (dashboard) and verifying against a LOCAL
            production build (`npm run build && npm run start`) first.
            The NEXT_PUBLIC_COOKIEYES_ID Railway var is now inert. */}
        <body className="bg-white text-zinc-900 antialiased font-sans" suppressHydrationWarning>
          <ServiceWorkerTombstone />
          <AnalyticsProvider>
            {children}
          </AnalyticsProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
