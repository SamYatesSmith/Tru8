# Tru8 Frontend-Backend Integration Guide

## Executive Summary

This document outlines all integration points, data structures, API endpoints, and technical requirements needed to connect the Tru8 frontend (built with Next.js 15, React 19, TypeScript, and Tailwind CSS) to your existing backend infrastructure.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Integration Points](#api-integration-points)
3. [Data Models & TypeScript Interfaces](#data-models--typescript-interfaces)
4. [Authentication & Authorization](#authentication--authorization)
5. [Environment Variables](#environment-variables)
6. [API Endpoints Required](#api-endpoints-required)
7. [WebSocket/Real-time Requirements](#websocketreal-time-requirements)
8. [File Upload & Storage](#file-upload--storage)
9. [Payment Integration](#payment-integration)
10. [Error Handling & Validation](#error-handling--validation)
11. [Testing Considerations](#testing-considerations)
12. [Deployment Checklist](#deployment-checklist)

---

## 1. Architecture Overview

### Frontend Stack
- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS v4
- **Component Library**: shadcn/ui
- **Type Safety**: TypeScript
- **State Management**: React hooks + SWR (recommended for data fetching)
- **Date Handling**: date-fns
- **API Client**: Native fetch API with custom wrapper

### Current API Configuration
\`\`\`typescript
// lib/api.ts
export const API_BASE_URL = "https://api.tru8.ai/api/v1"
\`\`\`

### Key Frontend Routes
\`\`\`
Public Routes:
- / (Landing page)

Protected Routes (require authentication):
- /dashboard (User dashboard)
- /checks (Fact-check history)
- /checks/new (Create new check)
- /checks/[id] (View check results)
- /settings (User settings with tabs: account, subscription, notifications)
\`\`\`

---

## 2. API Integration Points

### Current Implementation
The frontend uses a centralized API client in `lib/api.ts`:

\`\`\`typescript
export async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`)
  }

  return response.json()
}
\`\`\`

### Required Enhancements
You'll need to add:
1. **Authentication token injection** in headers
2. **Refresh token logic** for expired sessions
3. **Request/response interceptors** for logging
4. **Retry logic** for failed requests
5. **CORS configuration** on backend

---

## 3. Data Models & TypeScript Interfaces

### User Model
\`\`\`typescript
interface User {
  id: string
  email: string
  fullName: string
  initials: string
  avatar?: string
  plan: "free" | "professional"
  createdAt: string // ISO 8601
  updatedAt: string // ISO 8601
}
\`\`\`

### Check/Verification Model
\`\`\`typescript
interface Check {
  id: string
  userId: string
  status: "processing" | "completed" | "failed"
  verdict: "supported" | "contradicted" | "uncertain"
  confidence: number // 0-1 (e.g., 0.85 = 85%)
  summary: string
  inputType: "url" | "text" | "image" | "video"
  content?: string // Original text content
  url?: string // Original URL if inputType is "url"
  evidence: Evidence[]
  createdAt: string // ISO 8601
  updatedAt: string // ISO 8601
  processingTime?: number // milliseconds
}
\`\`\`

### Evidence Model
\`\`\`typescript
interface Evidence {
  id?: string
  source: string // e.g., "Reuters"
  publisher: string // e.g., "Reuters News Agency"
  date: string // ISO 8601
  relevance: number // 0-1 (how relevant to the claim)
  credibility: number // 0-1 (source credibility score)
  snippet: string // Excerpt from the source
  url?: string // Link to the source
  metadata?: {
    author?: string
    publicationType?: string
    [key: string]: any
  }
}
\`\`\`

### Subscription Model
\`\`\`typescript
interface Subscription {
  id: string
  userId: string
  plan: "free" | "professional"
  status: "active" | "cancelled" | "expired" | "trial"
  checksLimit: number // e.g., 5 for free, 40 for professional
  checksUsed: number // Current month usage
  billingCycle: "monthly" | "yearly"
  currentPeriodStart: string // ISO 8601
  currentPeriodEnd: string // ISO 8601
  cancelAtPeriodEnd: boolean
  stripeCustomerId?: string
  stripeSubscriptionId?: string
}
\`\`\`

### Notification Settings Model
\`\`\`typescript
interface NotificationSettings {
  userId: string
  emailNotifications: {
    checkComplete: boolean
    weeklyDigest: boolean
    productUpdates: boolean
    securityAlerts: boolean
  }
  pushNotifications?: {
    checkComplete: boolean
    weeklyDigest: boolean
  }
}
\`\`\`

---

## 4. Authentication & Authorization

### Current State
- Frontend has **placeholder authentication** (no real auth implemented)
- Sign out button exists but only redirects to homepage
- User data is hardcoded in components

### Required Backend Implementation

#### Authentication Flow
1. **Sign Up**: `POST /auth/signup`
   \`\`\`json
   Request:
   {
     "email": "user@example.com",
     "password": "securePassword123",
     "fullName": "John Doe"
   }
   
   Response:
   {
     "user": { ...User },
     "accessToken": "jwt_token",
     "refreshToken": "refresh_token"
   }
   \`\`\`

2. **Sign In**: `POST /auth/signin`
   \`\`\`json
   Request:
   {
     "email": "user@example.com",
     "password": "securePassword123"
   }
   
   Response:
   {
     "user": { ...User },
     "accessToken": "jwt_token",
     "refreshToken": "refresh_token"
   }
   \`\`\`

3. **Sign Out**: `POST /auth/signout`
   \`\`\`json
   Request:
   {
     "refreshToken": "refresh_token"
   }
   
   Response:
   {
     "success": true
   }
   \`\`\`

4. **Refresh Token**: `POST /auth/refresh`
   \`\`\`json
   Request:
   {
     "refreshToken": "refresh_token"
   }
   
   Response:
   {
     "accessToken": "new_jwt_token",
     "refreshToken": "new_refresh_token"
   }
   \`\`\`

5. **Get Current User**: `GET /auth/me`
   \`\`\`json
   Headers:
   {
     "Authorization": "Bearer jwt_token"
   }
   
   Response:
   {
     "user": { ...User }
   }
   \`\`\`

#### Token Storage
- Store `accessToken` in memory (React state/context)
- Store `refreshToken` in httpOnly cookie (recommended) or localStorage
- Include `Authorization: Bearer {accessToken}` header in all authenticated requests

#### Protected Routes
All routes under `/dashboard`, `/checks`, `/settings` require authentication.

Frontend will need middleware to:
- Check for valid token
- Redirect to login if unauthenticated
- Refresh token if expired

---

## 5. Environment Variables

### Required Environment Variables

\`\`\`bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://api.tru8.ai/api/v1

# Authentication (if using third-party auth)
NEXT_PUBLIC_AUTH_DOMAIN=your-auth-domain.com
AUTH_SECRET=your-secret-key

# Stripe (for payments)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Analytics (optional)
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX

# Feature Flags (optional)
NEXT_PUBLIC_ENABLE_WEBSOCKETS=true
NEXT_PUBLIC_ENABLE_FILE_UPLOAD=true
\`\`\`

### Backend CORS Configuration
Ensure your backend allows requests from:
- `http://localhost:3000` (development)
- `https://yourdomain.com` (production)
- `https://preview-*.vercel.app` (Vercel preview deployments)

---

## 6. API Endpoints Required

### User Endpoints

#### Get User Profile
\`\`\`
GET /users/me
Authorization: Bearer {token}

Response: 200 OK
{
  "user": { ...User }
}
\`\`\`

#### Update User Profile
\`\`\`
PATCH /users/me
Authorization: Bearer {token}

Request:
{
  "fullName": "Updated Name",
  "email": "newemail@example.com"
}

Response: 200 OK
{
  "user": { ...User }
}
\`\`\`

---

### Check/Verification Endpoints

#### Create New Check
\`\`\`
POST /checks
Authorization: Bearer {token}

Request:
{
  "inputType": "url" | "text",
  "content": "Text to verify" | null,
  "url": "https://example.com/article" | null
}

Response: 201 Created
{
  "check": {
    "id": "check_123",
    "status": "processing",
    ...Check
  }
}
\`\`\`

**Frontend Location**: `components/checks/new-check-form.tsx` (line 23-30)

#### Get Check by ID
\`\`\`
GET /checks/:id
Authorization: Bearer {token}

Response: 200 OK
{
  "check": { ...Check }
}
\`\`\`

**Frontend Location**: `components/checks/check-results.tsx` (line 44-82)

#### List User Checks
\`\`\`
GET /checks
Authorization: Bearer {token}
Query Parameters:
  - page: number (default: 1)
  - limit: number (default: 10)
  - status: "processing" | "completed" | "failed" | "all"
  - verdict: "supported" | "contradicted" | "uncertain" | "all"
  - search: string (optional)

Response: 200 OK
{
  "checks": [ ...Check[] ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 45,
    "totalPages": 5
  }
}
\`\`\`

**Frontend Location**: `components/checks/check-history.tsx` (line 15-35)

#### Delete Check
\`\`\`
DELETE /checks/:id
Authorization: Bearer {token}

Response: 204 No Content
\`\`\`

---

### Subscription Endpoints

#### Get User Subscription
\`\`\`
GET /subscriptions/me
Authorization: Bearer {token}

Response: 200 OK
{
  "subscription": { ...Subscription }
}
\`\`\`

**Frontend Location**: `components/settings/subscription-settings.tsx` (line 48-52)

#### Get Usage Statistics
\`\`\`
GET /subscriptions/usage
Authorization: Bearer {token}

Response: 200 OK
{
  "checksUsed": 15,
  "checksLimit": 40,
  "usagePercentage": 37.5,
  "periodStart": "2024-01-01T00:00:00Z",
  "periodEnd": "2024-01-31T23:59:59Z"
}
\`\`\`

**Frontend Location**: `components/dashboard/dashboard-content.tsx` (line 13-17)

#### Create Checkout Session (Stripe)
\`\`\`
POST /subscriptions/checkout
Authorization: Bearer {token}

Request:
{
  "plan": "professional",
  "billingCycle": "monthly"
}

Response: 200 OK
{
  "sessionId": "cs_test_...",
  "url": "https://checkout.stripe.com/..."
}
\`\`\`

#### Cancel Subscription
\`\`\`
POST /subscriptions/cancel
Authorization: Bearer {token}

Response: 200 OK
{
  "subscription": { ...Subscription }
}
\`\`\`

---

### Notification Settings Endpoints

#### Get Notification Settings
\`\`\`
GET /settings/notifications
Authorization: Bearer {token}

Response: 200 OK
{
  "settings": { ...NotificationSettings }
}
\`\`\`

**Frontend Location**: `components/settings/notification-settings.tsx`

#### Update Notification Settings
\`\`\`
PATCH /settings/notifications
Authorization: Bearer {token}

Request:
{
  "emailNotifications": {
    "checkComplete": true,
    "weeklyDigest": false
  }
}

Response: 200 OK
{
  "settings": { ...NotificationSettings }
}
\`\`\`

---

## 7. WebSocket/Real-time Requirements

### Check Processing Updates
When a user submits a check, the processing can take 10-60 seconds. Real-time updates improve UX.

#### WebSocket Connection
\`\`\`
ws://api.tru8.ai/ws?token={jwt_token}
\`\`\`

#### Events to Emit (Server → Client)

1. **Check Status Update**
\`\`\`json
{
  "event": "check:status",
  "data": {
    "checkId": "check_123",
    "status": "processing",
    "progress": 45 // percentage
  }
}
\`\`\`

2. **Check Completed**
\`\`\`json
{
  "event": "check:completed",
  "data": {
    "checkId": "check_123",
    "check": { ...Check }
  }
}
\`\`\`

3. **Check Failed**
\`\`\`json
{
  "event": "check:failed",
  "data": {
    "checkId": "check_123",
    "error": "Failed to process URL"
  }
}
\`\`\`

**Frontend Implementation Location**: 
- Add WebSocket hook in `hooks/use-websocket.ts`
- Integrate in `components/checks/progress-tracker.tsx`

---

## 8. File Upload & Storage

### Future Feature: Image/Video Verification
Currently not implemented, but the data model supports it (`inputType: "image" | "video"`).

#### Upload Endpoint (Future)
\`\`\`
POST /uploads
Authorization: Bearer {token}
Content-Type: multipart/form-data

Request:
{
  "file": <binary>,
  "type": "image" | "video"
}

Response: 200 OK
{
  "url": "https://cdn.tru8.ai/uploads/abc123.jpg",
  "fileId": "file_123"
}
\`\`\`

---

## 9. Payment Integration

### Stripe Integration
The frontend expects Stripe for payment processing.

#### Required Stripe Setup
1. Create Stripe products for:
   - Free Plan (£0/month)
   - Professional Plan (£7/month)

2. Configure Stripe webhook endpoint: `POST /webhooks/stripe`

3. Handle webhook events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

#### Frontend Stripe Flow
1. User clicks "Upgrade to Professional"
2. Frontend calls `POST /subscriptions/checkout`
3. Backend creates Stripe checkout session
4. Frontend redirects to Stripe checkout URL
5. After payment, Stripe redirects back to `/settings?tab=subscription&success=true`
6. Webhook updates subscription in database

**Frontend Location**: `components/settings/subscription-settings.tsx` (line 142)

---

## 10. Error Handling & Validation

### Expected Error Response Format
\`\`\`json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      }
    ]
  }
}
\`\`\`

### HTTP Status Codes
- `200 OK`: Successful GET/PATCH/DELETE
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE with no response body
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Duplicate resource (e.g., email already exists)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Frontend Error Handling
Currently implemented in:
- `lib/api.ts` (basic error throwing)
- Individual components (local error state)

**Needs Enhancement**:
- Global error boundary
- Toast notifications for errors
- Retry logic for failed requests

---

## 11. Testing Considerations

### API Mocking for Development
Currently, the frontend uses **hardcoded mock data** in components:
- `components/checks/check-results.tsx` (line 48-82)
- `components/checks/check-history.tsx` (line 15-35)
- `components/dashboard/dashboard-content.tsx` (line 13-17)

### Testing Strategy
1. **Unit Tests**: Test individual components with mocked API responses
2. **Integration Tests**: Test API client with mock server (MSW recommended)
3. **E2E Tests**: Test full user flows with Playwright/Cypress

### Mock Data Examples
See existing mock data in components for expected data structures.

---

## 12. Deployment Checklist

### Pre-Deployment
- [ ] Set all environment variables in production
- [ ] Configure CORS on backend for production domain
- [ ] Set up Stripe webhook endpoint
- [ ] Configure rate limiting on API
- [ ] Set up monitoring and logging
- [ ] Test authentication flow end-to-end
- [ ] Test payment flow with Stripe test mode
- [ ] Verify WebSocket connection works in production

### Post-Deployment
- [ ] Monitor error rates
- [ ] Check API response times
- [ ] Verify webhook delivery
- [ ] Test user sign-up flow
- [ ] Test check creation and processing
- [ ] Verify email notifications work

---

## Connection Points Summary

### Critical Integration Points (Priority 1)
1. **Authentication System** (`/auth/*` endpoints)
   - Sign up, sign in, sign out, token refresh
   - Frontend: `components/app-navigation.tsx`, `app/(app)/layout.tsx`

2. **Check Creation & Retrieval** (`/checks` endpoints)
   - Create check, get check by ID, list checks
   - Frontend: `components/checks/new-check-form.tsx`, `components/checks/check-results.tsx`, `components/checks/check-history.tsx`

3. **User Profile** (`/users/me` endpoint)
   - Get and update user profile
   - Frontend: `components/settings/account-settings.tsx`, `components/app-navigation.tsx`

### Important Integration Points (Priority 2)
4. **Subscription Management** (`/subscriptions/*` endpoints)
   - Get subscription, usage stats, create checkout session
   - Frontend: `components/settings/subscription-settings.tsx`, `components/dashboard/dashboard-content.tsx`

5. **Notification Settings** (`/settings/notifications` endpoint)
   - Get and update notification preferences
   - Frontend: `components/settings/notification-settings.tsx`

### Nice-to-Have Integration Points (Priority 3)
6. **WebSocket for Real-time Updates** (`ws://api.tru8.ai/ws`)
   - Check processing progress
   - Frontend: To be implemented in `hooks/use-websocket.ts`

7. **File Upload** (`/uploads` endpoint)
   - Future feature for image/video verification
   - Frontend: Not yet implemented

---

## Next Steps

1. **Review this document** with your backend team
2. **Implement authentication endpoints** first (critical path)
3. **Set up CORS** to allow frontend requests
4. **Implement check endpoints** (core functionality)
5. **Add WebSocket support** for real-time updates
6. **Integrate Stripe** for payments
7. **Test end-to-end** with frontend

---

## Contact & Support

For questions about frontend implementation or integration:
- Review component code in the locations specified above
- Check `lib/api.ts` for API client implementation
- All TODO comments in code indicate where backend integration is needed

**Key Files to Review**:
- `lib/api.ts` - API client
- `components/checks/new-check-form.tsx` - Check creation
- `components/checks/check-results.tsx` - Check display
- `components/checks/check-history.tsx` - Check listing
- `components/settings/*` - Settings pages
- `components/dashboard/dashboard-content.tsx` - Dashboard
- `app/(app)/layout.tsx` - Protected route layout

---

*Document Version: 1.0*  
*Last Updated: January 2025*  
*Frontend Version: Next.js 15, React 19*
