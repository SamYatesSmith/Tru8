import { authMiddleware } from "@clerk/nextjs";

export default authMiddleware({
  // Routes that don't require authentication
  publicRoutes: [
    "/",
    "/api/health",
    "/sign-in(.*)",
    "/sign-up(.*)",
  ],
  
  // Routes that are ignored by the auth middleware
  ignoredRoutes: [
    "/api/webhook/(.)*",
    "/api/health",
  ],
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};