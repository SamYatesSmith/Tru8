# Phase 2: Navigation (Desktop + Mobile)

**Status:** Not Started
**Estimated Time:** 1.5 hours
**Dependencies:** Phase 1 (Clerk authentication configured)
**Backend Integration:** Clerk modal triggers authentication, redirects to `/dashboard`

---

## 🎯 Objectives

1. Create desktop top navigation bar (sticky)
2. Create mobile bottom navigation bar (fixed)
3. Implement Tru8-styled Clerk authentication modal with tabs
4. Add smooth scroll navigation to page sections
5. Test auth modal and redirect flow
6. Ensure navigation highlights active section

---

## 📋 Task Checklist

- [ ] **Task 2.1:** Create desktop navigation component
- [ ] **Task 2.2:** Create mobile bottom navigation component
- [ ] **Task 2.3:** Create Tru8-styled Clerk auth modal with tabs
- [ ] **Task 2.4:** Implement smooth scroll to sections
- [ ] **Task 2.5:** Add active section highlighting
- [ ] **Task 2.6:** Test auth flow and navigation

---

## 🔧 Implementation Steps

### **Task 2.1: Create Desktop Navigation**

File: `web/components/layout/navigation.tsx`
```typescript
'use client';

import Link from 'next/link';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Desktop Navigation Component
 *
 * Top sticky navbar with smooth scroll to sections.
 *
 * Desktop only (>= 768px).
 * On mobile, hidden and replaced by bottom nav.
 *
 * Sections:
 * - Features → #features (Professional Fact-Checking Tools)
 * - How It Works → #how-it-works
 * - Pricing → #pricing
 *
 * CTAs:
 * - Sign In → Opens Clerk auth modal
 * - Get Started → Opens Clerk auth modal (same as Sign In)
 */
export function Navigation() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <nav className="hidden md:block fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e]/95 backdrop-blur-sm border-b border-slate-700">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <div className="text-3xl font-bold text-white">8</div>
              <span className="text-xl font-semibold text-white">Tru8</span>
            </Link>

            {/* Navigation Links */}
            <div className="flex items-center gap-8">
              <button
                onClick={() => scrollToSection('features')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
              >
                FEATURES
              </button>
              <button
                onClick={() => scrollToSection('how-it-works')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
              >
                HOW IT WORKS
              </button>
              <button
                onClick={() => scrollToSection('pricing')}
                className="text-slate-300 hover:text-[#f57a07] transition-colors text-sm font-medium"
              >
                PRICING
              </button>
            </div>

            {/* Auth CTAs */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="text-white hover:text-[#f57a07] transition-colors text-sm font-medium"
              >
                Sign In
              </button>
              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="px-6 py-2 bg-[#4a90e2] hover:bg-[#357abd] text-white rounded-md text-sm font-medium transition-colors"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
```

---

### **Task 2.2: Create Mobile Bottom Navigation**

File: `web/components/layout/mobile-bottom-nav.tsx`
```typescript
'use client';

import { useState } from 'react';
import { Sparkles, Info, CreditCard, User } from 'lucide-react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Mobile Bottom Navigation Component
 *
 * Fixed at bottom of screen on mobile only (< 768px).
 *
 * Navigation Items:
 * - Features (Sparkles icon) → Scrolls to #features
 * - How It Works (Info icon) → Scrolls to #how-it-works
 * - Pricing (CreditCard icon) → Scrolls to #pricing
 * - Sign In (User icon) → Opens Clerk auth modal
 *
 * Active State:
 * - Orange icon color (#f57a07)
 * - Orange bottom border
 *
 * Design:
 * - Background: #1a1f2e
 * - Border top: slate-700
 * - Icon size: 20px
 * - Text size: 12px
 * - Evenly distributed spacing
 */
export function MobileBottomNav() {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(sectionId);
    }
  };

  const navItems = [
    {
      id: 'features',
      label: 'Features',
      icon: Sparkles,
      onClick: () => scrollToSection('features'),
    },
    {
      id: 'how-it-works',
      label: 'How It Works',
      icon: Info,
      onClick: () => scrollToSection('how-it-works'),
    },
    {
      id: 'pricing',
      label: 'Pricing',
      icon: CreditCard,
      onClick: () => scrollToSection('pricing'),
    },
    {
      id: 'sign-in',
      label: 'Sign In',
      icon: User,
      onClick: () => setIsAuthModalOpen(true),
    },
  ];

  return (
    <>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#1a1f2e] border-t border-slate-700">
        <div className="grid grid-cols-4 h-16">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                onClick={item.onClick}
                className="flex flex-col items-center justify-center gap-1 relative"
                aria-label={item.label}
              >
                {/* Active indicator (orange bottom border) */}
                {isActive && (
                  <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
                )}

                {/* Icon */}
                <Icon
                  className={`w-5 h-5 ${
                    isActive ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                />

                {/* Label */}
                <span
                  className={`text-xs ${
                    isActive ? 'text-[#f57a07]' : 'text-slate-400'
                  }`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
```

---

### **Task 2.3: Create Tru8-Styled Clerk Auth Modal**

File: `web/components/auth/auth-modal.tsx`
```typescript
'use client';

import { SignIn, SignUp } from '@clerk/nextjs';
import { useState } from 'react';
import { X } from 'lucide-react';

/**
 * Tru8-Styled Clerk Authentication Modal
 *
 * Single modal with Sign In / Sign Up tabs.
 *
 * Styling:
 * - Dark background (#1a1f2e)
 * - Orange accents (#f57a07)
 * - Matches Tru8 brand
 *
 * Behavior:
 * - Opens when Sign In or Get Started clicked
 * - Tabs allow switching between Sign In ↔ Sign Up
 * - After auth: Redirects to /dashboard (configured in .env)
 * - Backend: User auto-created via GET /api/v1/users/me on first login
 *
 * Backend Integration:
 * - Clerk provides JWT token
 * - Frontend uses token to call /api/v1/users/me
 * - Backend auto-creates user with 3 credits
 */
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop - Dark opaque */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative bg-[#1a1f2e] rounded-lg border border-slate-700 p-6 max-w-md w-full mx-4 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('signin')}
            className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
              activeTab === 'signin'
                ? 'text-[#f57a07]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
            {activeTab === 'signin' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('signup')}
            className={`pb-2 px-1 text-sm font-medium transition-colors relative ${
              activeTab === 'signup'
                ? 'text-[#f57a07]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign Up
            {activeTab === 'signup' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f57a07]" />
            )}
          </button>
        </div>

        {/* Clerk Components with Custom Styling */}
        <div className="clerk-modal-content">
          {activeTab === 'signin' ? (
            <SignIn
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-[#f57a07] hover:bg-[#e06a00] text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-white',
                  headerSubtitle: 'text-slate-300',
                  socialButtonsBlockButton:
                    'border-slate-700 text-white hover:bg-slate-800',
                  formFieldInput:
                    'bg-[#1a1f2e] border-slate-700 text-white focus:border-[#f57a07]',
                  formFieldLabel: 'text-slate-300',
                  footerActionLink: 'text-[#f57a07] hover:text-[#e06a00]',
                },
              }}
              redirectUrl="/dashboard"
            />
          ) : (
            <SignUp
              appearance={{
                elements: {
                  formButtonPrimary:
                    'bg-[#f57a07] hover:bg-[#e06a00] text-white font-medium',
                  card: 'bg-transparent shadow-none',
                  headerTitle: 'text-white',
                  headerSubtitle: 'text-slate-300',
                  socialButtonsBlockButton:
                    'border-slate-700 text-white hover:bg-slate-800',
                  formFieldInput:
                    'bg-[#1a1f2e] border-slate-700 text-white focus:border-[#f57a07]',
                  formFieldLabel: 'text-slate-300',
                  footerActionLink: 'text-[#f57a07] hover:text-[#e06a00]',
                },
              }}
              redirectUrl="/dashboard"
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

**Add Clerk Component Styling:**

File: `web/app/globals.css` (append)
```css
/* Clerk Modal Custom Styling */
.clerk-modal-content {
  /* Remove Clerk's default card styling */
}

.clerk-modal-content .cl-card {
  background: transparent !important;
  box-shadow: none !important;
}

.clerk-modal-content .cl-formButtonPrimary {
  background: #f57a07 !important;
}

.clerk-modal-content .cl-formButtonPrimary:hover {
  background: #e06a00 !important;
}
```

---

### **Task 2.4: Implement Smooth Scroll**

Already implemented in navigation components using `scrollIntoView({ behavior: 'smooth' })`.

**Add Section IDs to Page:**

File: `web/app/page.tsx` (example structure)
```typescript
export default function Home() {
  return (
    <main>
      <section id="hero">{/* Hero Section */}</section>
      <section id="how-it-works">{/* How Tru8 Works */}</section>
      <section id="features">{/* Professional Fact-Checking Tools */}</section>
      <section id="pricing">{/* Choose Your Plan */}</section>
    </main>
  );
}
```

---

### **Task 2.5: Active Section Highlighting**

**Desktop:** Hover states (already implemented in Task 2.1)

**Mobile:** Use Intersection Observer to detect active section:

File: `web/components/layout/mobile-bottom-nav.tsx` (update)
```typescript
// Add Intersection Observer to detect visible section
useEffect(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveSection(entry.target.id);
        }
      });
    },
    { threshold: 0.5 } // Section is active when 50% visible
  );

  const sections = ['features', 'how-it-works', 'pricing'];
  sections.forEach((id) => {
    const element = document.getElementById(id);
    if (element) observer.observe(element);
  });

  return () => observer.disconnect();
}, []);
```

---

### **Task 2.6: Test Auth Flow and Navigation**

#### **Test 1: Desktop Navigation**

1. Run dev server: `npm run dev`
2. Open: `http://localhost:3000`
3. Verify:
   - [ ] Desktop nav visible on desktop (>= 768px)
   - [ ] Clicking "FEATURES" scrolls to features section
   - [ ] Clicking "HOW IT WORKS" scrolls to how-it-works section
   - [ ] Clicking "PRICING" scrolls to pricing section
   - [ ] Smooth scroll animation works
   - [ ] Hover states show orange color

#### **Test 2: Mobile Navigation**

1. Open Chrome DevTools, switch to mobile view
2. Verify:
   - [ ] Bottom nav visible on mobile (< 768px)
   - [ ] 4 items evenly distributed
   - [ ] Icons displayed correctly (Sparkles, Info, CreditCard, User)
   - [ ] Clicking each item scrolls to correct section
   - [ ] Active section highlighted with orange color + border
   - [ ] Intersection Observer updates active section on scroll

#### **Test 3: Auth Modal**

1. Click "Sign In" or "Get Started"
2. Verify:
   - [ ] Modal opens with dark background
   - [ ] Background is darkened and blurred
   - [ ] Tabs visible (Sign In / Sign Up)
   - [ ] Clicking tabs switches between forms
   - [ ] Clerk forms styled with orange accents
   - [ ] Close button (X) closes modal
   - [ ] Clicking backdrop closes modal

#### **Test 4: Auth Flow End-to-End**

1. Click "Sign In"
2. Enter test credentials
3. Submit form
4. Verify:
   - [ ] Clerk authenticates successfully
   - [ ] JWT token received (check Network tab)
   - [ ] Redirects to `/dashboard`
   - [ ] Backend called `/api/v1/users/me` (check Network tab)
   - [ ] User created in database with 3 credits (verify with psql)

---

## 🔗 Backend Integration Details

### Authentication Flow

1. **User clicks "Sign In" or "Get Started"**
   - Opens Clerk modal

2. **User enters credentials and submits**
   - Clerk handles authentication
   - Clerk issues JWT token

3. **Clerk redirects to `/dashboard`**
   - Set in `.env`: `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard`

4. **Dashboard calls `GET /api/v1/users/me`**
   - API client automatically injects JWT token
   - Backend verifies token
   - Backend auto-creates user if doesn't exist:
     ```python
     User(
       id=clerk_user_id,
       email=clerk_email,
       credits=3
     )
     ```

5. **User sees dashboard with 3 credits**

---

## ✅ Definition of Done

- [ ] Desktop navigation component created and styled
- [ ] Mobile bottom navigation component created and styled
- [ ] Auth modal component created with Clerk integration
- [ ] Tab switching works (Sign In ↔ Sign Up)
- [ ] Smooth scroll to sections works on both desktop and mobile
- [ ] Active section highlighting works on mobile
- [ ] Clerk forms styled with Tru8 colors (orange accents)
- [ ] Auth flow tested end-to-end
- [ ] User auto-creation verified in database
- [ ] No console errors or warnings
- [ ] All components responsive
- [ ] All files committed with detailed message

---

## 📝 Commit Message Template

```
[Phase 2] Add Navigation (Desktop + Mobile) with Clerk authentication modal

Desktop Navigation:
- Created sticky top navbar (hidden on mobile)
- Logo + 3 menu items (Features, How It Works, Pricing)
- Smooth scroll to sections on click
- Sign In + Get Started CTAs trigger auth modal
- Hover states with orange color (#f57a07)

Mobile Bottom Navigation:
- Created fixed bottom navbar (< 768px only)
- 4 items: Features (Sparkles), How It Works (Info), Pricing (CreditCard), Sign In (User)
- Icons from lucide-react (20px size)
- Active section highlighted with orange icon + top border
- Intersection Observer tracks active section on scroll

Tru8-Styled Auth Modal:
- Single modal with Sign In / Sign Up tabs
- Dark background (#1a1f2e), orange accents (#f57a07)
- Clerk components styled to match Tru8 brand
- Close button + backdrop click to close
- Tab switching works smoothly

Clerk Integration:
- Configured redirectUrl: /dashboard
- JWT token injection via API client
- Tested: Auth succeeds, token received, user redirected

Backend Integration:
- Verified GET /api/v1/users/me called after auth
- Confirmed user auto-creation with 3 credits
- Tested in database: User record created successfully

Files created:
- components/layout/navigation.tsx
- components/layout/mobile-bottom-nav.tsx
- components/auth/auth-modal.tsx

Files modified:
- app/globals.css (Clerk styling)
- app/page.tsx (section IDs for smooth scroll)

Testing performed:
- ✅ Desktop navigation smooth scrolls work
- ✅ Mobile bottom nav displays correctly
- ✅ Active section highlighting works
- ✅ Auth modal opens and closes
- ✅ Tab switching works
- ✅ Clerk auth succeeds
- ✅ User auto-created in backend
```

---

## 🎯 Next Phase

**Phase 3:** Hero Section

**Dependencies from Phase 2:**
- Navigation components ready ✅
- Auth modal functional ✅
- Smooth scroll working ✅

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Estimated Completion:** 1.5 hours
