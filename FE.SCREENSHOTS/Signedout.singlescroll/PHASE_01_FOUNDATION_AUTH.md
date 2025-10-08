# Phase 1: Foundation & Authentication

**Status:** Not Started
**Estimated Time:** 2.5 hours
**Dependencies:** None (first phase)
**Backend Integration:** Clerk authentication, `/api/v1/users/me` endpoint

---

## 🎯 Objectives

1. Set up Next.js 14 project with App Router
2. Install and configure Clerk authentication
3. Create backend API client (`lib/api.ts`)
4. Generate and implement 3-layer animated pixel grid background
5. Test Clerk authentication flow end-to-end
6. Verify user auto-creation in backend

---

## 📋 Task Checklist

- [ ] **Task 1.1:** Initialize Next.js project with TypeScript
- [ ] **Task 1.2:** Install Clerk, Tailwind CSS, and dependencies
- [ ] **Task 1.3:** Configure Clerk provider and middleware
- [ ] **Task 1.4:** Create backend API client with Clerk token injection
- [ ] **Task 1.5:** Generate 3-layer pixel grid images
- [ ] **Task 1.6:** Implement animated background component
- [ ] **Task 1.7:** Test Clerk auth and backend `/users/me` endpoint

---

## 🔧 Implementation Steps

### **Task 1.1: Initialize Next.js Project**

```bash
# From /web/ directory (already exists but empty)
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
```

**Configuration:**
- TypeScript: ✅ Yes
- ESLint: ✅ Yes
- Tailwind CSS: ✅ Yes
- App Router: ✅ Yes
- Import alias (`@/*`): ✅ Yes

**Files Created:**
- `app/layout.tsx`
- `app/page.tsx`
- `app/globals.css`
- `tailwind.config.ts`
- `next.config.js`
- `package.json`

---

### **Task 1.2: Install Dependencies**

```bash
npm install @clerk/nextjs
npm install lucide-react
npm install clsx tailwind-merge
npm install -D @types/node
```

**Package Breakdown:**
- `@clerk/nextjs` - Authentication (Clerk SDK)
- `lucide-react` - Icons (Sparkles, Info, CreditCard, User, etc.)
- `clsx` + `tailwind-merge` - Utility for conditional classes
- `@types/node` - TypeScript types

---

### **Task 1.3: Configure Clerk**

#### **Step 1: Add Environment Variables**

Create `web/.env.local`:
```env
# Clerk Keys (from Clerk Dashboard)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx

# Clerk URLs
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### **Step 2: Create Clerk Middleware**

File: `web/middleware.ts`
```typescript
import { authMiddleware } from "@clerk/nextjs";

export default authMiddleware({
  publicRoutes: ["/"], // Marketing page is public
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
```

**What this does:**
- Makes marketing page (`/`) public (no auth required)
- Protected routes (like `/dashboard`) will redirect to Clerk sign-in if not authenticated

#### **Step 3: Wrap App with Clerk Provider**

File: `web/app/layout.tsx`
```typescript
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tru8 - Transparent Fact-Checking with Dated Evidence',
  description: 'Professional fact-checking platform providing instant verification with dated evidence for journalists, researchers, and content creators.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}
```

---

### **Task 1.4: Create Backend API Client**

File: `web/lib/api.ts`
```typescript
import { auth } from '@clerk/nextjs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Backend API Client
 *
 * Automatically injects Clerk JWT token in Authorization header
 * for all backend requests.
 *
 * Backend Integration:
 * - Base URL: http://localhost:8000/api/v1
 * - Auth: Bearer token from Clerk
 * - Endpoints:
 *   - GET /users/me - Auto-creates user if not exists
 *   - POST /checks - Create fact-check
 *   - GET /checks - Get user's checks
 *   - POST /payments/create-checkout-session - Stripe checkout
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get Clerk auth token
   * This is used server-side in API routes
   */
  private async getToken(): Promise<string | null> {
    const { getToken } = auth();
    return await getToken();
  }

  /**
   * Generic request method
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * GET /api/v1/users/me
   * Returns user profile with credits
   * Auto-creates user if doesn't exist (first login)
   */
  async getCurrentUser() {
    return this.request('/api/v1/users/me');
  }

  /**
   * POST /api/v1/checks
   * Create a new fact-check
   */
  async createCheck(data: {
    input_type: 'url' | 'text' | 'image' | 'video';
    content?: string;
    url?: string;
    file_path?: string;
  }) {
    return this.request('/api/v1/checks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * POST /api/v1/payments/create-checkout-session
   * Create Stripe checkout session for Professional plan
   */
  async createCheckoutSession(data: {
    price_id: string;
    plan: string;
  }) {
    return this.request('/api/v1/payments/create-checkout-session', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
```

**What this does:**
- Automatically injects Clerk JWT token in `Authorization` header
- Provides type-safe methods for backend endpoints
- Handles errors consistently
- Used by all components that need backend data

---

### **Task 1.5: Generate 3-Layer Pixel Grid Images**

File: `web/lib/pixel-grid-generator.ts`
```typescript
/**
 * Pixel Grid Generator
 *
 * Generates seamless tiling pixel grid patterns for animated background.
 *
 * Specifications:
 * - 3 layers (back, middle, front)
 * - Pixel sizes: 8px, 12px, 16px (mixed)
 * - Colors: slate-300, slate-400, slate-500, stone-300, orange (#f57a07) sparse
 * - Pattern: 2x viewport height for seamless looping
 * - Seamless horizontal + vertical tiling
 */

const COLORS = [
  '#cbd5e1', // slate-300 (30% frequency)
  '#94a3b8', // slate-400 (25% frequency)
  '#64748b', // slate-500 (20% frequency)
  '#d6d3d1', // stone-300 (20% frequency)
  '#f57a07', // orange (5% frequency - accent)
];

const PIXEL_SIZES = [8, 12, 16];

export function generatePixelGrid(
  width: number,
  height: number,
  density: number = 0.03 // 3% of pixels filled
): string {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  if (!ctx) throw new Error('Canvas context not available');

  // Fill with transparent background
  ctx.clearRect(0, 0, width, height);

  // Calculate number of pixels based on density
  const totalPixels = Math.floor((width * height) / 256) * density;

  for (let i = 0; i < totalPixels; i++) {
    // Random position
    const x = Math.floor(Math.random() * width);
    const y = Math.floor(Math.random() * height);

    // Random pixel size
    const size = PIXEL_SIZES[Math.floor(Math.random() * PIXEL_SIZES.length)];

    // Random color (weighted distribution)
    let color: string;
    const rand = Math.random();
    if (rand < 0.30) color = COLORS[0]; // slate-300 (30%)
    else if (rand < 0.55) color = COLORS[1]; // slate-400 (25%)
    else if (rand < 0.75) color = COLORS[2]; // slate-500 (20%)
    else if (rand < 0.95) color = COLORS[3]; // stone-300 (20%)
    else color = COLORS[4]; // orange (5% - rare accent)

    // Draw pixel
    ctx.fillStyle = color;
    ctx.fillRect(x, y, size, size);
  }

  // Return as data URL
  return canvas.toDataURL('image/png');
}
```

**Usage in Component:**
```typescript
useEffect(() => {
  const layer1 = generatePixelGrid(1920, 2160, 0.02); // Least dense
  const layer2 = generatePixelGrid(1920, 2160, 0.03); // Medium
  const layer3 = generatePixelGrid(1920, 2160, 0.04); // Most dense

  // Save to state or use directly in CSS
}, []);
```

---

### **Task 1.6: Implement Animated Background Component**

File: `web/components/marketing/animated-background.tsx`
```typescript
'use client';

import { useEffect, useState } from 'react';
import { generatePixelGrid } from '@/lib/pixel-grid-generator';

/**
 * Animated Background Component
 *
 * 3-layer parallax pixel grid with ascending animation.
 *
 * Animation Specs:
 * - Layer 1 (Back): 100s cycle, 30% opacity, slowest
 * - Layer 2 (Middle): 80s cycle, 20% opacity
 * - Layer 3 (Front): 60s cycle, 10% opacity, fastest
 *
 * Accessibility:
 * - Respects prefers-reduced-motion (disables animation)
 *
 * Performance:
 * - GPU-accelerated (will-change: transform)
 * - Pure CSS animation (no JavaScript RAF)
 */
export function AnimatedBackground() {
  const [layers, setLayers] = useState<{
    layer1: string;
    layer2: string;
    layer3: string;
  } | null>(null);

  useEffect(() => {
    // Generate pixel grids on mount
    const layer1 = generatePixelGrid(1920, 2160, 0.02);
    const layer2 = generatePixelGrid(1920, 2160, 0.03);
    const layer3 = generatePixelGrid(1920, 2160, 0.04);

    setLayers({ layer1, layer2, layer3 });
  }, []);

  if (!layers) {
    // Loading state - show solid dark background
    return <div className="fixed inset-0 bg-[#0f1419] -z-10" />;
  }

  return (
    <div className="fixed inset-0 overflow-hidden -z-10 bg-[#0f1419]">
      {/* Layer 1 - Slowest, most visible */}
      <div
        className="absolute inset-0 animate-ascend-slow opacity-30"
        style={{
          backgroundImage: `url(${layers.layer1})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />

      {/* Layer 2 - Medium speed */}
      <div
        className="absolute inset-0 animate-ascend-medium opacity-20"
        style={{
          backgroundImage: `url(${layers.layer2})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />

      {/* Layer 3 - Fastest, least visible */}
      <div
        className="absolute inset-0 animate-ascend-fast opacity-10"
        style={{
          backgroundImage: `url(${layers.layer3})`,
          backgroundRepeat: 'repeat',
          backgroundSize: 'auto',
          willChange: 'transform',
        }}
      />
    </div>
  );
}
```

**Add CSS Animations:**

File: `web/app/globals.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer utilities {
  /* Ascending animations for pixel grid background */
  @keyframes ascend {
    from {
      transform: translateY(0);
    }
    to {
      transform: translateY(-50%);
    }
  }

  .animate-ascend-slow {
    animation: ascend 100s linear infinite;
  }

  .animate-ascend-medium {
    animation: ascend 80s linear infinite;
  }

  .animate-ascend-fast {
    animation: ascend 60s linear infinite;
  }

  /* Respect reduced motion preference */
  @media (prefers-reduced-motion: reduce) {
    .animate-ascend-slow,
    .animate-ascend-medium,
    .animate-ascend-fast {
      animation: none;
    }
  }
}
```

---

### **Task 1.7: Test Clerk Auth and Backend Integration**

#### **Test 1: Clerk Authentication**

1. Run Next.js dev server:
   ```bash
   npm run dev
   ```

2. Open browser: `http://localhost:3000`

3. Click "Sign In" (we'll add this button in Phase 2, but can test manually)

4. Verify:
   - [ ] Clerk modal opens
   - [ ] Can sign in with test account
   - [ ] JWT token received (check Network tab)
   - [ ] Redirects to `/dashboard` (will show 404 for now - expected)

#### **Test 2: Backend User Auto-Creation**

1. Start backend server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. Test `/users/me` endpoint with Clerk token:
   ```bash
   # Get token from Clerk (after sign-in)
   # Use it to call backend
   curl -H "Authorization: Bearer <clerk_jwt_token>" \
        http://localhost:8000/api/v1/users/me
   ```

3. Verify:
   - [ ] Returns 200 OK
   - [ ] User object returned with 3 credits
   - [ ] User created in database (check with psql or database GUI)

#### **Test 3: Animated Background**

1. Add `<AnimatedBackground />` to `app/page.tsx` temporarily
2. Open browser: `http://localhost:3000`
3. Verify:
   - [ ] 3 layers of pixels visible
   - [ ] Pixels ascending slowly
   - [ ] Smooth 60fps animation (check with Chrome DevTools Performance)
   - [ ] Reduced motion disables animation (test in browser DevTools)

---

## 🔗 Backend Integration Details

### Endpoints Used in This Phase

#### **GET /api/v1/users/me**
**Purpose:** Get current user profile, auto-create if doesn't exist

**Request:**
```http
GET /api/v1/users/me
Authorization: Bearer <clerk_jwt_token>
```

**Response (200 OK):**
```json
{
  "id": "user_xxx",
  "email": "user@example.com",
  "name": "John Doe",
  "credits": 3,
  "totalCreditsUsed": 0,
  "hasSubscription": false,
  "createdAt": "2025-10-07T12:00:00Z"
}
```

**Backend Auto-Creation Logic** (`backend/app/api/v1/auth.py:22-30`):
```python
if not user:
    user = User(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("name"),
        credits=3  # Free tier
    )
    session.add(user)
    await session.commit()
```

**Error Handling:**
- **401 Unauthorized:** Invalid/missing JWT token
- **500 Internal Server Error:** Database error

---

## ✅ Definition of Done

- [ ] Next.js project initialized with TypeScript and Tailwind
- [ ] Clerk installed and configured with middleware
- [ ] Environment variables set (`.env.local`)
- [ ] Backend API client created and documented
- [ ] Pixel grid generator utility created
- [ ] Animated background component implemented
- [ ] CSS animations added for 3 layers
- [ ] Reduced motion support implemented
- [ ] Clerk auth tested (sign-in works)
- [ ] Backend `/users/me` tested (user auto-creation works)
- [ ] Animated background renders smoothly at 60fps
- [ ] No console errors or warnings
- [ ] All files committed with detailed message

---

## 📝 Commit Message Template

```
[Phase 1] Add Next.js foundation with Clerk auth and animated background

Foundation:
- Initialized Next.js 14 with App Router, TypeScript, Tailwind CSS
- Installed dependencies: Clerk, lucide-react, clsx

Clerk Authentication:
- Configured Clerk provider and middleware
- Set up public route for marketing page (/)
- Configured redirects to /dashboard after auth
- Tested: Sign-in modal opens, JWT token received

Backend Integration:
- Created API client (lib/api.ts) with automatic Clerk token injection
- Integrated GET /api/v1/users/me endpoint
- Tested: User auto-creation works (3 credits assigned)
- Verified: User appears in database after first auth

Animated Background:
- Created pixel grid generator (lib/pixel-grid-generator.ts)
- Implemented 3-layer parallax animation
- Layer 1: 100s cycle, 30% opacity (back)
- Layer 2: 80s cycle, 20% opacity (middle)
- Layer 3: 60s cycle, 10% opacity (front)
- Added reduced motion support (@media prefers-reduced-motion)
- Tested: Smooth 60fps animation, no performance issues

Files created:
- app/layout.tsx, app/page.tsx, app/globals.css
- middleware.ts
- lib/api.ts
- lib/pixel-grid-generator.ts
- components/marketing/animated-background.tsx
- tailwind.config.ts, next.config.js

Testing performed:
- ✅ Clerk sign-in works
- ✅ JWT token received
- ✅ Backend user auto-creation works (verified in database)
- ✅ Animated background renders smoothly
- ✅ Reduced motion preference respected
```

---

## 🎯 Next Phase

**Phase 2:** Navigation (Desktop + Mobile Bottom Nav) with Auth Modal

**Dependencies from Phase 1:**
- Clerk authentication configured ✅
- API client ready ✅
- Animated background implemented ✅

---

**Phase Status:** ⏳ Ready to Begin
**Blockers:** None
**Estimated Completion:** 2.5 hours
