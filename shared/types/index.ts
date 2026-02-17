// Check status
export type CheckStatus = 'pending' | 'processing' | 'waiting_for_selection' | 'completed' | 'failed';

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
  entryMode?: string; // 'focused' or 'article'
  selectedClaimsCount?: number; // Article mode: claims selected for full analysis
  // Real-time progress fields (for polling fallback when SSE unavailable)
  currentStage?: string; // Current pipeline stage: ingest, extract, retrieve, select, decompose, analyze, complete
  progress?: number; // Progress percentage 0-100
  progressMessage?: string; // User-friendly progress message
}

// For API responses that include user context
export interface CheckWithUser extends Check {
  userId: string;
}

export interface Claim {
  id: string;
  checkId: string;
  text: string;
  evidence: Evidence[];
  position: number; // Order in the check
  sourcesReviewedCount?: number; // Total sources reviewed (for "View sources" link when none displayed)
  claimMap?: ClaimMap; // Full ClaimMap object (detail/public endpoints)
  claimType?: ClaimType; // 5-way taxonomy from decomposition
  isSelected?: boolean; // Article mode: selected for full analysis
  significanceRank?: number; // Article mode: position in significance ranking
  significanceScore?: number; // Article mode: significance score from ranking
}

export interface Evidence {
  id: string;
  claimId?: string; // Optional in some contexts
  evidenceId?: string; // Stable ID for cross-referencing with ClaimMap evidence_refs
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
  periodCreditsUsed: number;  // Monthly for subscribers, lifetime for trial
  creditsPerPeriod: number;   // Monthly limit for subscribers, trial limit for free
  isTrial: boolean;           // True if user is on free trial (not subscriber)
  subscription: {
    plan: string;             // 'free_trial', 'starter', 'pro', etc.
    creditsPerMonth?: number | null;  // null for trial users
    trialCredits?: number;    // Only present for trial users
    resetDate?: string | null;
    periodStart?: string | null;
  };
}

// Type aliases for cleaner imports
export type UserProfile = UserProfileResponse;
export type UserUsage = UserUsageResponse;

// Pipeline stages
export interface PipelineProgress {
  checkId: string;
  stage: 'ingest' | 'extract' | 'retrieve' | 'select' | 'decompose' | 'analyze' | 'complete';
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

// --- Claim Map types (Track B) ---
export type ClaimType = 'empirical' | 'definitional' | 'causal_interpretive' | 'predictive' | 'normative_flagged';
export type ElementState = 'supported' | 'disputed' | 'unresolved';
export type EvidenceRelationship = 'supports' | 'challenges' | 'context';

export interface EvidenceRef {
  evidenceId: string;
  relationship: EvidenceRelationship;
}

export interface ClaimElement {
  elementId: string;
  description: string;
  evidenceRefs: EvidenceRef[];
  state: ElementState | null;
  uncertainty: string | null;
}

export interface ClaimMap {
  claimId: string;
  normalisedClaim: string;
  claimType: ClaimType;
  elements: ClaimElement[];
  orientation: string | null;
  metadata: {
    decompositionModel: string;
    mappingModel: string | null;
    elementCount: number;
    completedAt: string | null;
  };
}