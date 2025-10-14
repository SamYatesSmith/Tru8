# 📄 PLAN #1: DASHBOARD LAYOUT

**File:** `web/app/dashboard/layout.tsx`
**Type:** Server Component (for initial data fetch)
**Status:** NOT STARTED

---

## **PURPOSE**

Shared authenticated layout wrapper for all dashboard pages. Handles:
- Authentication check (redirect if not signed in)
- User data fetching on layout mount
- Signed-in navigation rendering
- Footer rendering
- User context passing to child pages

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Navigation Bar** (visible in all dashboard screenshots)

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  [8]    DASHBOARD | HISTORY | SETTINGS    [New Check] [JD▾]   │
└────────────────────────────────────────────────────────────────┘
```

**Left Section:**
- Tru8 "8" logo
- Size: 40x40px
- Links to `/dashboard`

**Center Section:**
- Horizontal tab navigation
- Tabs: DASHBOARD | HISTORY | SETTINGS
- Active state: Orange text (`#f57a07`) + 2px bottom border
- Inactive state: Slate gray text
- Font: Bold, uppercase, spacing between tabs: 2rem

**Right Section:**
- "New Check" button
  - Background: `bg-slate-700`
  - Hover: `bg-slate-600`
  - Icon: `<Plus />` from lucide-react
  - Padding: px-4 py-2
  - Border radius: rounded-lg
- User avatar circle
  - Size: 40x40px
  - Background: `bg-slate-600`
  - Text: User initials (white, bold)
  - Click: Opens dropdown menu

### **User Dropdown Menu** (from navbar/signIn.quickprofmenu.png)

**Position:** Absolute, below avatar, right-aligned
**Appearance:**
- Background: Dark slate (`#1a1f2e`)
- Border: 1px solid `border-slate-700`
- Border radius: rounded-xl
- Padding: p-4
- Width: 240px
- Shadow: Large drop shadow

**Header:**
- User name: "John Doe" (white, font-semibold)
- Email: "john.doe@example.com" (slate-400, text-sm)

**Menu Items:**
```
[icon] Account        → /dashboard/settings?tab=account
[icon] Subscription   → /dashboard/settings?tab=subscription
[icon] Notifications  → /dashboard/settings?tab=notifications
─────────────────────
[icon] Sign Out       (RED text)
```

**Icons:** User, CreditCard, Bell, LogOut (lucide-react)

---

## **BACKEND INTEGRATION**

### **Authentication Check**
```typescript
import { auth } from '@clerk/nextjs';
import { redirect } from 'next/navigation';

const { userId, getToken } = auth();

if (!userId) {
  redirect('/?signin=true'); // Redirect to home with auth modal trigger
}
```

### **User Data Fetch**
```typescript
const token = await getToken();
const user = await apiClient.getCurrentUser(token);
```

**API Endpoint:** `GET /api/v1/users/me`

**Response Schema:**
```typescript
{
  id: string,           // Clerk user ID
  email: string,        // user@example.com
  name: string | null,  // "John Doe"
  credits: number,      // 3 (free) or subscription credits
  totalCreditsUsed: number,
  hasSubscription: boolean,
  createdAt: string     // ISO date
}
```

**Backend Logic:**
- Verifies Clerk JWT token
- Auto-creates user if doesn't exist (first login)
- Returns user with current credits

**File Reference:** `backend/app/api/v1/users.py:10-31`

---

## **COMPONENT STRUCTURE**

### **File: `web/app/dashboard/layout.tsx`**
```typescript
import { auth } from '@clerk/nextjs';
import { redirect } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { SignedInNav } from './components/signed-in-nav';
import { Footer } from '@/components/layout/footer';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // 1. Check authentication
  const { userId, getToken } = auth();

  if (!userId) {
    redirect('/?signin=true');
  }

  // 2. Fetch user data
  const token = await getToken();
  const user = await apiClient.getCurrentUser(token);

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
```

### **File: `web/app/dashboard/components/signed-in-nav.tsx`**
```typescript
'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Plus } from 'lucide-react';
import { UserMenuDropdown } from './user-menu-dropdown';

interface SignedInNavProps {
  user: {
    id: string;
    name: string | null;
    email: string;
    credits: number;
  };
}

export function SignedInNav({ user }: SignedInNavProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const pathname = usePathname();

  // Calculate user initials
  const initials = user.name
    ?.split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase() || 'U';

  const tabs = [
    { label: 'DASHBOARD', href: '/dashboard' },
    { label: 'HISTORY', href: '/dashboard/history' },
    { label: 'SETTINGS', href: '/dashboard/settings' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e]/95 backdrop-blur-sm border-b border-slate-800">
      <div className="container mx-auto px-6 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          {/* Left: Logo */}
          <Link href="/dashboard" className="flex-shrink-0">
            <Image
              src="/logo.proper.png"
              alt="Tru8"
              width={40}
              height={40}
              className="object-contain"
            />
          </Link>

          {/* Center: Tabs */}
          <div className="flex items-center gap-8">
            {tabs.map(tab => {
              const isActive = pathname === tab.href ||
                              (tab.href === '/dashboard/settings' && pathname.startsWith('/dashboard/settings'));

              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={`text-sm font-bold tracking-wide transition-colors pb-1 border-b-2 ${
                    isActive
                      ? 'text-[#f57a07] border-[#f57a07]'
                      : 'text-slate-300 border-transparent hover:text-white'
                  }`}
                >
                  {tab.label}
                </Link>
              );
            })}
          </div>

          {/* Right: New Check + Avatar */}
          <div className="flex items-center gap-4">
            <Link href="/dashboard/new-check">
              <button className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors">
                <Plus size={18} />
                <span className="font-medium">New Check</span>
              </button>
            </Link>

            {/* User Avatar */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center text-white font-bold hover:bg-slate-500 transition-colors"
              >
                {initials}
              </button>

              {dropdownOpen && (
                <>
                  {/* Backdrop */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setDropdownOpen(false)}
                  />

                  {/* Dropdown Menu */}
                  <div className="absolute top-full right-0 mt-2 z-50">
                    <UserMenuDropdown
                      user={user}
                      onClose={() => setDropdownOpen(false)}
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
```

### **File: `web/app/dashboard/components/user-menu-dropdown.tsx`**
```typescript
'use client';

import Link from 'next/link';
import { useClerk } from '@clerk/nextjs';
import { User, CreditCard, Bell, LogOut } from 'lucide-react';

interface UserMenuDropdownProps {
  user: {
    name: string | null;
    email: string;
  };
  onClose: () => void;
}

export function UserMenuDropdown({ user, onClose }: UserMenuDropdownProps) {
  const { signOut } = useClerk();

  const handleSignOut = async () => {
    await signOut();
    window.location.href = '/';
  };

  const menuItems = [
    {
      icon: User,
      label: 'Account',
      href: '/dashboard/settings?tab=account',
    },
    {
      icon: CreditCard,
      label: 'Subscription',
      href: '/dashboard/settings?tab=subscription',
    },
    {
      icon: Bell,
      label: 'Notifications',
      href: '/dashboard/settings?tab=notifications',
    },
  ];

  return (
    <div className="w-60 bg-[#1a1f2e] border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
      {/* User Info Header */}
      <div className="px-4 py-3 border-b border-slate-700">
        <p className="text-white font-semibold truncate">
          {user.name || 'User'}
        </p>
        <p className="text-slate-400 text-sm truncate">
          {user.email}
        </p>
      </div>

      {/* Menu Items */}
      <div className="py-2">
        {menuItems.map(item => (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Sign Out */}
      <div className="border-t border-slate-700 py-2">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-4 py-2 w-full text-red-400 hover:bg-slate-800 hover:text-red-300 transition-colors"
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
```

---

## **STYLING REQUIREMENTS**

### **Colors**
- Navigation background: `bg-[#1a1f2e]/95` with backdrop-blur
- Border: `border-slate-800`
- Active tab: `text-[#f57a07]` with `border-[#f57a07]`
- Button background: `bg-slate-700`
- Dropdown background: `bg-[#1a1f2e]`

### **Typography**
- Tab labels: Bold, uppercase, 14px
- User name: Semibold, 16px
- Email: Regular, 14px, slate-400

### **Spacing**
- Navigation height: 64px (h-16)
- Container max-width: 1024px
- Padding: px-6
- Tab spacing: gap-8

### **Z-Index**
- Navigation: z-50
- Dropdown backdrop: z-40
- Dropdown menu: z-50

---

## **REUSABLE COMPONENTS**

### **From Existing Codebase**
✅ **`<Footer />`** - `web/components/layout/footer.tsx`
- Already built for marketing site
- Reuse as-is for signed-in pages
- Contains: Logo, product links, company links, legal links, social icons

---

## **ZERO DUPLICATION STRATEGY**

### **Existing Code to Leverage**
1. **Footer Component** - Direct import, no changes needed
2. **API Client** - `web/lib/api.ts` already has `getCurrentUser()` method
3. **Clerk Auth** - `useClerk()` hook for sign-out functionality

### **New Components (No Overlap)**
- `SignedInNav` - New component (marketing nav is different)
- `UserMenuDropdown` - New component (no existing dropdown)

### **Styling Patterns to Match**
- Use existing color variables from marketing site
- Match button styles (orange primary, slate secondary)
- Follow existing spacing system (4pt grid)

---

## **GAP RESOLUTIONS**

### **User Initials Calculation**
```typescript
const initials = user.name
  ?.split(' ')
  .map(n => n[0])
  .join('')
  .toUpperCase() || 'U';
```

**Edge Cases:**
- No name: Show "U" (default)
- Single name: Show first letter
- Multiple names: Show first letter of first + last name

### **Clerk Image URL (Optional Enhancement)**
```typescript
import { useUser } from '@clerk/nextjs';

// In client component
const { user: clerkUser } = useUser();
const avatarUrl = clerkUser?.imageUrl;

// Use if available
{avatarUrl ? (
  <Image src={avatarUrl} alt="Avatar" width={40} height={40} className="rounded-full" />
) : (
  <div className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center">
    {initials}
  </div>
)}
```

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Layout Structure**
- [ ] Create `web/app/dashboard/layout.tsx`
- [ ] Add authentication check with redirect
- [ ] Fetch user data from API
- [ ] Render main layout structure

### **Phase 2: Navigation Component**
- [ ] Create `web/app/dashboard/components/signed-in-nav.tsx`
- [ ] Implement logo with link
- [ ] Build tab navigation with active states
- [ ] Add "New Check" button
- [ ] Create avatar circle with initials

### **Phase 3: User Menu Dropdown**
- [ ] Create `web/app/dashboard/components/user-menu-dropdown.tsx`
- [ ] Build dropdown UI with backdrop
- [ ] Add menu items with icons
- [ ] Implement sign-out functionality
- [ ] Add click-outside to close

### **Phase 4: Styling & Polish**
- [ ] Apply all color variables
- [ ] Ensure 4pt grid spacing
- [ ] Add hover states and transitions
- [ ] Test responsive behavior (mobile)
- [ ] Verify z-index stacking

### **Phase 5: Testing**
- [ ] Test authentication redirect
- [ ] Test user data fetching
- [ ] Test tab active states
- [ ] Test dropdown open/close
- [ ] Test sign-out flow
- [ ] Test initials calculation edge cases

---

## **DEPENDENCIES**

### **Required Before Starting**
- ✅ Clerk authentication configured
- ✅ API client with `getCurrentUser()` method
- ✅ Footer component available
- ✅ Backend `/users/me` endpoint functional

### **External Dependencies**
- `@clerk/nextjs` - Authentication
- `lucide-react` - Icons
- `next/navigation` - Routing hooks

---

## **TESTING SCENARIOS**

### **Authentication**
1. **Not signed in:** Should redirect to `/?signin=true`
2. **Signed in:** Should fetch user and render layout
3. **API error:** Should show error message (add error boundary)

### **Navigation**
1. **Tab highlighting:** Active tab should have orange text + border
2. **Logo click:** Should navigate to `/dashboard`
3. **New Check click:** Should navigate to `/dashboard/new-check`

### **User Menu**
1. **Avatar click:** Should open dropdown
2. **Click outside:** Should close dropdown
3. **Menu item click:** Should navigate and close dropdown
4. **Sign out:** Should call `signOut()` and redirect to home

### **User Initials**
1. **Full name:** "John Doe" → "JD"
2. **Single name:** "John" → "J"
3. **No name:** null → "U"
4. **Three names:** "John Michael Doe" → "JD"

---

## **NOTES**

- This layout wraps ALL dashboard pages
- User data is fetched once per navigation (server-side)
- Client components handle interactivity (dropdown, tabs)
- Footer is consistent with marketing site for brand continuity
- Navigation is fixed (sticky) at top of page
