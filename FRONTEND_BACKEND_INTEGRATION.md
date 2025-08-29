# Frontend-Backend Integration Guide
*Ensuring DRY principles and consistent naming across the full stack*

## 🎯 **Critical Integration Requirements**

### **MUST Maintain Consistency**
1. **Naming Conventions**: Frontend must match exact backend response formats
2. **Type Safety**: Shared TypeScript types ensure compile-time validation
3. **API Contracts**: Frontend calls must match backend endpoints exactly
4. **Data Transformation**: camelCase frontend ↔ snake_case backend conversion
5. **Error Handling**: Consistent error response formats across all endpoints

---

## 📡 **API Endpoint Structure**

### **Base Configuration**
```typescript
// Backend: http://localhost:8000/api/v1
// Frontend: configured in shared/constants/index.ts
const API_BASE_URL = 'http://localhost:8000';
const API_VERSION = 'v1';
```

### **Authentication**
- **Method**: Clerk JWT validation
- **Header**: `Authorization: Bearer <clerk-jwt-token>`
- **All endpoints require authentication except health checks**

---

## 🔗 **API Endpoints & Frontend Integration**

### **1. Checks Endpoints**

#### **POST /api/v1/checks** - Create New Check
**Backend Request Model:**
```python
class CreateCheckRequest(BaseModel):
    input_type: str  # 'url', 'text', 'image', 'video'
    content: Optional[str] = None
    url: Optional[str] = None
```

**Frontend TypeScript Interface:**
```typescript
interface CreateCheckRequest {
  inputType: InputType;  // Note: camelCase conversion
  content?: string;
  url?: string;
  file?: File; // For uploads (handled separately)
}
```

**Backend Response:**
```json
{
  "check": {
    "id": "uuid",
    "status": "pending",
    "inputType": "url",        // camelCase in response
    "createdAt": "2024-01-01T00:00:00Z",
    "creditsUsed": 1
  },
  "remainingCredits": 47,
  "taskId": "celery-task-id"
}
```

#### **GET /api/v1/checks** - Get Check History
**Query Parameters:**
- `skip: int = 0` (pagination)
- `limit: int = 20` (max results)

**Response Format:**
```json
{
  "checks": [
    {
      "id": "uuid",
      "inputType": "url",
      "inputUrl": "https://example.com",
      "status": "completed",
      "creditsUsed": 1,
      "processingTimeMs": 8500,
      "claimsCount": 3,
      "createdAt": "2024-01-01T00:00:00Z",
      "completedAt": "2024-01-01T00:00:10Z"
    }
  ],
  "total": 25
}
```

#### **GET /api/v1/checks/{check_id}** - Get Check Details
**Critical Response Structure:**
```json
{
  "id": "check-uuid",
  "inputType": "url",
  "inputContent": {"content": "...", "url": "..."},
  "inputUrl": "https://example.com",
  "status": "completed",
  "creditsUsed": 1,
  "processingTimeMs": 8234,
  "claims": [
    {
      "id": "claim-uuid",
      "text": "COVID-19 vaccines are 95% effective",
      "verdict": "supported",        // 'supported' | 'contradicted' | 'uncertain'
      "confidence": 87.5,           // 0-100
      "rationale": "Multiple clinical trials...",
      "position": 0,
      "evidence": [
        {
          "id": "evidence-uuid",
          "source": "BBC News",
          "url": "https://bbc.com/article",
          "title": "COVID-19 Vaccine Effectiveness Study",
          "snippet": "Clinical trial results show...",
          "publishedDate": "2024-01-01T00:00:00Z",
          "relevanceScore": 0.92     // 0-1
        }
      ]
    }
  ],
  "createdAt": "2024-01-01T00:00:00Z",
  "completedAt": "2024-01-01T00:00:10Z"
}
```

#### **GET /api/v1/checks/{check_id}/progress** - SSE Stream
**Server-Sent Events Format:**
```typescript
// Event types the frontend will receive
interface ProgressEvent {
  type: 'connected' | 'progress' | 'completed' | 'error' | 'heartbeat' | 'timeout';
  checkId: string;
  stage?: 'queued' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge';
  progress?: number; // 0-100
  message?: string;
  timestamp?: string;
  error?: string;
}
```

**Frontend EventSource Implementation:**
```typescript
const eventSource = new EventSource(`/api/v1/checks/${checkId}/progress`, {
  headers: { Authorization: `Bearer ${clerkToken}` }
});

eventSource.onmessage = (event) => {
  const data: ProgressEvent = JSON.parse(event.data);
  // Handle progress updates
};
```

### **2. User Endpoints**

#### **GET /api/v1/users/profile** - User Profile
**Response:**
```json
{
  "id": "clerk-user-id",
  "email": "user@example.com",
  "name": "John Doe",
  "credits": 47,
  "totalCreditsUsed": 23,
  "subscription": {
    "plan": "pro",
    "status": "active",
    "creditsPerMonth": 300,
    "currentPeriodEnd": "2024-02-01T00:00:00Z"
  },
  "stats": {
    "totalChecks": 23,
    "completedChecks": 21,
    "failedChecks": 2
  },
  "createdAt": "2024-01-01T00:00:00Z"
}
```

#### **GET /api/v1/users/usage** - Usage Statistics
```json
{
  "creditsRemaining": 47,
  "totalCreditsUsed": 23,
  "subscription": {
    "plan": "pro",
    "creditsPerMonth": 300,
    "resetDate": "2024-02-01T00:00:00Z"
  }
}
```

---

## 🎨 **Critical Naming Consistency Issues**

### **Backend → Frontend Transformations**

#### **1. Case Conversion**
```typescript
// Backend (snake_case) → Frontend (camelCase)
const transformations = {
  input_type: 'inputType',
  input_content: 'inputContent',
  input_url: 'inputUrl',
  credits_used: 'creditsUsed',
  processing_time_ms: 'processingTimeMs',
  created_at: 'createdAt',
  completed_at: 'completedAt',
  published_date: 'publishedDate',
  relevance_score: 'relevanceScore',
  total_credits_used: 'totalCreditsUsed',
  current_period_end: 'currentPeriodEnd'
};
```

#### **2. Verdict Values (CRITICAL)**
```typescript
// Backend and Frontend MUST use identical values:
type VerdictType = 'supported' | 'contradicted' | 'uncertain';

// These are used for:
// - Database storage
// - CSS class names (.verdict-supported)
// - Color assignments (--verdict-supported)
// - Display labels
```

#### **3. Status Values**
```typescript
// Check status - MUST match exactly
type CheckStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Pipeline stages - MUST match progress events
type PipelineStage = 'queued' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge';
```

---

## 🔧 **Shared Constants Integration**

### **MUST Update shared/constants/index.ts**
The existing constants file needs updates to match our design system:

#### **Current Issues:**
```typescript
// ❌ OLD COLORS - Don't match design system
export const COLORS = {
  supported: '#1E6F3D',      // Should be: #059669 (emerald)
  contradicted: '#B3261E',   // Should be: #DC2626 (red)  
  uncertain: '#A15C00',      // Should be: #D97706 (amber)
  darkIndigo: '#2C2C54',     // Should be replaced with CSS vars
  // Missing: tru8-primary, gradients, etc.
};
```

#### **Required Updates:**
```typescript
// ✅ NEW COLORS - Match DESIGN_SYSTEM.md
export const COLORS = {
  // Primary brand
  primary: '#1E40AF',
  primaryLight: '#3B82F6', 
  primaryDark: '#1E3A8A',
  
  // Semantic verdicts - match CSS variables
  verdictSupported: '#059669',
  verdictContradicted: '#DC2626',
  verdictUncertain: '#D97706',
  
  // Verdict backgrounds
  verdictSupportedBg: '#ECFDF5',
  verdictContradictedBg: '#FEF2F2',
  verdictUncertainBg: '#FFFBEB',
} as const;
```

---

## 🏗️ **Frontend Architecture Requirements**

### **1. API Client (lib/api.ts)**
```typescript
class ApiClient {
  private baseURL = `${API_BASE_URL}/api/${API_VERSION}`;
  
  // MUST handle Clerk authentication
  private async getAuthHeaders() {
    const token = await window.Clerk?.session?.getToken();
    return { Authorization: `Bearer ${token}` };
  }
  
  // MUST handle case conversion
  private transformResponse(data: any) {
    // Convert snake_case → camelCase
  }
  
  // MUST handle errors consistently
  private handleError(error: any) {
    // Transform backend errors to frontend format
  }
}
```

### **2. React Query Integration**
```typescript
// Query keys MUST match API endpoints
const queryKeys = {
  checks: ['checks'] as const,
  checkHistory: (skip: number, limit: number) => ['checks', 'list', skip, limit],
  check: (id: string) => ['checks', id],
  userProfile: ['users', 'profile'],
  userUsage: ['users', 'usage'],
};
```

### **3. Component Props (Type Safety)**
```typescript
// Component props MUST use shared types
interface ClaimCardProps {
  claim: Claim; // From shared/types/index.ts
  onEvidenceToggle: (claimId: string) => void;
}

interface VerdictPillProps {
  verdict: VerdictType; // Ensures type safety
  confidence: number;
  size?: 'sm' | 'md' | 'lg';
}
```

---

## 🚨 **Critical Integration Points**

### **1. File Upload Handling**
```typescript
// Backend expects multipart/form-data for images/videos
const uploadCheck = async (file: File, inputType: 'image' | 'video') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('input_type', inputType);
  
  // POST to /api/v1/checks with multipart data
};
```

### **2. Real-time Progress (SSE)**
```typescript
// MUST handle all progress event types
const handleProgressEvent = (event: ProgressEvent) => {
  switch (event.type) {
    case 'connected':
      setConnectionStatus('connected');
      break;
    case 'progress':
      setProgress({ stage: event.stage, progress: event.progress });
      break;
    case 'completed':
      navigateToResults(event.checkId);
      break;
    case 'error':
      showError(event.error);
      break;
    case 'timeout':
      showTimeout();
      break;
  }
};
```

### **3. Error Handling**
```typescript
// Backend error format
interface ApiError {
  detail: string;      // Main error message
  status_code: number; // HTTP status
  type?: string;       // Error type
}

// Frontend must transform to:
interface FrontendError {
  message: string;
  statusCode: number;
  type?: string;
}
```

### **4. Credit Management**
```typescript
// MUST track credits across all operations
const useCredits = () => {
  const { data: usage } = useQuery(queryKeys.userUsage);
  
  const reserveCredits = (amount: number) => {
    // Optimistic update before API call
  };
  
  const confirmCredits = (checkId: string) => {
    // Confirm usage after successful check
  };
};
```

---

## ✅ **Quality Assurance Checklist**

### **Before Frontend Implementation:**
- [ ] All API endpoints tested with exact request/response formats
- [ ] Shared types updated to match backend models exactly  
- [ ] Constants file updated with design system colors
- [ ] Clerk authentication flow tested
- [ ] SSE event handling verified
- [ ] Error response formats documented

### **During Implementation:**
- [ ] All API calls use shared types for type safety
- [ ] Case conversion handled correctly (snake_case ↔ camelCase)  
- [ ] Verdict values match exactly across all systems
- [ ] Credit management works optimistically
- [ ] Progress events display correct stage names
- [ ] File uploads handle multipart correctly

### **Testing Requirements:**
- [ ] E2E test: Create check → Monitor progress → View results
- [ ] Integration test: All API endpoints with authentication
- [ ] Type safety test: Shared types prevent runtime errors
- [ ] Consistency test: Verdict colors match design system
- [ ] Performance test: SSE connections handle disconnections

---

## 🎯 **Next Steps for Track B Week 1**

With this integration guide established:

1. **Update shared/constants** to match design system
2. **Create API client** with proper authentication and case conversion
3. **Set up React Query** with correct query keys
4. **Build components** using shared types exclusively  
5. **Test authentication** flow with Clerk
6. **Validate** all naming consistency before proceeding

This ensures **zero discrepancies** between frontend and backend, maintaining DRY principles and preventing integration issues.

---

*This integration guide is the source of truth for all frontend-backend communication. All implementations MUST follow these specifications exactly.*