# 📄 PLAN #2: DASHBOARD HOME PAGE

**File:** `web/app/dashboard/page.tsx`
**Type:** Server Component (initial data) + Client Components (interactivity)
**Status:** NOT STARTED

---

## **PURPOSE**

Main dashboard landing page after sign-in. Shows:
- Welcome message with user name
- Usage statistics and credit balance
- Premium feature upgrade prompt (if on free plan)
- Quick action to start new check
- Recent check history (last 5 checks)

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Screenshot References**
- `dashboard/signIn.dashboard01.png` - Hero, upgrade banner, usage/quick action cards
- `dashboard/signIn.dashboard02.png` - Recent checks list

---

### **SECTION A: Hero**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Tru8: Your truth companion              [Justice Scales Graphic]│
│  Instantly verify claims, URLs, and      │                     │
│  articles.                               │                     │
│                                          │                     │
│  [Start Verifying Button]                │                     │
│                                                         [Social] │
└─────────────────────────────────────────────────────────────────┘
```

**Left Side:**
- **Heading:** "Tru8: Your truth companion"
  - Font: `text-4xl md:text-5xl font-black text-white`
  - Line height: Tight
- **Subheading:** "Instantly verify claims, URLs, and articles."
  - Font: `text-lg text-slate-300`
  - Margin: mt-4
- **CTA Button:** "Start Verifying"
  - Background: `bg-[#f57a07] hover:bg-[#e06a00]`
  - Text: White, bold
  - Padding: px-8 py-3
  - Border radius: rounded-xl
  - Links to: `/dashboard/new-check`

**Right Side:**
- **Justice Scales Graphic**
  - Dimensions: 300x300px
  - Placeholder: Gradient div with Scale icon

**Far Right Edge:**
- **Vertical Social Icons** (Facebook, Instagram, Twitter, YouTube)
  - Position: Absolute right edge
  - Icons: 24x24px, slate-400
  - Spacing: gap-4, vertical stack

---

### **SECTION B: Welcome Message**

```
Welcome back, [User Name]
```

- Font: `text-3xl font-bold text-white`
- Margin: mt-12 mb-8
- User name from: `user.name` (backend)

---

### **SECTION C: Unlock Premium Features** (Conditional)

**Display Logic:** Only if `subscription.plan === 'free'` or `!subscription.hasSubscription`

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│ [✨] Unlock Premium Features              [Upgrade Now →]      │
│     Current Plan: Free                                         │
│                                                                 │
│  • Unlimited fact-checks per month    • Priority verification  │
│  • Advanced source analysis           • Export reports         │
└────────────────────────────────────────────────────────────────┘
```

**Elements:**
- Icon: Sparkles (`<Sparkles />` from lucide-react)
- Heading: "Unlock Premium Features" (text-xl font-bold text-white)
- Current plan: "Current Plan: **Free**" (text-slate-400)
- Features: 2-column grid on desktop, 1-column on mobile
  - "Unlimited fact-checks per month"
  - "Priority verification processing"
  - "Advanced source analysis"
  - "Export reports and citations"
- Button: "Upgrade Now" with arrow icon
  - Background: `bg-[#f57a07]`
  - Position: Top-right of card
  - Action: Navigate to `/dashboard/settings?tab=subscription`

**Styling:**
- Background: `bg-[#1a1f2e]`
- Border: `border border-slate-700`
- Border radius: `rounded-xl`
- Padding: `p-8`

---

### **SECTION D: Two-Column Cards**

**Layout:**
```
┌──────────────────────────────┬───────────────────────────────┐
│  Usage Summary               │  Quick Action                 │
│  Checks used this month:     │  Start a new fact-check       │
│  0 / 40                      │  verification                 │
│                              │                               │
│  [Progress Bar]              │  [+ New Check Button]         │
│  0                  / 40     │                               │
└──────────────────────────────┴───────────────────────────────┘
```

#### **D1: Usage Summary Card**

**Elements:**
- Heading: "Usage Summary" (text-xl font-bold text-white)
- Subheading: "Checks used this month: 0 / X" (text-slate-400)
  - **FREE USERS:** Show "0 / 3" (✅ APPROVED: Display 3 free checks)
  - **SUBSCRIBED USERS:** Show "0 / [creditsPerMonth]"
- Large number: "0" (text-6xl font-black text-white)
- Progress bar:
  - Background: `bg-slate-800`
  - Fill: `bg-gradient-to-r from-blue-500 to-blue-400`
  - Height: 8px
  - Border radius: Full
  - Animated transition
- Right text: "/ X" (text-slate-400)

**Data Source:**
- Monthly usage: ✅ APPROVED: Calculate from `checks` table filtered by `createdAt >= start of month`
- Total: `subscription.creditsPerMonth` or `3` (free users)

#### **D2: Quick Action Card**

**Elements:**
- Heading: "Quick Action" (text-xl font-bold text-white)
- Description: "Start a new fact-check verification" (text-slate-400)
- Button: "+ New Check"
  - Full width: `w-full`
  - Background: `bg-[#f57a07] hover:bg-[#e06a00]`
  - Text: White, font-bold
  - Padding: py-4
  - Icon: `<Plus />` from lucide-react
  - Links to: `/dashboard/new-check`

---

### **SECTION E: Recent Checks**

**Header:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Recent Checks                                        [View All] │
│  Your latest fact-checking verifications                        │
└─────────────────────────────────────────────────────────────────┘
```

- Heading: "Recent Checks" (text-2xl font-bold text-white)
- Subheading: "Your latest fact-checking verifications" (text-slate-400)
- Button: "View All" (bg-slate-700, top-right) → `/dashboard/history`

**Check Cards:** (3 shown in screenshot)

#### **Check Card #1:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [✓ SUPPORTED]  Oct 5, 2025                                 92% │
│                                                         Confidence│
│ Climate change is primarily caused by human activities...       │
└─────────────────────────────────────────────────────────────────┘
```

- **Verdict Pill:** Green background, "SUPPORTED" text, CheckCircle2 icon
- **Date:** "Oct 5, 2025" (formatted from `createdAt`)
- **Claim Text:** First claim from check
- **Confidence:** Large orange number on right (92%)

#### **Check Card #2:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [✗ CONTRADICTED]  Oct 2, 2025                              88% │
│                                                         Confidence│
│ Vaccines cause autism - this claim has been thoroughly...      │
│ 🔗 https://example.com/article                                  │
└─────────────────────────────────────────────────────────────────┘
```

- **Verdict Pill:** Red background, "CONTRADICTED" text, XCircle icon
- **URL Link:** External link icon + URL (if `inputUrl` exists)

#### **Check Card #3:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [⚠ UNCERTAIN]  Sep 30, 2025                                45% │
│                                                         Confidence│
│ New technology will revolutionize the industry...               │
└─────────────────────────────────────────────────────────────────┘
```

- **Verdict Pill:** Amber background, "UNCERTAIN" text, AlertCircle icon

**Empty State:**
If `checks.length === 0`:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                   [Icon]                                        │
│           No checks yet                                         │
│           Start your first verification!                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## **BACKEND INTEGRATION**

### **Data Fetching (Server Component)**

```typescript
export default async function DashboardPage() {
  const { getToken } = auth();
  const token = await getToken();

  // Parallel fetch for performance
  const [user, subscription, recentChecks] = await Promise.all([
    apiClient.getUserProfile(token),
    apiClient.getSubscriptionStatus(token),
    apiClient.getChecks(token, 0, 5),
  ]);

  // Calculate monthly usage (GAP #4 resolution)
  const monthlyUsage = calculateMonthlyUsage(recentChecks.checks);

  return (
    <DashboardContent
      user={user}
      subscription={subscription}
      recentChecks={recentChecks}
      monthlyUsage={monthlyUsage}
    />
  );
}
```

### **API Endpoints**

#### **1. GET /api/v1/users/profile**
```typescript
Response: {
  id: string,
  email: string,
  name: string | null,
  credits: number,
  totalCreditsUsed: number,
  stats: {
    totalChecks: number,
    completedChecks: number,
    failedChecks: number
  },
  createdAt: string
}
```

**Backend File:** `backend/app/api/v1/users.py:33-61`

#### **2. GET /api/v1/payments/subscription-status**
```typescript
Response: {
  hasSubscription: boolean,
  plan: 'free' | 'starter' | 'pro',
  status: 'active' | 'cancelled' | 'past_due',
  creditsPerMonth: number,
  creditsRemaining: number,
  currentPeriodEnd: string | null,
  stripeSubscriptionId: string | null
}
```

**Backend File:** `backend/app/api/v1/payments.py:98-124`

**Special Cases:**
- If no subscription: `hasSubscription = false`, `plan = 'free'`, `creditsPerMonth = 3`

#### **3. GET /api/v1/checks?skip=0&limit=5**
```typescript
Response: {
  checks: [{
    id: string,
    status: 'completed' | 'pending' | 'processing' | 'failed',
    inputType: 'url' | 'text' | 'image' | 'video',
    inputUrl: string | null,
    creditsUsed: number,
    createdAt: string,
    completedAt: string | null,
    claims: [{
      id: string,
      text: string,
      verdict: 'supported' | 'contradicted' | 'uncertain',
      confidence: number,  // 0-100
      position: number
    }]
  }],
  total: number
}
```

**Backend File:** `backend/app/api/v1/checks.py:46-75`

**Sorting:** Checks are returned newest first (`ORDER BY created_at DESC`)

---

## **COMPONENT BREAKDOWN**

### **1. PageHeader Component** (Reusable)
**File:** `web/app/dashboard/components/page-header.tsx`

```typescript
interface PageHeaderProps {
  title: string;
  subtitle: string;
  ctaText?: string;
  ctaHref?: string;
  graphic?: React.ReactNode;
}

export function PageHeader({ title, subtitle, ctaText, ctaHref, graphic }: PageHeaderProps) {
  return (
    <div className="relative mb-12">
      <div className="flex items-center justify-between">
        {/* Left content */}
        <div className="flex-1 max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-black text-white mb-4 leading-tight">
            {title}
          </h1>
          <p className="text-lg text-slate-300 mb-6">
            {subtitle}
          </p>
          {ctaText && ctaHref && (
            <Link href={ctaHref}>
              <button className="bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-8 py-3 rounded-xl transition-colors">
                {ctaText}
              </button>
            </Link>
          )}
        </div>

        {/* Right graphic */}
        {graphic && (
          <div className="hidden lg:block flex-shrink-0 ml-12">
            {graphic}
          </div>
        )}
      </div>

      {/* Social icons (absolute positioned) - ✅ APPROVED: Web Share API */}
      <div className="hidden xl:flex absolute right-0 top-0 flex-col gap-4">
        <button
          onClick={() => handleShare('facebook')}
          className="text-slate-400 hover:text-white transition-colors"
        >
          <Facebook size={24} />
        </button>
        <button
          onClick={() => handleShare('instagram')}
          className="text-slate-400 hover:text-white transition-colors"
        >
          <Instagram size={24} />
        </button>
        <button
          onClick={() => handleShare('twitter')}
          className="text-slate-400 hover:text-white transition-colors"
        >
          <Twitter size={24} />
        </button>
        <button
          onClick={() => handleShare('youtube')}
          className="text-slate-400 hover:text-white transition-colors"
        >
          <Youtube size={24} />
        </button>
      </div>
    </div>
  );
}

// ✅ APPROVED: Client-side Web Share API implementation
const handleShare = async (platform: string) => {
  const url = window.location.origin;
  const title = 'Tru8 - Fact-Checking Platform';
  const text = 'Check out Tru8 for instant fact verification with dated evidence';

  // Try native Web Share API first
  if (navigator.share && platform === 'native') {
    try {
      await navigator.share({ title, text, url });
      return;
    } catch (err) {
      console.log('Share cancelled or failed');
    }
  }

  // Fallback to platform-specific URLs
  const shareUrls = {
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
    twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
    instagram: url, // Instagram doesn't support direct URL sharing
    youtube: url, // YouTube doesn't support direct sharing
  };

  const shareUrl = shareUrls[platform as keyof typeof shareUrls];
  if (shareUrl) {
    window.open(shareUrl, '_blank', 'width=600,height=400');
  }
}
```

### **2. JusticeScalesGraphic Component** ✅ UPDATED
```typescript
import Image from 'next/image';

export function JusticeScalesGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/justice-scales.png"
        alt="Justice scales"
        fill
        className="object-contain"
      />
    </div>
  );
}
```

**Note:** ✅ APPROVED: Graphics added to `web/public/imagery/` folder

### **3. UpgradeBanner Component** (Reusable) ✅ UPDATED
**File:** `web/app/dashboard/components/upgrade-banner.tsx`

```typescript
'use client';

import Link from 'next/link';
import { Sparkles, ArrowRight } from 'lucide-react';

interface UpgradeBannerProps {
  currentPlan: string;
}

export function UpgradeBanner({ currentPlan }: UpgradeBannerProps) {
  const features = [
    'Unlimited fact-checks per month',
    'Priority verification processing',
    'Advanced source analysis',
    'Export reports and citations',
  ];

  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8 mb-8">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <Sparkles className="text-[#f57a07]" size={28} />
          <div>
            <h3 className="text-xl font-bold text-white">Unlock Premium Features</h3>
            {/* ✅ APPROVED: Show "Free (3 checks)" */}
            <p className="text-slate-400">Current Plan: <span className="font-semibold">{currentPlan} (3 checks)</span></p>
          </div>
        </div>

        <Link href="/dashboard/settings?tab=subscription">
          <button className="bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold px-6 py-3 rounded-lg flex items-center gap-2 transition-colors">
            Upgrade Now
            <ArrowRight size={18} />
          </button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {features.map((feature, index) => (
          <div key={index} className="flex items-center gap-2 text-slate-300">
            <span className="text-[#f57a07]">•</span>
            {feature}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### **4. UsageCard Component** (Reusable)
**File:** `web/app/dashboard/components/usage-card.tsx`

```typescript
interface UsageCardProps {
  used: number;
  total: number;
  label: string;
}

export function UsageCard({ used, total, label }: UsageCardProps) {
  const percentage = (used / total) * 100;

  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-2">Usage Summary</h3>
      <p className="text-slate-400 mb-6">{label}: {used} / {total}</p>

      <div className="flex items-end justify-between mb-4">
        <div className="text-6xl font-black text-white">{used}</div>
        <div className="text-2xl text-slate-400">/ {total}</div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

### **5. QuickActionCard Component**
```typescript
import Link from 'next/link';
import { Plus } from 'lucide-react';

export function QuickActionCard() {
  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-2">Quick Action</h3>
      <p className="text-slate-400 mb-6">Start a new fact-check verification</p>

      <Link href="/dashboard/new-check">
        <button className="w-full bg-[#f57a07] hover:bg-[#e06a00] text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-colors">
          <Plus size={20} />
          New Check
        </button>
      </Link>
    </div>
  );
}
```

### **6. RecentChecksList Component**
```typescript
import Link from 'next/link';
import { CheckCard } from './check-card';
import { EmptyState } from './empty-state';

interface RecentChecksListProps {
  checks: any[];
}

export function RecentChecksList({ checks }: RecentChecksListProps) {
  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Recent Checks</h2>
          <p className="text-slate-400">Your latest fact-checking verifications</p>
        </div>

        <Link href="/dashboard/history">
          <button className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors">
            View All
          </button>
        </Link>
      </div>

      {checks.length === 0 ? (
        <EmptyState
          icon={<FileQuestion size={48} className="text-slate-600" />}
          message="No checks yet"
          submessage="Start your first verification!"
        />
      ) : (
        <div className="space-y-4">
          {checks.map(check => (
            <CheckCard key={check.id} check={check} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### **7. CheckCard Component** (Reusable)
**File:** `web/app/dashboard/components/check-card.tsx`

```typescript
import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import { VerdictPill } from './verdict-pill';
import { formatDate } from '@/lib/utils';

interface CheckCardProps {
  check: {
    id: string;
    status: string;
    inputUrl: string | null;
    createdAt: string;
    claims: Array<{
      text: string;
      verdict: 'supported' | 'contradicted' | 'uncertain';
      confidence: number;
    }>;
  };
}

export function CheckCard({ check }: CheckCardProps) {
  // Only show completed checks with claims
  if (check.status !== 'completed' || !check.claims || check.claims.length === 0) {
    return null;
  }

  const firstClaim = check.claims[0];

  return (
    <Link href={`/dashboard/check/${check.id}`}>
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors cursor-pointer">
        <div className="flex items-start justify-between gap-6">
          {/* Left: Claim info */}
          <div className="flex-1 min-w-0">
            {/* Verdict + Date */}
            <div className="flex items-center gap-3 mb-3">
              <VerdictPill verdict={firstClaim.verdict} />
              <span className="text-slate-400 text-sm">
                {formatDate(check.createdAt)}
              </span>
            </div>

            {/* Claim text */}
            <p className="text-white mb-2 line-clamp-2">
              {firstClaim.text}
            </p>

            {/* URL if exists */}
            {check.inputUrl && (
              <a
                href={check.inputUrl}
                onClick={(e) => e.stopPropagation()}
                className="text-slate-400 text-sm flex items-center gap-1 hover:text-slate-300"
              >
                <ExternalLink size={14} />
                <span className="truncate">{check.inputUrl}</span>
              </a>
            )}
          </div>

          {/* Right: Confidence */}
          <div className="flex-shrink-0 text-right">
            <div className="text-3xl font-bold text-[#f57a07]">
              {Math.round(firstClaim.confidence)}%
            </div>
            <div className="text-slate-400 text-sm">Confidence</div>
          </div>
        </div>
      </div>
    </Link>
  );
}
```

### **8. VerdictPill Component** (Reusable)
**File:** `web/app/dashboard/components/verdict-pill.tsx`

```typescript
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface VerdictPillProps {
  verdict: 'supported' | 'contradicted' | 'uncertain';
}

const verdictConfig = {
  supported: {
    icon: CheckCircle2,
    label: 'SUPPORTED',
    bgColor: 'bg-emerald-900/30',
    textColor: 'text-emerald-400',
    borderColor: 'border-emerald-600',
  },
  contradicted: {
    icon: XCircle,
    label: 'CONTRADICTED',
    bgColor: 'bg-red-900/30',
    textColor: 'text-red-400',
    borderColor: 'border-red-600',
  },
  uncertain: {
    icon: AlertCircle,
    label: 'UNCERTAIN',
    bgColor: 'bg-amber-900/30',
    textColor: 'text-amber-400',
    borderColor: 'border-amber-600',
  },
};

export function VerdictPill({ verdict }: VerdictPillProps) {
  const config = verdictConfig[verdict];
  const Icon = config.icon;

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor}`}>
      <Icon size={16} />
      <span className="text-xs font-bold">{config.label}</span>
    </div>
  );
}
```

### **9. EmptyState Component** (Reusable)
**File:** `web/app/dashboard/components/empty-state.tsx`

```typescript
interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
  submessage?: string;
}

export function EmptyState({ icon, message, submessage }: EmptyStateProps) {
  return (
    <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-12 text-center">
      <div className="flex justify-center mb-4">
        {icon}
      </div>
      <p className="text-xl font-semibold text-white mb-2">{message}</p>
      {submessage && (
        <p className="text-slate-400">{submessage}</p>
      )}
    </div>
  );
}
```

---

## **UTILITY FUNCTIONS**

### **Monthly Usage Calculation** (GAP #4 Resolution)
**File:** `web/lib/usage-utils.ts`

```typescript
export function calculateMonthlyUsage(checks: any[]): number {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  const monthlyChecks = checks.filter(check => {
    const checkDate = new Date(check.createdAt);
    return checkDate >= startOfMonth;
  });

  return monthlyChecks.reduce((sum, check) => {
    return sum + (check.creditsUsed || 1);
  }, 0);
}
```

### **Date Formatting**
**File:** `web/lib/utils.ts` (add to existing file)

```typescript
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // Relative time for recent dates
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  // Absolute date for older dates
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}
```

---

## **ZERO DUPLICATION STRATEGY**

### **Reusable Components Created**
1. ✅ **`<PageHeader />`** - Used on all dashboard pages
2. ✅ **`<VerdictPill />`** - Used on Dashboard, History, Check Detail pages
3. ✅ **`<CheckCard />`** - Used on Dashboard, History pages
4. ✅ **`<UpgradeBanner />`** - Can be used on any page for free users
5. ✅ **`<UsageCard />`** - Used on Dashboard, Settings pages
6. ✅ **`<EmptyState />`** - Used on Dashboard, History pages

### **Existing Code Leveraged**
- **Footer** - Imported from `web/components/layout/footer.tsx`
- **API Client** - All methods already exist in `web/lib/api.ts`
- **Icons** - All from `lucide-react` (already installed)

---

## **GAP RESOLUTIONS**

### **GAP #1: Free Plan Credits**
- Display "3 free checks" to match backend default
- Show in Usage Summary card
- Update UpgradeBanner to reflect correct number

### **GAP #4: Monthly Usage Calculation**
- Implemented in `calculateMonthlyUsage()` utility
- Filters checks by `createdAt >= start of current month`
- Sums `creditsUsed` field from each check

### **GAP #9: Graphics**
- Justice Scales: Gradient placeholder with Scale icon
- Social icons: Positioned absolutely on right edge
- All using lucide-react icons

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Components**
- [ ] Create PageHeader component
- [ ] Create VerdictPill component
- [ ] Create CheckCard component
- [ ] Create UpgradeBanner component
- [ ] Create UsageCard component
- [ ] Create EmptyState component
- [ ] Create QuickActionCard component
- [ ] Create JusticeScalesPlaceholder component

### **Phase 2: Utils**
- [ ] Add calculateMonthlyUsage() function
- [ ] Add formatDate() function

### **Phase 3: Main Page**
- [ ] Create dashboard page.tsx
- [ ] Fetch all required data (parallel)
- [ ] Calculate monthly usage
- [ ] Render hero section
- [ ] Conditionally render upgrade banner
- [ ] Render usage/quick action cards
- [ ] Render recent checks list

### **Phase 4: Styling**
- [ ] Ensure all colors match design system
- [ ] Verify 4pt grid spacing
- [ ] Test responsive breakpoints
- [ ] Add hover states and transitions

### **Phase 5: Testing**
- [ ] Test with no checks (empty state)
- [ ] Test with free plan (show upgrade banner)
- [ ] Test with subscription (hide upgrade banner)
- [ ] Test monthly usage calculation
- [ ] Test all navigation links

---

## **DEPENDENCIES**

- ✅ Layout complete (provides user data)
- ✅ Backend endpoints functional
- ✅ API client methods available
- ✅ Design system colors defined

---

## **NOTES**

- Server Component for initial data fetch (fast page load)
- All interactivity in client components (buttons, links)
- Uses Suspense boundaries for loading states
- Mobile-first responsive design
- Optimized with parallel data fetching
