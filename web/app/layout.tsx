import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import { PerformanceProvider } from "@/components/providers/performance-provider";
import { Toaster } from "@/components/ui/toaster";
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';
import CookieConsent from 'react-cookie-consent';
import Link from 'next/link';
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

// LEGACY: Basic fallback metadata for non-homepage pages
// NOTE: Homepage uses enhanced Phase 01 metadata from ./metadata.ts
export const metadata: Metadata = {
  title: {
    default: "Tru8 - Professional Fact-Checking Platform",
    template: "%s | Tru8"
  },
  description: "Get instant, explainable fact checks with sources and dates",
  keywords: ["fact check", "verification", "truth", "misinformation"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className={inter.className}>
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            enableSystem={false}
            disableTransitionOnChange
          >
            <QueryProvider>
              <SessionProvider>
                {/* PHASE 01: Performance monitoring and analytics */}
                <PerformanceProvider>
                  {children}
                  <Toaster />
                  {/* PHASE 01: Vercel Analytics & Speed Insights */}
                  <Analytics />
                  <SpeedInsights />
                </PerformanceProvider>
              </SessionProvider>
            </QueryProvider>

            {/* PHASE 04: Cookie Consent Banner */}
            <CookieConsent
              location="bottom"
              buttonText="Accept"
              declineButtonText="Decline"
              enableDeclineButton
              cookieName="tru8-analytics-consent"
              style={{ background: "#2B373B" }}
              buttonStyle={{ color: "#4e503b", fontSize: "13px" }}
              declineButtonStyle={{ color: "#9CA3AF", fontSize: "13px" }}
              onAccept={() => {
                // Initialize analytics only after consent
                import('@/lib/analytics').then(({ analytics }) => {
                  analytics.initialize();
                });
              }}
              onDecline={() => {
                console.log('[Analytics] User declined cookie consent');
                // Analytics will remain uninitialized
              }}
            >
              We use cookies to improve your experience and analyze site usage.{" "}
              <span style={{ fontSize: "10px", color: "#9CA3AF" }}>
                Contact us for privacy questions
              </span>
            </CookieConsent>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}