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

// Check & Claims
export interface Check {
  id: string;
  userId: string;
  inputType: InputType;
  inputContent: string;
  inputUrl?: string;
  status: CheckStatus;
  claims: Claim[];
  creditsUsed: number;
  processingTimeMs?: number;
  createdAt: Date;
  completedAt?: Date;
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
  claimId: string;
  source: string; // Publisher name
  url: string;
  title: string;
  snippet: string;
  publishedDate?: Date;
  relevanceScore: number; // 0-1
}

// API Requests
export interface CreateCheckRequest {
  inputType: InputType;
  content?: string; // For text input
  url?: string; // For URL input
  file?: File; // For image/video upload
}

export interface CheckResponse {
  check: Check;
  remainingCredits: number;
}

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