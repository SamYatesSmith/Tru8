# 📄 PLAN #3: HISTORY PAGE

**File:** `web/app/dashboard/history/page.tsx`
**Type:** Server Component (initial data) + Client Components (search/filter/pagination)
**Status:** NOT STARTED

---

## **PURPOSE**

Full check history page with search and filtering capabilities. Shows:
- All user's fact-checking verifications (paginated)
- Search functionality to find specific checks
- Filter by verdict (SUPPORTED/CONTRADICTED/UNCERTAIN)
- Filter by status (pending/processing/completed/failed)
- "Load More" pagination (✅ APPROVED: 20 per page)

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Screenshot References**
- `history/signIn.checkhistory1.png` - Full page with search/filter
- `history/signIn.checkhistory2.png` - Check list continuation + footer

---

### **SECTION A: Hero**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Check History                               [Compass Graphic]  │
│  View, search, and manage all your fact-                       │
│  checking verifications in one place                           │
│                                                                 │
│  [New Check Button]                                            │
└─────────────────────────────────────────────────────────────────┘
```

**Elements:**
- **Heading:** "Check History" (text-4xl font-black text-white)
- **Subheading:** "View, search, and manage all your fact-checking verifications in one place" (text-lg text-slate-300)
- **CTA Button:** "New Check" (orange, rounded)
  - Links to: `/dashboard/new-check`
- **Graphic:** Compass illustration (right side)
  - Source: ✅ `/imagery/compass.png` (or appropriate filename)
  - Dimensions: 300x300px

---

### **SECTION B: Search & Filter Bar**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Search & Filter                                                │
│  Find specific verifications quickly                            │
│                                                                 │
│  [🔍 Search checks...]  [All Verdicts ▾]  [All Status ▾]      │
└─────────────────────────────────────────────────────────────────┘
```

**Card Styling:**
- Background: `bg-[#1a1f2e]`
- Border: `border border-slate-700`
- Border radius: `rounded-xl`
- Padding: `p-6`

**Elements:**

#### **1. Search Input**
- Icon: Search icon (lucide-react)
- Placeholder: "Search checks..."
- Width: Flexible (takes remaining space)
- Background: `bg-slate-800`
- Border: `border-slate-700`
- Text color: `text-white`
- Padding: px-4 py-2

**Search Behavior:**
- Client-side search (filter loaded checks)
- Search fields: Claim text, input URL
- Case-insensitive
- Real-time filtering (debounced 300ms)

**⚠️ NEW GAP #11:** Backend search endpoint?
- **Current:** Client-side filtering of loaded checks
- **Option 1:** Keep client-side for MVP (simple, works for <100 checks)
- **Option 2:** Add backend search endpoint `GET /checks?search=query`
- **Recommendation:** Client-side for MVP, backend if performance issues

#### **2. Verdict Filter Dropdown**
- Label: "All Verdicts"
- Icon: Filter icon
- Options:
  - All Verdicts
  - Supported
  - Contradicted
  - Uncertain
- Default: "All Verdicts"

**Filter Logic:**
```typescript
const verdictFilter = (check) => {
  if (selectedVerdict === 'all') return true;
  return check.claims?.some(claim => claim.verdict === selectedVerdict);
};
```

#### **3. Status Filter Dropdown**
- Label: "All Status"
- Icon: Filter icon
- Options:
  - All Status
  - Completed
  - Processing
  - Pending
  - Failed
- Default: "All Status"

**Filter Logic:**
```typescript
const statusFilter = (check) => {
  if (selectedStatus === 'all') return true;
  return check.status === selectedStatus;
};
```

---

### **SECTION C: Checks List**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [✓ SUPPORTED]  Oct 5, 2025                                 92% │
│                                                         Confidence│
│ Climate change is primarily caused by human activities...       │
├─────────────────────────────────────────────────────────────────┤
│ [✗ CONTRADICTED]  Oct 2, 2025                              88% │
│                                                         Confidence│
│ Vaccines cause autism - this claim has been thoroughly...      │
│ 🔗 https://example.com/article                                  │
├─────────────────────────────────────────────────────────────────┤
│ [⚠ UNCERTAIN]  Sep 30, 2025                                45% │
│                                                         Confidence│
│ New technology will revolutionize the industry...               │
└─────────────────────────────────────────────────────────────────┘
```

**Check Cards:**
- Reuse `<CheckCard />` component from Dashboard (✅ Zero duplication)
- Spacing: `space-y-4` (16px gap)
- All checks are clickable → navigate to `/dashboard/check/[id]`

**Empty State** (if no checks or no search results):
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                   [Search Icon]                                 │
│           No checks found                                       │
│           Try adjusting your search or filters                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Loading State** (while fetching more):
```
┌─────────────────────────────────────────────────────────────────┐
│                   [Spinner Animation]                           │
│                   Loading more checks...                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### **SECTION D: Pagination**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    [Load More Button]                           │
│                  Showing 20 of 47 checks                        │
└─────────────────────────────────────────────────────────────────┘
```

**Load More Button:**
- ✅ APPROVED: "Load More" button, 20 per page
- Text: "Load More"
- Background: `bg-slate-700 hover:bg-slate-600`
- Width: Auto (centered)
- Padding: px-8 py-3
- Border radius: rounded-lg

**Counter Text:**
- "Showing X of Y checks"
- Font: text-sm text-slate-400
- Centered below button

**Behavior:**
- Click → Load next 20 checks
- Append to existing list (don't replace)
- Hide button when all checks loaded
- Show loading spinner during fetch

---

## **BACKEND INTEGRATION**

### **Initial Data Fetch (Server Component)**

```typescript
export default async function HistoryPage() {
  const { getToken } = auth();
  const token = await getToken();

  // Fetch first 20 checks
  const initialChecks = await apiClient.getChecks(token, 0, 20);

  return (
    <HistoryContent initialChecks={initialChecks} token={token} />
  );
}
```

### **API Endpoint**

**Request:** `GET /api/v1/checks?skip=0&limit=20`

**Response:**
```typescript
{
  checks: [{
    id: string,
    status: 'completed' | 'pending' | 'processing' | 'failed',
    inputType: 'url' | 'text' | 'image' | 'video',
    inputUrl: string | null,
    creditsUsed: number,
    processingTimeMs: number | null,
    createdAt: string,
    completedAt: string | null,
    claimsCount: number,
    claims: [{
      id: string,
      text: string,
      verdict: 'supported' | 'contradicted' | 'uncertain',
      confidence: number,
      position: number
    }]
  }],
  total: number  // Total count of all user's checks
}
```

**Backend File:** `backend/app/api/v1/checks.py:46-75`

**Query Parameters:**
- `skip`: Offset for pagination (default: 0)
- `limit`: Number of checks to return (default: 20, max: 100)

---

## **COMPONENT STRUCTURE**

### **File: `web/app/dashboard/history/page.tsx`**
```typescript
import { auth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';
import { HistoryContent } from './components/history-content';
import { PageHeader } from '../components/page-header';
import { CompassGraphic } from '../components/compass-graphic';

export default async function HistoryPage() {
  const { getToken } = auth();
  const token = await getToken();

  // Fetch first page
  const initialChecks = await apiClient.getChecks(token, 0, 20);

  return (
    <div>
      <PageHeader
        title="Check History"
        subtitle="View, search, and manage all your fact-checking verifications in one place"
        ctaText="New Check"
        ctaHref="/dashboard/new-check"
        graphic={<CompassGraphic />}
      />

      <HistoryContent initialChecks={initialChecks} />
    </div>
  );
}
```

### **File: `web/app/dashboard/history/components/history-content.tsx`**
```typescript
'use client';

import { useState, useMemo } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Search, Filter } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { CheckCard } from '../../components/check-card';
import { EmptyState } from '../../components/empty-state';
import { LoadingSpinner } from '../../components/loading-spinner';

interface HistoryContentProps {
  initialChecks: {
    checks: any[];
    total: number;
  };
}

export function HistoryContent({ initialChecks }: HistoryContentProps) {
  const { getToken } = useAuth();
  const [checks, setChecks] = useState(initialChecks.checks);
  const [total] = useState(initialChecks.total);
  const [isLoading, setIsLoading] = useState(false);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Load more checks
  const handleLoadMore = async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      const newChecks = await apiClient.getChecks(token, checks.length, 20);
      setChecks([...checks, ...newChecks.checks]);
    } catch (error) {
      console.error('Failed to load more checks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply filters
  const filteredChecks = useMemo(() => {
    return checks.filter(check => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesText = check.claims?.some((claim: any) =>
          claim.text.toLowerCase().includes(query)
        );
        const matchesUrl = check.inputUrl?.toLowerCase().includes(query);
        if (!matchesText && !matchesUrl) return false;
      }

      // Verdict filter
      if (verdictFilter !== 'all') {
        const hasVerdict = check.claims?.some((claim: any) =>
          claim.verdict === verdictFilter
        );
        if (!hasVerdict) return false;
      }

      // Status filter
      if (statusFilter !== 'all' && check.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [checks, searchQuery, verdictFilter, statusFilter]);

  const hasMore = checks.length < total;

  return (
    <div className="space-y-8">
      {/* Search & Filter Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-6">
        <div className="mb-4">
          <h3 className="text-xl font-bold text-white">Search & Filter</h3>
          <p className="text-slate-400 text-sm">Find specific verifications quickly</p>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
              type="text"
              placeholder="Search checks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-slate-600"
            />
          </div>

          {/* Verdict Filter */}
          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-slate-600"
          >
            <option value="all">All Verdicts</option>
            <option value="supported">Supported</option>
            <option value="contradicted">Contradicted</option>
            <option value="uncertain">Uncertain</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-slate-600"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Checks List */}
      {filteredChecks.length === 0 ? (
        <EmptyState
          icon={<Search size={48} className="text-slate-600" />}
          message={searchQuery || verdictFilter !== 'all' || statusFilter !== 'all'
            ? "No checks found"
            : "No checks yet"}
          submessage={searchQuery || verdictFilter !== 'all' || statusFilter !== 'all'
            ? "Try adjusting your search or filters"
            : "Start your first verification!"}
        />
      ) : (
        <div className="space-y-4">
          {filteredChecks.map(check => (
            <CheckCard key={check.id} check={check} />
          ))}
        </div>
      )}

      {/* Load More Button */}
      {hasMore && !isLoading && filteredChecks.length > 0 && (
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleLoadMore}
            className="bg-slate-700 hover:bg-slate-600 text-white font-semibold px-8 py-3 rounded-lg transition-colors"
          >
            Load More
          </button>
          <p className="text-sm text-slate-400">
            Showing {checks.length} of {total} checks
          </p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center gap-3 py-8">
          <LoadingSpinner />
          <p className="text-slate-400">Loading more checks...</p>
        </div>
      )}
    </div>
  );
}
```

---

## **NEW COMPONENTS**

### **1. CompassGraphic Component**
**File:** `web/app/dashboard/components/compass-graphic.tsx`

```typescript
import Image from 'next/image';

export function CompassGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/compass.png"
        alt="Compass"
        fill
        className="object-contain"
      />
    </div>
  );
}
```

**Note:** ✅ APPROVED: Graphics added to `web/public/imagery/`

### **2. LoadingSpinner Component** (Reusable)
**File:** `web/app/dashboard/components/loading-spinner.tsx`

```typescript
export function LoadingSpinner() {
  return (
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#f57a07]" />
  );
}
```

---

## **REUSABLE COMPONENTS**

### **From Existing Code**
1. ✅ **`<PageHeader />`** - Already created in PLAN_02
2. ✅ **`<CheckCard />`** - Already created in PLAN_02
3. ✅ **`<EmptyState />`** - Already created in PLAN_02

### **New Reusable Components**
4. ✅ **`<LoadingSpinner />`** - Created for this page, reusable everywhere

---

## **ZERO DUPLICATION STRATEGY**

### **Existing Components Reused**
- **CheckCard**: Same component from Dashboard (no duplication)
- **EmptyState**: Same component from Dashboard (no duplication)
- **PageHeader**: Same component from Dashboard (no duplication)

### **Styling Consistency**
- Search input matches form inputs from other pages
- Filter dropdowns use same styling as other selects
- Load More button matches secondary button style

---

## **GAP RESOLUTIONS**

### **GAP #10 Resolution: Pagination** ✅ APPROVED
```typescript
// Load More button implementation
const handleLoadMore = async () => {
  const token = await getToken();
  const newChecks = await apiClient.getChecks(token, checks.length, 20);
  setChecks([...checks, ...newChecks.checks]); // Append, don't replace
};
```

**Features:**
- Shows "Showing X of Y checks" counter
- Hides button when all checks loaded
- Smooth loading experience

### **✅ GAP #11 RESOLVED: Search Implementation**
**Issue:** Client-side vs backend search

**DECISION APPROVED:** ✅ Client-side filtering for MVP

**Implementation:**
```typescript
const filteredChecks = checks.filter(check => {
  return check.claims?.some(claim =>
    claim.text.toLowerCase().includes(searchQuery.toLowerCase())
  );
});
```

**Rationale:**
- Simpler implementation, no backend changes required
- Instant results for better UX
- Acceptable performance for <100 checks per user (MVP scale)
- Can refactor to backend search if users exceed 100 checks

**Phase 2 Enhancement:**
- Add backend search endpoint if user growth requires it
- Endpoint: `GET /api/v1/checks?search=query&verdict=supported`
- Implement full-text search with relevance scoring

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Components**
- [ ] Create CompassGraphic component
- [ ] Create LoadingSpinner component
- [ ] Create HistoryContent client component

### **Phase 2: Search & Filter**
- [ ] Implement search input with debounce
- [ ] Implement verdict filter dropdown
- [ ] Implement status filter dropdown
- [ ] Connect filters to check list

### **Phase 3: Pagination**
- [ ] Implement Load More button
- [ ] Fetch and append new checks
- [ ] Show loading state
- [ ] Hide button when all loaded

### **Phase 4: Main Page**
- [ ] Create history page.tsx (server component)
- [ ] Fetch initial checks
- [ ] Render PageHeader with compass graphic
- [ ] Render HistoryContent with filters

### **Phase 5: Polish**
- [ ] Add empty state handling
- [ ] Test search functionality
- [ ] Test filter combinations
- [ ] Test pagination edge cases
- [ ] Ensure mobile responsiveness

---

## **TESTING SCENARIOS**

### **Search**
1. **Empty query:** Show all checks
2. **Matching claim text:** Show filtered results
3. **Matching URL:** Show filtered results
4. **No matches:** Show empty state with message
5. **Case insensitivity:** "vaccine" matches "Vaccine"

### **Filters**
1. **Verdict: Supported:** Only show checks with supported claims
2. **Verdict: Contradicted:** Only show checks with contradicted claims
3. **Status: Completed:** Only show completed checks
4. **Combined filters:** Search + Verdict + Status work together
5. **Clear filters:** Reset shows all checks

### **Pagination**
1. **First load:** Show 20 checks
2. **Load more:** Append next 20 checks
3. **All loaded:** Hide Load More button
4. **Loading state:** Show spinner during fetch
5. **Error handling:** Show error message if fetch fails

### **Edge Cases**
1. **No checks:** Show empty state immediately
2. **Exactly 20 checks:** Show Load More, then hide after click
3. **Network error:** Show error message, allow retry
4. **Filters with pagination:** Filters apply to all loaded checks

---

## **DEPENDENCIES**

- ✅ Layout complete (provides navigation)
- ✅ CheckCard component available
- ✅ EmptyState component available
- ✅ PageHeader component available
- ✅ Backend `/checks` endpoint functional
- ✅ API client `getChecks()` method available

---

## **NOTES**

- Client-side filtering for MVP (simple, fast for small datasets)
- Load More pattern is simpler than infinite scroll
- All filters work together (AND logic)
- Search is debounced to avoid excessive filtering
- Backend search can be added later if needed (NEW GAP #11)
