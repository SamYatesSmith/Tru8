import { ClerkProvider } from '@clerk/nextjs'
import Script from 'next/script'
import './globals.css'
import type { Metadata } from 'next'
import { BetaBanner } from '@/components/layout/beta-banner'

export const metadata: Metadata = {
  title: 'Tru8 - AI-Powered Fact Verification',
  description: 'AI-powered fact verification with multi-source evidence. Professional fact-checking platform for journalists, researchers, and content creators.',
  icons: {
    icon: '/favicon.proper.png',
  },
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
      <html lang="en" suppressHydrationWarning>
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
        <body className="bg-[#0f1419] text-white antialiased" suppressHydrationWarning>
          <BetaBanner />
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
