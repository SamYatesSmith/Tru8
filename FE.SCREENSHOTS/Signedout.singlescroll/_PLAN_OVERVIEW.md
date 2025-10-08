# Signed-Out Marketing Page - Implementation Plan Overview

**Project:** Tru8 Frontend - Marketing Landing Page
**Status:** Planning Complete - Ready for Implementation
**Started:** October 7, 2025
**Target Completion:** 3 days (7 phases)

---

## 📋 Implementation Progress

### Phase Status
- [ ] **Phase 1:** Foundation & Authentication (0/6 tasks) - _Not Started_
- [ ] **Phase 2:** Navigation (0/6 tasks) - _Not Started_
- [ ] **Phase 3:** Hero Section (0/4 tasks) - _Not Started_
- [ ] **Phase 4:** Content Sections (0/7 tasks) - _Not Started_
- [ ] **Phase 5:** Pricing (0/6 tasks) - _Not Started_
- [ ] **Phase 6:** Footer (0/3 tasks) - _Not Started_
- [ ] **Phase 7:** Responsive & Polish (0/5 tasks) - _Not Started_

**Overall Progress:** 0/37 tasks (0%)

---

## 🎯 Page Structure Overview

### Single-Scroll Marketing Page Sections

1. **Navigation Bar**
   - **Desktop:** Top sticky navbar with logo, menu, Sign In/Get Started buttons
   - **Mobile:** Bottom fixed navbar with icons + labels (Sparkles, Info, CreditCard, User)
   - Logo: Tru8 "8" icon
   - Menu: Features, How It Works, Pricing
   - Auth: Sign In / Get Started (triggers Clerk modal with tabs)

2. **Animated Background**
   - 3-layer parallax pixel grid
   - Ascending animation (60s, 80s, 100s cycles)
   - Colors: slate-300, slate-400, slate-500, stone-300, orange accents
   - Sizes: Various (8-16px squares)
   - Reduced motion support included

3. **Hero Section**
   - Main headline: "Tru8 - Transparent Fact-Checking with Dated Evidence"
   - Subheadline
   - Dual CTAs: "Start Verifying Free" (orange) + "See How It Works" (outline)
   - Trust indicators: 3 icons with labels

4. **How Tru8 Works**
   - 3 process steps with icons
   - Submit Content → AI Verification → Get Results

5. **Professional Fact-Checking Tools** (Carousel)
   - 6 feature cards (rollerdeck style, 3D perspective)
   - Auto-play: 5 seconds
   - Manual controls (left/right arrows)
   - Center card: 100% opacity, scaled 1.0
   - Adjacent cards: 70% opacity, scaled 0.85
   - Far cards: 40% opacity, scaled 0.7
   - Features:
     1. Multi-Source Verification
     2. Article Analysis
     3. Dated Evidence
     4. Source Credibility
     5. Confidence Scoring
     6. Global Coverage

6. **See Tru8 in Action**
   - Video placeholder with play button
   - "Demo video coming soon" text

7. **Choose Your Plan**
   - 2 pricing cards: Free vs Professional
   - **Free:** £0, 3 checks, basic features, "START FREE TRIAL" CTA
   - **Professional:** £7/month, 40 checks, advanced features, "GET STARTED" CTA (Most Popular badge)

8. **Footer**
   - Logo + tagline
   - Product links: Features, How It Works, Pricing
   - Company links: About, Blog, Contact
   - Legal: Privacy Policy, Terms of Service, Cookie Policy
   - Copyright: © 2025 Tru8

---

## 🔗 Backend Integration Points

### Authentication (Clerk)
- **Sign In/Get Started Buttons** → Opens Clerk modal → Redirects to `/dashboard`
- **Modal Style:** Tru8-branded (dark background `#1a1f2e`, orange accents `#f57a07`)
- **Modal Type:** Single modal with Sign In / Sign Up tabs
- **After Auth:** User redirected to `/dashboard`, backend auto-creates user

### User Auto-Creation
- **Endpoint:** `GET /api/v1/users/me`
- **Backend Auto-creates User:**
  ```python
  User(
    id=clerk_user_id,
    email=clerk_email,
    name=clerk_name,
    credits=3  # Free tier
  )
  ```
- **Flow:** Clerk auth → JWT token → `/users/me` call → User created → Dashboard loads

### Pricing - Free Plan
- **CTA:** "START FREE TRIAL"
- **Action:** Opens Clerk modal → Sign up → Redirect to `/dashboard`
- **Backend:** User gets 3 free credits automatically (no payment)

### Pricing - Professional Plan
- **CTA:** "GET STARTED"
- **Action:** Opens Clerk modal → Sign up → Redirect to Stripe checkout
- **Endpoint:** `POST /api/v1/payments/create-checkout-session`
- **Request Body:**
  ```json
  {
    "price_id": "price_xxx",
    "plan": "professional"
  }
  ```
- **Flow:** Auth → Create checkout session → Stripe → Webhook creates subscription → Dashboard

### Static Sections (No Backend)
- Animated background (pure CSS)
- Hero section
- How Tru8 Works
- Professional Tools carousel
- See Tru8 in Action
- Footer (links only)

---

## 🎨 Design Specifications

### Color Palette (from COLOR_PALETTE_GUIDE.md)

**Primary Colors:**
- **Orange:** `#f57a07` (CTAs, active states, accents)
- **Orange Hover:** `#e06a00`
- **Cyan:** `#22d3ee` (cyan-400) (secondary accents, icons, highlights)

**Backgrounds:**
- **Page:** Animated pixel grid (slate/stone tones)
- **Cards:** `rgba(30, 41, 59, 0.8)` (semi-transparent dark blue)
- **Navbar Mobile:** `#1a1f2e`
- **Footer:** `#151823`

**Text:**
- **Primary:** `white`
- **Secondary:** `slate-300`
- **Tertiary:** `slate-400`

**Borders:**
- **Primary:** `slate-700`
- **Secondary:** `slate-600`

**Pixel Grid Colors (Background):**
- `slate-300` (#cbd5e1)
- `slate-400` (#94a3b8)
- `slate-500` (#64748b)
- `stone-300` (#d6d3d1)
- `#f57a07` (orange accent pixels - sparse)

### Animated Background Specifications
- **Type:** Multi-layer CSS parallax
- **Layers:** 3 layers
- **Layer 1 (Back):** 100s cycle, 30% opacity, slowest
- **Layer 2 (Middle):** 80s cycle, 20% opacity
- **Layer 3 (Front):** 60s cycle, 10% opacity, fastest
- **Animation:** Continuous upward scroll (`translateY`)
- **Accessibility:** `@media (prefers-reduced-motion: reduce)` disables animation
- **Pixel Sizes:** Mix of 8px, 12px, 16px squares
- **Pattern:** Seamless tiling (2x viewport height)

### Mobile Bottom Navigation
- **Position:** Fixed at bottom of screen
- **Display:** `< 768px` only
- **Background:** `#1a1f2e`
- **Border:** Top border `slate-700`
- **Items:** 4 navigation items
  - **Features:** `Sparkles` icon + "Features" text
  - **How It Works:** `Info` icon + "How It Works" text
  - **Pricing:** `CreditCard` icon + "Pricing" text
  - **Sign In:** `User` icon + "Sign In" text
- **Active State:** Orange icon color + orange underline
- **Icon Size:** 20px
- **Text Size:** 12px
- **Spacing:** Evenly distributed

---

## 📱 Responsive Design

### Breakpoints
- **Mobile:** `< 768px` (bottom nav, vertical stacks)
- **Tablet:** `768px - 1024px` (2-column layouts)
- **Desktop:** `> 1024px` (full layouts)

### Mobile Adaptations (`< 768px`)
- **Navigation:** Bottom fixed navbar (not hamburger)
- **Hero CTAs:** Stack vertically
- **How It Works:** 3 cards → vertical stack
- **Carousel:** 3 visible cards → 1 card visible, swipeable
- **Pricing:** 2 cards side-by-side → vertical stack
- **Footer:** Links stack vertically

### Tablet Adaptations (`768px - 1024px`)
- **Navigation:** Top navbar (same as desktop)
- **Carousel:** 2 cards visible
- **Pricing:** 2 cards side-by-side (smaller)

---

## 🚀 Implementation Strategy

### Day 1: Foundation + Core Sections (4.5 hours)
- **Phase 1:** Next.js setup, Clerk integration, API client, animated background (2.5 hours)
- **Phase 2:** Desktop + mobile navigation with auth modal (1.5 hours)
- **Phase 3:** Hero section (30 minutes)

### Day 2: Content + Pricing (5 hours)
- **Phase 4:** How It Works + Carousel + Video (3 hours)
- **Phase 5:** Pricing with Stripe integration (2 hours)

### Day 3: Polish + Testing (2.5 hours)
- **Phase 6:** Footer (30 minutes)
- **Phase 7:** Responsive design + Accessibility (2 hours)

**Total Estimated Time:** ~12 hours over 3 days

---

## ✅ Testing Checklist

### Backend Integration Tests
- [ ] Clerk Sign In modal opens correctly
- [ ] Clerk Sign Up modal opens with tabs
- [ ] Tab switching works (Sign In ↔ Sign Up)
- [ ] JWT token received after authentication
- [ ] Redirect to `/dashboard` after auth succeeds
- [ ] User auto-created in backend (verify with database query)
- [ ] Free plan CTA creates user with 3 credits
- [ ] Professional plan CTA creates Stripe checkout session
- [ ] Stripe checkout redirects correctly
- [ ] Stripe webhook creates subscription (test mode)

### UI/UX Tests
- [ ] Desktop navigation smooth scrolls to sections
- [ ] Mobile bottom navigation smooth scrolls to sections
- [ ] Mobile bottom nav highlights active section
- [ ] Carousel auto-plays every 5 seconds
- [ ] Carousel manual controls work (left/right)
- [ ] Carousel rollerdeck effect displays correctly (3D perspective)
- [ ] All CTAs trigger correct actions
- [ ] Background animation runs smoothly (60fps)
- [ ] Reduced motion setting disables animation
- [ ] Mobile responsive on iPhone/Android
- [ ] Tablet responsive on iPad
- [ ] Desktop layout matches screenshots exactly

### Accessibility Tests
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Screen reader announces all sections correctly
- [ ] Focus states visible on all interactive elements
- [ ] Color contrast meets WCAG AA standards
- [ ] All images have alt text
- [ ] Carousel controls keyboard accessible
- [ ] Reduced motion preference respected
- [ ] Bottom nav icons have aria-labels

### Performance Tests
- [ ] Lighthouse Performance > 90
- [ ] Lighthouse Accessibility > 95
- [ ] No console errors or warnings
- [ ] Background animation doesn't impact FPS
- [ ] Page load time < 2 seconds
- [ ] Mobile smooth scrolling (no janky)

---

## 📝 Git Commit Strategy

Each phase = 1 commit with detailed message including backend context.

**Commit Message Format:**
```
[Phase X] Add [Component Name] with [Backend Integration]

- Component details
- Backend endpoint(s) used
- Testing performed
- Related files modified
```

**Example:**
```
[Phase 2] Add Navigation (Desktop + Mobile) with Clerk authentication modal

- Created Navigation component with desktop top bar and mobile bottom bar
- Integrated Clerk SignIn/SignUp modal (Tru8-styled, tabbed)
- Configured redirect to /dashboard after auth
- Tested: Modal opens, tabs switch, auth succeeds, redirect works
- Files:
  - components/layout/navigation.tsx
  - components/layout/mobile-bottom-nav.tsx
  - components/auth/auth-modal.tsx
  - app/layout.tsx
```

---

## 📊 Success Criteria

### Functional Requirements
- [ ] All 8 sections render correctly
- [ ] Animated background runs smoothly
- [ ] Desktop and mobile navigation work
- [ ] Clerk authentication flow works end-to-end
- [ ] Free plan signup creates user with 3 credits
- [ ] Professional plan signup redirects to Stripe
- [ ] Smooth scrolling navigation works (desktop + mobile)
- [ ] Carousel auto-plays and manual controls work
- [ ] Mobile/tablet responsive design works
- [ ] All links route correctly

### Quality Requirements
- [ ] No console errors or warnings
- [ ] Lighthouse score: Performance > 90
- [ ] Lighthouse score: Accessibility > 95
- [ ] Matches design screenshots pixel-perfectly
- [ ] Colors only used as shown in screenshots
- [ ] Clean, readable code with comments
- [ ] Background animation doesn't cause performance issues

### Documentation Requirements
- [ ] Each component has JSDoc comments
- [ ] Backend integration documented in component
- [ ] README updated with setup instructions
- [ ] All phases committed with detailed messages
- [ ] Plan overview updated after each phase

---

## 📁 File Structure

```
web/
├── app/
│   ├── layout.tsx                    # Root layout with Clerk provider
│   ├── page.tsx                      # Marketing landing page
│   └── globals.css                   # Global styles + Tru8 colors + animations
├── components/
│   ├── layout/
│   │   ├── navigation.tsx            # Desktop navbar
│   │   ├── mobile-bottom-nav.tsx     # Mobile bottom navigation
│   │   └── footer.tsx                # Footer with links
│   ├── marketing/
│   │   ├── animated-background.tsx   # 3-layer pixel grid animation
│   │   ├── hero-section.tsx          # Hero with CTAs
│   │   ├── how-it-works.tsx          # 3-step process
│   │   ├── feature-carousel.tsx      # 6-item rollerdeck carousel
│   │   ├── video-demo.tsx            # Video placeholder
│   │   └── pricing-cards.tsx         # Free + Pro plans
│   ├── ui/
│   │   ├── button.tsx                # Reusable button component
│   │   ├── dialog.tsx                # Modal wrapper for Clerk
│   │   └── card.tsx                  # Card component
│   └── auth/
│       └── auth-modal.tsx            # Tru8-styled Clerk modal with tabs
├── lib/
│   ├── api.ts                        # Backend API client
│   ├── utils.ts                      # Utility functions
│   └── pixel-grid-generator.ts       # Generate seamless pixel grid pattern
├── public/
│   └── pixel-grid/
│       ├── layer-1.png               # Back layer (slowest)
│       ├── layer-2.png               # Middle layer
│       └── layer-3.png               # Front layer (fastest)
├── middleware.ts                     # Clerk middleware (public routes)
├── package.json
├── next.config.js
└── tailwind.config.ts               # Tru8 color system
```

---

## 🔄 Latest Updates

**[October 7, 2025 - 16:30]**
- ✅ Planning phase completed
- ✅ All 7 phase plans created
- ✅ Backend integration points identified
- ✅ Color palette confirmed (COLOR_PALETTE_GUIDE.md)
- ✅ Mobile bottom navigation specified (not hamburger)
- ✅ Animated background approach confirmed (multi-layer CSS parallax)
- ✅ Responsive strategy defined
- ✅ Icon choices confirmed (Option A: Sparkles, Info, CreditCard, User)
- ✅ Reduced motion accessibility approved
- ⏳ Ready to begin Phase 1 implementation

---

## 🎯 Next Steps

1. ✅ **Review all 7 phase plans** in this directory
2. **Approve Phase 1 plan** to begin implementation
3. **I implement Phase 1** (Foundation, Clerk, API client, Animated background)
4. **Test Phase 1** with backend
5. **Commit Phase 1** with detailed message
6. **Update this overview** with progress checkboxes
7. **Move to Phase 2** after approval

---

## 📖 Phase Plan Files

- ✅ `_PLAN_OVERVIEW.md` - This file (master tracker)
- ⏳ `PHASE_01_FOUNDATION_AUTH.md` - Next.js setup, Clerk integration, API client, Animated background
- ⏳ `PHASE_02_NAVIGATION.md` - Desktop navbar + Mobile bottom nav, Auth modal
- ⏳ `PHASE_03_HERO_SECTION.md` - Hero headline, CTAs, trust indicators
- ⏳ `PHASE_04_CONTENT_SECTIONS.md` - How It Works, Carousel, Video demo
- ⏳ `PHASE_05_PRICING.md` - Free/Pro pricing cards, Stripe integration
- ⏳ `PHASE_06_FOOTER.md` - Footer navigation, legal links
- ⏳ `PHASE_07_RESPONSIVE_POLISH.md` - Mobile/tablet responsive, accessibility, reduced motion

---

**Status:** 📋 Planning Complete - Awaiting Implementation Approval
**Current Phase:** None (Pre-implementation)
**Next Action:** Review Phase 1 plan and approve to start
**Estimated Completion:** 3 days (12 hours total)
