# 📄 PLAN #6: SETTINGS PAGE

**File:** `web/app/dashboard/settings/page.tsx`
**Type:** Client Component (tab navigation and forms)
**Status:** NOT STARTED

---

## **PURPOSE**

Comprehensive settings page with 3 tabs:
1. **Account** - Profile management (Clerk integration)
2. **Subscription** - Plan management, usage, billing (Stripe integration)
3. **Notifications** - Email preferences (frontend-only for MVP per GAP #7)

All tabs share horizontal tab navigation, with query param routing (`?tab=account`).

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Page Header**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Tree Graphic]                                             │
│  Settings                                                   │
│  Manage your account and preferences                        │
└─────────────────────────────────────────────────────────────┘
```

**Elements:**
- Background graphic: Tree icon (`/imagery/tree.png`)
- Headline: "Settings" (text-4xl, font-black)
- Subheading: "Manage your account and preferences" (text-slate-400)
- Reuse: `<PageHeader />` component from PLAN_02

### **Tab Navigation** (screenshot: Settings.account.png)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [ACCOUNT] [Subscription] [Notifications]                   │
└─────────────────────────────────────────────────────────────┘
```

**Styling:**
- Horizontal tabs below page header
- Active tab: `text-[#f57a07] border-b-2 border-[#f57a07]`
- Inactive tab: `text-slate-400 hover:text-white`
- Font: Bold, uppercase
- Spacing: `gap-8`
- Bottom border: 2px solid for active, transparent for inactive

---

## **TAB 1: ACCOUNT** (Settings.account.png)

### **Profile Section**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Profile Information                                        │
│                                                             │
│  [Avatar Circle with initials]                             │
│                                                             │
│  Name                                                       │
│  [John Doe                                              ]   │
│                                                             │
│  Email                                                      │
│  [john.doe@example.com                                  ]   │
│  (Read-only, managed by authentication provider)           │
│                                                             │
│  [Update Profile]                                          │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Large avatar circle (80x80px) with user initials or Clerk profile image
- Name input (editable via Clerk API)
- Email display (read-only, grey background)
- Helper text explaining email is managed by auth provider
- Update button (primary gradient style)

### **Security Section**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Security                                                   │
│                                                             │
│  Password                                                   │
│  ••••••••                                                   │
│  [Change Password]                                         │
│                                                             │
│  Two-Factor Authentication                                 │
│  Status: Enabled / Disabled                                │
│  [Configure 2FA]                                           │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Password display (masked, read-only)
- Change Password button → Opens Clerk modal
- 2FA status badge (green if enabled, grey if disabled)
- Configure 2FA button → Opens Clerk modal

**Implementation:**
- All security actions delegate to Clerk's built-in UI components
- Use `useClerk()` hook to trigger Clerk modals

### **Danger Zone**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Danger Zone                                                │
│                                                             │
│  Delete Account                                            │
│  Once you delete your account, there is no going back.    │
│  Please be certain.                                        │
│                                                             │
│  [Delete Account]                                          │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Red border and background tint
- Warning text
- Delete Account button (red background, red text on hover)
- Confirmation modal before deletion

---

## **TAB 2: SUBSCRIPTION** (Settings.subscriptions.png)

### **Current Plan Card**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Your Current Plan                                          │
│                                                             │
│  Free                                                       │
│  3 free checks                                             │
│                                                             │
│  Usage this month: 0 / 3 checks                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0%      │
│                                                             │
│  [Upgrade to Professional]                                 │
└─────────────────────────────────────────────────────────────┘
```

**For Free Users:**
- Plan name: "Free"
- Credits: "3 free checks" (per GAP #1 resolution)
- Monthly usage bar (as per GAP #4 resolution)
- Upgrade button (primary gradient)

**For Professional Users:**
```
┌─────────────────────────────────────────────────────────────┐
│  Your Current Plan                                          │
│                                                             │
│  Professional                                              │
│  £7 per month · Unlimited checks                          │
│                                                             │
│  Next billing date: March 15, 2024                        │
│  Usage this month: 24 checks                              │
│                                                             │
│  [Manage Subscription]                                     │
└─────────────────────────────────────────────────────────────┘
```

**For Professional Users:**
- Plan name: "Professional"
- Price: "£7 per month" (per GAP #2 resolution)
- Features: "Unlimited checks"
- Next billing date (from Stripe subscription)
- Monthly usage count (no limit bar)
- Manage Subscription button → Opens Stripe billing portal

### **Available Plans** (Pricing Cards)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Available Plans                                            │
│                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐ │
│  │  Free                   │  │  Professional           │ │
│  │                         │  │                         │ │
│  │  £0                     │  │  £7                     │ │
│  │  per month              │  │  per month              │ │
│  │                         │  │                         │ │
│  │  ✓ 3 free checks        │  │  ✓ Unlimited checks     │ │
│  │  ✓ Basic verification   │  │  ✓ Priority processing  │ │
│  │  ✓ Standard support     │  │  ✓ Priority support     │ │
│  │                         │  │  ✓ Advanced features    │ │
│  │                         │  │                         │ │
│  │  [Current Plan]         │  │  [Upgrade Now]          │ │
│  └─────────────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Styling:**
- Two cards side-by-side (grid-cols-1 md:grid-cols-2)
- Card background: `bg-slate-800/50`
- Border: `border border-slate-700`
- Professional card: Add subtle gradient border (optional enhancement)
- **NO "Most Popular" badge** (per GAP #5 resolution)

**Features List:**
- Free: 3 free checks, Basic verification, Standard support
- Professional: Unlimited checks, Priority processing, Priority support, Advanced features

**Buttons:**
- Free card: "Current Plan" (disabled, grey) if user is on free
- Professional card: "Upgrade Now" (gradient) if user is free
- Professional card: "Current Plan" (disabled) if user is pro
- Free card: "Downgrade" (grey) if user is pro (opens confirmation modal)

### **Billing History** (For Professional Users Only)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Billing History                                            │
│                                                             │
│  Date           Amount    Status      Invoice              │
│  ─────────────────────────────────────────────────────────  │
│  Mar 1, 2024    £7.00     Paid        [Download]           │
│  Feb 1, 2024    £7.00     Paid        [Download]           │
│  Jan 1, 2024    £7.00     Paid        [Download]           │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Table with date, amount, status, download link
- Last 5 invoices displayed
- "View All" link → Opens Stripe billing portal
- Download links fetch invoice PDF from Stripe

---

## **TAB 3: NOTIFICATIONS** (Settings.notifications.png)

### **Email Notifications Section**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Email Notifications                                        │
│                                                             │
│  Email Notifications                                        │
│  Receive notifications via email                           │
│                                                [Toggle ON]  │
│                                                             │
│  Check Completion                                          │
│  Get notified when your fact-checks are complete           │
│                                                [Toggle ON]  │
│                                                             │
│  Weekly Digest                                             │
│  Receive a weekly summary of your activity                 │
│                                                [Toggle OFF] │
│                                                             │
│  Marketing Emails                                          │
│  Receive updates about new features and offers             │
│                                                [Toggle OFF] │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- 4 toggle switches (as per GAP #7 resolution)
- Master toggle: "Email Notifications" (controls all others)
- Individual toggles: Check Completion, Weekly Digest, Marketing Emails
- Helper text below each toggle
- **Frontend-only (localStorage) for MVP** (per GAP #7 resolution)

**Implementation:**
```typescript
interface NotificationPreferences {
  emailEnabled: boolean;
  checkCompletion: boolean;
  weeklyDigest: boolean;
  marketing: boolean;
}

// Load from localStorage
const loadPreferences = (): NotificationPreferences => {
  const saved = localStorage.getItem('notificationPrefs');
  return saved ? JSON.parse(saved) : {
    emailEnabled: true,
    checkCompletion: true,
    weeklyDigest: false,
    marketing: false,
  };
};

// Save to localStorage
const savePreferences = (prefs: NotificationPreferences) => {
  localStorage.setItem('notificationPrefs', JSON.stringify(prefs));
};
```

**Future Backend Integration:**
- Phase 2: Add backend endpoints to save preferences
- Add fields to User model: `email_notifications_enabled`, `check_completion_emails`, etc.
- Sync localStorage to backend on change

### **Push Notifications Section** (Future Enhancement)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Push Notifications                                         │
│                                                             │
│  Browser Notifications                                     │
│  Get notified in your browser when checks complete         │
│                                                [Enable]     │
└─────────────────────────────────────────────────────────────┘
```

**Note:** Not shown in screenshots, optional Phase 2 enhancement

---

## **BACKEND INTEGRATION**

### **Account Tab**

**User Data Fetch:**
```typescript
const token = await getToken();
const user = await apiClient.getCurrentUser(token);
```

**API Endpoint:** `GET /api/v1/users/me`

**Response Schema:**
```typescript
{
  id: string,
  email: string,
  name: string | null,
  credits: number,
  totalCreditsUsed: number,
  hasSubscription: boolean,
  createdAt: string
}
```

**Update User Name:**
```typescript
// Via Clerk API (not backend)
import { useUser } from '@clerk/nextjs';

const { user } = useUser();
await user?.update({ firstName: 'John', lastName: 'Doe' });
```

**Delete Account:**
```typescript
// Via Clerk API + Backend cleanup
await user?.delete();
await apiClient.deleteUser(userId, token); // Backend cleanup
```

### **Subscription Tab**

**Subscription Data Fetch:**
```typescript
const subscription = await apiClient.getSubscriptionStatus(token);
const usage = await apiClient.getMonthlyUsage(token);
```

**API Endpoint:** `GET /api/v1/payments/subscription-status`

**Response Schema:**
```typescript
{
  hasSubscription: boolean,
  plan: 'starter' | 'pro' | null,
  status: 'active' | 'canceled' | 'past_due' | null,
  creditsPerMonth: number | null,
  creditsRemaining: number,
  currentPeriodStart: string | null,
  currentPeriodEnd: string | null,
  cancelAtPeriodEnd: boolean
}
```

**Create Checkout Session (Upgrade Flow):**
```typescript
const session = await apiClient.createCheckoutSession(token);
window.location.href = session.url; // Redirect to Stripe Checkout
```

**API Endpoint:** `POST /api/v1/payments/create-checkout-session`

**Request Body:**
```typescript
{
  priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO,
  successUrl: `${window.location.origin}/dashboard/settings?tab=subscription&success=true`,
  cancelUrl: `${window.location.origin}/dashboard/settings?tab=subscription`
}
```

**Manage Subscription (Billing Portal):**
```typescript
const portal = await apiClient.createBillingPortalSession(token);
window.location.href = portal.url; // Redirect to Stripe Portal
```

**API Endpoint:** `POST /api/v1/payments/create-portal-session`

**Monthly Usage Calculation:**
```typescript
// As per GAP #4 resolution
const now = new Date();
const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

const checks = await apiClient.getChecks(token, 0, 1000); // Fetch all for month
const monthlyChecks = checks.checks.filter(c => new Date(c.createdAt) >= startOfMonth);
const monthlyUsage = monthlyChecks.reduce((sum, c) => sum + c.creditsUsed, 0);
```

**Backend File References:**
- `backend/app/api/v1/payments.py:10-45` - Subscription status
- `backend/app/api/v1/payments.py:48-78` - Checkout session
- `backend/app/api/v1/payments.py:81-102` - Billing portal

### **Notifications Tab**

**Frontend-Only (MVP):**
- No backend calls required
- All preferences stored in localStorage
- Load on mount, save on change

**Phase 2 Backend Integration:**
```typescript
// Future endpoint
await apiClient.updateNotificationPreferences(token, {
  emailNotificationsEnabled: true,
  checkCompletionEmails: true,
  weeklyDigestEnabled: false,
  marketingEmailsEnabled: false,
});
```

---

## **COMPONENT STRUCTURE**

### **File: `web/app/dashboard/settings/page.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import { PageHeader } from '../components/page-header';
import { SettingsTabs } from './components/settings-tabs';
import { AccountTab } from './components/account-tab';
import { SubscriptionTab } from './components/subscription-tab';
import { NotificationsTab } from './components/notifications-tab';
import { apiClient } from '@/lib/api';

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { user: clerkUser } = useUser();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('account');
  const [userData, setUserData] = useState(null);
  const [subscriptionData, setSubscriptionData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Get active tab from query param
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab && ['account', 'subscription', 'notifications'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Fetch user and subscription data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = await getToken();

        const [user, subscription] = await Promise.all([
          apiClient.getCurrentUser(token),
          apiClient.getSubscriptionStatus(token),
        ]);

        setUserData(user);
        setSubscriptionData(subscription);
      } catch (error) {
        console.error('Failed to fetch settings data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [getToken]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    router.push(`/dashboard/settings?tab=${tab}`);
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Settings"
          description="Manage your account and preferences"
          imagePath="/imagery/tree.png"
        />
        <div className="text-center py-12">
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Manage your account and preferences"
        imagePath="/imagery/tree.png"
      />

      <SettingsTabs activeTab={activeTab} onTabChange={handleTabChange} />

      <div className="mt-8">
        {activeTab === 'account' && (
          <AccountTab clerkUser={clerkUser} userData={userData} />
        )}
        {activeTab === 'subscription' && (
          <SubscriptionTab
            userData={userData}
            subscriptionData={subscriptionData}
            onUpdate={() => {
              // Refresh subscription data
              fetchData();
            }}
          />
        )}
        {activeTab === 'notifications' && <NotificationsTab />}
      </div>
    </div>
  );
}
```

### **File: `web/app/dashboard/settings/components/settings-tabs.tsx`**

```typescript
'use client';

interface SettingsTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function SettingsTabs({ activeTab, onTabChange }: SettingsTabsProps) {
  const tabs = [
    { id: 'account', label: 'Account' },
    { id: 'subscription', label: 'Subscription' },
    { id: 'notifications', label: 'Notifications' },
  ];

  return (
    <div className="border-b border-slate-700">
      <div className="flex items-center gap-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`pb-4 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-[#f57a07] border-[#f57a07]'
                : 'text-slate-400 border-transparent hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### **File: `web/app/dashboard/settings/components/account-tab.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { User as ClerkUser } from '@clerk/nextjs/server';
import { useClerk } from '@clerk/nextjs';
import Image from 'next/image';
import { User, Shield, Trash2 } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface AccountTabProps {
  clerkUser: ClerkUser | null;
  userData: any;
}

export function AccountTab({ clerkUser, userData }: AccountTabProps) {
  const { openUserProfile, signOut } = useClerk();
  const [name, setName] = useState(clerkUser?.fullName || '');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const handleUpdateProfile = () => {
    // Open Clerk's built-in profile modal
    openUserProfile();
  };

  const handleChangePassword = () => {
    // Open Clerk's security modal
    openUserProfile({ page: 'security' });
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you absolutely sure? This action cannot be undone.')) {
      return;
    }

    try {
      // Delete from Clerk
      await clerkUser?.delete();

      // Cleanup backend data
      await apiClient.deleteUser(userData.id, await getToken());

      // Sign out
      await signOut();
      window.location.href = '/';
    } catch (error) {
      console.error('Failed to delete account:', error);
      alert('Failed to delete account. Please contact support.');
    }
  };

  const initials = clerkUser?.firstName?.[0] + clerkUser?.lastName?.[0] || 'U';

  return (
    <div className="space-y-8">
      {/* Profile Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <User size={20} />
          Profile Information
        </h3>

        <div className="space-y-6">
          {/* Avatar */}
          <div className="flex justify-center">
            {clerkUser?.imageUrl ? (
              <Image
                src={clerkUser.imageUrl}
                alt="Profile"
                width={80}
                height={80}
                className="rounded-full"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-slate-600 flex items-center justify-center text-white text-2xl font-bold">
                {initials}
              </div>
            )}
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-[#f57a07] transition-colors"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Email
            </label>
            <input
              type="email"
              value={clerkUser?.primaryEmailAddress?.emailAddress || ''}
              disabled
              className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-slate-500 cursor-not-allowed"
            />
            <p className="text-xs text-slate-400 mt-1">
              Email is managed by your authentication provider
            </p>
          </div>

          <button
            onClick={handleUpdateProfile}
            className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all"
          >
            Update Profile
          </button>
        </div>
      </section>

      {/* Security Section */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Shield size={20} />
          Security
        </h3>

        <div className="space-y-4">
          {/* Password */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-300">Password</p>
              <p className="text-xs text-slate-400">••••••••</p>
            </div>
            <button
              onClick={handleChangePassword}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
            >
              Change Password
            </button>
          </div>

          {/* 2FA */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-300">
                Two-Factor Authentication
              </p>
              <p className="text-xs text-slate-400">
                Status:{' '}
                {clerkUser?.twoFactorEnabled ? (
                  <span className="text-emerald-400 font-medium">Enabled</span>
                ) : (
                  <span className="text-slate-500 font-medium">Disabled</span>
                )}
              </p>
            </div>
            <button
              onClick={handleChangePassword}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
            >
              Configure 2FA
            </button>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-red-900/10 border border-red-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-red-400 mb-4 flex items-center gap-2">
          <Trash2 size={20} />
          Danger Zone
        </h3>

        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-300">Delete Account</p>
            <p className="text-xs text-slate-400 mt-1">
              Once you delete your account, there is no going back. Please be certain.
            </p>
          </div>

          <button
            onClick={handleDeleteAccount}
            className="px-6 py-3 bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-700 font-medium rounded-lg transition-colors"
          >
            Delete Account
          </button>
        </div>
      </section>
    </div>
  );
}
```

### **File: `web/app/dashboard/settings/components/subscription-tab.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Check, Download } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { calculateMonthlyUsage } from '@/lib/usage-utils';
import { format } from 'date-fns';

interface SubscriptionTabProps {
  userData: any;
  subscriptionData: any;
  onUpdate: () => void;
}

export function SubscriptionTab({
  userData,
  subscriptionData,
  onUpdate,
}: SubscriptionTabProps) {
  const { getToken } = useAuth();
  const [monthlyUsage, setMonthlyUsage] = useState(0);
  const [loading, setLoading] = useState(false);

  const isFree = !subscriptionData.hasSubscription;
  const isPro = subscriptionData.plan === 'pro';

  // Calculate monthly usage
  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const token = await getToken();
        const checks = await apiClient.getChecks(token, 0, 1000);
        const usage = calculateMonthlyUsage(checks.checks);
        setMonthlyUsage(usage);
      } catch (error) {
        console.error('Failed to fetch usage:', error);
      }
    };

    fetchUsage();
  }, [getToken]);

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const session = await apiClient.createCheckoutSession(token);
      window.location.href = session.url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start upgrade process. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const portal = await apiClient.createBillingPortalSession(token);
      window.location.href = portal.url;
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      alert('Failed to open billing portal. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Current Plan Card */}
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6">Your Current Plan</h3>

        <div className="space-y-4">
          {/* Plan Name */}
          <div>
            <h4 className="text-2xl font-black text-white">
              {isFree ? 'Free' : 'Professional'}
            </h4>
            <p className="text-slate-400 mt-1">
              {isFree ? '3 free checks' : '£7 per month · Unlimited checks'}
            </p>
          </div>

          {/* Usage */}
          {isFree ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-300">
                  Usage this month: {monthlyUsage} / 3 checks
                </p>
                <p className="text-sm font-bold text-slate-300">
                  {Math.round((monthlyUsage / 3) * 100)}%
                </p>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] transition-all duration-500"
                  style={{ width: `${Math.min((monthlyUsage / 3) * 100, 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-300 mb-1">
                Next billing date:{' '}
                {subscriptionData.currentPeriodEnd
                  ? format(new Date(subscriptionData.currentPeriodEnd), 'MMMM d, yyyy')
                  : 'N/A'}
              </p>
              <p className="text-sm text-slate-300">
                Usage this month: {monthlyUsage} checks
              </p>
            </div>
          )}

          {/* Action Button */}
          {isFree ? (
            <button
              onClick={handleUpgrade}
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Upgrade to Professional'}
            </button>
          ) : (
            <button
              onClick={handleManageSubscription}
              disabled={loading}
              className="w-full px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Manage Subscription'}
            </button>
          )}
        </div>
      </section>

      {/* Available Plans */}
      <section>
        <h3 className="text-xl font-bold text-white mb-6">Available Plans</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Plan Card */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h4 className="text-2xl font-black text-white mb-2">Free</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-white">£0</p>
              <p className="text-slate-400">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>3 free checks</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Basic verification</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Standard support</span>
              </li>
            </ul>

            <button
              disabled={isFree}
              className="w-full px-6 py-3 bg-slate-700 text-slate-400 font-medium rounded-lg cursor-not-allowed"
            >
              {isFree ? 'Current Plan' : 'Downgrade'}
            </button>
          </div>

          {/* Professional Plan Card */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h4 className="text-2xl font-black text-white mb-2">Professional</h4>
            <div className="mb-6">
              <p className="text-4xl font-black text-white">£7</p>
              <p className="text-slate-400">per month</p>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Unlimited checks</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Priority processing</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Priority support</span>
              </li>
              <li className="flex items-start gap-2 text-slate-300">
                <Check size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>Advanced features</span>
              </li>
            </ul>

            {isPro ? (
              <button
                disabled
                className="w-full px-6 py-3 bg-slate-700 text-slate-400 font-medium rounded-lg cursor-not-allowed"
              >
                Current Plan
              </button>
            ) : (
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full px-6 py-3 bg-gradient-to-r from-[#f57a07] to-[#ff8c1a] hover:from-[#ff8c1a] hover:to-[#f57a07] text-white font-medium rounded-lg transition-all disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Upgrade Now'}
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Billing History (Pro Only) */}
      {isPro && (
        <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-xl font-bold text-white mb-6">Billing History</h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left text-sm font-medium text-slate-400 pb-3">
                    Date
                  </th>
                  <th className="text-left text-sm font-medium text-slate-400 pb-3">
                    Amount
                  </th>
                  <th className="text-left text-sm font-medium text-slate-400 pb-3">
                    Status
                  </th>
                  <th className="text-right text-sm font-medium text-slate-400 pb-3">
                    Invoice
                  </th>
                </tr>
              </thead>
              <tbody>
                {/* Placeholder - would fetch from Stripe in production */}
                <tr className="border-b border-slate-700/50">
                  <td className="py-3 text-sm text-slate-300">Mar 1, 2024</td>
                  <td className="py-3 text-sm text-slate-300">£7.00</td>
                  <td className="py-3">
                    <span className="text-sm text-emerald-400 font-medium">Paid</span>
                  </td>
                  <td className="py-3 text-right">
                    <button className="text-sm text-[#f57a07] hover:text-[#ff8c1a] transition-colors flex items-center gap-1 ml-auto">
                      <Download size={14} />
                      <span>Download</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <button
            onClick={handleManageSubscription}
            className="mt-4 text-sm text-[#f57a07] hover:text-[#ff8c1a] transition-colors"
          >
            View All Invoices →
          </button>
        </section>
      )}
    </div>
  );
}
```

### **File: `web/app/dashboard/settings/components/notifications-tab.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';

interface NotificationPreferences {
  emailEnabled: boolean;
  checkCompletion: boolean;
  weeklyDigest: boolean;
  marketing: boolean;
}

export function NotificationsTab() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    emailEnabled: true,
    checkCompletion: true,
    weeklyDigest: false,
    marketing: false,
  });

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('notificationPrefs');
    if (saved) {
      try {
        setPreferences(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to parse notification preferences:', error);
      }
    }
  }, []);

  // Save to localStorage on change
  const updatePreference = (key: keyof NotificationPreferences, value: boolean) => {
    const updated = { ...preferences, [key]: value };

    // If master toggle is disabled, disable all others
    if (key === 'emailEnabled' && !value) {
      updated.checkCompletion = false;
      updated.weeklyDigest = false;
      updated.marketing = false;
    }

    setPreferences(updated);
    localStorage.setItem('notificationPrefs', JSON.stringify(updated));
  };

  return (
    <div className="space-y-8">
      <section className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Bell size={20} />
          Email Notifications
        </h3>

        <div className="space-y-6">
          {/* Master Toggle */}
          <div className="flex items-center justify-between pb-6 border-b border-slate-700">
            <div>
              <p className="text-sm font-medium text-white">Email Notifications</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive notifications via email
              </p>
            </div>
            <button
              onClick={() => updatePreference('emailEnabled', !preferences.emailEnabled)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.emailEnabled ? 'bg-[#f57a07]' : 'bg-slate-600'
              }`}
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.emailEnabled ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Check Completion */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Check Completion</p>
              <p className="text-xs text-slate-400 mt-1">
                Get notified when your fact-checks are complete
              </p>
            </div>
            <button
              onClick={() =>
                updatePreference('checkCompletion', !preferences.checkCompletion)
              }
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.checkCompletion && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.checkCompletion && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Weekly Digest */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Weekly Digest</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive a weekly summary of your activity
              </p>
            </div>
            <button
              onClick={() => updatePreference('weeklyDigest', !preferences.weeklyDigest)}
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.weeklyDigest && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.weeklyDigest && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Marketing Emails */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Marketing Emails</p>
              <p className="text-xs text-slate-400 mt-1">
                Receive updates about new features and offers
              </p>
            </div>
            <button
              onClick={() => updatePreference('marketing', !preferences.marketing)}
              disabled={!preferences.emailEnabled}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                preferences.marketing && preferences.emailEnabled
                  ? 'bg-[#f57a07]'
                  : 'bg-slate-600'
              } ${!preferences.emailEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div
                className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  preferences.marketing && preferences.emailEnabled
                    ? 'translate-x-6'
                    : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
          <p className="text-xs text-blue-300">
            ℹ️ <strong>Note:</strong> Notification preferences are currently stored locally.
            Backend sync coming in Phase 2.
          </p>
        </div>
      </section>
    </div>
  );
}
```

### **File: `web/lib/usage-utils.ts`**

```typescript
// Reusable monthly usage calculation (as per GAP #4 resolution)

export function calculateMonthlyUsage(checks: any[]): number {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  const monthlyChecks = checks.filter((check) => {
    const checkDate = new Date(check.createdAt);
    return checkDate >= startOfMonth;
  });

  return monthlyChecks.reduce((sum, check) => {
    return sum + (check.creditsUsed || 1);
  }, 0);
}
```

---

## **STYLING REQUIREMENTS**

### **Colors**
- Card background: `bg-slate-800/50`
- Border: `border-slate-700`
- Active tab: `text-[#f57a07] border-[#f57a07]`
- Danger zone: `bg-red-900/10 border-red-700`

### **Toggle Switches**
- Enabled: `bg-[#f57a07]`
- Disabled: `bg-slate-600`
- Transition: Smooth 200ms

### **Typography**
- Page title: `text-4xl font-black`
- Section headings: `text-xl font-bold`
- Labels: `text-sm font-medium`
- Helper text: `text-xs text-slate-400`

### **Spacing** (4pt Grid)
- Card padding: `p-6`
- Section gaps: `space-y-8`
- Form element gaps: `space-y-6`

---

## **REUSABLE COMPONENTS**

### **From Existing Plans**
✅ **`<PageHeader />`** - PLAN_02
- Reuse for "Settings" header with tree graphic

### **New Components**
- `SettingsTabs` - Horizontal tab navigation
- `AccountTab` - Profile and security management
- `SubscriptionTab` - Plan and billing management
- `NotificationsTab` - Email preferences

---

## **ZERO DUPLICATION STRATEGY**

### **Existing Code to Leverage**
1. **Monthly Usage Calculation** - Create shared utility `calculateMonthlyUsage()` (used in Dashboard + Settings)
2. **API Client Methods** - All payment methods already exist in `web/lib/api.ts`
3. **Clerk Hooks** - Use `useUser()` and `useClerk()` for profile management
4. **Design System** - Follow existing button, card, and form styles

### **New Utility Functions**
- `web/lib/usage-utils.ts` - Shared monthly usage calculation
- `web/lib/notification-utils.ts` - LocalStorage notification preference management

---

## **GAP RESOLUTIONS**

### **Clerk Profile Updates**

**Challenge:** How to update user profile data (name, avatar)?

**Solution:** Use Clerk's built-in UI components

```typescript
import { useClerk } from '@clerk/nextjs';

const { openUserProfile } = useClerk();

// Open profile modal
openUserProfile();

// Open specific tab
openUserProfile({ page: 'security' });
```

**Alternative:** Use Clerk's `useUser()` hook for direct API updates

```typescript
const { user } = useUser();
await user?.update({ firstName: 'John', lastName: 'Doe' });
```

### **Stripe Pricing ID Configuration**

**Environment Variable Required:**
```bash
NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=price_xxxxxxxxxxxxxx
```

**Backend must create Stripe Price:**
- Product: "Tru8 Professional"
- Price: £7.00 GBP
- Recurring: Monthly
- Copy Price ID to environment variable

### **LocalStorage Notification Preferences**

**Implementation:**
```typescript
// Load
const saved = localStorage.getItem('notificationPrefs');
const prefs = saved ? JSON.parse(saved) : defaultPrefs;

// Save
localStorage.setItem('notificationPrefs', JSON.stringify(prefs));
```

**Phase 2 Migration:**
- Add backend endpoint: `PUT /api/v1/users/me/notification-preferences`
- Add User model fields: `email_notifications_enabled`, etc.
- Sync localStorage to backend on change
- Load from backend on mount (fallback to localStorage)

---

## **GAPS RESOLVED**

### **✅ GAP #17 RESOLVED: Billing History Data Source**

**Issue:**
- Screenshot shows billing history table
- Stripe provides invoice data via API
- Need to fetch and display last 5 invoices

**DECISION APPROVED:** ✅ Display billing history on Settings page

**Backend Implementation (New Endpoint Required):**
```python
@router.get("/invoices")
async def get_invoices(current_user: User = Depends(get_current_user)):
    # Only for Pro users with Stripe customer ID
    if not current_user.stripe_customer_id:
        return {"invoices": []}

    stripe_customer_id = current_user.stripe_customer_id
    invoices = stripe.Invoice.list(customer=stripe_customer_id, limit=5)

    return {
        "invoices": [
            {
                "id": inv.id,
                "date": inv.created,
                "amount": inv.amount_paid / 100,
                "currency": inv.currency,
                "status": inv.status,
                "pdf_url": inv.invoice_pdf
            }
            for inv in invoices.data
        ]
    }
```

**Frontend:**
```typescript
// Fetch invoices for Pro users
const invoices = await apiClient.getInvoices(token);

// Display in table
<table>
  <tr>
    <td>{format(new Date(invoice.date * 1000), 'MMM d, yyyy')}</td>
    <td>£{invoice.amount.toFixed(2)}</td>
    <td>{invoice.status}</td>
    <td><a href={invoice.pdf_url} download>Download</a></td>
  </tr>
</table>

// "View All" link to Stripe portal
```

**Rationale:**
- Better UX to show recent invoices on Settings page
- Reduces friction for users checking billing history
- "View All" link provides escape hatch to Stripe portal

---

### **✅ GAP #18 RESOLVED: Account Deletion Backend Cleanup**

**Issue:**
- Clerk deletes user authentication
- Backend database still has User, Checks, Claims, Evidence records
- Need backend endpoint to cascade delete all user data

**DECISION APPROVED:** ✅ Immediate deletion

**Backend Implementation (New Endpoint Required):**
```python
@router.delete("/users/me")
async def delete_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Delete all checks (cascade deletes claims and evidence via foreign key)
    db.query(Check).filter(Check.user_id == current_user.id).delete()

    # Delete subscription records
    db.query(Subscription).filter(Subscription.user_id == current_user.id).delete()

    # Delete user
    db.delete(current_user)
    db.commit()

    return {"message": "User deleted successfully"}
```

**Frontend Flow:**
```typescript
const handleDeleteAccount = async () => {
  // Double confirmation
  if (!confirm('Are you absolutely sure? This action cannot be undone.')) {
    return;
  }

  try {
    // 1. Delete backend data
    await apiClient.deleteUser(userId, token);

    // 2. Delete Clerk authentication
    await clerkUser?.delete();

    // 3. Sign out and redirect
    await signOut();
    window.location.href = '/';
  } catch (error) {
    console.error('Failed to delete account:', error);
    alert('Failed to delete account. Please contact support.');
  }
};
```

**Rationale:**
- Simpler implementation for MVP
- Immediate GDPR compliance (right to erasure)
- Clear user expectation (no ambiguity about when data is deleted)
- Can add grace period in Phase 2 if user feedback requests it

**Database Cascade:**
- User deletion → cascades to Checks
- Check deletion → cascades to Claims
- Claim deletion → cascades to Evidence
- Ensure foreign key constraints configured for CASCADE DELETE

---

### **✅ GAP #19 RESOLVED: Downgrade Flow**

**Issue:**
- Screenshot doesn't show downgrade UI
- Professional → Free transition needs handling
- Questions: Immediate or end of billing period? What happens to excess usage?

**DECISION APPROVED:** ✅ Option B: End of period downgrade

**Implementation:**

**Frontend:**
```typescript
const handleDowngrade = async () => {
  if (!confirm('Downgrade to Free plan at end of billing period?')) {
    return;
  }

  try {
    const token = await getToken();
    await apiClient.cancelSubscription(token);

    // Refresh subscription data
    const updated = await apiClient.getSubscriptionStatus(token);
    setSubscriptionData(updated);

    alert(`Your plan will downgrade to Free on ${format(new Date(updated.currentPeriodEnd), 'MMMM d, yyyy')}`);
  } catch (error) {
    console.error('Failed to cancel subscription:', error);
    alert('Failed to cancel subscription. Please try again.');
  }
};
```

**Backend (New Endpoint Required):**
```python
@router.post("/payments/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    # Set Stripe subscription to cancel at period end
    subscription = stripe.Subscription.modify(
        current_user.stripe_subscription_id,
        cancel_at_period_end=True
    )

    return {
        "message": "Subscription will cancel at period end",
        "cancel_at": subscription.current_period_end
    }
```

**UI Display:**
```typescript
// Show cancellation notice in Current Plan card
{subscriptionData.cancelAtPeriodEnd && (
  <div className="mt-4 p-4 bg-amber-900/20 border border-amber-700 rounded-lg">
    <p className="text-sm text-amber-300">
      Your plan will downgrade to Free on{' '}
      {format(new Date(subscriptionData.currentPeriodEnd), 'MMMM d, yyyy')}
    </p>
    <button
      onClick={handleReactivate}
      className="mt-2 text-sm text-amber-400 hover:text-amber-300 underline"
    >
      Reactivate subscription
    </button>
  </div>
)}
```

**Rationale:**
- Fair to user (keeps Pro access until billing period ends)
- Industry standard practice (Netflix, Spotify, etc.)
- User can reactivate before period ends
- Automatic downgrade on period end via Stripe webhook

**Webhook Handling:**
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    event = stripe.Webhook.construct_event(
        await request.body(),
        request.headers.get("stripe-signature"),
        STRIPE_WEBHOOK_SECRET
    )

    if event.type == "customer.subscription.deleted":
        # Subscription ended - downgrade user to Free
        subscription = event.data.object
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription.id
        ).first()

        if user:
            # Reset to free plan
            user.stripe_subscription_id = None
            user.credits = 3
            db.commit()

    return {"status": "success"}
```

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Page Structure**
- [ ] Create `web/app/dashboard/settings/page.tsx`
- [ ] Add query param routing (?tab=account)
- [ ] Fetch user and subscription data
- [ ] Create `SettingsTabs` component

### **Phase 2: Account Tab**
- [ ] Create `AccountTab` component
- [ ] Implement profile section with avatar
- [ ] Add Clerk profile modal integration
- [ ] Implement security section (password, 2FA)
- [ ] Add danger zone with account deletion

### **Phase 3: Subscription Tab**
- [ ] Create `SubscriptionTab` component
- [ ] Implement Current Plan card (free vs pro)
- [ ] Add monthly usage calculation and display
- [ ] Create pricing cards (Free + Professional)
- [ ] Implement Stripe checkout flow
- [ ] Add billing portal integration
- [ ] Add billing history table (if implementing GAP #17)

### **Phase 4: Notifications Tab**
- [ ] Create `NotificationsTab` component
- [ ] Implement toggle switches (4 preferences)
- [ ] Add localStorage persistence
- [ ] Implement master toggle logic
- [ ] Add Phase 2 notice for backend sync

### **Phase 5: Styling & Polish**
- [ ] Apply 4pt grid spacing
- [ ] Add transition animations
- [ ] Implement hover states
- [ ] Test responsive behavior
- [ ] Add loading states

### **Phase 6: Testing**
- [ ] Test tab navigation and query params
- [ ] Test profile update via Clerk modal
- [ ] Test password change flow
- [ ] Test 2FA configuration
- [ ] Test account deletion (with confirmation)
- [ ] Test upgrade flow (Stripe checkout)
- [ ] Test billing portal redirect
- [ ] Test notification toggles and persistence
- [ ] Test monthly usage calculation

---

## **DEPENDENCIES**

### **Required Before Starting**
- ✅ Backend `/users/me` endpoint functional
- ✅ Backend `/payments/subscription-status` endpoint functional
- ✅ Backend `/payments/create-checkout-session` endpoint functional
- ✅ Backend `/payments/create-portal-session` endpoint functional
- ✅ Stripe Product and Price configured (£7 Professional plan)
- ✅ `NEXT_PUBLIC_STRIPE_PRICE_ID_PRO` environment variable set
- ✅ Clerk authentication configured

### **External Dependencies**
- `@clerk/nextjs` - Authentication and profile management
- `date-fns` - Date formatting
- `lucide-react` - Icons

### **Optional (for GAP #17)**
- Backend `/payments/invoices` endpoint

### **Optional (for GAP #18)**
- Backend `DELETE /users/me` endpoint

---

## **TESTING SCENARIOS**

### **Tab Navigation**
1. **Direct URL:** `/dashboard/settings?tab=subscription` should open Subscription tab
2. **Tab click:** Should update URL and active state
3. **Default tab:** No query param should default to Account tab

### **Account Tab**
1. **Profile update:** Should open Clerk modal
2. **Password change:** Should open Clerk security modal
3. **Account deletion:** Should show confirmation, delete from Clerk + backend, sign out

### **Subscription Tab**
1. **Free user:** Should show usage bar, "Upgrade" button
2. **Pro user:** Should show next billing date, "Manage Subscription" button
3. **Upgrade flow:** Should redirect to Stripe checkout, return to Settings on success
4. **Billing portal:** Should redirect to Stripe portal

### **Notifications Tab**
1. **Master toggle OFF:** Should disable all other toggles
2. **Individual toggles:** Should save to localStorage
3. **Persistence:** Should load saved preferences on page refresh

### **Monthly Usage**
1. **Free user:** Should calculate usage from checks table, show X / 3
2. **Pro user:** Should calculate usage, show count without limit

---

## **NOTES**

- Settings page uses query param routing for tabs (not nested routes)
- Account management delegates to Clerk's built-in UI (less custom code)
- Subscription management integrates with Stripe Checkout and Billing Portal
- Notifications are frontend-only for MVP (backend sync in Phase 2)
- Monthly usage calculation is shared utility used in Dashboard + Settings
- All pricing displays "£7" for Professional plan (per GAP #2)
- Free plan displays "3 free checks" (per GAP #1)
- No "Most Popular" badge on pricing cards (per GAP #5)

---

## **PERFORMANCE CONSIDERATIONS**

### **Data Fetching**
- Fetch user and subscription data in parallel on mount
- Cache subscription data to avoid repeated Stripe API calls
- Use React Query for caching if implementing real-time updates

### **LocalStorage Operations**
- Read from localStorage only on mount (not on every render)
- Debounce localStorage writes if implementing real-time sync

### **Stripe Redirects**
- Show loading spinner during redirect (checkout, billing portal)
- Handle redirect back with success/cancel query params
