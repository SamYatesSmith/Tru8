import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

/**
 * UNIFIED AUTH FLOW - Single Source of Truth
 *
 * Middleware is the ONLY place that checks authentication.
 * Protected pages trust middleware - no redundant checks.
 *
 * Flow:
 * 1. Check if route is protected
 * 2. If protected and user not authenticated → Redirect to home with modal trigger
 * 3. If authenticated or public route → Allow through
 */

const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/api/protected(.*)',
]);

export default clerkMiddleware(async (auth, req) => {
  const { userId } = await auth();

  // Protected route requires authentication
  if (isProtectedRoute(req)) {
    if (!userId) {
      // Not authenticated → Redirect to home with auth modal trigger
      const url = new URL('/', req.url);
      url.searchParams.set('auth_redirect', 'true');
      // Path AND query: the hero field sends a signed-out visitor to
      // /dashboard/new-check?text=…&run=1, and the claim must survive the
      // auth modal (2026-09-01). Clerk's forceRedirectUrl accepts a full path.
      url.searchParams.set('redirect_url', req.nextUrl.pathname + req.nextUrl.search);
      return NextResponse.redirect(url);
    }
    // Authenticated → Allow through (pages trust middleware)
  }

  // Public routes → Allow through
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
