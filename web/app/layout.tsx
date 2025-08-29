import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Tru8 - Instant Fact Checking",
  description: "Get instant, explainable fact checks with sources and dates",
  keywords: ["fact check", "verification", "truth", "misinformation"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#1E40AF",    // Tru8 primary blue
          colorBackground: "#FFFFFF", // Clean white background
          colorText: "#1F2937",       // Gray-800 for text
          borderRadius: "0.5rem",     // 8px border radius (design system)
        },
        elements: {
          card: "shadow-lg border border-gray-200",
          headerTitle: "text-gray-900 font-bold",
          headerSubtitle: "text-gray-600",
        }
      }}
    >
      <html lang="en" suppressHydrationWarning>
        <body className={inter.className}>
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            enableSystem={false}
            disableTransitionOnChange
          >
            <QueryProvider>
              {children}
              <Toaster />
            </QueryProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}