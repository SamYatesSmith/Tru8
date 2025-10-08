import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tru8 - Transparent Fact-Checking with Dated Evidence',
  description: 'Professional fact-checking platform providing instant verification with dated evidence for journalists, researchers, and content creators.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-[#0f1419] text-white antialiased">{children}</body>
      </html>
    </ClerkProvider>
  )
}
