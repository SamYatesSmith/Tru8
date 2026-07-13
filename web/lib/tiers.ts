export interface TierConfig {
  id: string;
  name: string;
  price: number | null;
  period: string | null;
  credits: number | null;
  description: string;
  features: string[];
  cta: string;
  highlighted: boolean;
  priceEnvVar?: string;
  /** Optional annual price (Console: £200/yr). */
  annualPrice?: number;
  annualPriceEnvVar?: string;
  contactUrl?: string;
  /** Retired from sale (2026-07 Console pricing) — kept so existing
   *  subscribers' current plan still renders; never offered as an upgrade. */
  retired?: boolean;
}

export const TIERS: TierConfig[] = [
  {
    id: "free",
    name: "Free Trial",
    price: 0,
    period: "lifetime",
    credits: 3,
    description: "Try Tru8 with 3 free checks",
    features: ["3 evidence checks", "All source types", "All six views"],
    cta: "Get Started",
    highlighted: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: 7,
    period: "month",
    credits: 40,
    description: "For regular research",
    features: ["40 checks per month", "All source types", "All six views", "Export reports"],
    cta: "Upgrade",
    highlighted: false,
    priceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_PRO",
    retired: true,
  },
  {
    id: "professional",
    name: "Professional",
    price: 29,
    period: "month",
    credits: 200,
    description: "High-volume evidence research",
    features: ["200 checks per month", "Full API & MCP access", "Priority processing", "Export reports"],
    cta: "Upgrade",
    highlighted: false,
    priceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER",
    retired: true,
  },
  {
    id: "console",
    name: "Tru8 Console",
    price: 20,
    period: "month",
    credits: 200,
    description: "Evidence research in the browser",
    features: [
      "200 checks per month",
      "All six views",
      "Signed records + PDF export",
      "Targeted re-search",
    ],
    cta: "Upgrade",
    highlighted: true,
    priceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE",
    annualPrice: 200,
    annualPriceEnvVar: "NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE_ANNUAL",
  },
  {
    id: "enterprise",
    name: "Teams",
    price: null,
    period: null,
    credits: null,
    description: "For teams working evidence together",
    features: ["From £75/month", "Team onboarding", "Volume pricing", "Direct support"],
    cta: "Contact Us",
    highlighted: false,
    contactUrl: "/contact",
  },
];

/** Tiers offered for purchase (retired tiers stay renderable for existing
 *  subscribers via TIERS, but are never sold). */
export function purchasableTiers(currentPlanId: string): TierConfig[] {
  return TIERS.filter((t) => !t.retired || t.id === currentPlanId);
}

/** Human price for a tier at a billing cadence.
 *
 * Console monthly (£20/mo) and annual (£200/yr) share one tier with a flat
 * `price`; the backend now reports the cadence (`billingInterval`) so we can
 * show the amount actually billed. Falls back to the monthly price when no
 * annual price exists or the interval is unknown. Returns "Custom" for
 * quote-only tiers (Teams). */
export function formatTierPrice(
  tier: TierConfig,
  interval?: 'month' | 'year' | string | null
): string {
  if (tier.price == null) return 'Custom';
  if (interval === 'year' && tier.annualPrice != null) {
    return `£${tier.annualPrice}/year`;
  }
  return `£${tier.price}/month`;
}

/** Resolve a tier's Stripe price ID.
 *
 * Next.js inlines NEXT_PUBLIC_* env vars at build time. The references
 * must be literal (not dynamic) for the compiler to replace them.
 */
export function getTierPriceId(
  tier: TierConfig,
  interval: 'month' | 'year' = 'month'
): string | null {
  const envVar = interval === 'year' ? tier.annualPriceEnvVar : tier.priceEnvVar;
  switch (envVar) {
    case 'NEXT_PUBLIC_STRIPE_PRICE_ID_PRO':
      return process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_PRO || null;
    case 'NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER':
      return process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER || null;
    case 'NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE':
      return process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE || null;
    case 'NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE_ANNUAL':
      return process.env.NEXT_PUBLIC_STRIPE_PRICE_ID_CONSOLE_ANNUAL || null;
    default:
      return null;
  }
}
