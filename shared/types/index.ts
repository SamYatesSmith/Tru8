// Verdict types
export type VerdictType = 'supported' | 'contradicted' | 'uncertain';

// Check status
export type CheckStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Input types
export type InputType = 'url' | 'text' | 'image' | 'video';

// User & Auth
export interface User {
  id: string;
  email: string;
  name?: string;
  credits: number;
  subscription?: Subscription;
  createdAt: Date;
  updatedAt: Date;
}

export interface Subscription {
  id: string;
  userId: string;
  plan: 'starter' | 'pro';
  status: 'active' | 'cancelled' | 'past_due';
  currentPeriodEnd: Date;
  creditsPerMonth: number;
}

// Check & Claims - MUST match backend API responses exactly
export interface Check {
  id: string;
  inputType: InputType;
  inputContent?: any; // JSON object from backend
  inputUrl?: string;
  status: CheckStatus;
  claims?: Claim[]; // Optional - not always included
  creditsUsed: number;
  processingTimeMs?: number;
  errorMessage?: string; // Backend includes this field
  createdAt: string; // ISO string from backend, not Date object
  completedAt?: string; // ISO string from backend
  claimsCount?: number; // For list view
}

// For API responses that include user context
export interface CheckWithUser extends Check {
  userId: string;
}

export interface Claim {
  id: string;
  checkId: string;
  text: string;
  verdict: VerdictType;
  confidence: number; // 0-100
  rationale: string;
  evidence: Evidence[];
  position: number; // Order in the check
}

export interface Evidence {
  id: string;
  claimId?: string; // Optional in some contexts
  source: string; // Publisher name
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string; // ISO string from backend, not Date
  relevanceScore: number; // 0-1 (semantic similarity)
  credibilityScore?: number; // 0-1 (source trustworthiness)
}

// API Requests
export interface CreateCheckRequest {
  inputType: InputType;
  content?: string; // For text input
  url?: string; // For URL input
  file?: File; // For image/video upload
}

// API Responses - Match backend exactly
export interface CreateCheckResponse {
  check: {
    id: string;
    status: CheckStatus;
    inputType: InputType;
    createdAt: string;
    creditsUsed: number;
  };
  remainingCredits: number;
  taskId: string;
}

export interface CheckListResponse {
  checks: Check[];
  total: number;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  name?: string;
  credits: number;
  totalCreditsUsed: number;
  subscription?: {
    plan: string;
    status: string;
    creditsPerMonth: number;
    currentPeriodEnd: string;
  };
  stats: {
    totalChecks: number;
    completedChecks: number;
    failedChecks: number;
  };
  createdAt: string;
}

export interface UserUsageResponse {
  creditsRemaining: number;
  totalCreditsUsed: number;
  subscription: {
    plan: string;
    creditsPerMonth: number;
    resetDate?: string;
  };
}

// Type aliases for cleaner imports
export type UserProfile = UserProfileResponse;
export type UserUsage = UserUsageResponse;

// Pipeline stages
export interface PipelineProgress {
  checkId: string;
  stage: 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'complete';
  progress: number; // 0-100
  message?: string;
}

// Errors
export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, any>;
  statusCode: number;
}