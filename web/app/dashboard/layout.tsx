import { auth } from '@clerk/nextjs/server';
import { apiClient } from '@/lib/api';
import { SignedInNav } from './components/signed-in-nav';
import { Footer } from '@/components/layout/footer';

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
  const { getToken } = auth();
  const token = await getToken();

  // Fetch authenticated user data
  const user = await apiClient.getCurrentUser(token) as User;

  // Render layout
  return (
    <div className="min-h-screen bg-[#0f1419]">
      <SignedInNav user={user} />

      <main className="pt-24 pb-12">
        <div className="container mx-auto px-6 max-w-7xl">
          {children}
        </div>
      </main>

      <Footer />
    </div>
  );
}
