'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import { PageHeader } from '../components/page-header';
import { SettingsTabs } from './components/settings-tabs';
import { AccountTab } from './components/account-tab';
import { SubscriptionTab } from './components/subscription-tab';
import { NotificationsTab } from './components/notifications-tab';
import { DeveloperTab } from './components/developer-tab';
import { apiClient } from '@/lib/api';

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { user: clerkUser } = useUser();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('account');
  const [userData, setUserData] = useState<any>(null);
  const [subscriptionData, setSubscriptionData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Get active tab from query param
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab && ['account', 'subscription', 'notifications', 'developer'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Fetch user and subscription data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = await getToken();

        // Authentication is required - middleware will redirect if not authenticated
        if (!token) {
          console.error('No authentication token available');
          setLoading(false);
          return;
        }

        const [user, subscription] = await Promise.all([
          apiClient.getCurrentUser(token) as Promise<any>,
          apiClient.getSubscriptionStatus(token) as Promise<any>,
        ]);

        setUserData(user);
        setSubscriptionData(subscription);
      } catch (error) {
        console.error('Failed to fetch settings data:', error);
        // Set fallback data using Clerk info on API error
        setUserData({
          id: clerkUser?.id || 'unknown',
          email: clerkUser?.primaryEmailAddress?.emailAddress || '',
          name: clerkUser?.fullName || '',
          credits: 3,
        });
        setSubscriptionData({
          hasSubscription: false,
          plan: 'free_trial',
          creditsPerPeriod: 3,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [getToken, clerkUser]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    router.push(`/dashboard/settings?tab=${tab}`);
  };

  const handleUpdate = async () => {
    // Refresh data after subscription changes
    try {
      const token = await getToken();
      if (!token) return;

      const [user, subscription] = await Promise.all([
        apiClient.getCurrentUser(token) as Promise<any>,
        apiClient.getSubscriptionStatus(token) as Promise<any>,
      ]);

      setUserData(user);
      setSubscriptionData(subscription);
    } catch (error) {
      console.error('Failed to refresh settings data:', error);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Settings"
          subtitle="Manage your account and preferences"
        />
        <div className="text-center py-12">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-zinc-900 border-r-transparent"></div>
          <p className="text-zinc-400 mt-4">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        subtitle="Manage your account and preferences"
      />

      <SettingsTabs activeTab={activeTab} onTabChange={handleTabChange} />

      <div className="mt-8">
        {activeTab === 'account' && (
          <AccountTab clerkUser={clerkUser} userData={userData} subscriptionData={subscriptionData} />
        )}
        {activeTab === 'subscription' && (
          <SubscriptionTab
            userData={userData}
            subscriptionData={subscriptionData}
            onUpdate={handleUpdate}
          />
        )}
        {activeTab === 'notifications' && <NotificationsTab />}
        {activeTab === 'developer' && <DeveloperTab />}
      </div>
    </div>
  );
}
