# 📄 PLAN #4: NEW CHECK PAGE

**File:** `web/app/dashboard/new-check/page.tsx`
**Type:** Client Component (form submission requires client-side interaction)
**Status:** NOT STARTED

---

## **PURPOSE**

Create new fact-check page. Allows users to:
- Submit URLs for article verification
- Submit text claims for fact-checking
- View social sharing options (informational)
- Redirect to check detail page after submission

---

## **UI ELEMENTS FROM SCREENSHOTS**

### **Screenshot References**
- `new check/signIn.newCheck.01.png` - Form with URL tab active
- `new check/signIn.newCheck.02.png` - Footer section

---

### **SECTION A: Hero**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Create New Claim Check                      [Prism Graphic]    │
│  Submit claims, URLs, or articles for                           │
│  instant verification                                           │
└─────────────────────────────────────────────────────────────────┘
```

**Elements:**
- **Heading:** "Create New Claim Check" (text-4xl font-black text-white)
- **Subheading:** "Submit claims, URLs, or articles for instant verification" (text-lg text-slate-300)
- **Graphic:** Prism illustration (right side)
  - Source: ✅ `/imagery/prism.png` (or appropriate filename)
  - Dimensions: 300x300px

---

### **SECTION B: Submit Content Card**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Submit Content                                                 │
│  Enter a URL or paste text to verify claims and check facts    │
│                                                                 │
│  [URL] [TEXT]  ← Tab selector                                  │
│                                                                 │
│  Website URL                                                    │
│  [https://example.com/article                    ]             │
│  Enter the URL of an article, blog post, or webpage to verify  │
│                                                                 │
│  [           START FACT CHECK            ]                     │
└─────────────────────────────────────────────────────────────────┘
```

**Card Styling:**
- Background: `bg-[#1a1f2e]`
- Border: `border border-slate-700`
- Border radius: `rounded-xl`
- Padding: `p-8`

#### **Tab Selector**
```
[URL] [TEXT]
```

- Active tab: `text-[#f57a07]` with `border-b-2 border-[#f57a07]`
- Inactive tab: `text-slate-400` with no border
- Font: Bold, uppercase
- Spacing: gap-6
- Padding bottom: pb-2

**⚠️ NEW GAP #12:** Screenshot shows only URL/TEXT tabs, but backend supports 4 input types
- **Backend supports:** `url`, `text`, `image`, `video`
- **Screenshot shows:** Only URL and TEXT tabs
- **Decision needed:** Add IMAGE and VIDEO tabs for MVP or defer to Phase 2?
- **Recommendation:** Start with URL and TEXT only (matches screenshot), add IMAGE/VIDEO in Phase 2

#### **URL Tab Content**

**Label:** "Website URL" (text-sm font-semibold text-white)

**Input:**
- Placeholder: "https://example.com/article"
- Width: Full width
- Background: `bg-slate-800`
- Border: `border border-slate-700`
- Text: `text-white`
- Padding: px-4 py-3
- Border radius: rounded-lg
- Focus state: `focus:border-[#f57a07] focus:outline-none`

**Helper Text:**
- "Enter the URL of an article, blog post, or webpage to verify"
- Font: text-sm text-slate-400
- Margin: mt-2

**Validation:**
- Required field
- Must be valid URL format
- Show error message if invalid

#### **TEXT Tab Content**

**Label:** "Text Content" (text-sm font-semibold text-white)

**Input:**
- Component: `<textarea>`
- Placeholder: "Paste or type the text you want to fact-check..."
- Width: Full width
- Height: 200px (rows={8})
- Background: `bg-slate-800`
- Border: `border border-slate-700`
- Text: `text-white`
- Padding: px-4 py-3
- Border radius: rounded-lg
- Resize: vertical
- Focus state: `focus:border-[#f57a07] focus:outline-none`

**Helper Text:**
- "Enter text containing claims you want to verify"
- Font: text-sm text-slate-400
- Margin: mt-2

**Validation:**
- Required field
- Minimum 10 characters
- Maximum 5000 characters (to prevent abuse)
- Show character count: "500 / 5000 characters"

**⚠️ NEW GAP #13:** Text length limits?
- **Issue:** No backend validation documented for text length
- **Client-side recommendation:** Min 10, Max 5000 characters
- **Decision needed:** Confirm with backend team if limits exist
- **Backend file to check:** `backend/app/api/v1/checks.py` validation

#### **Submit Button**

```
[           START FACT CHECK            ]
```

- Text: "START FACT CHECK" (uppercase, bold)
- Background: `bg-[#f57a07] hover:bg-[#e06a00]`
- Width: Full width
- Padding: py-4
- Border radius: rounded-xl
- Text color: white
- Font: Bold
- Transition: All properties 200ms

**States:**
- **Default:** Orange background
- **Hover:** Darker orange
- **Loading:** Show spinner, text changes to "PROCESSING..."
- **Disabled:** `opacity-50 cursor-not-allowed` (when form invalid or no credits)

**Credit Check:**
```typescript
// Before submission, check credits
if (user.credits <= 0 && !user.hasSubscription) {
  showError("No credits remaining. Please upgrade to continue.");
  return;
}
```

---

### **SECTION C: Share Your Results**

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│                     Share Your Results                          │
│  Once your fact-check is complete, share the verified results   │
│  with your network to help combat misinformation                │
│                                                                 │
│        [f] [📷] [🐦] [▶] [💬]                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Card Styling:**
- Background: `bg-[#1a1f2e]`
- Border: `border border-slate-700`
- Border radius: `rounded-xl`
- Padding: `p-8`
- Text align: center

**Elements:**
- **Heading:** "Share Your Results" (text-2xl font-bold text-white, centered)
- **Description:** "Once your fact-check is complete, share the verified results with your network to help combat misinformation"
  - Font: text-slate-300
  - Max width: 600px (centered)
  - Margin: mt-3 mb-6

**Social Icons:**
- Icons: Facebook, Instagram, Twitter, YouTube, Message
- Size: 48x48px
- Background: `bg-slate-800 hover:bg-slate-700`
- Padding: p-3
- Border radius: rounded-full
- Color: `text-slate-400 hover:text-white`
- Spacing: gap-4
- Centered horizontally

**Icon Mapping:**
- Facebook: `<Facebook />` from lucide-react
- Instagram: `<Instagram />`
- Twitter: `<Twitter />`
- YouTube: `<Youtube />`
- Message: `<MessageCircle />`

**Functionality:**
- ✅ APPROVED: Web Share API + fallback URLs
- Icons are clickable (open share dialog)
- Note: This is informational for now (shares generic Tru8 info)
- After check completes, user can share specific check result from check detail page

---

## **BACKEND INTEGRATION**

### **Form Submission**

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  // Validate form
  if (activeTab === 'url' && !isValidUrl(urlInput)) {
    setError('Please enter a valid URL');
    return;
  }

  if (activeTab === 'text' && textInput.length < 10) {
    setError('Text must be at least 10 characters');
    return;
  }

  // Check credits
  if (user.credits <= 0 && !user.hasSubscription) {
    setError('No credits remaining. Please upgrade to continue.');
    return;
  }

  setIsSubmitting(true);
  setError(null);

  try {
    const token = await getToken();

    const result = await apiClient.createCheck({
      input_type: activeTab,
      url: activeTab === 'url' ? urlInput : undefined,
      content: activeTab === 'text' ? textInput : undefined,
    }, token);

    // Redirect to check detail page
    router.push(`/dashboard/check/${result.check.id}`);
  } catch (err) {
    setError(err.message || 'Failed to create check. Please try again.');
    setIsSubmitting(false);
  }
};
```

### **API Endpoint**

**Request:** `POST /api/v1/checks`

**Request Body (URL):**
```typescript
{
  input_type: 'url',
  url: 'https://example.com/article',
}
```

**Request Body (TEXT):**
```typescript
{
  input_type: 'text',
  content: 'Climate change is primarily caused by human activities...',
}
```

**Response:**
```typescript
{
  check: {
    id: string,
    status: 'pending',
    inputType: 'url' | 'text',
    createdAt: string,
    creditsUsed: 1
  },
  remainingCredits: number,
  taskId: string  // Celery task ID for background processing
}
```

**Backend File:** `backend/app/api/v1/checks.py:23-44`

**Backend Logic:**
1. Validates JWT token
2. Checks user has sufficient credits
3. Creates check record with status 'pending'
4. Deducts 1 credit from user
5. Queues background task (Celery) for processing
6. Returns check ID immediately

---

## **COMPONENT STRUCTURE**

### **File: `web/app/dashboard/new-check/page.tsx`**
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Facebook, Instagram, Twitter, Youtube, MessageCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { PageHeader } from '../components/page-header';
import { PrismGraphic } from '../components/prism-graphic';
import { isValidUrl } from '@/lib/utils';

export default function NewCheckPage() {
  const router = useRouter();
  const { getToken } = useAuth();

  // Tab state
  const [activeTab, setActiveTab] = useState<'url' | 'text'>('url');

  // Form state
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (activeTab === 'url') {
      if (!urlInput.trim()) {
        setError('Please enter a URL');
        return;
      }
      if (!isValidUrl(urlInput)) {
        setError('Please enter a valid URL (e.g., https://example.com)');
        return;
      }
    } else {
      if (!textInput.trim()) {
        setError('Please enter some text');
        return;
      }
      if (textInput.length < 10) {
        setError('Text must be at least 10 characters');
        return;
      }
      if (textInput.length > 5000) {
        setError('Text must be less than 5000 characters');
        return;
      }
    }

    setIsSubmitting(true);

    try {
      const token = await getToken();

      const result = await apiClient.createCheck({
        input_type: activeTab,
        url: activeTab === 'url' ? urlInput : undefined,
        content: activeTab === 'text' ? textInput : undefined,
      }, token);

      // Redirect to check detail page
      router.push(`/dashboard/check/${result.check.id}`);
    } catch (err: any) {
      console.error('Failed to create check:', err);
      setError(err.message || 'Failed to create check. Please try again.');
      setIsSubmitting(false);
    }
  };

  const handleShare = (platform: string) => {
    const url = window.location.origin;
    const text = 'Check out Tru8 for instant fact verification with dated evidence';

    const shareUrls: Record<string, string> = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      instagram: url,
      youtube: url,
      message: `sms:?&body=${encodeURIComponent(text + ' ' + url)}`,
    };

    const shareUrl = shareUrls[platform];
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
    }
  };

  return (
    <div className="space-y-12">
      <PageHeader
        title="Create New Claim Check"
        subtitle="Submit claims, URLs, or articles for instant verification"
        graphic={<PrismGraphic />}
      />

      {/* Submit Content Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8">
        <div className="mb-6">
          <h3 className="text-xl font-bold text-white mb-2">Submit Content</h3>
          <p className="text-slate-400">Enter a URL or paste text to verify claims and check facts</p>
        </div>

        {/* Tab Selector */}
        <div className="flex gap-6 border-b border-slate-700 mb-6">
          <button
            onClick={() => setActiveTab('url')}
            className={`pb-2 font-bold uppercase text-sm transition-colors ${
              activeTab === 'url'
                ? 'text-[#f57a07] border-b-2 border-[#f57a07]'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            URL
          </button>
          <button
            onClick={() => setActiveTab('text')}
            className={`pb-2 font-bold uppercase text-sm transition-colors ${
              activeTab === 'text'
                ? 'text-[#f57a07] border-b-2 border-[#f57a07]'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            TEXT
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {activeTab === 'url' ? (
            <div>
              <label htmlFor="url-input" className="block text-sm font-semibold text-white mb-2">
                Website URL
              </label>
              <input
                id="url-input"
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors"
                disabled={isSubmitting}
              />
              <p className="text-sm text-slate-400 mt-2">
                Enter the URL of an article, blog post, or webpage to verify
              </p>
            </div>
          ) : (
            <div>
              <label htmlFor="text-input" className="block text-sm font-semibold text-white mb-2">
                Text Content
              </label>
              <textarea
                id="text-input"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste or type the text you want to fact-check..."
                rows={8}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-500 focus:border-[#f57a07] focus:outline-none transition-colors resize-vertical"
                disabled={isSubmitting}
              />
              <div className="flex items-center justify-between mt-2">
                <p className="text-sm text-slate-400">
                  Enter text containing claims you want to verify
                </p>
                <p className="text-sm text-slate-400">
                  {textInput.length} / 5000 characters
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-900/30 border border-red-600 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-[#f57a07] hover:bg-[#e06a00] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all"
          >
            {isSubmitting ? 'PROCESSING...' : 'START FACT CHECK'}
          </button>
        </form>
      </div>

      {/* Share Your Results Card */}
      <div className="bg-[#1a1f2e] border border-slate-700 rounded-xl p-8 text-center">
        <h3 className="text-2xl font-bold text-white mb-3">Share Your Results</h3>
        <p className="text-slate-300 max-w-2xl mx-auto mb-6">
          Once your fact-check is complete, share the verified results with your network to help combat misinformation
        </p>

        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => handleShare('facebook')}
            className="bg-slate-800 hover:bg-slate-700 p-3 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Share on Facebook"
          >
            <Facebook size={24} />
          </button>
          <button
            onClick={() => handleShare('instagram')}
            className="bg-slate-800 hover:bg-slate-700 p-3 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Share on Instagram"
          >
            <Instagram size={24} />
          </button>
          <button
            onClick={() => handleShare('twitter')}
            className="bg-slate-800 hover:bg-slate-700 p-3 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Share on Twitter"
          >
            <Twitter size={24} />
          </button>
          <button
            onClick={() => handleShare('youtube')}
            className="bg-slate-800 hover:bg-slate-700 p-3 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Share on YouTube"
          >
            <Youtube size={24} />
          </button>
          <button
            onClick={() => handleShare('message')}
            className="bg-slate-800 hover:bg-slate-700 p-3 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Share via Message"
          >
            <MessageCircle size={24} />
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## **NEW COMPONENTS**

### **1. PrismGraphic Component**
**File:** `web/app/dashboard/components/prism-graphic.tsx`

```typescript
import Image from 'next/image';

export function PrismGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/prism.png"
        alt="Prism"
        fill
        className="object-contain"
      />
    </div>
  );
}
```

---

## **UTILITY FUNCTIONS**

### **URL Validation**
**File:** `web/lib/utils.ts` (add to existing)

```typescript
export function isValidUrl(string: string): boolean {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}
```

---

## **REUSABLE COMPONENTS**

### **From Existing Code**
1. ✅ **`<PageHeader />`** - Already created in PLAN_02

### **New Components**
2. ✅ **`<PrismGraphic />`** - Created for this page

---

## **ZERO DUPLICATION STRATEGY**

- PageHeader reused from Dashboard
- Social share logic reused from PLAN_02 (GAP #6 resolution)
- Form styling matches Settings page inputs
- Button styling matches primary buttons throughout app

---

## **GAP RESOLUTIONS**

### **✅ GAP #12 RESOLVED: Input Type Support**
**Issue:** Backend supports 4 types, screenshot shows 2

**DECISION APPROVED:** ✅ URL + TEXT only for MVP

**Backend Input Types:**
- `url` ✅ MVP
- `text` ✅ MVP
- `image` ❌ Phase 2
- `video` ❌ Phase 2

**Implementation:**
- New Check page will have 2 tabs: URL and TEXT
- IMAGE and VIDEO tabs deferred to Phase 2
- Backend already supports all 4 types (no changes needed)

**Rationale:**
- Simpler UX for MVP launch
- Faster development cycle
- Focus on core fact-checking functionality
- Can add IMAGE/VIDEO after MVP user validation

**Phase 2 Enhancement:**
- Add IMAGE tab with file upload + preview
- Add VIDEO tab with URL input or file upload
- Implement file validation (size, format)

---

### **✅ GAP #13 RESOLVED: Text Length Limits**
**Issue:** No documented backend validation for text input length

**DECISION APPROVED:** ✅ Min: 10 characters, Max: 5,000 characters

**Implementation:**
```typescript
const MAX_LENGTH = 5000;
const MIN_LENGTH = 10;

// Validation
if (textInput.length < MIN_LENGTH) {
  setError(`Minimum ${MIN_LENGTH} characters required`);
}
if (textInput.length > MAX_LENGTH) {
  setError(`Maximum ${MAX_LENGTH} characters exceeded`);
}
```

**UI Display:**
- Character counter: "2,450 / 5,000 characters"
- Real-time validation as user types
- Error message if limits exceeded

**Backend Alignment:**
- Backend should validate same limits (10-5000 chars)
- Return 400 error if limits exceeded
- File: `backend/app/api/v1/checks.py:23-44`

---

## **IMPLEMENTATION CHECKLIST**

### **Phase 1: Components**
- [ ] Create PrismGraphic component
- [ ] Create isValidUrl utility function

### **Phase 2: Form**
- [ ] Create tab selector (URL/TEXT)
- [ ] Implement URL input with validation
- [ ] Implement TEXT textarea with character count
- [ ] Add form validation
- [ ] Handle submit with loading state

### **Phase 3: Integration**
- [ ] Connect to API createCheck endpoint
- [ ] Handle success (redirect to check detail)
- [ ] Handle errors (display error message)
- [ ] Check credits before submission

### **Phase 4: Social Share**
- [ ] Implement Share Your Results card
- [ ] Add social icons
- [ ] Connect to Web Share API

### **Phase 5: Polish**
- [ ] Add error messages
- [ ] Add loading states
- [ ] Test URL validation
- [ ] Test TEXT validation
- [ ] Test form submission
- [ ] Test mobile responsiveness

---

## **TESTING SCENARIOS**

### **URL Tab**
1. **Valid URL:** Accepts and submits
2. **Invalid URL:** Shows error "Please enter a valid URL"
3. **Empty URL:** Shows error "Please enter a URL"
4. **HTTP URL:** Accepts (backend may redirect to HTTPS)
5. **HTTPS URL:** Accepts

### **TEXT Tab**
1. **Valid text (>10 chars):** Accepts and submits
2. **Too short (<10 chars):** Shows error
3. **Too long (>5000 chars):** Shows error
4. **Empty text:** Shows error
5. **Character counter:** Updates in real-time

### **Form Submission**
1. **Success:** Redirects to `/dashboard/check/{id}`
2. **No credits:** Shows error "No credits remaining..."
3. **Network error:** Shows error "Failed to create check..."
4. **Loading state:** Button shows "PROCESSING..."
5. **After submission:** Form disabled, button disabled

### **Social Share**
1. **Facebook click:** Opens Facebook share dialog
2. **Twitter click:** Opens Twitter share dialog
3. **Other platforms:** Open appropriate dialogs
4. **Mobile:** Uses native share if available

---

## **DEPENDENCIES**

- ✅ Layout complete (provides navigation)
- ✅ PageHeader component available
- ✅ Backend `/checks` endpoint functional
- ✅ API client `createCheck()` method available

---

## **NOTES**

- Client-side validation runs before API call (fast feedback)
- Backend validation is final authority (security)
- Redirect to check detail page shows real-time progress
- Social share is informational (shares generic Tru8 info)
- After check completes, user can share specific result
- IMAGE and VIDEO tabs deferred to Phase 2 (NEW GAP #12)
