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
  starter: {
    name: 'Starter',
    price: 6.99,
    currency: 'GBP',
    creditsPerMonth: 120,
    features: ['Quick checks', 'Email support'],
  },
  pro: {
    name: 'Pro',
    price: 12.99,
    currency: 'GBP',
    creditsPerMonth: 300,
    features: ['Quick checks', 'Deep mode (coming soon)', 'Priority support'],
  },
} as const;

// Credit costs
export const CREDIT_COSTS = {
  quick: 1,
  deep: 3, // Hidden for MVP
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
} as const;

// Verdict icons
export const VERDICT_ICONS = {
  supported: '✓',
  contradicted: '!',
  uncertain: '?',
} as const;