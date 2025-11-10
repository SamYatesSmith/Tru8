import { ClerkProvider } from '@clerk/nextjs'
import Script from 'next/script'
import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tru8 - Transparent Fact-Checking with Dated Evidence',
  description: 'Professional fact-checking platform providing instant verification with dated evidence for journalists, researchers, and content creators.',
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
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
