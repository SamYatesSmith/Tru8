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

// Evidence tier classification (E06)
export type EvidenceTier = 'primary' | 'reporting' | 'commentary';

// Evidence type classification (E06)
export type EvidenceType =
  | 'data'
  | 'official_statement'
  | 'news_reporting'
  | 'analysis'
  | 'opinion'
  | 'academic';

// Receipt pipeline status (E08)
// 'unmapped' added by B3 (Track N pipeline quality): items the mapper
// classified as valid evidence but did not connect to any claim element.
// Surfaced in the Librarian funnel alongside 'excluded' for retrieval
// transparency. Backend assigns this in runner._apply_post_mapping_receipts.
export type ReceiptStatus =
  | 'found'
  | 'extracted'
  | 'classified'
  | 'excluded'
  | 'unmapped'
  | 'shown';

export interface Evidence {
  id: string;
  claimId?: string; // Optional in some contexts
  evidenceId?: string; // Stable ID for cross-referencing with ClaimMap evidence_refs
  source: string; // Publisher name
  url: string;
  title: string;
  snippet: string;
  publishedDate?: string; // ISO string from backend, not Date
  // Date provenance (F2): where publishedDate came from.
  // 'page_metadata' | 'engine' | 'url_inferred_suspect' | 'api_adapter'
  // Suspect = engine date echoing a /YYYY/MM/ URL path, unconfirmed by the page.
  dateBasis?: string;
  relevanceScore: number; // 0-1 (semantic similarity)
  // Classification (E06)
  tier?: EvidenceTier;
  evidenceType?: EvidenceType;
  receiptStatus?: ReceiptStatus;
  // Corroboration (E07)
  corroborationGroupId?: number;
  corroboratingEvidenceIds?: string; // Comma-separated evidence IDs
  // Source type fields
  isFactcheck?: boolean;
  externalSourceProvider?: string;
  sourceType?: string;
  // Fact-check detail — surfaced (dashboard + public) only for a fact-check
  // confirmed to be about THIS claim (parsed + above relevance threshold).
  factcheckPublisher?: string;
  factcheckRating?: string;
  factcheckDate?: string; // ISO string
  contextBefore?: string;
  contextAfter?: string;
  // Auto-archiving (F10)
  archivedUrl?: string; // Wayback Machine archive URL
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
  stage: 'ingest' | 'extract' | 'retrieve' | 'select' | 'decompose' | 'classify' | 'analyze' | 'complete';
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

// --- Video Recommendations (E14) ---
export interface VideoRecommendation {
  id: string;
  claimId: string;
  videoId: string;
  title: string;
  description?: string;
  channelName: string;
  channelId?: string;
  publishDate?: string;
  videoUrl: string;
  thumbnailUrl?: string;
  duration?: string; // ISO 8601 e.g. "PT4M32S"
  tierLabel?: EvidenceTier;
  typeLabel?: EvidenceType;
}

export interface VideoRecommendationsResponse {
  checkId: string;
  videos: VideoRecommendation[];
}

// --- Claim Map types (Track B) ---
export type ClaimType = 'empirical' | 'definitional' | 'causal_interpretive' | 'predictive' | 'normative_flagged';
export type ElementState = 'supported' | 'disputed' | 'unresolved' | 'contextual';
export type EvidenceRelationship = 'supports' | 'challenges' | 'context';

export interface EvidenceRef {
  evidenceId: string;
  relationship: EvidenceRelationship;
}

// Mechanical, no-LLM structural summary of the evidence on ONE side
// (supports or challenges) of an element — produced by the pipeline
// (claim_map_analyzer). Describes the SOURCES, never the claim's truth.
// NOTE: snake_case keys — the API serializer passes element `basis` through
// without recursively camelCasing its nested objects.
export interface EvidenceSideStructure {
  count: number;
  distinct_domains: number;
  tier_counts: { primary: number; reporting: number; commentary: number };
  derivation: { originals: number; derivative_count: number };
}

// Per-element basis metadata. Only the fields the frontend reads are typed;
// other keys (state_derivation, *_breakdown) are present but untyped.
export interface ElementBasis {
  support_structure?: EvidenceSideStructure;
  challenge_structure?: EvidenceSideStructure;
  [key: string]: unknown;
}

export interface ClaimElement {
  elementId: string;
  description: string;
  evidenceRefs: EvidenceRef[];
  state: ElementState | null;
  uncertainty: string | null;
  bountyText?: string; // G01: User-supplied research brief
  basis?: ElementBasis; // Phase 1: support/challenge structure (echo / thin-support)
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

// --- Seeker Explore Mode ---
export interface RelatedClaimElement {
  description: string;
  state: ElementState | null;
}

export interface RelatedClaim {
  normalisedClaim: string;
  claimType: ClaimType | null;
  elements: RelatedClaimElement[];
  consensus: {
    independentChecks: number;
    stability: string;
  } | null;
  entityOverlap: string[];
}

export interface ExploreData {
  relatedClaims: RelatedClaim[];
  mode: 'gaps' | 'explore';
  explorationBasis: string;
}