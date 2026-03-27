import { ClerkProvider } from '@clerk/nextjs'
import { Inter, JetBrains_Mono } from 'next/font/google'
import Script from 'next/script'
import './globals.css'
import type { Metadata, Viewport } from 'next'

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
        <head>
          {/* CookieYes Cookie Consent Banner */}
          {process.env.NEXT_PUBLIC_COOKIEYES_ID && (
            <Script
              id="cookieyes"
              src={`https://cdn-cookieyes.com/client_data/${process.env.NEXT_PUBLIC_COOKIEYES_ID}/script.js`}
              strategy="beforeInteractive"
            />
          )}
        </head>
        <body className="bg-white text-zinc-900 antialiased font-sans" suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
