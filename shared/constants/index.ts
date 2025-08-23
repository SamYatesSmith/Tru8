// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_VERSION = 'v1';

// Colors
export const COLORS = {
  // Brand
  darkIndigo: '#2C2C54',
  deepPurpleGrey: '#474787',
  coolGrey: '#AAABB8',
  lightGrey: '#ECECEC',
  
  // Semantic
  supported: '#1E6F3D',
  contradicted: '#B3261E',
  uncertain: '#A15C00',
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