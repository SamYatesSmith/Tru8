import { ClerkProvider } from '@clerk/nextjs'
import { Inter, JetBrains_Mono } from 'next/font/google'
import Script from 'next/script'
import './globals.css'
import type { Metadata } from 'next'

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

export const metadata: Metadata = {
  title: 'Tru8 — AI-Powered Evidence Research',
  description: 'Professional evidence research platform. Analyse claims, URLs, and articles with AI-powered multi-source research.',
  icons: {
    icon: '/favicon.proper.png',
    apple: '/apple-touch-icon.png',
  },
  themeColor: '#f27907',
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'https://tru8.app'),
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
