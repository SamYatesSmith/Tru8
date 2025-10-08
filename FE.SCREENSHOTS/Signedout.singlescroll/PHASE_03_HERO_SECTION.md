# Phase 3: Hero Section

**Status:** Not Started
**Estimated Time:** 30 minutes
**Dependencies:** Phase 2 (Auth modal functional)
**Backend Integration:** Auth modal triggers (no direct backend calls in this section)

---

## 🎯 Objectives

1. Create hero section with headline and subheadline
2. Add dual CTAs (Start Verifying Free + See How It Works)
3. Add trust indicators (3 icons with labels)
4. Ensure CTAs trigger auth modal and scroll
5. Match screenshot design exactly

---

## 📋 Task Checklist

- [ ] **Task 3.1:** Create hero section component
- [ ] **Task 3.2:** Add headline and subheadline with proper typography
- [ ] **Task 3.3:** Add dual CTAs with correct styling
- [ ] **Task 3.4:** Add 3 trust indicators below CTAs
- [ ] **Task 3.5:** Test CTA interactions (auth modal + scroll)

---

## 🔧 Implementation Steps

### **Task 3.1: Create Hero Section Component**

File: `web/components/marketing/hero-section.tsx`
```typescript
'use client';

import { CheckCircle, Clock, Users } from 'lucide-react';
import { useState } from 'react';
import { AuthModal } from '@/components/auth/auth-modal';

/**
 * Hero Section Component
 *
 * Main landing page hero with headline, CTAs, and trust indicators.
 *
 * Content:
 * - Headline: "Tru8"
 * - Subheadline: "Transparent Fact-Checking with Dated Evidence"
 * - Description: "Built for journalists, researchers, and content creators..."
 * - CTAs:
 *   - Primary: "Start Verifying Free" (orange, opens auth modal)
 *   - Secondary: "See How It Works" (outline, scrolls to #how-it-works)
 * - Trust Indicators:
 *   - Verified Sources (CheckCircle icon)
 *   - Real-time Results (Clock icon)
 *   - Professional Grade (Users icon)
 *
 * Backend Integration:
 * - "Start Verifying Free" triggers Clerk auth modal
 * - After auth: Redirects to /dashboard
 * - Backend auto-creates user with 3 free credits
 */
export function HeroSection() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const scrollToHowItWorks = () => {
    const element = document.getElementById('how-it-works');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <section
        id="hero"
        className="relative min-h-screen flex items-center justify-center pt-16 pb-20 px-4"
      >
        {/* Content Container */}
        <div className="max-w-4xl mx-auto text-center">
          {/* Headline */}
          <h1 className="text-6xl md:text-7xl font-bold text-white mb-6">
            Tru8
          </h1>

          {/* Subheadline */}
          <h2 className="text-3xl md:text-4xl font-semibold text-white mb-6">
            Transparent Fact-Checking with Dated Evidence
          </h2>

          {/* Description */}
          <p className="text-lg md:text-xl text-slate-300 mb-12 max-w-3xl mx-auto leading-relaxed">
            Built for journalists, researchers, and content creators who demand
            accuracy. Get instant verification with transparent, sourced
            evidence—not just answers, but proof you can cite.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            {/* Primary CTA - Opens Auth Modal */}
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="px-8 py-4 bg-[#f57a07] hover:bg-[#e06a00] text-white rounded-lg text-lg font-semibold transition-all hover:shadow-lg hover:shadow-[rgba(245,122,7,0.3)] min-w-[240px]"
            >
              Start Verifying Free
            </button>

            {/* Secondary CTA - Scroll to How It Works */}
            <button
              onClick={scrollToHowItWorks}
              className="px-8 py-4 bg-transparent border-2 border-slate-700 hover:border-[#f57a07] text-white rounded-lg text-lg font-semibold transition-all min-w-[240px]"
            >
              See How It Works
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8 text-sm">
            {/* Verified Sources */}
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Verified Sources</span>
            </div>

            {/* Real-time Results */}
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Real-time Results</span>
            </div>

            {/* Professional Grade */}
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#22d3ee]" />
              <span className="text-slate-400">Professional Grade</span>
            </div>
          </div>
        </div>
      </section>

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

### **Task 3.2: Typography Styling**

Already implemented in component above. Key points:

**Headline "Tru8":**
- Font size: `text-6xl md:text-7xl` (responsive)
- Font weight: `font-bold`
- Color: `text-white`

**Subheadline:**
- Font size: `text-3xl md:text-4xl`
- Font weight: `font-semibold`
- Color: `text-white`

**Description:**
- Font size: `text-lg md:text-xl`
- Color: `text-slate-300`
- Max width: `max-w-3xl` (centered)

---

### **Task 3.3: CTA Styling**

**Primary CTA ("Start Verifying Free"):**
- Background: `bg-[#f57a07]` (orange)
- Hover: `hover:bg-[#e06a00]` (darker orange)
- Shadow on hover: `hover:shadow-lg hover:shadow-[rgba(245,122,7,0.3)]` (orange glow)
- Text: `text-white`
- Padding: `px-8 py-4`
- Font: `text-lg font-semibold`

**Secondary CTA ("See How It Works"):**
- Background: `bg-transparent`
- Border: `border-2 border-slate-700`
- Hover: `hover:border-[#f57a07]`
- Text: `text-white`
- Padding: `px-8 py-4`
- Font: `text-lg font-semibold`

---

### **Task 3.4: Trust Indicators**

**Icons:** `lucide-react` (CheckCircle, Clock, Users)
- Size: `w-5 h-5`
- Color: `text-[#22d3ee]` (cyan-400)

**Labels:**
- Text: "Verified Sources", "Real-time Results", "Professional Grade"
- Color: `text-slate-400`
- Font: `text-sm`

**Layout:**
- Horizontal row on desktop
- Stack vertically on mobile (`flex-col sm:flex-row`)

---

### **Task 3.5: Add to Page**

File: `web/app/page.tsx`
```typescript
import { AnimatedBackground } from '@/components/marketing/animated-background';
import { Navigation } from '@/components/layout/navigation';
import { MobileBottomNav } from '@/components/layout/mobile-bottom-nav';
import { HeroSection } from '@/components/marketing/hero-section';

export default function Home() {
  return (
    <>
      {/* Animated Background */}
      <AnimatedBackground />

      {/* Navigation */}
      <Navigation />
      <MobileBottomNav />

      {/* Main Content */}
      <main>
        <HeroSection />

        {/* TODO: Other sections will be added in later phases */}
      </main>
    </>
  );
}
```

---

## ✅ Testing Checklist

### Visual Tests
- [ ] Headline "Tru8" displays correctly
- [ ] Subheadline displays on 2 lines (desktop) or wraps (mobile)
- [ ] Description text readable and centered
- [ ] CTAs aligned horizontally (desktop) or vertically (mobile)
- [ ] CTAs have correct colors (orange for primary, outline for secondary)
- [ ] Trust indicators display in row (desktop) or stack (mobile)
- [ ] Icons display correctly (cyan color)

### Interaction Tests
- [ ] Clicking "Start Verifying Free" opens auth modal
- [ ] Clicking "See How It Works" scrolls to how-it-works section
- [ ] Primary CTA hover shows orange glow shadow
- [ ] Secondary CTA hover changes border to orange
- [ ] Auth modal opens correctly from hero CTA

### Responsive Tests
- [ ] Hero section centered on all screen sizes
- [ ] Text readable on mobile (no overflow)
- [ ] CTAs stack vertically on mobile
- [ ] Trust indicators stack vertically on mobile
- [ ] Proper spacing on all breakpoints

---

## 🔗 Backend Integration

**No direct backend calls in hero section.**

**Indirect Integration:**
- "Start Verifying Free" CTA → Opens Clerk auth modal (from Phase 2)
- After auth: Clerk redirects to `/dashboard`
- Dashboard calls `GET /api/v1/users/me`
- Backend auto-creates user with 3 credits

---

## ✅ Definition of Done

- [ ] Hero section component created
- [ ] Headline, subheadline, and description display correctly
- [ ] Dual CTAs styled and functional
- [ ] "Start Verifying Free" triggers auth modal
- [ ] "See How It Works" scrolls to how-it-works section
- [ ] Trust indicators display with correct icons and labels
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] No console errors or warnings
- [ ] Component documented with JSDoc comments
- [ ] All files committed with detailed message

---

## 📝 Commit Message Template

```
[Phase 3] Add Hero Section with CTAs and trust indicators

Hero Section:
- Created hero component with centered layout
- Headline: "Tru8" (large bold)
- Subheadline: "Transparent Fact-Checking with Dated Evidence"
- Description paragraph with brand messaging

CTAs:
- Primary: "Start Verifying Free" (orange bg, triggers auth modal)
- Secondary: "See How It Works" (outline, scrolls to #how-it-works)
- Hover states: Orange glow shadow (primary), orange border (secondary)
- Mobile: CTAs stack vertically

Trust Indicators:
- 3 indicators: Verified Sources, Real-time Results, Professional Grade
- Icons: CheckCircle, Clock, Users (cyan-400 color)
- Labels: slate-400 text
- Layout: Horizontal row (desktop), vertical stack (mobile)

Backend Integration:
- "Start Verifying Free" → Clerk auth modal → /dashboard
- No direct backend calls in this component

Files created:
- components/marketing/hero-section.tsx

Files modified:
- app/page.tsx (added HeroSection component)

Testing performed:
- ✅ Hero section displays correctly
- ✅ CTAs trigger correct actions (auth modal, scroll)
- ✅ Trust indicators display correctly
- ✅ Responsive design works on all breakpoints
```

---

## 🎯 Next Phase

**Phase 4:** Content Sections (How Tru8 Works + Carousel + Video)

**Dependencies from Phase 3:**
- Hero section complete ✅
- Auth modal functional ✅
- Smooth scroll working ✅

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Estimated Completion:** 30 minutes
