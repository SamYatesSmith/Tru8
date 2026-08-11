import { auth } from '@clerk/nextjs/server';
import { apiClient } from '@/lib/api';
import { AttributionFlush } from '@/components/analytics/attribution-flush';
import { SignedInNav } from './components/signed-in-nav';
import { Footer } from '@/components/layout/footer';
import { FeedbackWidget } from './components/feedback-widget';

interface User {
  id: string;
  name: string | null;
  email: string;
  credits: number;
}

/**
 * Dashboard Layout
 *
 * UNIFIED AUTH FLOW:
 * - Middleware guarantees user is authenticated (no need to check here)
 * - We trust middleware - just fetch user data and render
 * - If you reach this component, you ARE authenticated
 */
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Middleware guarantees authentication - just get the token
  const { getToken } = await auth();
  const token = await getToken();

  // Fetch authenticated user data
  const user = await apiClient.getCurrentUser(token) as User;

  // Render layout
  return (
    <div className="min-h-screen bg-white">
      {/* Delivers a stored ?src= signup tag once, now that auth is certain */}
      <AttributionFlush />
      <SignedInNav user={user} />

      {/* Main content - adjusted padding for mobile nav (top: h-14, bottom: h-16) */}
      <main className="pt-20 md:pt-24 pb-20 md:pb-12">
        <div className="container mx-auto px-4 md:px-6 max-w-7xl">
          {children}
        </div>
      </main>

      <Footer />

      {/* Beta Testing Feedback Widget */}
      <FeedbackWidget />
    </div>
  );
}
