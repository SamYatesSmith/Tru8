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
  // 1. Check authentication - middleware will redirect if not authenticated
  const { userId, getToken } = auth();

  if (!userId) {
    // No user ID means not authenticated - redirect to sign-in
    redirect('/?signin=true');
  }

  // 2. Fetch authenticated user data
  const token = await getToken();
  const user = await apiClient.getCurrentUser(token) as User;

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
