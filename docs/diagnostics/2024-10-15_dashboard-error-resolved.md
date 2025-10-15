 GET /dashboard?_rsc=3y0gy 200 in 1443ms
 ⨯ lib\api.ts (50:13) @ ApiClient.request
 ⨯ Error: Unknown error
    at ApiClient.request (./lib/api.ts:43:19)
    at async Promise.all (index 1)
    at async DashboardPage (./app/dashboard/page.tsx:36:50)
digest: "4148776816"
  48 |     if (!response.ok) {
  49 |       const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
> 50 |       throw new Error(error.detail || `API error: ${response.status}`);
     |             ^
  51 |     }
  52 |
  53 |     return response.json();