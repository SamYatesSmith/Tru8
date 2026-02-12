// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_VERSION = 'v1';

// Colors - MUST match DESIGN_SYSTEM.md exactly
export const COLORS = {
  // Primary brand colors
  primary: '#1E40AF',
  primaryLight: '#3B82F6',
  primaryDark: '#1E3A8A',
  
  // Semantic verdict colors - HIGH CONTRAST
  verdictSupported: '#059669',      // Emerald Green
  verdictContradicted: '#DC2626',   // Strong Red
  verdictUncertain: '#D97706',      // Warning Amber
  
  // Verdict backgrounds
  verdictSupportedBg: '#ECFDF5',
  verdictSupportedBorder: '#A7F3D0',
  verdictContradictedBg: '#FEF2F2',
  verdictContradictedBorder: '#FECACA',
  verdictUncertainBg: '#FFFBEB',
  verdictUncertainBorder: '#FDE68A',
  
  // Neutral palette
  gray900: '#111827',
  gray800: '#1F2937',
  gray700: '#374151',
  gray600: '#4B5563',
  gray500: '#6B7280',
  gray400: '#9CA3AF',
  gray300: '#D1D5DB',
  gray200: '#E5E7EB',
  gray100: '#F3F4F6',
  gray50: '#F9FAFB',
  white: '#FFFFFF',
} as const;

// Limits
export const LIMITS = {
  maxClaimsPerCheck: 12,
  maxInputLength: 2500, // words
  maxVideoLength: 8 * 60, // 8 minutes in seconds
  maxImageSize: 6 * 1024 * 1024, // 6MB in bytes
  pipelineTimeout: 10000, // 10 seconds in ms
} as const;

// Plans
export const PLANS = {
  free_trial: {
    name: 'Free Trial',
    price: 0,
    currency: 'GBP',
    trialCredits: 3,  // One-time trial, not monthly
    features: ['Fact-checking', 'Standard support'],
  },
  professional: {
    name: 'Professional',
    price: 7,
    currency: 'GBP',
    creditsPerMonth: 40,
    features: ['Fact-checking', 'URL verification', 'Export to PDF/JSON/CSV', 'Priority support'],
  },
} as const;

// Credit costs
export const CREDIT_COSTS = {
  standard: 1,
} as const;

// Feature flags
export const FEATURES = {
  deepMode: false,
  reverseImageSearch: false,
  longVideoSupport: false,
  lightTheme: false,
  localPrivacyMode: false,
} as const;

// Verdict labels
export const VERDICT_LABELS = {
  supported: 'Supported',
  contradicted: 'Contradicted',
  uncertain: 'Uncertain',
  insufficient_evidence: 'Insufficient Evidence',
  conflicting_expert_opinion: 'Conflicting Opinions',
  outdated_claim: 'Outdated',
} as const;

// Verdict icons
export const VERDICT_ICONS = {
  supported: '✓',
  contradicted: '!',
  uncertain: '?',
  insufficient_evidence: '?',
  conflicting_expert_opinion: '⚖',
  outdated_claim: '⏱',
} as const;

// Verdict type (for TypeScript)
export type VerdictType = keyof typeof VERDICT_LABELS;

// --- Claim Map constants (Track B) ---
export const ELEMENT_STATE_COLORS = {
  supported: '#22c55e',
  disputed: '#f59e0b',
  unresolved: '#94a3b8',
} as const;

export const ELEMENT_STATE_LABELS = {
  supported: 'Supported',
  disputed: 'Disputed',
  unresolved: 'Unresolved',
} as const;

export const CLAIM_TYPE_LABELS = {
  empirical: 'Empirical',
  definitional: 'Definitional',
  causal_interpretive: 'Causal / Interpretive',
  predictive: 'Predictive',
  normative_flagged: 'Normative (flagged)',
} as const;