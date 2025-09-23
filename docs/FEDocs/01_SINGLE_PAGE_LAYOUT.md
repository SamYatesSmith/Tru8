# 01. Single-Page Layout - Marketing Experience (Track A)

## 🎯 Objective
Transform the homepage into a conversion-optimized, scrollable single-page marketing experience **for signed-out users only**, with smooth anchor navigation and compelling content flow inspired by Reflect.app's seamless user experience.

## 🔀 Dual-Track Context
**This document applies to Track A (Marketing) only**
- **Signed-out users**: Get full marketing experience with single-page scroll
- **Signed-in users**: Skip marketing entirely - redirect to dashboard or show app-focused content

## 🚨 Backend Compatibility Warning
**CRITICAL: This is a functional project with working backend integrations**
- ✅ **Safe**: Homepage layout changes, marketing content organization
- ⚠️ **Test Required**: Authentication routing (preserve Clerk token handling)
- ❌ **Forbidden**: Modifying `/dashboard` route, API calls, user data flows
- **Must preserve**: All existing dashboard functionality, fact-check creation, SSE progress tracking

## 📊 Current State Analysis

### Existing Homepage Structure (web/app/page.tsx)
```tsx
<MainLayout>
  <section className="hero-section">         // Hero with CTA
  <section className="py-24 bg-white">       // Features (3x2 grid)
  <section className="py-16 bg-gray-100">    // CTA section
</MainLayout>
```

### Current Navigation (web/components/layout/navigation.tsx)
- Two-pill system with hover reveal
- Links to separate pages: /dashboard, /checks/new, /pricing, /account, /settings
- Fixed positioning with proper z-index management

## 🎨 Reflect.app Inspiration

### Key Elements to Implement
1. **Smooth scrolling navigation** - Links scroll to page sections instead of routing
2. **Section-based content** - Organize content into logical scrollable sections
3. **Visual continuity** - Seamless flow between sections
4. **Anchor-based URLs** - Enable direct linking to sections (#hero, #features, #pricing)

## 🏗️ Implementation Strategy

### Phase 1A: Authentication-Based Routing
**Implement conditional homepage experience (CLIENT-SIDE RENDERING):**

```tsx
// Core routing logic in web/app/page.tsx
'use client';

import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const { isSignedIn, isLoaded } = useUser();
  const router = useRouter();

  useEffect(() => {
    // Track B: Signed-in users redirect to dashboard
    if (isLoaded && isSignedIn) {
      router.push('/dashboard');
    }
  }, [isSignedIn, isLoaded, router]);

  // Show loading state during auth check
  if (!isLoaded) {
    return <LoadingSpinner />;
  }

  // Track A: Signed-out users get marketing experience
  if (!isSignedIn) {
    return <MarketingHomepage />;
  }

  // Prevent flash during redirect
  return <LoadingSpinner />;
}
```

**Alternative Approach (Server-Side with Middleware):**
```tsx
// Better: Handle in middleware.ts
const isPublicRoute = createRouteMatcher([
  "/",
  "/api/health",
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

export default clerkMiddleware((auth, req) => {
  const { userId } = auth();

  // Redirect signed-in users from homepage to dashboard
  if (userId && req.nextUrl.pathname === '/') {
    return NextResponse.redirect(new URL('/dashboard', req.url));
  }

  if (!isPublicRoute(req)) auth().protect();
});
```

### Phase 1B: Marketing Section Organization
**Create conversion-optimized marketing flow for signed-out users:**

```tsx
// Marketing homepage structure (Track A only)
function MarketingHomepage() {
  return (
    <MainLayout>
      <section id="hero" className="hero-section">
        // Compelling hero with product demo + sign-up CTAs
      </section>

      <section id="features" className="features-section">
        // 4x2 feature grid showcasing all benefits
      </section>

      <section id="how-it-works" className="process-section">
        // Step-by-step fact-checking process demonstration
      </section>

      <section id="pricing" className="pricing-section">
        // Clear pricing tiers with conversion focus
      </section>

      <section id="testimonials" className="testimonials-section">
        // Social proof and credibility indicators
      </section>

      <section id="cta" className="cta-section">
        // Final conversion push with multiple sign-up options
      </section>
    </MainLayout>
  );
}
```

### Phase 1C: Marketing Navigation System
**Navigation anchors for marketing sections only:**

```tsx
// Marketing navigation (signed-out users only)
const marketingNavItems = [
  { name: "Features", href: "#features", type: "anchor" },
  { name: "How it Works", href: "#how-it-works", type: "anchor" },
  { name: "Pricing", href: "#pricing", type: "anchor" },
  { name: "Testimonials", href: "#testimonials", type: "anchor" },
];

// App navigation handled separately (see 02_THREE_PART_NAVIGATION.md)
```

### Phase 1D: Smooth Scrolling Implementation
**Add smooth scrolling behavior:**

```css
/* Add to globals.css */
html {
  scroll-behavior: smooth;
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}
```

## 🛠️ Technical Implementation

### 1. Homepage Transformation (web/app/page.tsx)

#### Current Structure Preservation
- Keep existing hero section intact
- Enhance features section with better grid layout
- Add new sections for complete experience

#### New Sections to Add

**How It Works Section:**
```tsx
<section id="how-it-works" className="py-24 bg-gray-50">
  <div className="container">
    <h2 className="text-4xl font-bold text-center mb-16">How Tru8 Works</h2>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {processSteps.map((step, index) => (
        <div key={index} className="text-center">
          <div className="step-indicator">{index + 1}</div>
          <h3 className="step-title">{step.title}</h3>
          <p className="step-description">{step.description}</p>
        </div>
      ))}
    </div>
  </div>
</section>
```

**Embedded Pricing Section:**
- Move core pricing content from /pricing page
- Maintain link to full pricing page for detailed comparisons
- Focus on key plans and benefits

### 2. Navigation Component Updates (web/components/layout/navigation.tsx)

#### Mixed Navigation Strategy
```tsx
const navItems = [
  // Anchor links for homepage sections
  { name: "Features", href: "#features", icon: CheckCircle, type: "anchor" },
  { name: "How it Works", href: "#how-it-works", icon: ArrowRight, type: "anchor" },
  { name: "Pricing", href: "#pricing", icon: CreditCard, type: "anchor" },

  // Page links for authenticated users
  ...(isSignedIn ? [
    { name: "Dashboard", href: "/dashboard", icon: Home, type: "page" },
    { name: "New Check", href: "/checks/new", icon: CheckCircle, type: "page" },
  ] : [])
];
```

#### Smart Link Component
```tsx
const SmartLink = ({ item, children }) => {
  if (item.type === 'anchor') {
    return (
      <a
        href={item.href}
        className={cn("navbar-secondary-item", isActive && "active")}
        onClick={(e) => {
          e.preventDefault();
          document.querySelector(item.href)?.scrollIntoView({
            behavior: 'smooth'
          });
        }}
      >
        {children}
      </a>
    );
  }

  return (
    <Link href={item.href} className={cn("navbar-secondary-item", isActive && "active")}>
      {children}
    </Link>
  );
};
```

### 3. CSS Enhancements (web/app/globals.css)

#### Smooth Scrolling System
```css
/* Smooth scrolling with accessibility */
html {
  scroll-behavior: smooth;
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
}

/* Section spacing system */
.section-spacing {
  padding-top: var(--space-24);
  padding-bottom: var(--space-24);
}

/* Anchor offset for fixed navigation */
section[id] {
  scroll-margin-top: 100px; /* Account for fixed navbar */
}
```

#### Enhanced Section Styling
```css
/* Section backgrounds for visual variety */
.section-hero {
  background: var(--gradient-hero);
}

.section-features {
  background: var(--white);
}

.section-process {
  background: var(--gray-50);
}

.section-pricing {
  background: var(--white);
}

.section-testimonials {
  background: var(--gray-50);
}

.section-cta {
  background: var(--gradient-primary);
}
```

## 🛡️ Technical Edge Cases & UX Patterns

### Authentication Edge Cases
```tsx
// Handle authentication edge cases
export default function HomePage() {
  const { isSignedIn, isLoaded, user } = useUser();
  const [redirecting, setRedirecting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && isSignedIn && !redirecting) {
      setRedirecting(true);
      router.push('/dashboard');
    }
  }, [isSignedIn, isLoaded, redirecting, router]);

  // 1. Loading state during auth check
  if (!isLoaded) {
    return <LoadingPage />;
  }

  // 2. Signed-in user during redirect
  if (isSignedIn) {
    return <RedirectingPage />;
  }

  // 3. Signed-out user gets marketing
  return <MarketingHomepage />;
}
```

### Offline/Online UX Patterns
```tsx
// Handle network connectivity
import { useNetworkState } from '@/hooks/useNetworkState';

function MarketingHomepage() {
  const { isOnline } = useNetworkState();

  return (
    <MainLayout>
      {!isOnline && (
        <div className="bg-amber-50 border-b border-amber-200 p-3 text-center">
          <p className="text-amber-800 text-sm">
            You're currently offline. Some features may not work properly.
          </p>
        </div>
      )}

      {/* Marketing sections */}
    </MainLayout>
  );
}
```

### SEO and Social Sharing
```tsx
// Marketing homepage metadata
export const metadata: Metadata = {
  title: "Tru8 - Instant Fact-Checking with Dated Evidence",
  description: "Get explainable verdicts on claims from articles, images, videos, and text. Professional-grade verification in seconds.",
  keywords: ["fact checking", "verification", "misinformation", "AI"],
  openGraph: {
    title: "Tru8 - Professional Fact-Checking Platform",
    description: "Instant fact-checking with transparent sources and dated evidence",
    images: [{ url: "/og-marketing-image.jpg" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Tru8 - Instant Fact-Checking",
    description: "Professional-grade verification in seconds",
  },
};
```

## 🔄 Migration Strategy

### Step 1: Authentication Infrastructure
- Implement proper client-side routing with loading states
- Update middleware for signed-in user redirects
- Test authentication edge cases (expired tokens, network issues)

### Step 2: Content Separation
- Separate marketing content into dedicated components
- Ensure signed-in users never see marketing content
- Test offline behavior and loading states

### Step 3: Navigation Transition
- Implement conditional navigation rendering
- Add loading skeletons to prevent hydration issues
- Test anchor link behavior on marketing pages

### Step 4: SEO and Analytics
- Set up marketing-specific meta tags
- Implement section-based analytics tracking
- Ensure proper URL fragment handling for marketing anchors

## ✅ Testing Checklist

### Functionality Testing
- [ ] All existing navigation links work correctly
- [ ] Smooth scrolling works on all devices
- [ ] Section anchors load correctly via direct URL
- [ ] Mobile navigation remains functional
- [ ] Two-pill navbar system unaffected

### Performance Testing
- [ ] Page load time remains under 2.5s
- [ ] Smooth scrolling performance >60fps
- [ ] Mobile scroll performance optimized
- [ ] No layout shift during scroll

### Accessibility Testing
- [ ] Keyboard navigation works for all sections
- [ ] Screen readers can navigate sections
- [ ] Reduced motion preferences respected
- [ ] Focus management during section navigation

### Browser Testing
- [ ] Chrome, Firefox, Safari, Edge compatibility
- [ ] Mobile browser smooth scrolling
- [ ] Fallback behavior for older browsers

## 📈 Success Metrics

### Marketing Conversion (Track A - Signed-Out Users)
- **Sign-up conversion rate** (target: +25% improvement)
- **Scroll depth to pricing** (target: 80% of visitors reach pricing section)
- **Time on marketing page** (target: +50% increase)
- **Reduced bounce rate** (target: -30% on homepage)
- **CTA click-through rates** (track all sign-up buttons)

### User Journey Optimization
- **Section engagement rates** (Features, How it Works, Pricing)
- **Anchor navigation usage** (smooth scroll effectiveness)
- **Mobile conversion parity** (ensure mobile experience converts)
- **Social sharing** (track testimonials and feature sharing)

### Technical Performance (Both Tracks)
- Maintained page load speeds (<2.5s)
- Smooth 60fps scroll animations
- Zero broken navigation links
- Auth routing works flawlessly (signed-in → dashboard)

## 🚀 Next Steps

1. **Review current homepage thoroughly** - Map all existing content and functionality
2. **Plan content migration** - Identify which pages to integrate
3. **Implement navigation updates** - Add anchor link support
4. **Create new sections** - Build engaging intermediate content
5. **Test comprehensive functionality** - Ensure no regressions

## 🔗 Related Documents
- **02_THREE_PART_NAVIGATION.md** - Navigation layout enhancements
- **07_FEATURE_GRID.md** - 4x2 feature grid implementation
- **06_ANIMATED_CENTERPIECE.md** - Hero section animations

---

**Phase**: 1A - Foundation Enhancement
**Priority**: High
**Estimated Effort**: 2-3 days
**Dependencies**: None
**Impact**: High - Fundamental UX improvement