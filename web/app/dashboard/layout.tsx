import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { SignedInNav } from './components/signed-in-nav';
import { Footer } from '@/components/layout/footer';

interface User {
  id: string;
  name: string | null;
  email: string;
  credits: number;
}

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // 1. Check authentication
  const { userId, getToken } = auth();

  // TEMPORARY: Mock user data for testing when not authenticated
  let user: User;

  if (!userId) {
    // Mock user for testing
    user = {
      id: 'test-user-123',
      name: 'Test User',
      email: 'test@example.com',
      credits: 3,
    };
  } else {
    // 2. Fetch real user data
    const token = await getToken();
    user = await apiClient.getCurrentUser(token) as User;
  }

  // 3. Render layout
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
