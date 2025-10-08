PS C:\Users\projects\Tru8\web> npm run dev

> tru8-web@0.1.0 dev
> next dev

 ⚠ Port 3000 is in use, trying 3001 instead.
  ▲ Next.js 14.2.13
  - Local:        http://localhost:3001
  - Environments: .env

 ✓ Starting...
 ✓ Ready in 1696ms
 ○ Compiling /middleware ...
 ⚠ ./middleware.ts
Attempted import error: 'authMiddleware' is not exported from '@clerk/nextjs' (imported as 'authMiddleware').
 ⚠ ./middleware.ts
Attempted import error: 'authMiddleware' is not exported from '@clerk/nextjs' (imported as 'authMiddleware').
 ⨯ middleware.ts (3:1) @ <unknown>
 ⨯ (0 , _clerk_nextjs__WEBPACK_IMPORTED_MODULE_0__.authMiddleware) is not a function
  1 | import { authMiddleware } from "@clerk/nextjs";
  2 |
> 3 | export default authMiddleware({
    | ^
  4 |   publicRoutes: ["/"], // Marketing page is public
  5 | });
  6 |
 ⚠ ./middleware.ts
Attempted import error: 'authMiddleware' is not exported from '@clerk/nextjs' (imported as 'authMiddleware').
 GET / 404 in 4ms
 ⚠ ./middleware.ts
Attempted import error: 'authMiddleware' is not exported from '@clerk/nextjs' (imported as 'authMiddleware').
 ⚠ Fast Refresh had to perform a full reload due to a runtime error.
 ⨯ middleware.ts (3:1) @ <unknown>
 ⨯ (0 , _clerk_nextjs__WEBPACK_IMPORTED_MODULE_0__.authMiddleware) is not a function
  1 | import { authMiddleware } from "@clerk/nextjs";
  2 |
> 3 | export default authMiddleware({
    | ^
  4 |   publicRoutes: ["/"], // Marketing page is public
  5 | });
  6 |
 ⚠ ./middleware.ts
Attempted import error: 'authMiddleware' is not exported from '@clerk/nextjs' (imported as 'authMiddleware').
 GET / 404 in 3ms
 ⨯ middleware.ts (3:1) @ <unknown>
 ⨯ (0 , _clerk_nextjs__WEBPACK_IMPORTED_MODULE_0__.authMiddleware) is not a function
  1 | import { authMiddleware } from "@clerk/nextjs";
  2 |
> 3 | export default authMiddleware({
    | ^
  4 |   publicRoutes: ["/"], // Marketing page is public
  5 | });
  6 |
 ⚠ Fast Refresh had to perform a full reload due to a runtime error.
 ⨯ middleware.ts (3:1) @ <unknown>
 ⨯ (0 , _clerk_nextjs__WEBPACK_IMPORTED_MODULE_0__.authMiddleware) is not a function
  1 | import { authMiddleware } from "@clerk/nextjs";
  2 |
> 3 | export default authMiddleware({
    | ^
  4 |   publicRoutes: ["/"], // Marketing page is public
  5 | });
  6 |
 GET / 404 in 2ms